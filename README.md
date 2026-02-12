# 🔬 Clean Eating Agent — Příbram

**Biomedicínsky nákupný audit s reálnymi dátami z letákov. 100% zadarmo.**

Mobilná appka (PWA) pre iPhone, ktorá automaticky sťahuje akciové ceny z českých supermarketov, filtruje ultra-spracované potraviny a hodnotí produkty z biomedicínskeho hľadiska.

## ✅ Čo to robí

- 🔄 **Automaticky sťahuje** akcie z Kupi.cz (Lidl, Kaufland, Penny, Billa, Albert)
- 🚫 **Filtruje UPF** — žiadne uzeniny, sladkosti, chipsy, aditíva (E250, modifikovaný škrob...)
- 🔬 **Biomedicínsky audit** — mikrobióm, kardiovaskulárne, metabolizmus (score 1-10)
- 📱 **PWA na iPhone** — pridaj si na Home Screen, funguje offline
- 💰 **0 Kč prevádzka** — GitHub Pages + GitHub Actions, žiadne API

## 🚀 Rýchly štart (15 minút)

### 1. Fork/clone tento repozitár
```bash
git clone https://github.com/TVOJ-USERNAME/clean-eating-app.git
cd clean-eating-app
```

### 2. Otestuj scraper lokálne
```bash
pip install -r requirements.txt
python scraper/kupi_scraper.py --output data
```
Scraper stiahne aktuálne akcie z Kupi.cz a uloží ich do `data/products.json`.

### 3. Zapni GitHub Pages
```
GitHub → Settings → Pages → Source: Deploy from branch → main → / (root)
→ Folder: /frontend → Save
```
Tvoja appka bude na `https://TVOJ-USERNAME.github.io/clean-eating-app/frontend/`

### 4. Zapni GitHub Actions
```
GitHub → Actions → "I understand my workflows" → Enable
```
Scraper sa automaticky spúšťa:
- **Pondelok 06:00** — nové letáky Lidl
- **Streda 06:00** — nové letáky Kaufland, Billa, Albert
- **Štvrtok 06:00** — štvrtková akcia Lidl, Penny

### 5. Pridaj na iPhone
```
Safari → otvor URL stránky → Share (⬆) → Add to Home Screen → "Clean Eating"
```

**Hotovo.** Appka sa automaticky aktualizuje 3× týždenne s novými letákovými dátami.

---

## 📁 Štruktúra projektu

```
clean-eating-app/
├── .github/workflows/
│   └── scrape.yml              # Automatický CRON scraper (zadarmo)
├── scraper/
│   └── kupi_scraper.py         # Python scraper + UPF filter + scoring
├── data/
│   ├── products.json           # Aktuálne akciové produkty (generované)
│   ├── products_verified_*.json # Ručne overené dáta
│   ├── bio_audit.json          # Predpočítané biomedicínske šablóny
│   └── summary.json            # Súhrn pre dashboard (generované)
├── frontend/
│   ├── index.html              # PWA frontend (React-like vanilla JS)
│   ├── manifest.json           # PWA manifest (ikonka, farby)
│   └── sw.js                   # Service Worker (offline podpora)
├── requirements.txt
├── ARCHITECTURE.md             # Detailný popis architektúry
└── README.md
```

## 💰 Náklady

| Služba | Cena |
|--------|------|
| GitHub repo | 0 Kč |
| GitHub Actions (scraping) | 0 Kč (2000 min/mesiac free) |
| GitHub Pages (hosting) | 0 Kč |
| SSL certifikát | 0 Kč (automatický) |
| Claude API | 0 Kč (nepoužívame — audity sú predpočítané) |
| **Celkom** | **0 Kč / mesiac** |

## 🔬 Biomedicínsky audit

Každý produkt je hodnotený v 3 oblastiach (score 1-10):
- **🦠 Mikrobióm** — vplyv na črevný mikrobióm, prebiotický potenciál
- **❤️ Kardiovaskulárne** — vplyv na srdce, cievy, krvný tlak, cholesterol
- **⚡ Metabolizmus** — vplyv na energetický metabolizmus, inzulínovú citlivosť

Hodnotenia sú založené na peer-reviewed výskume a predpočítané pre 24 kategórií produktov v `data/bio_audit.json`. **Nie je to lekárske odporúčanie.**

## 🚫 UPF Filter

Automaticky vylúčené:
- Uzeniny (párky, salámy, šunka, klobásy)
- Sladkosti (čokoláda, sušienky, chipsy)
- Aditíva: E250, modifikovaný škrob, karagénan, glukózový sirup, palmový olej
- Hotové jedlá, polotovary, instantné potraviny

## ⚠️ Obmedzenia

- Dáta sú letákové ceny, nie regálové — produkt môže byť vypredaný
- Scraper beží 3×/týždeň, medzi scrapom a nákupom môže byť delay
- Zloženie nie je vždy dostupné z letákov — filter pracuje s názvom produktu
- Biomedicínsky audit je informatívny, nie lekárske odporúčanie

## 📄 Licencia

MIT — voľne použiteľné, vrátane komerčného využitia.
