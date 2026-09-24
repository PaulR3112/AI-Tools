# SmartGrocery

„Čo, kde a za koľko kúpim“ naprieč supermarketmi v ČR: cena, balenie, jednotková cena
(Kč/kg, Kč/l, Kč/ks), platnosť a odkaz na zdroj. Podľa *Master Specification v0.2*.

**Stav: Fáza A = Rez 1 („prvý tok“)**: leták → extrakcia (Claude vision) → validátor → PostgreSQL → vyhľadávacie API.

## Architektúra

```
Scheduler (každých 5 min vyberie zdroje s uplynutým 30-min intervalom)
  → Fetch (ETag / Last-Modified / SHA-256) ── bez zmeny → run "unchanged"
  → Raw storage (pred spracovaním, retencia 90 dní)
  → PDF → PNG stránky (pypdfium2, 170 DPI)
  → Claude vision → JSON podľa pevnej schémy (structured outputs)
  → Deterministický validátor ── chyba → validation_events (review queue)
  → PostgreSQL: offers (immutable, unit_price = generated column)
  → REST API /v1 (service layer, ktorý neskôr použije aj MCP a /v1/ai/query)
```

| Komponent | Technológia |
|---|---|
| API | FastAPI, SQLAlchemy 2, Alembic |
| Worker + scheduler | procrastinate (fronta v PostgreSQL, žiadny Redis) |
| DB | PostgreSQL 16 + `pg_trgm`, `unaccent` |
| Extrakcia | Claude API (`claude-opus-5`), structured outputs, server-side fallbacks |
| Úložisko | lokálny disk (Azure Blob neskôr) |

## Princípy zabudované v kóde

- **Právny status pred spracovaním:** zdroj sa spracuje len pri `legal_status = approved`, inak `LegalStatusError`.
  Adaptér konkrétneho obchodu zatiaľ neexistuje; je len `manual` (ručne zadaná URL alebo lokálny súbor).
- **AI nevymýšľa cenu:** výstup modelu vždy prechádza validátorom. Sporné ponuky majú `status = review`
  a nie sú vo vyhľadávaní, kým ich neschváliš.
- **Immutable ponuky:** oprava vytvorí nový riadok a starý dostane `superseded_by`. Re-extrakcia
  vytvorí novú `flyer_version` a stará prestane byť aktuálna.
- **Idempotencia:** rovnaký `content_hash` s rovnakou `extraction_version` sa spracuje len raz (unikátny index).
- **Náklady:** každý beh zapisuje tokeny a cenu. Pri dosiahnutí `SG_LLM_DAILY_COST_LIMIT_USD` sa extrakcia zastaví.

## Spustenie (Docker)

```bash
cd smartgrocery
cp .env.example .env          # doplň ANTHROPIC_API_KEY, SG_ADMIN_TOKEN, e-mail v SG_HTTP_USER_AGENT
docker compose up -d --build  # db → migrate → api (:8000) + worker
```

Pridanie obchodu a zdroja (až po posúdení podmienok webu):

```bash
docker compose exec api smartgrocery add-store --code lidl --name Lidl --website https://www.lidl.cz
docker compose exec api smartgrocery add-source --store lidl --kind pdf \
    --url "https://…/letak.pdf" --terms-url "https://…/podminky" \
    --legal-status approved --legal-note "Podmienky posúdené 24. 9. 2026: …"
docker compose exec api smartgrocery check 1          # ihneď, inak ho worker zoberie do 30 min
```

Ak leták neobsahuje čitateľnú platnosť, zadaj ju ručne: `check 1 --valid-from 2026-09-24 --valid-to 2026-09-30`.
Re-extrakcia so zmeneným promptom alebo modelom (zvýš `SG_EXTRACTION_VERSION`): `smartgrocery reextract <raw_document_id>`.

## Spustenie lokálne (bez Dockeru)

```bash
cd smartgrocery/backend
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
export SG_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/smartgrocery
smartgrocery migrate
uvicorn app.main:app --reload
procrastinate --log-level=info --app=app.worker.app worker
```

## API v1

| Metóda | Endpoint | Účel |
|---|---|---|
| GET | `/v1/offers/search?q=&active_at=&validity=current\|today\|week\|future&store_id=&category=&price_max=&unit_price_max=&no_loyalty=&sort=relevance\|unit_price\|price` | vyhľadávanie |
| GET | `/v1/offers/{id}` | detail + podmienky + zdroj (strana, bbox) |
| GET | `/v1/stores`, `/v1/flyers`, `/v1/categories` | katalóg |
| GET | `/v1/admin/runs` | stav ingestion behov (Bearer `SG_ADMIN_TOKEN`) |
| GET/POST | `/v1/admin/review`, `/v1/admin/review/{id}` | review queue: `approve` / `reject` / `fix` |

OpenAPI: `http://localhost:8000/docs`. Poradie výsledkov: relevancia textu → aktívne dnes pred budúcimi → jednotková cena.
Vyhľadávanie ignoruje diakritiku (`mleko` → *Mléko*) a zvláda preklepy aj tvary (`tvarohu` → *Tvaroh*) cez trigramy.

## Testy

```bash
createdb smartgrocery_test
cd smartgrocery/backend && pytest -q
```

50 testov: normalizácia jednotiek, jednotková cena (Python = DB), validátor, celý tok s nahranou odpoveďou
modelu (bez API kľúča), tvar požiadavky na Claude API (mock), REST API vrátane review queue.

## Čo ešte nie je (ďalšie fázy)

- **Fáza B (Rez 2):** 3 obchody a ich adaptéry (po legal review), regression korpus 30+ stránok s metrikou ≥ 95 %, druhý kontrolný prechod na 10 % stránok, admin UI.
- **Fáza C (Rez 3):** kategórie a klasifikácia, český ispell slovník + tabuľka synoným SK→CZ, MCP server, `/v1/ai/query`.
- **Fáza D (Rez 4):** PWA (React + Vite), monitoring a alerty (Sentry), hosting (Azure Container Apps, Bicep).
