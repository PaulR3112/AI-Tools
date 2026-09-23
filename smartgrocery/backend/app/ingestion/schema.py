"""Pevná výstupná schéma extrakcie (kap. 5). Model vracia presne toto."""

from typing import Literal

from pydantic import BaseModel, Field


class ExtractedConditions(BaseModel):
    loyalty_card: bool = Field(description="Cena platí len s vernostnou kartou / aplikáciou obchodu (klubová cena).")
    loyalty_program: str | None = Field(description="Názov programu, napr. 'Lidl Plus', 'Kaufland Card'.")
    min_qty: int | None = Field(description="Minimálny počet kusov na získanie ceny, napr. 'pri kúpe 3 ks'.")
    multibuy_buy: int | None = Field(description="Pri akcii typu 2+1: koľko kusov treba kúpiť (2).")
    multibuy_get: int | None = Field(description="Pri akcii typu 2+1: koľko kusov je zadarmo (1).")
    app_only: bool = Field(description="Ponuka len cez aplikáciu / e-shop.")
    coupon: bool = Field(description="Cena len s kupónom.")


class ExtractedOffer(BaseModel):
    raw_name: str = Field(description="Názov produktu presne ako v letáku, vrátane gramáže ak je v názve.")
    brand: str | None = Field(description="Značka, ak je čitateľná.")
    price: float | None = Field(
        description="Akciová cena v Kč za jednu položku ponuky (nie za kg, ak nie je price_type=per_kg)."
    )
    regular_price: float | None = Field(description="Preškrtnutá / bežná cena v Kč, ak je uvedená.")
    quantity: float | None = Field(description="Množstvo jedného balenia, napr. 250 pre 250 g.")
    unit: Literal["g", "kg", "ml", "l", "ks"] | None = Field(description="Jednotka množstva.")
    pack_count: int | None = Field(description="Počet balení v multipacku, napr. 4 pre '4 × 100 g'.")
    price_type: Literal["standard", "from", "per_kg", "multibuy"] = Field(
        description=(
            "standard; from = cena 'od'; per_kg = cena je uvedená za 1 kg (vážený tovar); "
            "multibuy = akcia typu 2+1 / 3 za 2."
        )
    )
    conditions: ExtractedConditions
    valid_from: str | None = Field(
        description="Začiatok platnosti tejto ponuky (YYYY-MM-DD), ak je pri ponuke uvedený; inak null."
    )
    valid_to: str | None = Field(
        description="Koniec platnosti tejto ponuky (YYYY-MM-DD), ak je pri ponuke uvedený; inak null."
    )
    bbox: list[float] = Field(
        description=(
            "Výrez ponuky na stránke [x, y, šírka, výška] ako podiel 0–1 z rozmerov stránky, počiatok vľavo hore."
        )
    )
    confidence: float = Field(description="Istota 0–1, že cena, množstvo a názov sú prečítané správne.")


class PageExtraction(BaseModel):
    flyer_valid_from: str | None = Field(
        description="Platnosť celého letáku od (YYYY-MM-DD), ak je na stránke uvedená."
    )
    flyer_valid_to: str | None = Field(description="Platnosť celého letáku do (YYYY-MM-DD), ak je na stránke uvedená.")
    offers: list[ExtractedOffer] = Field(description="Všetky cenové ponuky na stránke. Prázdne, ak stránka nemá ceny.")
