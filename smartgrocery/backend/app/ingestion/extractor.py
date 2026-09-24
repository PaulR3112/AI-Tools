"""Extrakcia ponúk zo stránky letáku cez Claude vision → pevná JSON schéma.

Model nerozhoduje o pravde; výstup vždy prechádza deterministickým validátorom.
"""

import base64
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol

import anthropic
from pydantic import ValidationError

from app.config import Settings
from app.ingestion.schema import PageExtraction

# JSON schéma pre structured outputs (SDK odstráni nepodporované obmedzenia)
PAGE_SCHEMA = anthropic.transform_schema(PageExtraction)

SYSTEM_PROMPT = """Si extraktor cien z akciových letákov českých supermarketov.
Zo stránky letáku vypíš každú cenovú ponuku podľa schémy. Pravidlá:
- Prepisuj len to, čo je na stránke. Nič nedopočítavaj a nehádaj; nečitateľné pole = null a nižšia confidence.
- price je cena, ktorú zákazník zaplatí za jednu položku ponuky.
  Ak je uvedená len cena za kg (vážený tovar), price_type = per_kg.
- Ak je pri ponuke viac cien (bežná a klubová/s kartou), price = klubová cena a conditions.loyalty_card = true;
  regular_price = preškrtnutá cena, ak existuje.
- Cena „od“ → price_type = from. Akcia 2+1 alebo „3 za 2“ → price_type = multibuy a vyplň multibuy_buy / multibuy_get.
- Multipack „4 × 100 g“ → quantity = 100, unit = g, pack_count = 4.
- Dátumy vracaj ako YYYY-MM-DD. Rok dopočítaj podľa referenčného dátumu v zadaní.
- bbox je obdĺžnik ponuky (obrázok + názov + cena) ako podiel rozmerov stránky.
"""


@dataclass
class PageContext:
    store_name: str
    page_number: int
    page_count: int
    reference_date: date


@dataclass
class ExtractionResult:
    page: PageExtraction
    model_id: str
    input_tokens: int = 0
    output_tokens: int = 0


class ExtractionError(Exception):
    pass


class PageExtractor(Protocol):
    extraction_version: str

    def extract(self, image_png: bytes, ctx: PageContext) -> ExtractionResult: ...


class ClaudeExtractor:
    def __init__(self, settings: Settings, client: anthropic.Anthropic | None = None):
        self.settings = settings
        self.client = client or anthropic.Anthropic()
        self.extraction_version = settings.extraction_version

    def extract(self, image_png: bytes, ctx: PageContext) -> ExtractionResult:
        s = self.settings
        extra: dict = {}
        if s.llm_server_fallbacks:
            # pri odmietnutí (refusal) API samo zopakuje požiadavku na záložnom modeli
            extra = {
                "extra_headers": {"anthropic-beta": "server-side-fallback-2026-07-01"},
                "extra_body": {"fallbacks": "default"},
            }
        try:
            # create + vlastná validácia (nie parse), aby sa stop_reason skontroloval skôr než JSON
            response = self.client.messages.create(
                model=s.llm_model,
                max_tokens=s.llm_max_tokens,
                system=SYSTEM_PROMPT,
                output_config={"effort": s.llm_effort, "format": {"type": "json_schema", "schema": PAGE_SCHEMA}},
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": base64.b64encode(image_png).decode(),
                                },
                            },
                            {
                                "type": "text",
                                "text": (
                                    f"Obchod: {ctx.store_name}. Stránka {ctx.page_number} z {ctx.page_count}. "
                                    f"Referenčný dátum (stiahnutie letáku): {ctx.reference_date.isoformat()}."
                                ),
                            },
                        ],
                    }
                ],
                **extra,
            )
        except anthropic.APIStatusError as e:
            raise ExtractionError(f"Claude API {e.status_code}: {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise ExtractionError(f"Claude API nedostupné: {e}") from e

        if response.stop_reason == "refusal":
            raise ExtractionError(f"Model odmietol stránku {ctx.page_number}")
        if response.stop_reason == "max_tokens":
            raise ExtractionError(f"Stránka {ctx.page_number}: výstup prekročil max_tokens")
        text = next((b.text for b in response.content if b.type == "text"), None)
        if not text:
            raise ExtractionError(f"Stránka {ctx.page_number}: prázdna odpoveď modelu ({response.stop_reason})")
        try:
            page = PageExtraction.model_validate_json(text)
        except ValidationError as e:
            raise ExtractionError(f"Stránka {ctx.page_number}: neplatný JSON: {e.error_count()} chýb") from e

        return ExtractionResult(
            page=page,
            model_id=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )


class RecordedExtractor:
    """Prehrá uložené odpovede modelu (testy, regression korpus). Súbor: {"pages": [PageExtraction, ...]}."""

    def __init__(self, path: Path, extraction_version: str = "recorded-v1"):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.pages = [PageExtraction.model_validate(p) for p in data["pages"]]
        self.extraction_version = extraction_version

    def extract(self, image_png: bytes, ctx: PageContext) -> ExtractionResult:
        idx = ctx.page_number - 1
        page = (
            self.pages[idx]
            if idx < len(self.pages)
            else PageExtraction(flyer_valid_from=None, flyer_valid_to=None, offers=[])
        )
        return ExtractionResult(page=page, model_id="recorded")
