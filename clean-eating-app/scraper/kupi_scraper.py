#!/usr/bin/env python3
"""
Clean Eating Agent — Kupi.cz Scraper
Sťahuje reálne akciové ceny z letákov pre obchody v Příbrame.
100% zadarmo, žiadne API, žiadne poplatky.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, date
from typing import Optional
import time
import os

# ============================================================
# KONFIGURÁCIA
# ============================================================

STORES = {
    "lidl": "Lidl",
    "kaufland": "Kaufland", 
    "penny-market": "Penny Market",
    "billa": "Billa",
    "albert": "Albert",
}

# Kategórie na Kupi.cz relevantné pre Clean Eating
CATEGORIES = {
    "maso": [
        "/slevy/drubez",           # Drůbež (kuřecí, krůtí)
        "/slevy/hovezi",           # Hovězí
        "/slevy/veprove",          # Vepřové
    ],
    "ryby": [
        "/slevy/ryby-2",           # Ryby
        "/slevy/mrazene-ryby",     # Mražené ryby
    ],
    "mliecne": [
        "/slevy/jogurty",          # Jogurty
        "/slevy/tvaroh",           # Tvaroh
        "/slevy/syry",             # Sýry (mozzarella, cottage)
        "/slevy/vejce",            # Vejce
        "/slevy/maslo-a-margariny", # Máslo
        "/slevy/mleko",            # Mléko
    ],
    "ovocie_zelenina": [
        "/slevy/ovoce",            # Ovoce
        "/slevy/zelenina",         # Zelenina
        "/slevy/mrazena-zelenina", # Mražená zelenina
    ],
    "trvanlive": [
        "/slevy/konzervy",         # Konzervy (strukoviny, tuniak)
        "/slevy/tuky-a-oleje",     # Oleje, máslo
        "/slevy/toustovy-a-cerstvy-chleb", # Celozrnné pečivo
        "/slevy/cestoviny-a-ryze", # Těstoviny, rýže
        "/slevy/lusteninove-a-obilne-vyrobky", # Luštěniny
    ],
}

# ============================================================
# UPF FILTER — Zakázané ingrediencie a kategórie
# ============================================================

BANNED_KEYWORDS = [
    # Uzeniny a spracované mäso
    "párky", "párků", "párek", "klobás", "salám", "šunk", "paštik", "paštět",
    "špekáč", "vuřt", "buřt", "slanin", "mortadel", "kabanos", "jaternic",
    "tlačenk", "jelít", "utopen", "vysočin", "gothaj", "debrecín", "piken",
    "hot dog", "bacon", "chorizo", "prosciutt", "pancetta",
    
    # Sladkosti a snacky
    "čokolád", "sušenk", "oplatk", "chips", "brambůrk", "tyčink",
    "bonbon", "želé", "gumov", "drops", "karamel", "nugát",
    "müsli tyčink", "proteinov", "fitness tyčink",
    
    # Hotové jedlá (UPF)
    "hotové jídlo", "pizza", "lasagn", "burger", "nugget", "kroket",
    "hranolk", "smažen", "obalovan", "předsmažen",
    
    # Omáčky a dresingy (UPF)
    "kečup", "tatars", "dresin", "majonéz",
    
    # Sladené nápoje
    "limonád", "cola", "fanta", "sprite", "energy", "džus",
    
    # Instantné a polotovary
    "instantn", "polévka sáčk", "bujón",
]

BANNED_ADDITIVES = [
    "e250", "e251", "e252",                    # Dusitany/dusičnany
    "modifikovaný škrob", "modified starch",
    "karagénan", "karagenan", "e407",
    "glukózový sirup", "fruktózový sirup",
    "high fructose", "kukuřičný sirup",
    "palmový olej", "palm oil",
    "tavicí sůl", "tavící sůl", "e452", "e339", "e341",
    "aspartam", "e951", "acesulfam", "e950",
    "glutamát", "e621",
]

# Produkty, ktoré CHCEME (prioritné)
PRIORITY_KEYWORDS = [
    "kuřecí prs", "kuřecí stehen", "kuřecí řízk",
    "krůtí prs", "krůtí řízk",
    "hovězí", "telecí",
    "vejce", "vajec",
    "máslo", "butter",
    "tvaroh", "cottage",
    "jogurt", "skyr", "kefír",
    "mozzarell",
    "losos", "tuňák", "tresk", "pstruh", "makrela",
    "špenát", "brokolice", "květák", "fazol", "čočk", "hrách", "cizrn",
    "rajčat", "paprik", "cuketa", "okurk", "mrkev", "celer",
    "jablk", "banán", "pomeranč", "citron", "borůvk", "malín",
    "olivový olej", "extra virgin",
    "rýže", "ovesné vločky", "pohanka", "quinoa",
    "ořech", "mandle", "vlašsk",
]


def is_clean(product_name: str) -> bool:
    """Skontroluje, či produkt NIE je ultra-spracovaný."""
    name_lower = product_name.lower()
    for banned in BANNED_KEYWORDS:
        if banned.lower() in name_lower:
            return False
    return True


def is_priority(product_name: str) -> bool:
    """Skontroluje, či produkt patrí medzi prioritné."""
    name_lower = product_name.lower()
    for keyword in PRIORITY_KEYWORDS:
        if keyword.lower() in name_lower:
            return True
    return False


def get_clean_category(product_name: str) -> str:
    """Priradí Clean Eating kategóriu."""
    name_lower = product_name.lower()
    
    meat_kw = ["kuřecí", "krůtí", "hovězí", "vepřov", "telecí", "jehněčí", "kachní"]
    fish_kw = ["losos", "tuňák", "tresk", "pstruh", "makrela", "filé", "ryb"]
    dairy_kw = ["tvaroh", "jogurt", "skyr", "mozzarell", "cottage", "vejce", "vajec", "máslo", "sýr", "eidam", "gouda", "mléko", "smetana", "kefír"]
    produce_kw = ["jablk", "banán", "pomeranč", "rajčat", "paprik", "okurk", "mrkev", "brokolice", "špenát", "květák", "cuketa", "borůvk", "malín", "hrozn", "citron", "kiwi", "mango", "avokád", "celer", "červen", "zelení"]
    pantry_kw = ["olivový", "rýže", "čočk", "fazol", "hrách", "cizrn", "ovesné", "pohanka", "ořech", "mandle", "vlašsk", "konzerv", "těstovin"]
    
    for kw in meat_kw:
        if kw in name_lower: return "meat"
    for kw in fish_kw:
        if kw in name_lower: return "fish"
    for kw in dairy_kw:
        if kw in name_lower: return "dairy"
    for kw in produce_kw:
        if kw in name_lower: return "produce"
    for kw in pantry_kw:
        if kw in name_lower: return "pantry"
    
    return "other"


# ============================================================
# SCRAPER
# ============================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "cs-CZ,cs;q=0.9",
}


def scrape_kupi_category(category_url: str, store_filter: Optional[str] = None) -> list:
    """
    Scrapuje jednu kategóriu z Kupi.cz.
    Vracia zoznam produktov s cenami.
    """
    url = f"https://www.kupi.cz{category_url}"
    if store_filter:
        url += f"/{store_filter}"
    
    products = []
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Kupi.cz produktové karty
        # Hľadáme akciové produkty na stránke
        product_cards = soup.select(".product-list__item, .product-card, .deal-card, article.product")
        
        if not product_cards:
            # Alternatívny selektor — Kupi.cz môže mať rôzne layouty
            product_cards = soup.select("[class*='product'], [class*='deal'], [class*='offer']")
        
        # Skúsime aj parsovať textový obsah ak nie sú štrukturované karty
        if not product_cards:
            # Fallback: extrahujeme zo stránky všetky akcie
            all_links = soup.select("a[href*='/sleva/']")
            seen = set()
            for link in all_links:
                href = link.get("href", "")
                if href in seen:
                    continue
                seen.add(href)
                
                name = link.get_text(strip=True)
                if name and len(name) > 3:
                    products.append({
                        "name": name,
                        "url": f"https://www.kupi.cz{href}" if href.startswith("/") else href,
                    })
        
        # Extrahujeme ceny z textu stránky
        price_blocks = soup.select("[class*='price'], [class*='cena']")
        
        return products
        
    except Exception as e:
        print(f"  ⚠ Chyba pri {url}: {e}")
        return []


def scrape_kupi_product_page(product_url: str) -> dict:
    """
    Scrapuje detail jedného produktu — cena, obchody, platnosť.
    """
    try:
        resp = requests.get(product_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        result = {
            "url": product_url,
            "stores": [],
        }
        
        # Názov produktu
        h1 = soup.select_one("h1")
        if h1:
            result["name"] = h1.get_text(strip=True)
        
        # Bežná cena
        regular_price = soup.select_one("[class*='regular'], [class*='original'], [class*='bezna']")
        if regular_price:
            price_text = regular_price.get_text(strip=True)
            price_match = re.search(r'(\d+[,.]?\d*)\s*Kč', price_text)
            if price_match:
                result["regular_price"] = float(price_match.group(1).replace(",", "."))
        
        # Akciové ceny po obchodoch
        store_sections = soup.select("[class*='store'], [class*='shop'], [class*='offer']")
        
        # Parsujeme celú stránku pre ceny a obchody
        page_text = soup.get_text()
        
        for store_slug, store_name in STORES.items():
            if store_name.lower() in page_text.lower():
                # Nájdeme cenu pre tento obchod
                store_pattern = re.compile(
                    rf'{re.escape(store_name)}.*?(\d+[,.]?\d*)\s*Kč',
                    re.IGNORECASE | re.DOTALL
                )
                match = store_pattern.search(page_text)
                if match:
                    price = float(match.group(1).replace(",", "."))
                    result["stores"].append({
                        "store": store_name,
                        "store_slug": store_slug,
                        "sale_price": price,
                    })
        
        return result
        
    except Exception as e:
        print(f"  ⚠ Chyba pri {product_url}: {e}")
        return {}


def scrape_kupi_search(query: str) -> list:
    """
    Vyhľadávanie na Kupi.cz — najspoľahlivejšia metóda.
    """
    url = f"https://www.kupi.cz/hledej?f={requests.utils.quote(query)}"
    products = []
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Hľadáme produktové odkazy
        links = soup.select("a[href*='/sleva/']")
        seen = set()
        
        for link in links:
            href = link.get("href", "")
            if href in seen or not href:
                continue
            seen.add(href)
            
            name = link.get_text(strip=True)
            if name and len(name) > 3 and not any(skip in name.lower() for skip in ["leták", "kategori", "zobrazit"]):
                full_url = f"https://www.kupi.cz{href}" if href.startswith("/") else href
                products.append({
                    "name": name,
                    "url": full_url,
                    "search_query": query,
                })
        
        return products
        
    except Exception as e:
        print(f"  ⚠ Chyba pri hľadaní '{query}': {e}")
        return []


def scrape_kupi_sleva_page(slug: str) -> dict:
    """
    Scrapuje priamo stránku /sleva/{slug} pre konkrétny produkt.
    Vracia všetky akciové ceny zo všetkých obchodov.
    """
    url = f"https://www.kupi.cz/sleva/{slug}"
    result = {
        "slug": slug,
        "url": url,
        "name": "",
        "regular_price": None,
        "offers": [],
    }
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return result
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Názov
        h1 = soup.select_one("h1")
        if h1:
            result["name"] = h1.get_text(strip=True)
        
        # Bežná cena
        text = soup.get_text()
        bezna_match = re.search(r'běžně\s+stojí\s+(\d+[,.]?\d*)\s*Kč', text)
        if bezna_match:
            result["regular_price"] = float(bezna_match.group(1).replace(",", "."))
        
        # Všetky ponuky — hľadáme ceny s obchodmi
        # Kupi.cz má štruktúru: Logo obchodu + cena + platnosť
        offer_blocks = soup.select(".product-offer, .offer-item, [class*='offer']")
        
        # Parsujeme textom — spoľahlivejšie
        for store_slug, store_name in STORES.items():
            # Hľadáme vzor: "Lidl ... 109,90 Kč"
            pattern = re.compile(
                rf'({re.escape(store_name)})\s*.*?cena\s*(\d+[,.]?\d*)\s*Kč',
                re.IGNORECASE | re.DOTALL
            )
            for match in pattern.finditer(text):
                price = float(match.group(2).replace(",", "."))
                result["offers"].append({
                    "store": store_name,
                    "store_slug": store_slug,
                    "sale_price": price,
                })
            
            # Alternatívny vzor
            pattern2 = re.compile(
                rf'({re.escape(store_name)}).*?(\d+[,.]?\d*)\s*Kč\s*/\s*(\d+\s*(?:kg|g|ks|l|ml))',
                re.IGNORECASE | re.DOTALL
            )
            for match in pattern2.finditer(text):
                price = float(match.group(2).replace(",", "."))
                unit = match.group(3).strip()
                
                # Deduplikácia
                existing = [o for o in result["offers"] if o["store"] == store_name and o["sale_price"] == price]
                if not existing:
                    result["offers"].append({
                        "store": store_name,
                        "store_slug": store_slug,
                        "sale_price": price,
                        "unit": unit,
                    })
        
        # Najlacnejšia cena
        nejlevnejsi_match = re.search(r'Nejvýhodněji.*?(\d+[,.]?\d*)\s*Kč', text)
        if nejlevnejsi_match:
            result["best_price"] = float(nejlevnejsi_match.group(1).replace(",", "."))
        
        # Zľava v percentách
        sleva_match = re.findall(r'[–-](\d+)\s*%', text)
        if sleva_match:
            result["max_discount"] = max(int(s) for s in sleva_match)
        
        return result
        
    except Exception as e:
        print(f"  ⚠ Chyba pri /sleva/{slug}: {e}")
        return result


# ============================================================
# HLAVNÝ SCRAPING PIPELINE
# ============================================================

# Zoznam konkrétnych produktových slugov na Kupi.cz
# Toto sú REÁLNE stránky, overené ručne
CLEAN_PRODUCT_SLUGS = {
    "meat": [
        "kureci-prsni-rizky",
        "kureci-prsa",
        "kureci-stehna",
        "kure",
        "kureci-ctvrtky-vodnanske-kure",
        "kruti-prsni-rizky",
        "kruti-prsa",
        "hovezi-zadni",
        "hovezi-svickova",
        "veprova-plec",
        "veprova-kyta",
        "mleta-smes",
    ],
    "fish": [
        "file-z-aljasske-tresky",
        "losos-file",
        "tunak-v-olivovem-oleji",
        "tunak-steak-franz-josef",
        "pstruh-duhovyy",
        "makrela-uzena",
    ],
    "dairy": [
        "vejce-m",
        "vejce-l",
        "vejce-s",
        "maslo-ceskee",
        "maslo-madeta",
        "tvaroh-jihocesky-madeta",
        "tvaroh-polotucny-jihocesky-madeta",
        "tvaroh-jaromericky",
        "tvaroh-tucny-karlova-koruna",
        "jogurt-recky-kolios",
        "jogurt-recky",
        "skyr-milko",
        "skyr-pilos",
        "mozzarella-galbani",
        "mozzarella-pilos",
        "cottage-cheese",
        "kefir",
    ],
    "produce": [
        "jablka-cervena",
        "banany",
        "pomerance",
        "citrony",
        "boruvky",
        "maliny",
        "rajcata",
        "papriky",
        "okurka-salatova",
        "brokolice",
        "spenat",
        "mrkev",
        "celer-bulvovy",
        "cuketa",
        "avokado",
    ],
    "pantry": [
        "olivovy-olej-extra-virgin",
        "olivovy-olej-bertolli",
        "ryze-basmati",
        "ryze-natural",
        "cocka-cervena",
        "ovesne-vlocky",
        "mandle",
        "vlaske-orechy",
    ],
}


def run_full_scrape():
    """Spustí kompletný scraping pre všetky Clean Eating produkty."""
    
    print("=" * 60)
    print("🔬 CLEAN EATING AGENT — Kupi.cz Scraper")
    print(f"📅 Dátum: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"📍 Cieľ: Příbram (Lidl, Kaufland, Penny, Billa, Albert)")
    print("=" * 60)
    
    all_products = []
    stats = {"total": 0, "clean": 0, "priority": 0, "with_price": 0}
    
    for category, slugs in CLEAN_PRODUCT_SLUGS.items():
        print(f"\n📦 Kategória: {category.upper()}")
        print("-" * 40)
        
        for slug in slugs:
            time.sleep(0.5)  # Rate limiting — šetrné k serveru
            
            data = scrape_kupi_sleva_page(slug)
            stats["total"] += 1
            
            if not data["name"]:
                print(f"  ⏭ {slug} — nenájdené")
                continue
            
            clean = is_clean(data["name"])
            priority = is_priority(data["name"])
            cat = get_clean_category(data["name"])
            
            if not clean:
                print(f"  🚫 {data['name']} — UPF/zakázané")
                continue
            
            stats["clean"] += 1
            if priority:
                stats["priority"] += 1
            if data.get("offers") or data.get("best_price"):
                stats["with_price"] += 1
            
            product = {
                "name": data["name"],
                "slug": slug,
                "category": cat,
                "is_priority": priority,
                "regular_price": data.get("regular_price"),
                "best_price": data.get("best_price"),
                "max_discount": data.get("max_discount"),
                "offers": data.get("offers", []),
                "url": data["url"],
                "scraped_at": datetime.now().isoformat(),
            }
            
            all_products.append(product)
            
            # Výpis
            price_str = ""
            if data.get("best_price"):
                price_str = f" → {data['best_price']} Kč"
            elif data.get("offers"):
                prices = [o["sale_price"] for o in data["offers"]]
                price_str = f" → od {min(prices)} Kč"
            
            discount_str = f" (-{data['max_discount']}%)" if data.get("max_discount") else ""
            priority_str = " ⭐" if priority else ""
            
            print(f"  ✅ {data['name']}{price_str}{discount_str}{priority_str}")
    
    # Výstupná štatistika
    print("\n" + "=" * 60)
    print("📊 VÝSLEDKY SCRAPU")
    print(f"  Celkom spracovaných: {stats['total']}")
    print(f"  Clean (prešli filtrom): {stats['clean']}")
    print(f"  Prioritné produkty: {stats['priority']}")
    print(f"  S aktuálnou cenou: {stats['with_price']}")
    print("=" * 60)
    
    return all_products


def save_results(products: list, output_dir: str = "."):
    """Uloží výsledky do JSON súborov pre PWA frontend."""
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Load bio_audit templates if available
    bio_templates = {}
    bio_path = os.path.join(output_dir, "bio_audit.json")
    if os.path.exists(bio_path):
        with open(bio_path, "r", encoding="utf-8") as f:
            bio_data = json.load(f)
            bio_templates = bio_data.get("templates", {})
    
    # Apply bio_audit templates to products
    for product in products:
        if not product.get("clean_score"):
            name_lower = product["name"].lower()
            for tpl_key, tpl in bio_templates.items():
                matched = False
                for kw in tpl.get("match_keywords", []):
                    if kw.lower() in name_lower:
                        product["clean_score"] = tpl["clean_score"]
                        product["bio_audit"] = tpl["bio_audit"]
                        matched = True
                        break
                if matched:
                    break
    
    # 1. Kompletný súbor
    full_path = os.path.join(output_dir, "products.json")
    output = {
        "generated_at": datetime.now().isoformat(),
        "store_location": "Příbram",
        "total_products": len(products),
        "products": products,
    }
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Uložené: {full_path}")
    
    # 2. Po kategóriách
    categories = {}
    for p in products:
        cat = p["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(p)
    
    for cat, items in categories.items():
        cat_path = os.path.join(output_dir, f"products_{cat}.json")
        cat_output = {
            "generated_at": datetime.now().isoformat(),
            "category": cat,
            "total_products": len(items),
            "products": items,
        }
        with open(cat_path, "w", encoding="utf-8") as f:
            json.dump(cat_output, f, ensure_ascii=False, indent=2)
        print(f"💾 Uložené: {cat_path} ({len(items)} produktov)")
    
    # 3. Súhrn pre frontend
    summary_path = os.path.join(output_dir, "summary.json")
    summary = {
        "generated_at": datetime.now().isoformat(),
        "store_location": "Příbram",
        "categories": {
            cat: {
                "count": len(items),
                "min_price": min((p["best_price"] for p in items if p.get("best_price")), default=None),
                "avg_discount": round(
                    sum(p.get("max_discount") or 0 for p in items) / max(len(items), 1), 1
                ),
            }
            for cat, items in categories.items()
        },
        "total_clean_products": len(products),
        "total_with_offers": sum(1 for p in products if p.get("offers") or p.get("best_price")),
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"💾 Uložené: {summary_path}")


# ============================================================
# SPUSTENIE
# ============================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data", help="Output directory for JSON files")
    args = parser.parse_args()
    
    products = run_full_scrape()
    save_results(products, output_dir=args.output)
    print("\n✅ Scraping dokončený!")
