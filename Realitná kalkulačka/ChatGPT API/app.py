import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

st.set_page_config(page_title="Realitná PRO Kalkulačka", layout="centered")

st.title("🏘️ Realitná investičná kalkulačka – PRO verzia")

st.header("Základné údaje")
kupna_cena = st.number_input("Kúpna cena nehnuteľnosti (CZK)", value=3500000, step=50000)
vlastne_zdroje = st.number_input("Vlastné zdroje (CZK)", value=700000, step=50000)
urokova_sadzka = st.number_input("Úroková sadzba hypotéky (%)", value=5.5) / 100
doba_splacania = st.slider("Doba splácania (roky)", 5, 40, 30)
fixacia = st.slider("Fixácia úroku (roky)", 1, 10, 5)

st.header("Prenájom a náklady")
mesacny_najom = st.number_input("Mesačný nájom (CZK)", value=17000, step=500)
rezijne_naklady = st.number_input("Mesačné režijné náklady (CZK)", value=4500, step=100)
sprava_bytu = st.slider("Náklady na správu bytu (% z nájmu)", 0, 20, 10) / 100
mesiace_neobsadenosti = st.slider("Počet mesiacov neobsadenosti ročne", 0, 12, 1)

st.header("Ostatné náklady a parametre")
poplatky_kupna = st.number_input("Poplatky pri kúpe (CZK)", value=60000)
rekonstrukcia = st.number_input("Rekonštrukcia / zariadenie (CZK)", value=300000)
rocne_naklady = st.number_input("Ročné náklady (poistenie, dane atď.)", value=6000)
dan_z_prijmu = st.slider("Daň z príjmu (%)", 0, 30, 15) / 100
dan_z_predaja = st.slider("Daň z predaja pri skoršom predaji (%)", 0, 30, 15) / 100
doba_drzania = st.slider("Plánovaná doba držania nehnuteľnosti (roky)", 1, 30, 10)
rocny_rast_hodnoty = st.slider("Ročný rast hodnoty (%)", 0, 10, 2) / 100
rocny_rast_najmu = st.slider("Ročný rast nájmu (%)", 0, 10, 2) / 100

st.header("Porovnanie s trhom")
priemerna_cena_m2 = st.number_input("Priemerná cena za m² v lokalite (CZK)", value=98000)
plocha_bytu = st.number_input("Plocha bytu (m²)", value=50)

# Výpočty
hypoteka = kupna_cena - vlastne_zdroje
r = urokova_sadzka / 12
n = doba_splacania * 12
mesacna_splatka = hypoteka * r * (1 + r)**n / ((1 + r)**n - 1)

sprava_naklad = mesacny_najom * sprava_bytu
vypadok = mesacny_najom * (mesiace_neobsadenosti / 12)
mesacny_cisty_zisk = mesacny_najom - rezijne_naklady - sprava_naklad - vypadok - mesacna_splatka
mesacny_zdaneny_zisk = mesacny_cisty_zisk * (1 - dan_z_prijmu)
rocny_zisk = mesacny_zdaneny_zisk * 12 - rocne_naklady

hodnota_po_rokoch = kupna_cena * ((1 + rocny_rast_hodnoty) ** doba_drzania)

total_najom = 0
sucasny_najom = mesacny_najom
for _ in range(doba_drzania):
    rocny_najom = (sucasny_najom * 12 - (sucasny_najom * mesiace_neobsadenosti)) * (1 - dan_z_prijmu)
    sprava = (sucasny_najom * 12) * sprava_bytu
    total_najom += rocny_najom - sprava - rocne_naklady
    sucasny_najom *= (1 + rocny_rast_najmu)

zdanenie_predaja = 0
if doba_drzania < 5:
    zdanenie_predaja = (hodnota_po_rokoch - kupna_cena) * dan_z_predaja

hypoteka_zaplacena = mesacna_splatka * 12 * doba_drzania
celkovy_zisk = (hodnota_po_rokoch - kupna_cena - zdanenie_predaja) + total_najom - poplatky_kupna - rekonstrukcia - hypoteka_zaplacena

investovane = vlastne_zdroje + poplatky_kupna + rekonstrukcia
roi = (celkovy_zisk / investovane) * 100 if investovane > 0 else 0

trhova_cena = priemerna_cena_m2 * plocha_bytu
vyhodnost = "výhodná" if kupna_cena < trhova_cena else "nevýhodná"

st.subheader("📊 Výsledky")
st.metric("Mesačná splátka hypotéky", f"{mesacna_splatka:,.0f} CZK")
st.metric("Mesačný zisk po zdanení", f"{mesacny_zdaneny_zisk:,.0f} CZK")
st.metric("Ročný čistý zisk", f"{rocny_zisk:,.0f} CZK")
st.metric("Zisk po {doba_drzania} rokoch", f"{celkovy_zisk:,.0f} CZK")
st.metric("ROI", f"{roi:.2f} %")
st.info(f"Nákup je pravdepodobne **{vyhodnost}** (trhová cena: {trhova_cena:,.0f} CZK)")
if zdanenie_predaja > 0:
    st.warning(f"Pozor: Predaj pred 5. rokom = daň z kapitálového zisku: {zdanenie_predaja:,.0f} CZK")