"""Synthetic requests and local emulator checks; no live model calls."""

import json
import sys
from pathlib import Path

import httpx
import pytest

from jev_atari import seaquest_execution as study
from jev_atari import seaquest_research as research
from jev_atari.io import digest, read_json, write_json
from jev_atari.models import BudgetExceeded
from jev_atari.seaquest_pilot import PIN, SeaquestProgram


def observation(y=90, oxygen=40, carried=0, facing="right", others=()):
    return {
        "schema_version": "seaquest-objects-v2",
        "game": "ALE/Seaquest-v5",
        "object_state": "active",
        "oxygen_raw": oxygen,
        "carried_divers": carried,
        "objects": [{"kind": "player", "bbox": [40, y, 16, 10], "facing": facing}, *others],
        "candidate_actions": [{"id": i, "ale_meaning": n} for i, n in enumerate(study.NAMES)],
    }


@pytest.mark.parametrize(
    "obs,rule,expected",
    [
        (observation(y=46, oxygen=59, carried=6), "late-diver", "FIRE"),
        (observation(oxygen=20, carried=1), "late-diver", "UPFIRE"),
        (observation(oxygen=20), "simple", "UPFIRE"),
        (observation(oxygen=20), "late-diver", "FIRE"),
        (observation(y=85), "late-diver", "DOWNFIRE"),
        (observation(y=101), "late-diver", "UPFIRE"),
        (
            observation(oxygen=32, others=[{"kind": "diver", "bbox": [60, 90, 8, 10]}]),
            "late-diver",
            "RIGHTFIRE",
        ),
        (
            observation(oxygen=33, others=[{"kind": "diver", "bbox": [60, 90, 8, 10]}]),
            "late-diver",
            "FIRE",
        ),
        (
            observation(oxygen=32, others=[{"kind": "diver", "bbox": [60, 100, 8, 10]}]),
            "late-diver",
            "DOWNFIRE",
        ),
        (
            observation(facing="left", others=[{"kind": "shark", "bbox": [60, 90, 8, 10]}]),
            "late-diver",
            "RIGHTFIRE",
        ),
        (
            observation(facing="right", others=[{"kind": "shark", "bbox": [20, 90, 8, 10]}]),
            "late-diver",
            "LEFTFIRE",
        ),
    ],
)
def test_priority_and_boundary_rule_cases(obs, rule, expected):
    assert study.literal(obs, rule)[0] == expected


def test_round_cap_deadline_and_closed_budget(tmp_path):
    path = tmp_path / "budget.json"
    with pytest.raises(BudgetExceeded):
        study.ExecutionBudget(path, 1, clock=lambda: 10).reserve()
    first = study.ExecutionBudget(path, 2, clock=lambda: 10)
    first.reserve()
    assert study.ExecutionBudget(path, 3).used == 1
    with pytest.raises(BudgetExceeded):
        study.ExecutionBudget(path, 3, clock=lambda: 86410).reserve()
    value = read_json(path)
    value["round_attempts"]["2"] = 400
    write_json(path, value)
    with pytest.raises(BudgetExceeded):
        first.reserve()
    value["closed"] = True
    write_json(path, value)
    with pytest.raises(BudgetExceeded):
        study.ExecutionBudget(path, 4).reserve()


def test_mock_probe_preserves_states_no_label_leakage_and_charges_retries(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-key")
    obs = observation()
    original = digest(obs)
    calls = []
    budget = study.ExecutionBudget(tmp_path / "budget.json", 2)

    def handler(request):
        body = json.loads(request.content)
        calls.append(body)
        assert body["state"] == {"observation": obs}
        assert read_json(budget.path)["used"] == len(calls)
        if len(calls) == 1:
            return httpx.Response(520)
        options = body["questions"]["next_action"]["criteria"]
        return httpx.Response(
            200,
            json={
                "model": PIN,
                "answers": {
                    "next_action": {
                        "type": "choice",
                        "choice": "FIRE",
                        "confidence": 1,
                        "probabilities": {k: int(k == "FIRE") for k in options},
                    }
                },
            },
        )

    ev = research.ResearchEvaluator(
        budget, client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    program = SeaquestProgram()
    try:
        metrics = study.probe(
            tmp_path / "probe",
            {"rows": [{"id": original, "observation": obs}]},
            {"reference": (program, "late-diver"), "candidate": (program, "late-diver")},
            ev,
        )
    finally:
        ev.close()
    assert budget.used == 3 and calls[0] == calls[1] == calls[2]
    assert digest(obs) == original and metrics["reference"]["matches"] == 1
    assert not study.execution_gate(metrics)["passed"]


def test_local_control_video_is_not_a_model_prediction(tmp_path, monkeypatch):
    monkeypatch.setattr(research, "DECISIONS", 3)
    ev = study.LiteralEvaluator("late-diver")
    summary = research.play_episode(tmp_path / "episode", 320, ev, "synthetic", SeaquestProgram())
    assert summary["api_attempts"] == 0 and summary["agent_decisions"] == 3
    rows = [
        json.loads(x) for x in (tmp_path / "episode/transitions.jsonl").read_text().splitlines()
    ]
    assert all(
        r["prediction"]["kind"] == "local-literal-control" for r in rows if r["phase"] == "control"
    )
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from seaquest_observation_check import verify_episode

    assert verify_episode(tmp_path / "episode", tmp_path / "audit")["status"] == "verified"
    with pytest.raises(ValueError, match="Wrong split"):
        study.build_packet([tmp_path / "episode"], split="test")


def test_sixth_round_rejected_without_calls(tmp_path, monkeypatch):
    monkeypatch.setattr(study, "source_revision", lambda: "frozen")
    write_json(tmp_path / "plan.json", {"source_revision": "frozen"})
    write_json(tmp_path / "results.json", {"status": "running", "rounds": [{}] * 5})
    with pytest.raises(ValueError, match="exactly five"):
        study.run_round(tmp_path, 6)
    assert not (tmp_path / "round-06").exists()


def test_five_round_mock_pipeline_and_full_offline_audit(tmp_path, monkeypatch):
    """Exercise selection fallback, final pairing and original exchange auditing together."""
    # Completed local studies must not contaminate this synthetic fresh-seed check.
    monkeypatch.setattr(study, "REVIEWED", study.REVIEWED.resolve())
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-key")
    monkeypatch.setattr(research, "DECISIONS", 4)
    monkeypatch.setattr(study, "source_revision", lambda: "synthetic-frozen")
    origin = tmp_path / "origin"
    monkeypatch.setattr(study, "SOURCE", origin)
    reference_value = read_json(study.REVIEWED / "round-08/proposal.json")["program"]
    for number, rule in ((3, "simple"), (8, "late-diver")):
        program = study.load_program(
            read_json(study.REVIEWED / f"round-{number:02d}/proposal.json")["program"]
        )
        for seed in study.TRAIN:
            research.play_episode(
                origin / f"round-{number:02d}/candidate/seed-{seed}",
                seed,
                study.LiteralEvaluator(rule),
                "synthetic-source",
                program,
            )
    root = tmp_path / "study"
    study.initialize(root)

    def handler(request):
        body = json.loads(request.content)
        options = body["questions"]["next_action"]["criteria"]
        return httpx.Response(
            200,
            json={
                "model": PIN,
                "answers": {
                    "next_action": {
                        "type": "choice",
                        "choice": "FIRE",
                        "confidence": 1,
                        "probabilities": {k: int(k == "FIRE") for k in options},
                    }
                },
            },
        )

    monkeypatch.setattr(
        study,
        "ResearchEvaluator",
        lambda budget: research.ResearchEvaluator(
            budget, client=httpx.Client(transport=httpx.MockTransport(handler))
        ),
    )
    study.run_round(root, 1)
    study.run_round(root, 2)
    for number in (3, 4):
        value = {**reference_value, "name": f"synthetic-variant-{number}"}
        path = root / f"proposal-{number}.json"
        write_json(
            path,
            {
                "origin": "interactive-coordinator-training-feedback",
                "hypothesis": "Synthetic",
                "program": value,
                "evidence": [str(root / "round-02/results.json")],
                "risks": "Synthetic",
                "intended_rule": "late-diver",
            },
        )
        study.run_round(root, number, path)
    study.run_round(root, 5)
    assert read_json(root / "budget.json")["closed"]
    assert read_json(root / "finalist-seal.json")["selected_round"] == 2
    assert not read_json(root / "round-05/results.json")["wording_improvement_gate"]
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from verify_seaquest_execution import verify

    result = verify(root, tmp_path / "audit")
    assert result["status"] == "verified" and len(result["episodes"]) == 10
