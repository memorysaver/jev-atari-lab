"""Synthetic checks for candidate feedback, transport audit, and bounded stage closure."""

import json
from pathlib import Path

import pytest
from test_openrouter import client_for

from jev_atari import candidate_study as study
from jev_atari.choice import ActionProgram
from jev_atari.environment import Protocol
from jev_atari.io import read_json, write_json
from jev_atari.models import BudgetExceeded

ROOT = Path(__file__).resolve().parents[1]


def program(name="synthetic-proposal"):
    return ActionProgram(name=name)


def test_three_round_schedule_and_reserved_budget():
    training = sum(2 if i == 0 else 4 for i in range(3)) * 500
    nonfinal = training + 3 * 3 * 2 * 500 + 3 * 480
    final = 3 * 8 * 500
    assert nonfinal == 15440 and final == 12000
    assert nonfinal <= study.LIMITS["nonfinal_limit"]
    assert final <= study.LIMITS["final_limit"]
    assert study.LIMITS["max_attempts"] == 30000
    assert len(study.TRAIN) == 1 and len(study.TRAIN[0]) == 3


def test_feedback_roles_unique_ids_and_no_development_leak(tmp_path):
    episodes = []
    for seed in (202, 203):
        for role in ("incumbent", "previous-candidate"):
            path = tmp_path / role / str(seed)
            p = program(role)
            write_json(
                path / "manifest.json",
                {
                    "seed": seed,
                    "split": "train",
                    "question_program": p.to_dict(),
                },
            )
            write_json(path / "summary.json", {"status": "complete"})
            rows = [
                {
                    "observation": {"objects": []},
                    "action": 0,
                    "rewards": [int(i % 3 == 0)],
                    "next_observation": {"objects": []},
                }
                for i in range(32)
            ]
            (path / "transitions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
            episodes.append((role, p, path))
    evidence = study.candidate_evidence(episodes)
    assert 32 <= len(evidence["examples"]) <= 48
    assert len(set(e["id"] for e in evidence["examples"])) == len(evidence["examples"])
    assert {e["role"] for e in evidence["examples"]} == {"incumbent", "previous-candidate"}
    assert {e["program_hash"] for e in evidence["examples"]} == {
        program(r).hash for r in ("incumbent", "previous-candidate")
    }
    assert study.packet_for("B", 2, program(), evidence, [])["evidence"] is None
    packet = study.packet_for("A", 2, program(), evidence, [])
    assert packet["contract"]["executor"] == study.RESPONSE_MODEL
    assert all("next_objects" in e for e in packet["evidence"]["examples"])
    path = episodes[0][2]
    manifest = read_json(path / "manifest.json")
    write_json(path / "manifest.json", {**manifest, "seed": 206})
    with pytest.raises(ValueError, match="training-only"):
        study.candidate_evidence(episodes)


def test_mocked_openrouter_episode_audits_and_rejects_model_tampering(tmp_path, monkeypatch):
    import importlib.util

    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-openrouter-key")
    original = study.OpenRouterChoiceEvaluator
    monkeypatch.setattr(
        study, "OpenRouterChoiceEvaluator", lambda **kw: original(**kw, client=client_for())
    )
    monkeypatch.setattr(study, "FRAMES", 12)
    root = tmp_path / "episode"
    budget = study.CandidateBudget(tmp_path / "budget.json")
    row = study.run_episode(root, Protocol(), program(), 200, 12, budget, "synthetic")
    assert row["evaluation_complete"] and read_json(budget.path)["attempts"] == 3
    spec = importlib.util.spec_from_file_location(
        "audit_matches_candidate_test", ROOT / "scripts/verify_matches.py"
    )
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    assert audit.verify(root, tmp_path / "audit")["status"] == "verified"
    path = root / "jev/seed-200/model-exchanges.jsonl"
    exchanges = [json.loads(line) for line in path.read_text().splitlines()]
    exchanges[0]["response"]["model"] = "typesafe/wrong-model"
    path.write_text("".join(json.dumps(x) + "\n" for x in exchanges))
    with pytest.raises(AssertionError):
        audit.verify(root, tmp_path / "tampered-audit")
    with pytest.raises(ValueError, match="Never restart"):
        study.run_episode(root, Protocol(), program(), 200, 12, budget, "synthetic")


def test_three_round_search_replays_rejected_candidate_then_seals(tmp_path, monkeypatch):
    packets, calls, feedback_roles, finals = [], [], [], []
    monkeypatch.setattr(study, "source_inventory", lambda repo: {"synthetic": True})
    monkeypatch.setattr(study, "isolation_check", lambda *args: {"synthetic": True})
    monkeypatch.setattr(
        study.subprocess,
        "check_output",
        lambda cmd, **kw: "" if "status" in cmd else "synthetic-source",
    )
    binary = tmp_path / "binary"
    binary.write_text("Synthetic fixture, never executed")

    def propose(root, packet, budget, *args):
        assert read_json(tmp_path / "study/plan.json")["model"] == study.MODEL
        budget.reserve("teacher")
        packets.append(packet)
        p = program(f"{packet['arm']}-round-{packet['round']}")
        return p, {"synthetic": p.name}

    def episode(root, protocol, p, seed, frames, budget, source):
        assert seed not in study.FINAL
        budget.reserve("nonfinal")
        calls.append((str(root), p.name, seed))
        return {
            "seed": seed,
            "evaluation_complete": True,
            "capped_episode_return": 0 if p.name == "pong-vertical-control-v2" else -2,
        }

    def evidence(episodes):
        feedback_roles.append([(role, p.name) for role, p, path in episodes])
        return {"split": "train", "episodes": [], "examples": []}

    def final(root, p, seed, budget, source, seal):
        assert read_json(budget.path)["training_closed"]
        study.validate_seal(seal, seed, p, Protocol())
        with pytest.raises(BudgetExceeded):
            budget.reserve("teacher")
        budget.reserve("final")
        finals.append(seed)
        return {"seed": seed, "evaluation_complete": True, "capped_episode_return": 0}

    monkeypatch.setattr(study, "propose", propose)
    monkeypatch.setattr(study, "run_episode", episode)
    monkeypatch.setattr(study, "candidate_evidence", evidence)
    monkeypatch.setattr(study, "audit_episode", lambda *args: None)
    monkeypatch.setattr(
        study, "probe", lambda *args: {k: {"eligible": True} for k in ("V2", "A", "B")}
    )
    monkeypatch.setattr(study, "final_episode", final)
    root = tmp_path / "study"
    study.run(root, ROOT, binary, tmp_path)
    assert len(calls) == 28 and len(packets) == 6 and finals == list(study.FINAL)
    assert (
        feedback_roles[1]
        == [("incumbent", "pong-vertical-control-v2"), ("previous-candidate", "A-round-1")] * 2
    )
    assert (
        feedback_roles[2]
        == [("incumbent", "pong-vertical-control-v2"), ("previous-candidate", "A-round-2")] * 2
    )
    assert all(p["evidence"] is None for p in packets if p["arm"] == "B")
    assert all(set(m) == {"round", "proposal"} for p in packets for m in p["prior_edits"])
    assert read_json(root / "status.json")["status"] == "complete"
    endpoint = read_json(root / "endpoint.json")
    assert not endpoint["milestone_1_screen_met"] and not endpoint["milestone_2_established"]
    with pytest.raises(ValueError, match="never reset"):
        study.run(root, ROOT, binary, tmp_path)


def test_final_admission_pin_and_complete_endpoint(tmp_path):
    p, protocol = program(), Protocol()
    seal = tmp_path / "seal.json"
    study.make_seal(seal, {"V2": p, "A1": p, "B1": p}, protocol, "synthetic")
    assert study.validate_seal(seal, study.FINAL[0], p, protocol)
    with pytest.raises(ValueError):
        study.validate_seal(seal, 200, p, protocol)
    with pytest.raises(ValueError):
        study.validate_seal(seal, study.FINAL[0], program("unselected"), protocol)
    budget = study.CandidateBudget(tmp_path / "budget.json")
    with pytest.raises(ValueError, match="Close training"):
        study.final_episode(tmp_path / "no-call", p, study.FINAL[0], budget, "synthetic", seal)
    rows = {
        k: [
            {"seed": seed, "evaluation_complete": True, "capped_episode_return": score}
            for seed in study.FINAL
        ]
        for k, score in (("V2", 0), ("A1", 2), ("B1", 0))
    }
    assert study.endpoint(rows)["milestone_1_screen_met"]
    rows["A1"][0]["evaluation_complete"] = False
    with pytest.raises(ValueError, match="Incomplete"):
        study.endpoint(rows)


def test_preparation_write_failure_cannot_reach_live_teacher(tmp_path, monkeypatch):
    monkeypatch.setattr(study, "source_inventory", lambda repo: {"synthetic": True})
    monkeypatch.setattr(study, "isolation_check", lambda *args: {"synthetic": True})
    monkeypatch.setattr(
        study.subprocess,
        "check_output",
        lambda cmd, **kw: "" if "status" in cmd else "synthetic-source",
    )
    binary = tmp_path / "binary"
    binary.write_text("Synthetic fixture, never executed")
    original = study.write_json

    def fail_plan(path, value):
        if path.name == "plan.json":
            raise OSError("Synthetic full filesystem")
        original(path, value)

    monkeypatch.setattr(study, "write_json", fail_plan)
    monkeypatch.setattr(study, "propose", lambda *a: pytest.fail("Live teacher reached"))
    with pytest.raises(OSError, match="Synthetic"):
        study.run(tmp_path / "study", ROOT, binary, tmp_path)
    assert not (tmp_path / "study/budget.json").exists()
