from dataclasses import dataclass
from typing import Protocol

from app.models import SourceEndpoint


@dataclass
class FetchResult:
    not_modified: bool
    content: bytes | None = None
    content_type: str | None = None
    etag: str | None = None
    last_modified: str | None = None


class Adapter(Protocol):
    """Adaptér zdroja. Structured zdroje (HTML/JSON) neskôr vrátia ponuky priamo bez vision kroku."""

    def fetch(self, source: SourceEndpoint, user_agent: str) -> FetchResult: ...
