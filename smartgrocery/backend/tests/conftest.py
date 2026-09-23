import io
import os
from pathlib import Path

import pytest

os.environ.setdefault("SG_DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/smartgrocery_test")
os.environ["SG_ADMIN_TOKEN"] = "test-admin-token"

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import get_engine, get_sessionmaker  # noqa: E402
from app.ingestion.extractor import RecordedExtractor  # noqa: E402
from app.ingestion.pipeline import Deps  # noqa: E402
from app.ingestion.storage import LocalStorage  # noqa: E402
from app.models import SourceEndpoint, Store  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).parent / "fixtures"
TABLES = (
    "api_audit_events, validation_events, offer_conditions, offers, extraction_runs, "
    "flyer_versions, flyers, raw_documents, source_endpoints, categories, stores"
)


@pytest.fixture(scope="session", autouse=True)
def _migrate():
    command.upgrade(Config(str(BACKEND / "alembic.ini")), "head")
    yield


@pytest.fixture
def session(_migrate):
    with get_engine().begin() as conn:
        conn.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
    with get_sessionmaker()() as s:
        yield s


def make_pdf(pages: int = 2) -> bytes:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument.new()
    for _ in range(pages):
        pdf.new_page(595, 842)
    buf = io.BytesIO()
    pdf.save(buf)
    pdf.close()
    return buf.getvalue()


@pytest.fixture
def flyer_pdf(tmp_path) -> Path:
    path = tmp_path / "letak.pdf"
    path.write_bytes(make_pdf(2))
    return path


@pytest.fixture
def deps(tmp_path) -> Deps:
    return Deps(
        settings=get_settings(),
        storage=LocalStorage(tmp_path / "raw"),
        extractor=RecordedExtractor(FIXTURES / "flyer_recorded.json"),
    )


@pytest.fixture
def source(session, flyer_pdf) -> SourceEndpoint:
    store = Store(code="testmarket", name="TestMarket")
    session.add(store)
    session.flush()
    src = SourceEndpoint(
        store_id=store.id,
        kind="pdf",
        adapter="manual",
        url=str(flyer_pdf),
        legal_status="approved",
        legal_note="test",
    )
    session.add(src)
    session.commit()
    return src
