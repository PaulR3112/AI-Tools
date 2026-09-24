from pathlib import Path

from app.config import get_settings
from app.ingestion.extractor import ClaudeExtractor, PageExtractor, RecordedExtractor
from app.ingestion.pipeline import Deps
from app.ingestion.storage import LocalStorage


def build_deps(recorded: Path | None = None) -> Deps:
    settings = get_settings()
    extractor: PageExtractor = RecordedExtractor(recorded) if recorded else ClaudeExtractor(settings)
    return Deps(settings=settings, storage=LocalStorage(settings.storage_dir), extractor=extractor)
