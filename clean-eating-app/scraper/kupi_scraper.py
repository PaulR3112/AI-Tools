#!/usr/bin/env python3
"""
Clean Eating Agent — Multi-Source Scraper v2
Sources: Kupi.cz + iLetaky.cz + AkcniCeny.cz with cross-verification.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Tuple
import time
import os

STORES = {"lidl": "Lidl", "kaufland": "Kaufland", "penny-market": "Penny Market", "billa": "Billa", "albert": "Albert"}
FLYER_CYCLES = {"Lidl": {"start_day": 0, "duration": 7}, "Kaufland": {"start_day": 3, "duration": 7}, "Penny Market": {"start_day": 2, "duration": 7}, "Billa": {"start_day": 2, "duration": 7}, "Albert": {"start_day": 2, "duration": 7}}

BANNED_KEYWORDS = ["párky","párků","párek","klobás","salám","šunk","paštik","paštět","špekáč","vuřt","buřt","slanin","mortadel","kabanos","jaternic","tlačenk","jelít","utopen","vysočin","gothaj","debrecín","piken","hot dog","bacon","chorizo","prosciutt","pancetta","čokolád","sušenk","oplatk","chips","brambůrk","tyčink","bonbon","želé","gumov","drops","karamel","nugát","müsli tyčink","proteinov","fitness tyčink","hotové jídlo","pizza","lasagn","burger","nugget","kroket","hranolk","smažen","obalovan","předsmažen","kečup","tatarsk","majonéz","dresing","limonád","cola","fant","sprite","energetick","energy","zmrzlin","nanuk","sorbet","toast","bageta","croissant","instantní","polévka sáčk","bujón"]
PRIORITY_KEYWORDS = ["kuřecí prsní","kuřecí prsa","kuře celé","krůtí","losos","tuňák","treska","tvaroh","jogurt řecký","skyr","cottage","vejce","brokolice","špenát","rajčata","borůvk","ovesné vločky","čočka","mandle","olivový olej","avokádo","batáty"]

HEADERS = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15", "Accept": "text/html,application/xhtml+xml", "Accept-Language": "cs-CZ,cs;q=0.9"}

def is_clean(name):
    nl = name.lower()
    return not any(b in nl for b in BANNED_KEYWORDS)

def is_priority(name):
    nl = name.lower()
    return any(k.lower() in nl for k in PRIORITY_KEYWORDS)

def get_clean_category(name):
    nl = name.lower()
    cats = {"meat": ["kuřecí","krůtí","hovězí","vepřov","telecí","jehněčí","kachní","kuře"], "fish": ["losos","tuňák","tresk","pstruh","makrela","filé","ryb"], "dairy": ["tvaroh","jogurt","skyr","mozzarell","cottage","vejce","vajec","máslo","sýr","eidam","gouda","mléko","smetana","kefír"], "produce": ["jablk","banán","pomeranč","rajčat","paprik","okurk","mrkev","brokolice","špenát","květák","cuketa","borůvk","malín","hrozn","citron","kiwi","mango","avokád","celer","zelení","cibule","česnek","batát"], "pantry": ["olivový","rýže","čočk","fazol","hrách","cizrn","ovesné","pohanka","ořech","mandle","vlašsk","konzerv","těstovin","med"]}
    for cat, kws in cats.items():
        if any(kw in nl for kw in kws): return cat
    return "other"

def get_validity_dates(store_name):
    today = date.today()
    cycle = FLYER_CYCLES.get(store_name, {"start_day": 2, "duration": 7})
    days_since = (today.weekday() - cycle["start_day"]) % 7
    start = today - timedelta(days=days_since)
    end = start + timedelta(days=cycle["duration"] - 1)
    return start.isoformat(), end.isoformat()

# ============================================================
# BIO AUDIT + NUTRITION
# ============================================================
BIO = {
    "meat": {"kuřecí prs": (92,8,9,9,"Čisté drůbeží maso, bohaté na tryptofan","Nízký nasycené tuky, vysoké bílkoviny","Vysoký TEF ~25%"), "kuře cel": (85,7,7,8,"Kolagen a glycin","Více železa a zinku, kůže zvyšuje tuky","Kompletní aminokyseliny, B-vitamíny"), "krůtí": (93,8,9,9,"Nejlibovější drůbeží maso","Téměř nulový tuk","Selen a B-vitamíny"), "hovězí": (80,7,6,8,"Bohaté na železo a B12","Vyšší nasycené tuky — max 2× týdně","B12, železo, zinek"), "vepřov": (72,6,5,7,"Thiamin (B1)","Vyšší nasycené tuky","Thiamin a selen"), "mlet": (70,6,5,7,"Záleží na kvalitě","Střední nasycené tuky","Bílkoviny, železo, B12")},
    "fish": {"losos": (96,9,10,9,"Omega-3 protizánětlivý účinek na mikrobiom","Omega-3 snižují triglyceridy a tlak","Vitamín D, selen, astaxanthin"), "tuňák": (85,7,8,8,"Minimální zpracování, pozor na sodík","Omega-3, niacin snižuje LDL","Niacin a selen"), "tresk": (90,8,8,8,"Lehce stravitelné filé","Nízkotučná ryba","Jód, fosfor, selen"), "pstruh": (93,8,9,8,"Sladkovodní ryba s omega-3","Nízký tuk, vitamín D","Kompletní bílkoviny, selen")},
    "dairy": {"tvaroh": (94,9,7,9,"Probiotické kultury, kasein","Bohatý na vápník a fosfor","Kasein = pomalé aminokyseliny"), "jogurt": (91,9,7,8,"Živé kultury L. bulgaricus","Fermentace zlepšuje profil tuků","Probiotika zlepšují absorpci"), "vejce": (98,8,8,10,"Lecitin podporuje střevní bariéru","Dietární cholesterol má minimální vliv","Cholin, vitamín D, B12, selen"), "mozzarell": (88,7,7,7,"Fermentovaný sýr","Střední tuky, bohatý na vápník","Vápník podporuje lipolýzu"), "máslo": (78,6,5,7,"Butyrát — živina pro střevo","Vysoký nasycené tuky","Vitamíny A, D, E, K2"), "cottage": (93,8,8,9,"Probiotické kultury, kasein","Nízký tuk","Pomalý kasein, ideální před spaním"), "skyr": (94,9,8,9,"Islandský fermentovaný produkt","Nízký tuk, vysoké bílkoviny","2-3× více bílkovin než jogurt"), "kefír": (92,10,7,8,"60+ druhů probiotik","Probiotika pro cévy","Zlepšuje absorpci vápníku")},
    "produce": {"jablk": (100,9,8,7,"Pektin a polyfenoly — top prebiotikum","Kvercetín chrání cievy","Nízký GI, vláknina"), "banán": (100,9,8,7,"Rezistentní škrob je prebiotikum","Draslík reguluje tlak","Rychlý zdroj energie"), "pomeranč": (100,9,9,8,"Pektin — rozpustná vláknina","Vitamín C, hesperidin","Vitamín C zvyšuje absorpci železa"), "rajčat": (100,8,9,8,"Lykopen podporuje mikrobiom","Lykopen chrání cévy","Ultra-nízkokalorické"), "brokolice": (100,9,9,9,"Sulforafan a indol-3-karbinol","Protizánětlivé účinky","Sulforafan aktivuje Nrf2"), "špenát": (100,9,10,9,"Polyfenoly živí prospěšné baktérie","Nitráty → oxid dusnatý","Železo, folát, vitamín K"), "avokád": (98,8,9,8,"Vláknina a polyfenoly","Mononenasycené tuky snižují LDL","Draslík, vláknina, zdravé tuky"), "mrkev": (100,8,8,8,"Vláknina a beta-karoten","Beta-karoten a luteolin","Beta-karoten → vitamín A"), "paprik": (100,8,9,8,"Vitamín C a vláknina","Vitamín C 127mg/100g","Kapsaicín zvyšuje termogenézu"), "cibule": (100,9,8,7,"Inulín a FOS — silné prebiotikum","Kvercetín a síra chrání cievy","Chróm podporuje inzulín"), "česnek": (100,9,9,8,"Allicín — prebiotické a antimikrobiálne","Allicín znižuje tlak a LDL","Selenoaminokyseliny"), "borůvk": (100,9,9,8,"Antokyany — mikrobiotická diverzita","Silné antioxidanty, ochrana DNA","Nízkokalorické, flavonoidy"), "kiwi": (100,8,8,8,"Actinidin usnadňuje trávení","Vitamín C chrání cévy","Nejvyšší zdroj vitamínu C"), "okurk": (100,7,7,7,"Vysoký obsah vody","Draslík a hořčík","Ultra-nízkokalorická"), "hrozn": (95,8,9,7,"Resveratrol podporuje diverzitu","Resveratrol chrání cévy","Přírodní cukry s polyfenoly"), "cuketa": (100,7,7,7,"Vláknina a voda","Draslík reguluje tlak","Ultra-nízkokalorická"), "citron": (100,8,9,8,"Pektin a polyfenoly","Vitamín C chrání cévy","Podporuje absorpci železa"), "malin": (100,9,9,8,"Ellagitaniny — silné prebiotikum","Antioxidanty chrání cévy","Nízkokalorické, vysoká vláknina")},
    "pantry": {"olivový": (95,8,10,8,"Polyfenoly podporují prospěšné baktérie","Kyselina olejová — základ středomořské diety","Mononenasycené tuky zlepšují inzulín"), "ovesné": (95,10,10,9,"Beta-glukan — zlatý standard prebiotík","3g beta-glukanu snižuje LDL o 5-10%","Nízký GI, pomalé uvolňování"), "čočk": (95,10,9,9,"Rezistentní škrob + oligosacharidy","Rozpustná vláknina snižuje LDL","Nízký GI, vysoké bílkoviny a železo"), "mandle": (98,9,10,9,"Vláknina a polyfenoly","30g ořechů snižuje KV riziko o 30%","Zdravé tuky, hořčík, vitamín E"), "rýže": (80,6,6,7,"Nízký obsah vlákniny","Neutrální vliv","Basmati má nižší GI"), "těstovin": (82,7,7,7,"Celozrnné — vláknina","Celozrnné mají nižší GI","Pomalé uvolňování energie"), "fazol": (88,9,8,8,"Luštěniny — TOP prebiotikum","Rozpustná vláknina snižuje LDL","Nízký GI, bílkoviny"), "med": (75,7,5,5,"Oligosacharidy s prebiotickým účinkom","Vysoký cukr — max 1 lyžica","Lepšia alternatíva k cukru"), "ořech": (97,9,10,9,"Polyfenoly a vláknina","Omega-3 (ALA)","Zdravé tuky, hořčík")}
}

NUTRI = {"kuřecí prs": (110,23.1,0,1.2,0), "kuře cel": (167,20,0,9.3,0), "kuřecí steh": (177,18.2,0,11.2,0), "krůtí": (104,24.6,0,0.7,0), "hovězí": (250,26,0,15,0), "vepřov": (186,18.5,0,12.2,0), "mlet": (145,20,0,7,0), "losos": (208,20.4,0,13.4,0), "tuňák": (116,25.5,0,1,0), "tresk": (82,17.6,0,0.7,0), "pstruh": (119,20.5,0,3.5,0), "tvaroh": (130,12.8,3.1,7.5,0), "jogurt": (72,3.5,4.8,3.8,0), "řecký": (97,9,3.5,5,0), "vejce": (143,12.6,0.7,9.9,0), "mozzarell": (254,18.5,1,19.5,0), "máslo": (717,0.6,0.8,81,0), "cottage": (98,11,3.3,4,0), "skyr": (63,11,4,0.2,0), "kefír": (56,3.3,4.7,1.5,0), "jablk": (52,0.3,13.8,0.2,2.4), "banán": (89,1.1,22.8,0.3,2.6), "pomeranč": (47,0.9,11.8,0.1,2.4), "rajčat": (18,0.9,3.9,0.2,1.2), "paprik": (31,1,6,0.3,2.1), "brokolice": (34,2.8,7,0.4,2.6), "špenát": (23,2.9,3.6,0.4,2.2), "mrkev": (41,0.9,9.6,0.2,2.8), "okurk": (15,0.7,3.6,0.1,0.5), "avokád": (160,2,9,15,6.7), "cibule": (40,1.1,9.3,0.1,1.7), "česnek": (149,6.4,33.1,0.5,2.1), "borůvk": (57,0.7,14.5,0.3,2.4), "kiwi": (63,1.1,15.4,0.3,2), "hrozn": (69,0.7,18.1,0.2,0.9), "cuketa": (17,1.2,3.1,0.3,1), "olivový": (884,0,0,100,0), "ovesné": (372,13.5,58.7,7,10.6), "rýže": (350,7,78,0.6,1), "čočk": (353,25.4,60.1,1.1,10.7), "mandle": (576,21.2,21.7,49.4,12.2), "těstovin": (348,13.5,65,2.5,7.5), "fazol": (81,4.6,12.9,0.5,3.7), "med": (304,0.3,76,0,0), "ořech": (654,15,14,65,6.7)}

def get_bio_audit(name, cat):
    nl = name.lower()
    tpls = BIO.get(cat, {})
    for kw, d in tpls.items():
        if kw in nl:
            return d[0], {"microbiome": {"score": d[1], "detail": d[4]}, "cardiovascular": {"score": d[2], "detail": d[5]}, "metabolism": {"score": d[3], "detail": d[6]}}
    defaults = {"meat": 75, "fish": 90, "dairy": 85, "produce": 100, "pantry": 80, "other": 60}
    s = defaults.get(cat, 70)
    return s, {"microbiome": {"score": 7, "detail": "Standardní produkt"}, "cardiovascular": {"score": 7, "detail": "Neutrální vliv"}, "metabolism": {"score": 7, "detail": "Standardní nutriční profil"}}

def get_nutrition(name):
    nl = name.lower()
    for kw, n in NUTRI.items():
        if kw in nl: return {"kcal": n[0], "protein": n[1], "carbs": n[2], "fat": n[3], "fiber": n[4]}
    return {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0}

# ============================================================
# SCRAPERS
# ============================================================

def scrape_kupi_sleva(slug):
    url = f"https://www.kupi.cz/sleva/{slug}"
    result = {"source": "kupi.cz", "slug": slug, "url": url, "name": "", "regular_price": None, "offers": [], "best_price": None, "max_discount": None}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200: return result
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text()
        h1 = soup.select_one("h1")
        if h1: result["name"] = h1.get_text(strip=True)
        bezna = re.search(r'běžně\s+stojí\s+(\d+[,.]?\d*)\s*Kč', text)
        if bezna: result["regular_price"] = float(bezna.group(1).replace(",", "."))
        nejl = re.search(r'Nejvýhodněji.*?(\d+[,.]?\d*)\s*Kč', text)
        if nejl: result["best_price"] = float(nejl.group(1).replace(",", "."))
        sleva = re.findall(r'[–-](\d+)\s*%', text)
        if sleva: result["max_discount"] = max(int(s) for s in sleva)
        for ss, sn in STORES.items():
            pat = re.compile(rf'({re.escape(sn)}).*?cena\s*(\d+[,.]?\d*)\s*Kč', re.IGNORECASE | re.DOTALL)
            for m in pat.finditer(text):
                p = float(m.group(2).replace(",", "."))
                if not any(o["store"]==sn and o["sale_price"]==p for o in result["offers"]):
                    vf, vu = get_validity_dates(sn)
                    result["offers"].append({"store": sn, "sale_price": p, "valid_from": vf, "valid_until": vu, "source": "kupi.cz"})
            pat2 = re.compile(rf'({re.escape(sn)}).*?(\d+[,.]?\d*)\s*Kč\s*/\s*(\d+\s*(?:kg|g|ks|l|ml))', re.IGNORECASE | re.DOTALL)
            for m in pat2.finditer(text):
                p = float(m.group(2).replace(",", "."))
                u = m.group(3).strip()
                if not any(o["store"]==sn and o["sale_price"]==p for o in result["offers"]):
                    vf, vu = get_validity_dates(sn)
                    result["offers"].append({"store": sn, "sale_price": p, "unit": u, "valid_from": vf, "valid_until": vu, "source": "kupi.cz"})
        for o in result["offers"]:
            plat = re.search(rf'{re.escape(o["store"])}.*?platí\s+do\s+\w+\s+(\d+)\.\s*(\d+)\.', text, re.IGNORECASE | re.DOTALL)
            if plat:
                d, mo = int(plat.group(1)), int(plat.group(2))
                o["valid_until"] = f"{date.today().year}-{mo:02d}-{d:02d}"
        return result
    except Exception as e:
        print(f"  ⚠ kupi.cz [{slug}]: {e}")
        return result

def scrape_iletaky(query):
    url = f"https://www.iletaky.cz/hledani/?q={requests.utils.quote(query)}"
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200: return results
        text = BeautifulSoup(resp.text, "html.parser").get_text()
        for ps in re.findall(r'(\d+[,.]?\d*)\s*Kč', text)[:5]:
            p = float(ps.replace(",", "."))
            if 1 < p < 1000: results.append({"source": "iletaky.cz", "price": p})
        return results
    except: return results

def scrape_akcniceny(query):
    url = f"https://www.akcniceny.cz/hledani/?q={requests.utils.quote(query)}"
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200: return results
        text = BeautifulSoup(resp.text, "html.parser").get_text()
        for ps in re.findall(r'(\d+[,.]?\d*)\s*Kč', text)[:5]:
            p = float(ps.replace(",", "."))
            if 1 < p < 1000: results.append({"source": "akcniceny.cz", "price": p})
        return results
    except: return results

def cross_verify(name, kupi_price):
    v = {"kupi_price": kupi_price, "other_sources": [], "verified": False, "confidence": "low"}
    il = scrape_iletaky(name)
    for i in il:
        v["other_sources"].append(i)
        if abs(i["price"] - kupi_price) < 2.0: v["verified"] = True
    time.sleep(0.3)
    ac = scrape_akcniceny(name)
    for i in ac:
        v["other_sources"].append(i)
        if abs(i["price"] - kupi_price) < 2.0: v["verified"] = True
    v["confidence"] = "high" if v["verified"] else ("medium" if v["other_sources"] else "low")
    return v

# ============================================================
# PRODUCT SLUGS
# ============================================================
SLUGS = {
    "meat": ["kureci-prsni-rizky","kureci-prsa","kureci-stehna","kure","kruti-prsni-rizky","kruti-prsa","hovezi-zadni","veprova-plec","mleta-smes"],
    "fish": ["losos-filety","losos-obecny-filety","tunak-steak-franz-josef","file-z-aljasske-tresky","pstruh-duhovy"],
    "dairy": ["vejce-m","vejce-s","maslo-madeta","maslo-ceske","tvaroh-jihocesky-madeta","tvaroh-polotucny-jihocesky-madeta","tvaroh-tucny-karlova-koruna","jogurt-recky","selsky-jogurt-hollandia","mozzarella-pilos","mozzarella-galbani","cottage-cheese","skyr-milko"],
    "produce": ["jablka-cervena","banany","pomerance","citrony","boruvky","maliny","rajcata","papriky","brokolice","spenat","mrkev","cuketa","avokado","okurka-salatova","cibule","cesnek","kiwi","hrozny"],
    "pantry": ["olivovy-olej-bertolli","olivovy-olej-extra-virgin","ryze-basmati","ovesne-vlocky","ovesne-vlocky-emco","cocka-cervena","mandle","vlaske-orechy","testoviny-barilla","fazole-bile","med"],
}

# ============================================================
# MAIN
# ============================================================

def run_full_scrape():
    print("=" * 60)
    print("🔬 CLEAN EATING AGENT — Multi-Source Scraper v2")
    print(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print("📡 Kupi.cz + iLetaky.cz + AkcniCeny.cz")
    print("=" * 60)
    
    products = []
    stats = {"total": 0, "clean": 0, "priority": 0, "with_price": 0, "verified": 0}
    
    for cat, slugs in SLUGS.items():
        print(f"\n📦 {cat.upper()}")
        print("-" * 40)
        for slug in slugs:
            time.sleep(0.5)
            stats["total"] += 1
            data = scrape_kupi_sleva(slug)
            if not data["name"]:
                print(f"  ⏭ {slug} — nenájdené")
                continue
            if not is_clean(data["name"]):
                print(f"  🚫 {data['name']} — UPF")
                continue
            stats["clean"] += 1
            c = get_clean_category(data["name"])
            pri = is_priority(data["name"])
            if pri: stats["priority"] += 1
            if data.get("offers") or data.get("best_price"): stats["with_price"] += 1
            
            ver = None
            if data.get("best_price"):
                time.sleep(0.3)
                ver = cross_verify(data["name"], data["best_price"])
                if ver["verified"]: stats["verified"] += 1
            
            score, bio = get_bio_audit(data["name"], c)
            nutri = get_nutrition(data["name"])
            
            p = {
                "name": data["name"], "slug": slug, "category": c, "is_priority": pri,
                "regular_price": data.get("regular_price"), "best_price": data.get("best_price"),
                "max_discount": data.get("max_discount"), "offers": data.get("offers", []),
                "clean_score": score, "bio_audit": bio, "nutrition": nutri,
                "source_url": data["url"],
                "sources_checked": list(set(["kupi.cz"] + [s["source"] for s in (ver or {}).get("other_sources", [])])),
                "verification": ver, "scraped_at": datetime.now().isoformat(),
            }
            products.append(p)
            
            ps = f" → {data['best_price']} Kč" if data.get("best_price") else (f" → od {min(o['sale_price'] for o in data['offers'])} Kč" if data.get("offers") else "")
            ds = f" (-{data['max_discount']}%)" if data.get("max_discount") else ""
            vs = " ✓" if ver and ver.get("verified") else ""
            print(f"  ✅ {data['name']}{ps}{ds}{' ⭐' if pri else ''}{vs}")
    
    print(f"\n{'='*60}\n📊 VÝSLEDKY\n  Spracovaných: {stats['total']}\n  Clean: {stats['clean']}\n  Prioritných: {stats['priority']}\n  S cenou: {stats['with_price']}\n  Cross-overených: {stats['verified']}\n{'='*60}")
    return products

def save_results(products, output_dir="."):
    os.makedirs(output_dir, exist_ok=True)
    fp = os.path.join(output_dir, "products.json")
    out = {"generated_at": datetime.now().isoformat(), "flyer_week": f"{date.today().strftime('%d.%m')} – {(date.today()+timedelta(days=6)).strftime('%d.%m.%Y')}", "store_location": "Příbram", "sources": ["kupi.cz","iletaky.cz","akcniceny.cz"], "total_products": len(products), "products": products}
    with open(fp, "w", encoding="utf-8") as f: json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n💾 {fp}")
    
    cats = {}
    for p in products:
        cats.setdefault(p["category"], []).append(p)
    for c, items in cats.items():
        cp = os.path.join(output_dir, f"products_{c}.json")
        with open(cp, "w", encoding="utf-8") as f: json.dump({"generated_at": datetime.now().isoformat(), "category": c, "total_products": len(items), "products": items}, f, ensure_ascii=False, indent=2)
        print(f"💾 {cp} ({len(items)})")
    
    sp = os.path.join(output_dir, "summary.json")
    summary = {"generated_at": datetime.now().isoformat(), "store_location": "Příbram", "sources": ["kupi.cz","iletaky.cz","akcniceny.cz"], "categories": {c: {"count": len(i), "min_price": min((p["best_price"] for p in i if p.get("best_price")), default=None), "avg_discount": round(sum(p.get("max_discount") or 0 for p in i)/max(len(i),1), 1)} for c, i in cats.items()}, "total_clean_products": len(products), "total_with_offers": sum(1 for p in products if p.get("offers") or p.get("best_price")), "total_verified": sum(1 for p in products if p.get("verification", {}).get("verified"))}
    with open(sp, "w", encoding="utf-8") as f: json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"💾 {sp}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data")
    args = parser.parse_args()
    products = run_full_scrape()
    save_results(products, output_dir=args.output)
    print("\n✅ Hotovo!")
