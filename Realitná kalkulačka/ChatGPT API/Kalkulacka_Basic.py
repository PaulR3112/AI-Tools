import streamlit as st
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
import locale

locale.setlocale(locale.LC_ALL, '')  # nastaví lokalitu podľa systému (napr. na 'sk_SK' alebo 'cs_CZ')

st.set_page_config(page_title="Ziskovosť nehnuteľnosti – Basic", layout="centered")
st.title("📊 Kalkulačka ziskovosti nehnuteľnosti")

st.sidebar.header("Základné vstupy")
kupna = st.sidebar.number_input("Kúpna cena (CZK)", value=3000000, step=50000)
vlastne = st.sidebar.number_input("Vlastné zdroje (CZK)", value=600000, step=50000)
urok = st.sidebar.number_input("Úroková sadzba (%)", value=4.8) / 100
doba = st.sidebar.slider("Doba splácania (roky)", 1, 60, 30)
najom = st.sidebar.number_input("Mesačný nájom (CZK)", value=15000, step=200)
rast_hodn = st.sidebar.number_input("Ročný rast hodnoty (%)", value=5.0) / 100
rast_najm = st.sidebar.number_input("Ročný rast nájmu (%)", value=5.0) / 100
naklady = st.sidebar.number_input("Ročné náklady (CZK)", value=20000, step=500)
roky_drzania = st.sidebar.slider("Počet rokov držania", 1, 50, 10)
predaj_v_roku = st.sidebar.slider("Simulovať predaj v roku (0 = nepredáva sa)", 0, roky_drzania, 0)


st.divider()

hypoteka = kupna - vlastne
r = urok / 12
n = doba * 12
splatka = hypoteka * r * (1 + r)**n / ((1 + r)**n - 1)

zisk = 0
aktualny_najom = najom
hodnota = kupna
roky = []
zisky = []
hodnoty = []

for rok in range(1, roky_drzania + 1):
    prijem = aktualny_najom * 12
    zisk_rok = prijem - (splatka * 12) - naklady
    zisk += zisk_rok
    aktualny_najom *= (1 + rast_najm)
    hodnota *= (1 + rast_hodn)

    if predaj_v_roku != 0 and rok == predaj_v_roku:
        predajna_cena = hodnota
        break

    roky.append(rok)
    zisky.append(zisk)
    hodnoty.append(hodnota)

    # ak sa predáva
if predaj_v_roku != 0:
    celkovy_zisk = zisk + predajna_cena - kupna
    st.warning(f"💰 Predaj simulovaný v roku {predaj_v_roku} za {int(predajna_cena):,} CZK")
else:
    celkovy_zisk = zisk

st.subheader("📈 Výsledky")
st.metric("Mesačná splátka hypotéky", f"{splatka:,.0f}".replace(",", " ") + " CZK")
st.metric("Celkový zisk po {roky_drzania} rokoch", f"{zisk:,.0f} CZK")
st.metric("Hodnota nehnuteľnosti po {roky_drzania} rokoch", f"{hodnota:,.0f} CZK")

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(roky, zisky, label="Kumulovaný zisk")
ax.plot(roky, hodnoty, label="Hodnota nehnuteľnosti")
ax.set_xlabel("Rok")
ax.set_ylabel("CZK")
ax.set_title("Vývoj zisku a hodnoty")
ax.grid(True)
ax.legend()
st.pyplot(fig)

# Export do PDF
if st.button("📄 Exportovať výsledky do PDF"):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(50, 800, f"Mesačná splátka hypotéky: {format(int(splatka), 'n').replace(',', ' ')} CZK")
    c.drawString(50, 780, f"Zisk: {format(int(celkovy_zisk), 'n').replace(',', ' ')} CZK")
    c.drawString(50, 760, f"Hodnota nehnuteľnosti: {format(int(hodnota), 'n').replace(',', ' ')} CZK")
    if predaj_v_roku != 0:
        c.drawString(50, 740, f"Simulovaný predaj v roku {predaj_v_roku}: {format(int(predajna_cena), 'n').replace(',', ' ')} CZK")
    c.showPage()
    c.save()
    buffer.seek(0)
    st.download_button("Stiahnuť PDF", data=buffer, file_name="vysledky_kalkulacky.pdf", mime="application/pdf")
