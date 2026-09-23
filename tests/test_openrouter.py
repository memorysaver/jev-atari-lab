"""Provider switching preserves question semantics and rejects model drift before action."""

import json
import sys

import httpx
import pytest

from jev_atari import cli
from jev_atari.choice import ActionPolicy, ActionProgram
from jev_atari.environment import Protocol
from jev_atari.experiment import play
from jev_atari.io import read_json
from jev_atari.models import ModelError
from jev_atari.openrouter import ENDPOINT, OpenRouterChoiceEvaluator
from jev_atari.replay import replay_episode

MODEL = "~typesafe/jev-latest"
PIN = "typesafe/jev-1.13-20260917"


def client_for(response_model=PIN, status=200):
    def handler(request):
        assert str(request.url) == ENDPOINT
        assert request.headers["Authorization"] == "Bearer synthetic-openrouter-key"
        payload = json.loads(request.content)
        assert payload["model"] == MODEL
        if status != 200:
            return httpx.Response(status, text="synthetic-openrouter-key")
        options = payload["questions"]["next_action"]["criteria"]
        return httpx.Response(
            200,
            json={
                "model": response_model,
                "provider": "TypeSafe",
                "usage": {"input_tokens": 12, "output_tokens": 3, "cost": 0.000001},
                "answers": {
                    "next_action": {
                        "type": "choice",
                        "choice": "NOOP",
                        "confidence": 1,
                        "probabilities": {k: int(k == "NOOP") for k in options},
                    }
                },
            },
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_cli_openrouter_rollout_preserves_request_and_replays(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-openrouter-key")
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(
        cli,
        "OpenRouterChoiceEvaluator",
        lambda **kw: OpenRouterChoiceEvaluator(**kw, client=client_for()),
    )
    episode = tmp_path / "episode"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "jev-atari",
            "play",
            "--policy",
            "jev-action",
            "--backend",
            "openrouter",
            "--model",
            MODEL,
            "--expected-response-model",
            PIN,
            "--seed",
            "150",
            "--decisions",
            "3",
            "--max-api-calls",
            "3",
            "--out",
            str(episode),
        ],
    )
    cli.main()
    manifest = read_json(episode / "manifest.json")
    assert manifest["model_transport"]["expected_response_model"] == PIN
    assert manifest["model_transport"]["max_retries"] == 0
    assert read_json(episode / "summary.json")["backend"] == "openrouter"
    rows = [json.loads(s) for s in (episode / "transitions.jsonl").read_text().splitlines()]
    exchanges = [
        json.loads(s) for s in (episode / "model-exchanges.jsonl").read_text().splitlines()
    ]
    for row, exchange in zip(rows, exchanges, strict=True):
        assert exchange["request"] == ActionProgram().request(row["observation"], MODEL)
        assert row["prediction"]["response_model"] == PIN
        assert row["prediction"]["usage"]["cost"] == 0.000001
        assert row["action"] == 0
    replay_episode(episode, tmp_path / "audit")


@pytest.mark.parametrize("failure", ["drift", "402"])
def test_drift_or_payment_failure_executes_no_action_and_does_not_retry(
    tmp_path, monkeypatch, failure
):
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-openrouter-key")
    ev = OpenRouterChoiceEvaluator(
        model=MODEL,
        expected_response_model=PIN,
        max_calls=5,
        client=client_for(
            "unexpected-model" if failure == "drift" else PIN,
            status=402 if failure == "402" else 200,
        ),
    )
    episode = tmp_path / "episode"
    ev.api.trace_path = episode / "model-exchanges.jsonl"
    with pytest.raises(ModelError):
        play(
            Protocol(),
            ActionPolicy(ev, ActionProgram()),
            seed=150,
            decisions=3,
            out=episode,
            evaluator=ev,
        )
    summary = read_json(episode / "summary.json")
    assert summary["status"] == "incomplete" and summary["decisions"] == 0
    assert summary["raw_frames"] == 0 and ev.api.budget.used == 1
    assert "synthetic-openrouter-key" not in (episode / "model-exchanges.jsonl").read_text()
    ev.close()


def test_openrouter_never_falls_back_to_direct_provider_credentials(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-direct-key")
    with pytest.raises(ModelError, match="missing"):
        OpenRouterChoiceEvaluator(model=MODEL, expected_response_model=PIN, max_calls=1)
    with pytest.raises(ValueError, match="pin"):
        OpenRouterChoiceEvaluator(model=MODEL, expected_response_model="", max_calls=1)
