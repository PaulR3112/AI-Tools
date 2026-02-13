# 🔬 Clean Eating Agent — Kompletná 0 Kč Architektúra

## TL;DR
Celá appka beží **100% zadarmo** na GitHub Pages + GitHub Actions.
Žiadny backend, žiadne API poplatky, žiadna databáza na údržbu.
Dáta sú 100% reálne z letákov cez automatický scraping.

---

## Ako to funguje

```
┌──────────────────────────────────────────────────────────────┐
│                    GITHUB REPOSITORY                          │
│                                                               │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐ │
│  │ .github/     │    │ scraper/     │    │ data/            │ │
│  │ workflows/   │    │              │    │                  │ │
│  │ scrape.yml   │───▶│ kupi_scraper │───▶│ products.json    │ │
│  │              │    │ .py          │    │ summary.json     │ │
│  │ (CRON)       │    │              │    │ bio_audit.json   │ │
│  │ Po/St/Šv     │    │ UPF filter   │    │                  │ │
│  │ 06:00 CET    │    │ Score calc   │    │ (git commit)     │ │
│  └─────────────┘    └──────────────┘    └────────┬─────────┘ │
│                                                   │           │
│  ┌────────────────────────────────────────────────┘           │
│  │                                                            │
│  │  ┌──────────────────────────────────────────────────────┐ │
│  │  │ frontend/                                             │ │
│  │  │                                                       │ │
│  └─▶│ index.html  ← PWA (React/vanilla JS)                 │ │
│     │ manifest.json ← Ikonka na Home Screen                │ │
│     │ sw.js        ← Service Worker (offline)               │ │
│     │                                                       │ │
│     │ Číta: /data/products.json (statický fetch)            │ │
│     └──────────────────────────────────────────────────────┘ │
│                          │                                    │
│                          │ GitHub Pages                       │
└──────────────────────────┼───────────────────────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   iPhone 16 Pro  │
                  │                  │
                  │  Safari → Share  │
                  │  → Add to Home  │
                  │    Screen       │
                  │                  │
                  │  = Vyzerá ako    │
                  │    natívna app   │
                  └─────────────────┘
```

---

## Náklady: 0 Kč

| Služba | Free tier | Náš usage |
|--------|-----------|-----------|
| **GitHub repo** | Unlimited | 1 repo |
| **GitHub Actions** | 2 000 min/mesiac | ~30 min/mesiac (scraping) |
| **GitHub Pages** | 1 GB, 100K views | <10 MB, <1K views |
| **Doména** | `username.github.io` | Zadarmo |
| **SSL certifikát** | Automatický od GitHub | Zadarmo |
| **Claude API** | ❌ NEPOUŽÍVAME | 0 Kč |
| **Databáza** | ❌ NEPOUŽÍVAME | 0 Kč |
| **Hosting** | ❌ NEPOUŽÍVAME | 0 Kč |

### Prečo nepotrebujeme Claude API?
Biomedicínske audity sú **predpočítané** a uložené v `data/bio_audit.json`.
Pre ~60 Clean Eating produktov stačí vygenerovať audit raz (tu v Claudovi)
a potom ho len priradiť podľa kategórie produktu.

Nové produkty sa auditujú podľa kategóriovej šablóny:
- "Kuřecí prsa" → šablóna `poultry_breast`
- "Tvaroh polotučný" → šablóna `cottage_cheese`
- Atď.

---

## Štruktúra repozitára

```
clean-eating-app/
├── .github/
│   └── workflows/
│       └── scrape.yml          # Automatický CRON scraper
├── scraper/
│   ├── kupi_scraper.py         # Hlavný scraper
│   ├── clean_filter.py         # UPF filter + scoring
│   └── config.py               # Zoznam produktov a pravidlá
├── data/
│   ├── products.json           # Aktuálne akciové produkty
│   ├── products_meat.json      # Po kategóriách
│   ├── products_dairy.json
│   ├── products_fish.json
│   ├── products_produce.json
│   ├── products_pantry.json
│   ├── bio_audit.json          # Predpočítané biomedicínske audity
│   ├── summary.json            # Súhrn pre dashboard
│   └── archive/                # Historické dáta
│       └── 2026-02-10.json
├── frontend/
│   ├── index.html              # Hlavná PWA stránka
│   ├── manifest.json           # PWA manifest
│   ├── sw.js                   # Service Worker (offline)
│   ├── icon-192.png            # App ikona
│   └── icon-512.png
├── README.md
└── LICENSE
```

---

## Krok za krokom: Setup (15 minút)

### 1. Vytvor GitHub repozitár
```bash
# Na github.com → New Repository → "clean-eating-app"
# Alebo:
gh repo create clean-eating-app --public
```

### 2. Nahraj súbory
```bash
git clone https://github.com/TVOJ-USERNAME/clean-eating-app
cd clean-eating-app
# Skopíruj všetky súbory z tohto projektu
git add .
git commit -m "🚀 Initial commit"
git push
```

### 3. Zapni GitHub Pages
```
Settings → Pages → Source: Deploy from branch → main → /frontend
→ Save
```

### 4. Zapni GitHub Actions
```
Actions → "I understand my workflows" → Enable
```

### 5. Prvý scrape (manuálne)
```
Actions → "🔬 Clean Eating Scraper" → Run workflow → Run
```

### 6. Pridaj na iPhone
```
Safari → https://TVOJ-USERNAME.github.io/clean-eating-app
→ Share (⬆) → Add to Home Screen → "Clean Eating"
```

**HOTOVO. Zadarmo. Navždy.**

---

## Bezpečnosť a súkromie

- Žiadne osobné údaje nikde neukladáme
- Žiadne cookies, žiadny tracking
- Žiadne API kľúče (všetko je verejné)
- Scraper je šetrný (0.5s delay medzi požiadavkami)
- Open source — ktokoľvek si môže overiť kód

---

## Obmedzenia a čestné upozornenia

1. **Dáta sú tak aktuálne, ako sú letáky**
   - Scraper beží 3×/týždeň, letáky sa menia 1-2×/týždeň
   - Medzi scrapom a tvojím nákupom môže byť 0-24h delay

2. **Ceny sú letákové, nie regálové**
   - Letáková cena ≠ vždy aktuálna cena v regáli
   - Produkt môže byť vypredaný

3. **Zloženie nie je vždy dostupné**
   - Kupi.cz nemá zloženie produktov
   - Filter funguje na názve (párky, salám = ban)
   - Pre detailné zloženie → Rohlik.cz alebo OpenFoodFacts.org

4. **Biomedicínsky audit je informatívny**
   - Nie je to lekárske odporúčanie
   - Založené na peer-reviewed výskume, ale zjednodušené

---

## Budúce rozšírenia (stále zadarmo)

- [ ] Notifikácie cez Telegram Bot (zadarmo)
- [ ] Porovnanie cien s minulým týždňom (archive/)
- [ ] Nákupný zoznam s odhadovanou cenou
- [ ] Receptové prepojenie (JSON databáza receptov)
- [ ] OpenFoodFacts integrácia pre zloženie
