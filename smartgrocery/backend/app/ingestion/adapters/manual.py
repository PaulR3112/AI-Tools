"""Manuálny adaptér: ručne zadaná URL (http/https) alebo lokálny súbor (file:// / cesta).

Neobsahuje logiku žiadneho konkrétneho obchodu – tie vzniknú až po posúdení legal_status.
"""

import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx

from app.ingestion.adapters.base import FetchResult
from app.models import SourceEndpoint


class ManualAdapter:
    timeout = 60.0

    def fetch(self, source: SourceEndpoint, user_agent: str) -> FetchResult:
        parsed = urlparse(source.url)
        if parsed.scheme in ("http", "https"):
            return self._fetch_http(source, user_agent)
        path = Path(unquote(parsed.path)) if parsed.scheme == "file" else Path(source.url)
        return self._fetch_file(path)

    def _fetch_http(self, source: SourceEndpoint, user_agent: str) -> FetchResult:
        headers = {"User-Agent": user_agent}
        if source.etag:
            headers["If-None-Match"] = source.etag
        if source.last_modified:
            headers["If-Modified-Since"] = source.last_modified
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            r = client.get(source.url, headers=headers)
        if r.status_code == 304:
            return FetchResult(not_modified=True, etag=source.etag, last_modified=source.last_modified)
        r.raise_for_status()
        content_type = r.headers.get("content-type", "application/octet-stream").split(";")[0].strip()
        return FetchResult(
            not_modified=False,
            content=r.content,
            content_type=content_type,
            etag=r.headers.get("etag"),
            last_modified=r.headers.get("last-modified"),
        )

    def _fetch_file(self, path: Path) -> FetchResult:
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return FetchResult(not_modified=False, content=path.read_bytes(), content_type=content_type)
