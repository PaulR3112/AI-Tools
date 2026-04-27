# 🚗 TableMaster Pro v7 - PWA Edition

Profesionálny editor tabuliek pre VW/Audi/Škoda dokumentáciu.

## 📦 Čo je v balíčku

| Súbor | Veľkosť | Popis |
|---|---|---|
| **`index.offline.html`** | 1.4 MB | **⭐ Odporúčaná verzia** - úplne offline, funguje aj bez internetu |
| `index.html` | 244 KB | Online/PWA verzia, čitateľný zdrojový kód (pre úpravy); vyžaduje internet pri prvom načítaní |
| `SPUSTIT.bat` | 2 KB | Windows - spustí appku v samostatnom okne |
| `manifest.json` | 3 KB | PWA metadata (pre PWA inštaláciu) |
| `sw.js` | 4 KB | Service Worker (pre PWA cache) |
| `README.md` | - | Tento súbor |

---

## 🚀 Rýchly štart - 3 spôsoby spustenia

### Spôsob 1: Otvoriť v prehliadači (najjednoduchšie)

1. Dvojklik na **`index.offline.html`**
2. Otvorí sa v Chrome/Edge/Firefox
3. Začnite pracovať!

✅ **Funguje aj bez internetu** (offline verzia)
✅ Žiadna inštalácia

### Spôsob 2: Spustiť ako desktop aplikáciu (Windows)

1. Dvojklik na **`SPUSTIT.bat`**
2. Otvorí sa v samostatnom okne (bez adresného riadku - vyzerá ako appka)

✅ Vyzerá ako profesionálna desktop appka
✅ Žiadna inštalácia

**Tip:** Vytvorte si **zástupcu na ploche** pre `SPUSTIT.bat`:
- Pravý klik → Odoslať → Pracovná plocha (vytvoriť zástupcu)
- Premenujte zástupcu na "TableMaster Pro"
- Pravý klik → Vlastnosti → Zmeniť ikonu (môžete použiť vlastnú)

### Spôsob 3: Inštalovať ako PWA (Progressive Web App)

Pre inštaláciu ako PWA potrebujeme HTTP server (nestačí `file://`).

#### Možnosť A: Python (ak máte nainštalované)

```bash
# Otvorte Príkazový riadok / PowerShell v adresári s aplikáciou
cd "C:\cesta\k\TableMaster_Pro_v7_PWA"

# Python 3
python -m http.server 8080
```

Potom otvorte: **http://localhost:8080/index.html**

#### Možnosť B: Node.js

```bash
npm install -g http-server
cd "C:\cesta\k\TableMaster_Pro_v7_PWA"
http-server -p 8080
```

#### Možnosť C: Bezplatný hosting

Nahrajte priečinok na:
- **Netlify Drop**: https://app.netlify.com/drop (drag & drop, 0 sekúnd)
- **Vercel**: https://vercel.com
- **GitHub Pages**: Free hosting z GitHub repo

#### Inštalácia po načítaní

1. Otvorte URL v Chrome/Edge
2. V adresnom riadku vpravo uvidíte ikonku **"⊕"** (Inštalovať)
3. Kliknite → "Inštalovať"
4. Aplikácia sa pridá do Štart menu / na plochu
5. Otvára sa v samostatnom okne ako natívna appka

✅ Vlastná ikona v Štart menu
✅ Funguje offline (po prvom načítaní)
✅ Auto-updaty pri zmene súboru

---

## 🎨 Funkcie aplikácie

### Import
- ✅ HTML, Excel (.xlsx), CSV, JSON
- ✅ Zachová **bold/italic/underline** formátovanie textu
- ✅ Zachová **farby** buniek a textu
- ✅ Automatická oprava rozostupeného textu z Excelu
- ✅ Normalizácia medzier

### Úpravy
- ✅ Editácia jednotlivých buniek (dvojklik)
- ✅ Pridanie/odstránenie riadkov a stĺpcov
- ✅ Drag & drop zoradenie riadkov
- ✅ Sort podľa stĺpca
- ✅ Filter
- ✅ **Find & Replace** s diakritiku ignorujúcim hľadaním
- ✅ Undo/Redo (Ctrl+Z / Ctrl+Y)
- ✅ Auto-save do localStorage každých 30s

### Export
- ✅ **HTML** so 6 témami (Modern, Elegant, Corporate, Minimal, Colorful, Škoda)
  - Vyhľadávanie s diakritiku ignorujúcim hľadaním + **zvýraznenie zhôd**
  - Navigácia kapitol (1.1, 3.7.4, atď.)
  - Fixovaná hlavička pri scrollovaní
- ✅ **PDF** so 6 témami + voliteľná **Cover page** (titulná strana)
  - Auto-orientation, auto-fit fontu
  - Skrytie prázdnych stĺpcov
  - A3 formát pri >10 stĺpcoch
- ✅ **Excel** s plne zachovaným formátovaním
- ✅ **CSV** (TAB / čiarka / bodkočiarka)
- ✅ **JSON** (array / object format)

### Špeciálne pre VW/Audi/Škoda
- ✅ Škoda téma so zelenou farbou (#0E3A2F + #78FAAE)
- ✅ Auto-detekcia kapitol "1.1.2.3 Názov"
- ✅ Prevod českých znakov pre PDF (helvetica nepodporuje ř/ě/ů)

---

## 💡 Tipy a triky

### Klávesové skratky

| Skratka | Funkcia |
|---|---|
| `Ctrl+O` | Otvoriť súbor |
| `Ctrl+S` | Uložiť |
| `Ctrl+F` | Find & Replace |
| `Ctrl+Z` | Späť |
| `Ctrl+Y` | Vpred |
| `Ctrl+D` | Duplikovať vybrané riadky |
| `Delete` | Vymazať vybrané riadky |
| `Esc` | Zatvoriť modálne okno |

### Obnova relácie po páde browseru

Aplikácia auto-ukladá vašu prácu každých 30 sekúnd. Ak browser spadne:
1. Otvorte aplikáciu znova
2. Hore uvidíte zelený banner "Obnoviť reláciu"
3. Klik → vaša práca sa obnoví

### Ochrana zdrojového kódu

Pre **maximálnu ochranu** pri zdieľaní kolegom:
1. Použite `index.offline.html` (knižnice sú vnorené, kód nie je ľahko čitateľný)
2. Nastavte súbor "Iba na čítanie": pravý klik → Vlastnosti → ☑ Iba na čítanie

---

## 🔧 Riešenie problémov

### "Aplikácia sa neotvorí" pri dvojkliku

- Skontrolujte default browser (Windows: Nastavenia → Aplikácie → Predvolené aplikácie)
- Skúste otvoriť cez pravý klik → Otvoriť pomocou → Chrome / Edge

### "PDF má zlé znaky" (napr. Y namiesto ř)

Toto je normálne - aplikácia automaticky nahradí ř→r, ě→e, ů→u atď. lebo PDF font (helvetica) ich nepodporuje. **Český text bude čitateľný, len bez háčikov nad e/u/r**.

### "Excel import vyzerá divne s rozostupmi"

Aplikácia automaticky opraví rozostupený text typu "V n i t ř n í" → "Vnitřní". Ak chcete zachovať originál, vypnite "Normalizácia medzier" v dialógu importu.

---

## 🖥️ Bonus: Vytvorenie .exe verzie (Electron)

Ak potrebujete **skutočnú samostatnú .exe aplikáciu** (~120 MB), tu je postup:

### Príprava
```bash
# 1. Vytvorte priečinok pre projekt
mkdir TableMaster-Electron
cd TableMaster-Electron

# 2. Inicializujte npm projekt
npm init -y

# 3. Nainštalujte Electron a builder
npm install --save-dev electron electron-builder
```

### Vytvorte `main.js`
```javascript
const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow() {
    const win = new BrowserWindow({
        width: 1400,
        height: 900,
        title: 'TableMaster Pro v7',
        icon: path.join(__dirname, 'icon.png'),
        webPreferences: { contextIsolation: true }
    });
    win.loadFile('index.html');
    win.removeMenu();
}

app.whenReady().then(() => {
    createWindow();
    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});
```

### Pridajte do `package.json`
```json
{
  "main": "main.js",
  "scripts": {
    "start": "electron .",
    "build": "electron-builder --win"
  },
  "build": {
    "appId": "com.tablemaster.pro",
    "productName": "TableMaster Pro v7",
    "win": { "target": "portable" },
    "files": ["main.js", "index.html"]
  }
}
```

### Skopírujte súbor a buildujte
```bash
# Skopírujte index.offline.html ako index.html do priečinka
cp /cesta/k/index.offline.html ./index.html

# Build .exe
npm run build

# Výsledok: dist/TableMaster Pro v7-1.0.0.exe (~120 MB)
```

Výhoda: **úplne samostatná .exe** ktorú môžete poslať komukoľvek.
Nevýhoda: 120 MB veľkosť (obsahuje celý Chromium).

---

## 📞 Kontakt a podpora

Pre otázky a feedback kontaktujte autora.

---

**TableMaster Pro v7 - PWA Edition**  
*Profesionálny editor tabuliek pre VW/Audi/Škoda technickú dokumentáciu*
