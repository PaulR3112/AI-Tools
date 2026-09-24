"""ClaudeExtractor bez siete: kontroluje tvar požiadavky a spracovanie odpovede."""

import json
from datetime import date

import anthropic
import httpx2
import pytest

from app.config import Settings
from app.ingestion.extractor import ClaudeExtractor, ExtractionError, PageContext

PAGE_JSON = {
    "flyer_valid_from": "2026-09-23",
    "flyer_valid_to": "2026-09-29",
    "offers": [],
}
CTX = PageContext("Lidl", 1, 12, date(2026, 9, 23))


def make_client(captured: list, stop_reason: str = "end_turn", text: str | None = None) -> anthropic.Anthropic:
    def handler(request: httpx2.Request) -> httpx2.Response:
        captured.append(request)
        return httpx2.Response(
            200,
            json={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "model": "claude-opus-5",
                "content": [{"type": "text", "text": text if text is not None else json.dumps(PAGE_JSON)}],
                "stop_reason": stop_reason,
                "stop_sequence": None,
                "usage": {"input_tokens": 1500, "output_tokens": 400},
            },
        )

    return anthropic.Anthropic(
        api_key="test", http_client=httpx2.Client(transport=httpx2.MockTransport(handler)), max_retries=0
    )


def test_request_shape_and_parsed_output():
    captured: list[httpx2.Request] = []
    extractor = ClaudeExtractor(Settings(), client=make_client(captured))
    result = extractor.extract(b"\x89PNG fake", CTX)

    assert result.page.flyer_valid_to == "2026-09-29"
    assert (result.input_tokens, result.output_tokens, result.model_id) == (1500, 400, "claude-opus-5")

    req = captured[0]
    body = json.loads(req.content)
    assert body["model"] == "claude-opus-5"
    assert body["output_config"]["effort"] == "high"
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert body["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in req.headers["anthropic-beta"]
    content = body["messages"][0]["content"]
    assert content[0]["type"] == "image" and content[0]["source"]["media_type"] == "image/png"
    assert "Stránka 1 z 12" in content[1]["text"]


def test_fallbacks_can_be_disabled():
    captured: list[httpx2.Request] = []
    extractor = ClaudeExtractor(Settings(llm_server_fallbacks=False), client=make_client(captured))
    extractor.extract(b"png", CTX)
    assert "fallbacks" not in json.loads(captured[0].content)


def test_refusal_and_truncation_raise():
    with pytest.raises(ExtractionError, match="odmietol"):
        ClaudeExtractor(Settings(), client=make_client([], stop_reason="refusal", text="")).extract(b"png", CTX)
    with pytest.raises(ExtractionError, match="max_tokens"):
        ClaudeExtractor(Settings(), client=make_client([], stop_reason="max_tokens", text='{"offers": [')).extract(
            b"png", CTX
        )
