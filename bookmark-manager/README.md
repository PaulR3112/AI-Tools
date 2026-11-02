# Bookmark Manager

Inteligentný správca záložiek ako jediný HTML súbor — beží úplne lokálne v prehliadači, bez inštalácie, bez backendu a bez externých JS knižníc. Všetky dáta sa ukladajú do `localStorage`.

## Spustenie

Otvor `index.html` priamo v prehliadači (dvojklikom, alebo `file://` cestou). Žiadny server ani build krok nie je potrebný.

## Funkcie

- **Priečinky a tagy** — vnorené priečinky (drag & drop), viacnásobné tagy s autocomplete, farebné štítky, pripnuté záložky.
- **Inteligentné vyhľadávanie** — fulltext cez title/URL/tagy/poznámku, diakriticky necitlivé, zvýrazňovanie zhôd, `Ctrl+K` / `/` na focus.
- **Duplicity** — pri ukladaní sa kontroluje normalizovaná URL a ponúkne sa možnosť otvoriť existujúcu záložku.
- **Kontrola odkazov** — v menu „⋯“ → Skontrolovať odkazy; otestuje všetky záložky a na konci ukáže výsledok (počty + zoznam problémových). Každá skontrolovaná záložka má značku ✓ dostupný / ✕ nedostupný / ⚠️ nepodarilo sa overiť (s časom poslednej kontroly v tooltipe) a v sidebare je pohľad „Problémové odkazy". Rozlišuje „nedostupný" (reálne zlyhanie) od „nepodarilo sa overiť" (intranet/lokálna sieť/`file://`, kde to prehliadač blokuje bez ohľadu na skutočnú dostupnosť).
- **Auto-fetch title/favicon**, s inteligentným fallbackom na názov odvodený z URL cesty/domény, keď sťahovanie titulku zlyhá (CORS) — a **automatické návrhy tagov** podľa domény a kľúčových slov z názvu.
- **Najnavštevovanejšie** a **Naposledy navštívené** — sidebar sekcie triedené podľa počtu kliknutí, resp. času poslednej návštevy; počet otvorení (ikona oka) aj čas poslednej návštevy sú vždy viditeľné na každej karte/riadku.
- **Hromadné akcie** — checkbox na výber viacerých záložiek naraz (aj „Vybrať všetko"), lišta s možnosťou hromadne pridať tag, presunúť do priečinka alebo zmazať. V koši sa dajú vybrané záložky hromadne obnoviť alebo vymazať natrvalo.
- **Hromadné mazanie priečinkov** — v sidebare „Priečinky → Vybrať" zapne zaškrtávanie priečinkov; zmazanie odstráni aj ich podpriečinky, záložky v nich ostanú zachované (presunú sa mimo priečinky).
- **Bookmarklet** (Import/Export → „Rýchle uloženie z inej stránky") — tlačidlo na pretiahnutie do lišty záložiek prehliadača, ktoré z ľubovoľnej stránky rovno predvyplní URL a názov v tomto nástroji. Pre pohodlnejšie jedno-klikové ukladanie s klávesovou skratkou a pravým klikom „Uložiť odkaz" existuje aj samostatné browser rozšírenie — pozri [`../bookmark-manager-extension`](../bookmark-manager-extension).
- **Import/Export** — úplná záloha do JSON (vrátane koša), import JSON (zlúčiť/nahradiť — pri zlučovaní sa priečinky s rovnakým názvom spoja, nevznikajú duplicity), export aj import HTML formátu prehliadača (priečinky, tagy, poznámky).
- **Pripomienka zálohy** — banner, ak JSON záloha ešte nebola urobená alebo je staršia ako 7 dní.
- **Súkromie ikon** — ikony stránok sa pre intranetové/lokálne adresy (vrátane firemných domén s neverejnou koncovkou, napr. `*.vwg`) nikdy neposielajú na Google; v menu „⋯“ sa dajú externé ikony vypnúť úplne (zobrazí sa farebné písmeno).
- **Kôš** — zmazané záložky sa dajú obnoviť; staršie ako 30 dní (alebo nad 100 záznamov) sa automaticky vyčistia.
- **Tmavý režim**, **kartové zobrazenie alebo zoznam (tabuľka)**, drag & drop radenie a presúvanie medzi priečinkami.
- **Vzhľad** — jednotná sada SVG ikon (bez emoji), akcie na karte sa ukážu až po nabehnutí myšou, checkbox výberu nahradí ikonu stránky pri hoveri, pripnuté záložky sú v zbaliteľnom páse kompaktných dlaždíc, v bočnom paneli sú sekcie Zbierka / Prehľady / Priečinky / Tagy (najpoužívanejšie tagy + „ďalšie“), prázdne stavy s nápovedou a svetlý aj tmavý režim s rovnakou paletou. Zriedkavé akcie (kontrola odkazov, import/export, ikony bez Google) sú v menu „⋯“.

## Poznámky

- Auto-fetch titulku aj kontrola odkazov závisia od CORS politiky cieľových stránok — mnohé stránky ich zablokujú, vtedy appka použije fallback (názov z URL, prípadne status „nepodarilo sa overiť" namiesto „nedostupný" pre intranet/lokálne adresy).
- Dáta sú viazané na konkrétny prehliadač/zariadenie (localStorage) — pre prenos alebo zálohu použi Export/Import JSON.
