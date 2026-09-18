import json

import httpx
import pytest

from jev_atari.models import CallBudget, JsonAPI, ModelError


def test_exchange_log_redacts_credentials_and_retains_request_response(tmp_path):
    key = "private-test-credential"
    api = JsonAPI(
        "https://example.test",
        key,
        CallBudget(1),
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={"model": "test", "answers": {}, "echo": key})
            )
        ),
    )
    api.trace_path = tmp_path / "exchanges.jsonl"
    request = {"model": "test", "state": {"frame": 4}, "questions": {}}
    try:
        api.post(request)
    finally:
        api.close()
    text = api.trace_path.read_text()
    assert key not in text
    assert "Authorization" not in text
    recorded = json.loads(text)
    assert recorded["request"] == request
    assert recorded["response"]["echo"] == "[REDACTED]"


def test_error_response_body_is_not_saved(tmp_path):
    api = JsonAPI(
        "https://example.test",
        "test-key",
        CallBudget(1),
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(401, text="sensitive-error-body")
            )
        ),
    )
    api.trace_path = tmp_path / "exchanges.jsonl"
    try:
        with pytest.raises(ModelError):
            api.post({"model": "test"})
    finally:
        api.close()
    assert "sensitive-error-body" not in api.trace_path.read_text()
    assert json.loads(api.trace_path.read_text())["transport"]["status"] == 401
