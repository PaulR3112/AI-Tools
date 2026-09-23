"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-09-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    # unaccent() nie je IMMUTABLE, preto wrapper – umožní funkčný index
    op.execute(
        """
        CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text
        LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
        AS $$ SELECT public.unaccent('public.unaccent'::regdictionary, lower($1)) $$
        """
    )

    op.create_table('api_audit_events',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('channel', sa.String(length=20), nullable=False),
    sa.Column('action', sa.String(length=60), nullable=False),
    sa.Column('params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('result_count', sa.Integer(), nullable=True),
    sa.Column('duration_ms', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('parent_id', sa.Integer(), nullable=True),
    sa.Column('slug', sa.String(length=80), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('unit_basis', sa.String(length=4), nullable=True),
    sa.Column('unit_price_min', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('unit_price_max', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.ForeignKeyConstraint(['parent_id'], ['categories.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug')
    )
    op.create_table('stores',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=40), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('website', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('source_endpoints',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('store_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('adapter', sa.String(length=40), nullable=False),
    sa.Column('url', sa.Text(), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('legal_status', sa.String(length=20), nullable=False),
    sa.Column('legal_note', sa.Text(), nullable=True),
    sa.Column('legal_reviewed_at', sa.Date(), nullable=True),
    sa.Column('terms_url', sa.Text(), nullable=True),
    sa.Column('terms_snapshot_key', sa.Text(), nullable=True),
    sa.Column('robots_url', sa.Text(), nullable=True),
    sa.Column('check_interval_minutes', sa.Integer(), nullable=False),
    sa.Column('raw_retention_days', sa.Integer(), nullable=False),
    sa.Column('etag', sa.Text(), nullable=True),
    sa.Column('last_modified', sa.Text(), nullable=True),
    sa.Column('last_hash', sa.String(length=64), nullable=True),
    sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('consecutive_failures', sa.Integer(), nullable=False),
    sa.CheckConstraint("kind IN ('structured', 'pdf', 'image')", name='ck_source_kind'),
    sa.CheckConstraint("legal_status IN ('approved', 'pending', 'rejected')", name='ck_source_legal_status'),
    sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('flyers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('store_id', sa.Integer(), nullable=False),
    sa.Column('source_endpoint_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.Text(), nullable=True),
    sa.Column('validity', postgresql.DATERANGE(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['source_endpoint_id'], ['source_endpoints.id'], ),
    sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('raw_documents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_endpoint_id', sa.Integer(), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('storage_key', sa.Text(), nullable=True),
    sa.Column('content_type', sa.String(length=100), nullable=False),
    sa.Column('size_bytes', sa.BigInteger(), nullable=False),
    sa.Column('fetched_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('delete_after', sa.Date(), nullable=True),
    sa.ForeignKeyConstraint(['source_endpoint_id'], ['source_endpoints.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source_endpoint_id', 'sha256')
    )
    op.create_table('flyer_versions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('flyer_id', sa.Integer(), nullable=False),
    sa.Column('raw_document_id', sa.Integer(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('validity', postgresql.DATERANGE(), nullable=False),
    sa.Column('page_count', sa.Integer(), nullable=False),
    sa.Column('is_current', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['flyer_id'], ['flyers.id'], ),
    sa.ForeignKeyConstraint(['raw_document_id'], ['raw_documents.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('flyer_id', 'version')
    )
    op.create_table('extraction_runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_endpoint_id', sa.Integer(), nullable=False),
    sa.Column('raw_document_id', sa.Integer(), nullable=True),
    sa.Column('flyer_version_id', sa.Integer(), nullable=True),
    sa.Column('checked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=True),
    sa.Column('parser_version', sa.String(length=40), nullable=True),
    sa.Column('extraction_version', sa.String(length=40), nullable=True),
    sa.Column('model_id', sa.String(length=80), nullable=True),
    sa.Column('offers_count', sa.Integer(), nullable=False),
    sa.Column('review_count', sa.Integer(), nullable=False),
    sa.Column('rejected_count', sa.Integer(), nullable=False),
    sa.Column('duration_ms', sa.Integer(), nullable=True),
    sa.Column('input_tokens', sa.Integer(), nullable=False),
    sa.Column('output_tokens', sa.Integer(), nullable=False),
    sa.Column('cost_usd', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['flyer_version_id'], ['flyer_versions.id'], ),
    sa.ForeignKeyConstraint(['raw_document_id'], ['raw_documents.id'], ),
    sa.ForeignKeyConstraint(['source_endpoint_id'], ['source_endpoints.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('offers',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('flyer_version_id', sa.Integer(), nullable=False),
    sa.Column('store_id', sa.Integer(), nullable=False),
    sa.Column('extraction_run_id', sa.Integer(), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=True),
    sa.Column('raw_name', sa.Text(), nullable=False),
    sa.Column('brand', sa.Text(), nullable=True),
    sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('regular_price', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=10, scale=3), nullable=True),
    sa.Column('unit', sa.String(length=3), nullable=True),
    sa.Column('pack_count', sa.Integer(), nullable=True),
    sa.Column('unit_price', sa.Numeric(precision=12, scale=2), sa.Computed("\nCASE\n  WHEN price_type = 'per_kg' THEN price\n  WHEN unit IS NULL OR quantity IS NULL OR quantity <= 0 THEN NULL\n  WHEN unit IN ('g', 'ml') THEN round(price * 1000 / (quantity * coalesce(pack_count, 1)), 2)\n  ELSE round(price / (quantity * coalesce(pack_count, 1)), 2)\nEND\n", persisted=True), nullable=True),
    sa.Column('unit_price_basis', sa.String(length=2), sa.Computed("\nCASE\n  WHEN price_type = 'per_kg' THEN 'kg'\n  WHEN unit IS NULL OR quantity IS NULL OR quantity <= 0 THEN NULL\n  WHEN unit IN ('g', 'kg') THEN 'kg'\n  WHEN unit IN ('ml', 'l') THEN 'l'\n  ELSE 'ks'\nEND\n", persisted=True), nullable=True),
    sa.Column('price_type', sa.String(length=10), nullable=False),
    sa.Column('validity', postgresql.DATERANGE(), nullable=False),
    sa.Column('source_page', sa.Integer(), nullable=False),
    sa.Column('bbox', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('confidence', sa.Numeric(precision=3, scale=2), nullable=True),
    sa.Column('status', sa.String(length=10), nullable=False),
    sa.Column('superseded_by', sa.BigInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("price_type IN ('standard', 'from', 'per_kg', 'multibuy')", name='ck_offer_price_type'),
    sa.CheckConstraint("status IN ('active', 'review', 'rejected')", name='ck_offer_status'),
    sa.CheckConstraint("unit IS NULL OR unit IN ('g', 'kg', 'ml', 'l', 'ks')", name='ck_offer_unit'),
    sa.CheckConstraint('NOT isempty(validity)', name='ck_offer_validity_nonempty'),
    sa.CheckConstraint('price > 0', name='ck_offer_price_positive'),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
    sa.ForeignKeyConstraint(['extraction_run_id'], ['extraction_runs.id'], ),
    sa.ForeignKeyConstraint(['flyer_version_id'], ['flyer_versions.id'], ),
    sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ),
    sa.ForeignKeyConstraint(['superseded_by'], ['offers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('offer_conditions',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('offer_id', sa.BigInteger(), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.CheckConstraint("kind IN ('loyalty_card', 'min_qty', 'multibuy', 'app_only', 'coupon')", name='ck_condition_kind'),
    sa.ForeignKeyConstraint(['offer_id'], ['offers.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('validation_events',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('extraction_run_id', sa.Integer(), nullable=False),
    sa.Column('offer_id', sa.BigInteger(), nullable=True),
    sa.Column('source_page', sa.Integer(), nullable=True),
    sa.Column('severity', sa.String(length=10), nullable=False),
    sa.Column('code', sa.String(length=60), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('status', sa.String(length=10), nullable=False),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['extraction_run_id'], ['extraction_runs.id'], ),
    sa.ForeignKeyConstraint(['offer_id'], ['offers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_index("ix_offers_validity", "offers", ["validity"], postgresql_using="gist")
    op.create_index("ix_offers_store_status", "offers", ["store_id", "status"])
    op.create_index("ix_offers_flyer_version", "offers", ["flyer_version_id"])
    op.execute("CREATE INDEX ix_offers_name_trgm ON offers USING gin (f_unaccent(raw_name) gin_trgm_ops)")
    op.create_index("ix_flyers_source_validity", "flyers", ["source_endpoint_id", "validity"])
    op.create_index("ix_validation_events_open", "validation_events", ["status", "severity"])
    op.create_index("ix_extraction_runs_source", "extraction_runs", ["source_endpoint_id", "checked_at"])
    # idempotencia: rovnaký obsah + verzia extrakcie sa úspešne spracuje len raz
    op.create_index(
        "ux_extraction_runs_hash_version",
        "extraction_runs",
        ["content_hash", "extraction_version"],
        unique=True,
        postgresql_where=sa.text("status = 'succeeded'"),
    )


def downgrade() -> None:
    op.drop_table('validation_events')
    op.drop_table('offer_conditions')
    op.drop_table('offers')
    op.drop_table('extraction_runs')
    op.drop_table('flyer_versions')
    op.drop_table('raw_documents')
    op.drop_table('flyers')
    op.drop_table('source_endpoints')
    op.drop_table('stores')
    op.drop_table('categories')
    op.drop_table('api_audit_events')
    op.execute("DROP FUNCTION IF EXISTS f_unaccent(text)")
