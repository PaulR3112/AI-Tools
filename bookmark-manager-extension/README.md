# Bookmark Manager – Uložiť stránku (rozšírenie)

Browser rozšírenie (Manifest V3 — funguje v Chrome, Edge, Brave a ďalších Chromium prehliadačoch), ktoré doplní [bookmark-manager](../bookmark-manager) nástroj o skutočné jedno-klikové ukladanie priamo z panela nástrojov, klávesovú skratku a pravé tlačidlo myši na odkazoch.

Na rozdiel od bookmarkletu (drag & drop tlačidlo do lišty záložiek, ktorý je súčasťou samotného `index.html`) toto vyžaduje inštaláciu rozšírenia — výmenou za to dostaneš:

- **Ikonu v paneli nástrojov** — jeden klik uloží aktuálne otvorenú stránku.
- **Klávesovú skratku** — `Ctrl+Shift+S` (Mac: `Cmd+Shift+S`) uloží aktuálnu stránku bez toho, aby si siahal na myš.
- **Pravý klik → „Uložiť odkaz do Bookmark Manager"** — priamo na akomkoľvek odkaze na stránke, bez toho, aby si naň musel kliknúť.
- **Pravý klik → „Uložiť túto stránku do Bookmark Manager"** — rovnaká vec pre celú stránku, dostupné aj z kontextového menu.

## Inštalácia

1. Otvor `chrome://extensions` (alebo `edge://extensions`).
2. Zapni **Vývojársky režim / Developer mode** (prepínač vpravo hore).
3. Klikni **Načítať nezbalené / Load unpacked** a vyber tento priečinok (`bookmark-manager-extension`).
4. V zozname rozšírení nájdi „Bookmark Manager – Uložiť stránku" → **Podrobnosti / Details** → zapni **„Povoliť prístup k adresám URL súborov" / „Allow access to file URLs"**.
   - Toto je nutné, inak rozšírenie nemôže otvoriť/prepnúť tvoj lokálny `file://` súbor.
5. Klikni pravým tlačidlom na ikonu rozšírenia → **Možnosti / Options** (alebo choď na stránku rozšírenia a klikni „Podrobnosti" → „Možnosti rozšírenia"). Vlož tam presnú `file://` adresu svojho `bookmark-manager/index.html` a ulož.

Odvtedy stačí kliknúť na ikonku rozšírenia (alebo `Ctrl+Shift+S`, alebo pravý klik) a stránka/odkaz sa uloží — rozšírenie otvorí alebo prepne existujúcu kartu s tvojím Bookmark Managerom, kde sa rovno predvyplní URL a názov (rovnaký mechanizmus ako bookmarklet — `?add=...&title=...`).

## Ako to funguje

Rozšírenie si iba pamätá cestu k tvojmu lokálnemu súboru (uloženú cez `chrome.storage.local`) a pri kliknutí/skratke/kontext-menu otvorí danú stránku s parametrami `?add=<url>&title=<title>`. Samotný `bookmark-manager/index.html` už tieto parametre spracováva (rovnaká logika ako pri bookmarklete) — rozšírenie teda nemusí nič zapisovať priamo do `localStorage` inej stránky (čo by ani nebolo možné, keďže `file://` stránky majú vlastný izolovaný pôvod/origin).

## Poznámky

- Toto rozšírenie nie je publikované v Chrome Web Store — je určené na lokálne použitie cez „Load unpacked". Ak by si ho chcel niekedy zdieľať s inými alebo mať automatické aktualizácie, dá sa neskôr zabaliť a publikovať.
- Ak sa ti nedarí získať text odkazu pri „Uložiť odkaz" (napr. na obrázkových odkazoch bez textu), názov sa proste doplní naprázdno a appka ho pri uložení odvodí z URL.
