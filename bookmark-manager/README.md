# Bookmark Manager

Inteligentný správca záložiek ako jediný HTML súbor — beží úplne lokálne v prehliadači, bez inštalácie, bez backendu a bez externých JS knižníc. Všetky dáta sa ukladajú do `localStorage`.

## Spustenie

Otvor `index.html` priamo v prehliadači (dvojklikom, alebo `file://` cestou). Žiadny server ani build krok nie je potrebný.

## Funkcie

- **Priečinky a tagy** — vnorené priečinky (drag & drop), viacnásobné tagy s autocomplete, farebné štítky, pripnuté záložky.
- **Inteligentné vyhľadávanie** — fulltext cez title/URL/tagy/poznámku, diakriticky necitlivé, zvýrazňovanie zhôd, `Ctrl+K` / `/` na focus.
- **Duplicity** — pri ukladaní sa kontroluje normalizovaná URL a ponúkne sa možnosť otvoriť existujúcu záložku.
- **Kontrola mŕtvych odkazov** — manuálne tlačidlo, ktoré otestuje dostupnosť všetkých záložiek.
- **Auto-fetch title/favicon** a **automatické návrhy tagov** podľa domény a kľúčových slov z názvu.
- **Import/Export** — záloha do JSON, import JSON zálohy (zlúčiť/nahradiť), import HTML exportu záložiek z prehliadača.
- **Kôš** — zmazané záložky sa dajú obnoviť; staršie ako 30 dní (alebo nad 100 záznamov) sa automaticky vyčistia.
- **Expirácia** — dátum vypršania, badge/upozornenie, voliteľný automatický presun do koša.
- **Tmavý režim**, **kartové/kompaktné zobrazenie**, drag & drop radenie a presúvanie medzi priečinkami.

## Poznámky

- Auto-fetch titulku aj kontrola mŕtvych odkazov závisia od CORS politiky cieľových stránok — mnohé stránky ich zablokujú, vtedy treba titulok doplniť ručne (fallback na doménu).
- Dáta sú viazané na konkrétny prehliadač/zariadenie (localStorage) — pre prenos alebo zálohu použi Export/Import JSON.
