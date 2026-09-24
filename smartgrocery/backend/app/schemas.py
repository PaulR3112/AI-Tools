"""API kontrakt (v1). Z neho sa generuje OpenAPI a TS klient pre PWA."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    website: str | None


class ConditionOut(BaseModel):
    kind: str
    value: dict | None


class OfferSource(BaseModel):
    flyer_id: int
    flyer_version_id: int
    page: int
    bbox: list[float] | None
    document_url: str | None = Field(description="URL zdroja letáku (oficiálny web obchodu)")


class OfferOut(BaseModel):
    id: int
    raw_name: str
    brand: str | None
    store: StoreOut
    price: Decimal
    regular_price: Decimal | None
    currency: str
    quantity: Decimal | None
    unit: str | None
    pack_count: int | None
    unit_price: Decimal | None
    unit_price_basis: str | None
    price_type: str
    valid_from: date
    valid_to: date
    is_active: bool = Field(description="Platí v deň active_at")
    conditions: list[ConditionOut]
    source: OfferSource


class OfferDetail(OfferOut):
    confidence: Decimal | None
    status: str
    extraction_run_id: int
    created_at: datetime


class SearchResponse(BaseModel):
    items: list[OfferOut]
    limit: int
    offset: int
    active_at: date


class FlyerOut(BaseModel):
    id: int
    store: StoreOut
    valid_from: date
    valid_to: date
    version: int
    page_count: int
    document_url: str | None


class CategoryOut(BaseModel):
    id: int
    slug: str
    name: str
    parent_id: int | None
    unit_basis: str | None


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_endpoint_id: int
    status: str
    checked_at: datetime
    finished_at: datetime | None
    content_hash: str | None
    extraction_version: str | None
    model_id: str | None
    offers_count: int
    review_count: int
    rejected_count: int
    duration_ms: int | None
    cost_usd: Decimal
    error: str | None


class ReviewItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    extraction_run_id: int
    offer_id: int | None
    source_page: int | None
    severity: str
    code: str
    message: str
    payload: dict | None
    status: str
    created_at: datetime


class OfferCorrection(BaseModel):
    raw_name: str | None = None
    brand: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    regular_price: Decimal | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    unit: Literal["g", "kg", "ml", "l", "ks"] | None = None
    pack_count: int | None = Field(default=None, ge=1)
    price_type: Literal["standard", "from", "per_kg", "multibuy"] | None = None
    valid_from: date | None = None
    valid_to: date | None = None


class ReviewDecision(BaseModel):
    action: Literal["approve", "reject", "fix"]
    correction: OfferCorrection | None = None
