"""The offline audit must reject modified criteria, actions and behavioral screens."""

import importlib
import json
from pathlib import Path

import httpx
import pytest

from jev_atari import criteria_study
from jev_atari.choice import ActionProgram, ChoiceEvaluator
from jev_atari.criteria_study import CriteriaBudget
from jev_atari.io import read_json, write_json
from jev_atari.question_diagnostics import interpret
from jev_atari.study import AllocatedBudget

ROOT = Path(__file__).resolve().parents[1]


def test_full_probe_roundtrip_and_tampering(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    auditor = importlib.import_module("verify_criteria_study")
    states = read_json(ROOT / "experiments/pong/motion-probe-v1/inputs.json")
    baseline = ActionProgram.from_dict(read_json(ROOT / "examples/vertical-policy-program.json"))
    criteria = baseline.request(states[0]["observation"], "jev-1.13.0")["questions"]["next_action"][
        "criteria"
    ]
    candidate = ActionProgram(
        name="synthetic-criteria-probe",
        guidance="Synthetic fixture only.",
        schema_version="action-choice-program-v2",
        action_criteria=criteria,
    )
    programs = {"V2": baseline, "A": candidate, "B": candidate}

    def handler(request):
        payload = json.loads(request.content)
        obs = payload["state"]["observation"]
        action = interpret(obs, "v2")["action"]
        name = next(a["ale_meaning"] for a in obs["candidate_actions"] if a["id"] == action)
        return httpx.Response(
            200,
            json={
                "model": "jev-1.13.0",
                "usage": {"input_tokens": 1, "output_tokens": 1},
                "answers": {
                    "next_action": {
                        "type": "choice",
                        "choice": name,
                        "confidence": 1,
                        "probabilities": {k: int(k == name) for k in criteria},
                    }
                },
            },
        )

    monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-key")

    def factory(budget, phase, cap):
        ev = ChoiceEvaluator(
            model="jev-1.13.0",
            max_calls=cap,
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        ev.api.budget = AllocatedBudget(budget, phase, cap)
        return ev

    monkeypatch.setattr(criteria_study, "evaluator_for", factory)
    budget = CriteriaBudget(tmp_path / "budget.json")
    root = tmp_path / "probe"
    criteria_study.probe(root, states, programs, budget)
    assert len(auditor.verify_probe(root, states, programs)) == 480
    screen = read_json(root / "screen.json")
    modified = json.loads(json.dumps(screen))
    modified["A"]["eligible"] = False
    write_json(root / "screen.json", modified)
    with pytest.raises(AssertionError):
        auditor.verify_probe(root, states, programs)
    write_json(root / "screen.json", screen)
    predictions = (root / "predictions.jsonl").read_text()
    rows = [json.loads(line) for line in predictions.splitlines()]
    rows[0]["prediction"]["chosen_action"] = 5
    (root / "predictions.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    with pytest.raises(AssertionError):
        auditor.verify_probe(root, states, programs)
    (root / "predictions.jsonl").write_text(predictions)
    raw = [json.loads(line) for line in (root / "model-exchanges.jsonl").read_text().splitlines()]
    raw[0]["request"]["questions"]["next_action"]["criteria"]["LEFT"] = "Tampered criterion"
    (root / "model-exchanges.jsonl").write_text("\n".join(json.dumps(r) for r in raw) + "\n")
    with pytest.raises(AssertionError):
        auditor.verify_probe(root, states, programs)
