"""No live calls: retry identity, immutable budgets, and pre-action failure paths."""

import json

import httpx
import pytest

from jev_atari import seaquest_pilot as pilot
from jev_atari.io import read_json
from jev_atari.models import BudgetExceeded, ModelError


def test_transient_retry_preserves_state_and_reserves_before_send(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-key")
    monkeypatch.setattr(pilot, "DECISIONS", 3)
    budget = pilot.PilotBudget(tmp_path / "budget.json")
    requests = []

    def handler(request):
        payload = json.loads(request.content)
        requests.append(payload)
        assert read_json(budget.path)["used"] == len(requests)
        if len(requests) <= 2:
            return httpx.Response(502, text="synthetic-key")
        options = payload["questions"]["next_action"]["criteria"]
        assert len(options) == 18
        return httpx.Response(
            200,
            json={
                "model": pilot.PIN,
                "usage": {"input_tokens": 3, "output_tokens": 1, "cost": 0.000001},
                "answers": {
                    "next_action": {
                        "type": "choice",
                        "choice": "DOWNFIRE",
                        "confidence": 1,
                        "probabilities": {k: int(k == "DOWNFIRE") for k in options},
                    }
                },
            },
        )

    ev = pilot.PilotEvaluator(budget, client=httpx.Client(transport=httpx.MockTransport(handler)))
    try:
        root = tmp_path / "episode"
        summary = pilot.play_episode(root, 310, ev, "synthetic-source", pilot.SeaquestProgram())
        assert summary["status"] == "complete" and summary["frames"] == 12
        assert budget.used == 5 and summary["decisions"] == 3
        assert requests[0] == requests[1] == requests[2]
        assert "synthetic-key" not in (root / "model-exchanges.jsonl").read_text()
        assert read_json(root / "manifest.json")["model_transport"]["max_retries"] == 2
    finally:
        ev.close()


@pytest.mark.parametrize("failure", ["402", "drift"])
def test_nonretryable_failure_executes_no_action(tmp_path, monkeypatch, failure):
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-key")
    monkeypatch.setattr(pilot, "DECISIONS", 3)
    budget = pilot.PilotBudget(tmp_path / "budget.json")

    def handler(request):
        if failure == "402":
            return httpx.Response(402)
        options = json.loads(request.content)["questions"]["next_action"]["criteria"]
        return httpx.Response(
            200,
            json={
                "model": "typesafe/changed",
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

    ev = pilot.PilotEvaluator(budget, client=httpx.Client(transport=httpx.MockTransport(handler)))
    try:
        root = tmp_path / "episode"
        with pytest.raises(ModelError):
            pilot.play_episode(root, 310, ev, "synthetic", pilot.SeaquestProgram())
        summary = read_json(root / "summary.json")
        assert summary["status"] == "incomplete" and summary["frames"] == 0
        assert summary["decisions"] == 0 and budget.used == 1
    finally:
        ev.close()


def test_budget_cannot_reset_or_exceed_deadline(tmp_path):
    now = [10]
    budget = pilot.PilotBudget(tmp_path / "budget.json", clock=lambda: now[0])
    budget.reserve()
    now[0] += 7200
    with pytest.raises(BudgetExceeded):
        budget.reserve()
    assert read_json(budget.path)["used"] == 1
    with pytest.raises(ValueError):
        pilot.PilotBudget(budget.path)
