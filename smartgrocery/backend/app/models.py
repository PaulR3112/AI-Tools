"""ORM model podľa kap. 6 špecifikácie (MVP tabuľky).

Enumy sú text + CHECK (ľahšie migrácie než PG ENUM). Jednotková cena je
generated column – počíta ju DB, nie aplikácia ani AI.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import DATERANGE, JSONB, Range
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

UNITS = ("g", "kg", "ml", "l", "ks")
PRICE_TYPES = ("standard", "from", "per_kg", "multibuy")
CONDITION_KINDS = ("loyalty_card", "min_qty", "multibuy", "app_only", "coupon")
LEGAL_STATUSES = ("approved", "pending", "rejected")
SOURCE_KINDS = ("structured", "pdf", "image")
OFFER_STATUSES = ("active", "review", "rejected")


def _in(col: str, values: tuple[str, ...]) -> str:
    return f"{col} IN ({', '.join(repr(v) for v in values)})"


UNIT_PRICE_SQL = """
CASE
  WHEN price_type = 'per_kg' THEN price
  WHEN unit IS NULL OR quantity IS NULL OR quantity <= 0 THEN NULL
  WHEN unit IN ('g', 'ml') THEN round(price * 1000 / (quantity * coalesce(pack_count, 1)), 2)
  ELSE round(price / (quantity * coalesce(pack_count, 1)), 2)
END
"""

UNIT_PRICE_BASIS_SQL = """
CASE
  WHEN price_type = 'per_kg' THEN 'kg'
  WHEN unit IS NULL OR quantity IS NULL OR quantity <= 0 THEN NULL
  WHEN unit IN ('g', 'kg') THEN 'kg'
  WHEN unit IN ('ml', 'l') THEN 'l'
  ELSE 'ks'
END
"""


class Base(DeclarativeBase):
    pass


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    website: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SourceEndpoint(Base):
    __tablename__ = "source_endpoints"
    __table_args__ = (
        CheckConstraint(_in("kind", SOURCE_KINDS), name="ck_source_kind"),
        CheckConstraint(_in("legal_status", LEGAL_STATUSES), name="ck_source_legal_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    kind: Mapped[str] = mapped_column(String(20))
    adapter: Mapped[str] = mapped_column(String(40), default="manual")
    url: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    legal_status: Mapped[str] = mapped_column(String(20), default="pending")
    legal_note: Mapped[str | None] = mapped_column(Text)
    legal_reviewed_at: Mapped[date | None] = mapped_column(Date)
    terms_url: Mapped[str | None] = mapped_column(Text)
    terms_snapshot_key: Mapped[str | None] = mapped_column(Text)
    robots_url: Mapped[str | None] = mapped_column(Text)

    check_interval_minutes: Mapped[int] = mapped_column(Integer, default=30)
    raw_retention_days: Mapped[int] = mapped_column(Integer, default=90)

    # stav lacnej kontroly zmien
    etag: Mapped[str | None] = mapped_column(Text)
    last_modified: Mapped[str | None] = mapped_column(Text)
    last_hash: Mapped[str | None] = mapped_column(String(64))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)

    store: Mapped[Store] = relationship()


class RawDocument(Base):
    __tablename__ = "raw_documents"
    __table_args__ = (UniqueConstraint("source_endpoint_id", "sha256"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_endpoint_id: Mapped[int] = mapped_column(ForeignKey("source_endpoints.id"))
    sha256: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str | None] = mapped_column(Text)  # NULL po uplynutí retencie
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    delete_after: Mapped[date | None] = mapped_column(Date)


class Flyer(Base):
    __tablename__ = "flyers"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    source_endpoint_id: Mapped[int] = mapped_column(ForeignKey("source_endpoints.id"))
    title: Mapped[str | None] = mapped_column(Text)
    validity: Mapped[Range[date]] = mapped_column(DATERANGE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FlyerVersion(Base):
    __tablename__ = "flyer_versions"
    __table_args__ = (UniqueConstraint("flyer_id", "version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    flyer_id: Mapped[int] = mapped_column(ForeignKey("flyers.id"))
    raw_document_id: Mapped[int] = mapped_column(ForeignKey("raw_documents.id"))
    version: Mapped[int] = mapped_column(Integer)
    validity: Mapped[Range[date]] = mapped_column(DATERANGE)
    page_count: Mapped[int] = mapped_column(Integer)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    flyer: Mapped[Flyer] = relationship()


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_endpoint_id: Mapped[int] = mapped_column(ForeignKey("source_endpoints.id"))
    raw_document_id: Mapped[int | None] = mapped_column(ForeignKey("raw_documents.id"))
    flyer_version_id: Mapped[int | None] = mapped_column(ForeignKey("flyer_versions.id"))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # running | unchanged | skipped | succeeded | failed
    status: Mapped[str] = mapped_column(String(20), default="running")
    content_hash: Mapped[str | None] = mapped_column(String(64))
    parser_version: Mapped[str | None] = mapped_column(String(40))
    extraction_version: Mapped[str | None] = mapped_column(String(40))
    model_id: Mapped[str | None] = mapped_column(String(80))
    offers_count: Mapped[int] = mapped_column(Integer, default=0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
    error: Mapped[str | None] = mapped_column(Text)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    unit_basis: Mapped[str | None] = mapped_column(String(4))
    unit_price_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    unit_price_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))


class Offer(Base):
    __tablename__ = "offers"
    __table_args__ = (
        CheckConstraint("price > 0", name="ck_offer_price_positive"),
        CheckConstraint(f"unit IS NULL OR {_in('unit', UNITS)}", name="ck_offer_unit"),
        CheckConstraint(_in("price_type", PRICE_TYPES), name="ck_offer_price_type"),
        CheckConstraint(_in("status", OFFER_STATUSES), name="ck_offer_status"),
        CheckConstraint("NOT isempty(validity)", name="ck_offer_validity_nonempty"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    flyer_version_id: Mapped[int] = mapped_column(ForeignKey("flyer_versions.id"))
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    extraction_run_id: Mapped[int] = mapped_column(ForeignKey("extraction_runs.id"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))

    raw_name: Mapped[str] = mapped_column(Text)
    brand: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    regular_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="CZK")
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    unit: Mapped[str | None] = mapped_column(String(3))
    pack_count: Mapped[int | None] = mapped_column(Integer)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), Computed(UNIT_PRICE_SQL, persisted=True))
    unit_price_basis: Mapped[str | None] = mapped_column(String(2), Computed(UNIT_PRICE_BASIS_SQL, persisted=True))
    price_type: Mapped[str] = mapped_column(String(10), default="standard")
    validity: Mapped[Range[date]] = mapped_column(DATERANGE)

    source_page: Mapped[int] = mapped_column(Integer)
    bbox: Mapped[list[float] | None] = mapped_column(JSONB)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    status: Mapped[str] = mapped_column(String(10), default="active")
    superseded_by: Mapped[int | None] = mapped_column(ForeignKey("offers.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    store: Mapped[Store] = relationship()
    flyer_version: Mapped[FlyerVersion] = relationship()
    conditions: Mapped[list["OfferCondition"]] = relationship(back_populates="offer", order_by="OfferCondition.id")


class OfferCondition(Base):
    __tablename__ = "offer_conditions"
    __table_args__ = (CheckConstraint(_in("kind", CONDITION_KINDS), name="ck_condition_kind"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(20))
    # napr. {"buy": 2, "get": 1}, {"min_qty": 3}, {"program": "Lidl Plus"}
    value: Mapped[dict | None] = mapped_column(JSONB)
    note: Mapped[str | None] = mapped_column(Text)

    offer: Mapped[Offer] = relationship(back_populates="conditions")


class ValidationEvent(Base):
    """Chyby validácie a review queue."""

    __tablename__ = "validation_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    extraction_run_id: Mapped[int] = mapped_column(ForeignKey("extraction_runs.id"))
    offer_id: Mapped[int | None] = mapped_column(ForeignKey("offers.id"))
    source_page: Mapped[int | None] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(10))  # reject | review | warning
    code: Mapped[str] = mapped_column(String(60))
    message: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(10), default="open")  # open | approved | rejected
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApiAuditEvent(Base):
    __tablename__ = "api_audit_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    channel: Mapped[str] = mapped_column(String(20))  # rest | mcp | ai
    action: Mapped[str] = mapped_column(String(60))
    params: Mapped[dict | None] = mapped_column(JSONB)
    result_count: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
