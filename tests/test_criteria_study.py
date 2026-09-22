"""Validate experimental isolation, schema compatibility and sealed evaluation offline."""

from copy import deepcopy
from pathlib import Path

import pytest

from jev_atari.choice import ActionProgram
from jev_atari.criteria_study import (
    ACTIONS,
    DEV,
    FINAL,
    FRAMES,
    LIMITS,
    TRAIN,
    CriteriaBudget,
    endpoint,
    final_episode,
    make_seal,
    packet_for,
    parse,
    propose,
    select,
    validate_seal,
)
from jev_atari.environment import Protocol
from jev_atari.io import read_json, write_json
from jev_atari.models import BudgetExceeded
from jev_atari.study import AllocatedBudget

ROOT = Path(__file__).resolve().parents[1]


def program():
    return ActionProgram(
        name="synthetic-criteria-test",
        guidance="Synthetic test only.",
        schema_version="action-choice-program-v2",
        action_criteria={name: f"Synthetic criterion for {name}." for name in ACTIONS},
    )


def proposal():
    return {
        "name": program().name,
        "guidance": program().guidance,
        "action_criteria": program().action_criteria,
        "hypothesis": "Synthetic hypothesis.",
        "operator": "criteria",
        "predicted_changes": "Synthetic change.",
        "regression_risks": "Synthetic risk.",
        "evidence_ids": [],
    }


def test_old_program_hash_and_all_native_actions_are_preserved():
    original = ActionProgram.from_dict(read_json(ROOT / "examples/vertical-policy-program.json"))
    assert original.hash == "2ef87250f491fcd5a2ba72f29e3f03b6bc66c4ab7315e9e724df76352326633d"
    assert "action_criteria" not in original.to_dict()
    states = read_json(ROOT / "experiments/pong/motion-probe-v1/inputs.json")
    p = program()
    assert ActionProgram.from_dict(p.to_dict()) == p
    for s in states:
        old, new = original.request(s["observation"], "test"), p.request(s["observation"], "test")
        assert old["state"] == new["state"]
        assert list(old["questions"]["next_action"]["criteria"]) == list(
            new["questions"]["next_action"]["criteria"]
        )
        new["questions"]["next_action"]["criteria"] = old["questions"]["next_action"]["criteria"]
        new["questions"]["next_action"]["instructions"]["question"] = original.guidance
        assert old == new
    for bad in (
        {"NOOP": "mask"},
        {**p.action_criteria, "FIRE": ""},
        {**p.action_criteria, "LEFT": "x" * 501},
    ):
        with pytest.raises(ValueError):
            ActionProgram(schema_version="action-choice-program-v2", action_criteria=bad)
    with pytest.raises(ValueError):
        ActionProgram(action_criteria=p.action_criteria)
    obs = deepcopy(states[0]["observation"])
    obs["candidate_actions"].pop()
    with pytest.raises(ValueError):
        p.request(obs, "test")


def test_packet_boundary_and_criteria_proposal_validation():
    evidence = {
        "split": "train",
        "episodes": [{"seed": 100}],
        "examples": [
            {"id": "train-100", "seed": 100, "next_observation": {"objects": []}},
        ],
    }
    a = packet_for("A", 1, program(), evidence, [])
    b = packet_for("B", 1, program(), evidence, [])
    assert a["evidence"] and b["evidence"] is None
    assert a["contract"] == b["contract"]
    assert parse(proposal(), a) == program()
    bad = proposal()
    bad["evidence_ids"] = ["train-100"]
    assert parse(bad, a) == program()
    with pytest.raises(ValueError):
        parse(bad, b)
    evidence["episodes"][0]["seed"] = FINAL[0]
    with pytest.raises(ValueError):
        packet_for("A", 1, program(), evidence, [])


def test_campaign_budget_preserves_reserves_deadline_and_closed_training(tmp_path):
    now = [10.0]
    p = tmp_path / "budget.json"
    budget = CriteriaBudget(p, clock=lambda: now[0])
    budget.reserve("teacher")
    state = read_json(p)
    assert state["teacher_invocations"] == 1 and state["started_at"] == 10
    state["nonfinal_attempts"] = state["nonfinal_limit"]
    state["attempts"] = state["nonfinal_attempts"]
    budget.save(state)
    with pytest.raises(BudgetExceeded):
        budget.reserve("nonfinal")
    budget.close_training()
    with pytest.raises(BudgetExceeded):
        budget.reserve("teacher")
    budget.reserve("final")
    assert CriteriaBudget(p, clock=lambda: now[0]).path == p
    now[0] += 86400
    with pytest.raises(BudgetExceeded):
        budget.reserve("final")
    state = read_json(p)
    state["max_attempts"] += 1
    budget.save(state)
    with pytest.raises(ValueError):
        CriteriaBudget(p)
    # Worst-case scheduled attempts leave retry capacity in each allocation.
    nonfinal = 3 * 2 * (2 * FRAMES // 4 + 3 * 2 * FRAMES // 4 + 80 * 3 * 2)
    final = 7 * len(FINAL) * FRAMES // 4
    assert nonfinal == 26880 < LIMITS["nonfinal_limit"]
    assert final == 28000 < LIMITS["final_limit"]
    assert nonfinal + final == 54880 < LIMITS["max_attempts"]


def test_selector_compares_fresh_v2_and_preserves_historical_best():
    seeds = DEV[0]

    def rows(values):
        return [
            {"seed": s, "evaluation_complete": True, "capped_episode_return": v}
            for s, v in zip(seeds, values, strict=True)
        ]

    assert select(rows([-2, -2]), rows([0, 0]), seeds, 0)["accepted"]
    assert not select(rows([-2, -2]), rows([-3, 3]), seeds, 0)["accepted"]
    assert not select(rows([-2, -2]), rows([0, 0]), seeds, 2)["accepted"]
    with pytest.raises(ValueError):
        select(rows([0, 0]), rows([0, 0]), FINAL[:2], 0)


def test_final_seal_rejects_wrong_seed_changed_program_and_horizon(tmp_path):
    seal = tmp_path / "seal.json"
    make_seal(seal, {"V2": program()}, Protocol(), "synthetic-source")
    assert validate_seal(seal, FINAL[0], program(), Protocol())
    with pytest.raises(ValueError):
        validate_seal(seal, TRAIN[0][0][0], program(), Protocol())
    with pytest.raises(ValueError):
        validate_seal(seal, FINAL[0], ActionProgram(), Protocol())
    data = read_json(seal)
    data["seal"]["max_frames"] += 4
    write_json(seal, data)
    with pytest.raises(ValueError):
        validate_seal(seal, FINAL[0], program(), Protocol())


def test_endpoint_reports_negative_unchanged_and_shared_seed_uncertainty():
    def result(value):
        return [
            {"seed": s, "evaluation_complete": True, "capped_episode_return": value} for s in FINAL
        ]

    values = {"V2": result(-3), **{f"{a}{i}": result(-3) for a in ("A", "B") for i in (1, 2, 3)}}
    report = endpoint(values)
    assert not report["milestone_1_screen_met"] and not report["replicated_signal_screen_met"]
    values.update({f"A{i}": result(0) for i in (1, 2, 3)})
    report = endpoint(values)
    assert report["milestone_1_screen_met"] and report["replicated_signal_screen_met"]
    assert report["primary_A1_over_v2"]["mean_gain"] == 3
    values["V2"][0]["evaluation_complete"] = False
    with pytest.raises(ValueError):
        endpoint(values)


def test_failed_access_retry_retains_packet_and_counts_invocations(tmp_path, monkeypatch):
    from jev_atari import criteria_study

    budget = CriteriaBudget(tmp_path / "budget.json")
    calls = []

    def fake(packet, out, budget, **kwargs):
        calls.append(packet)
        budget.reserve("teacher")
        out.mkdir()
        if len(calls) == 1:
            write_json(out / "execution.json", {"exit_code": 1})
            write_json(out / "events.json", [{"type": "turn.failed"}])
            raise ValueError("Synthetic access failure")
        return proposal()

    monkeypatch.setattr(criteria_study, "invoke_teacher", fake)
    packet = packet_for("B", 1, program(), {"split": "train", "episodes": [], "examples": []}, [])
    candidate, _ = propose(tmp_path / "teacher", packet, budget, Path("unused"), Path("unused"))
    assert candidate == program() and calls[0] == calls[1]
    assert read_json(budget.path)["teacher_invocations"] == 2
    assert read_json(budget.path)["teacher_transport_retries"] == 1
    assert (tmp_path / "teacher/invocation-1/retry-decision.json").exists()


def test_new_criteria_final_episode_uses_recorded_actions_and_replays(tmp_path, monkeypatch):
    from test_study import make_evaluator

    from jev_atari import criteria_study
    from jev_atari.study_runner import audit_episode

    def factory(budget, phase, cap):
        ev = make_evaluator(monkeypatch, cap, response_model="jev-1.13.0")
        ev.model = "jev-1.13.0"
        ev.api.budget = AllocatedBudget(budget, phase, cap)
        return ev

    monkeypatch.setattr(criteria_study, "evaluator_for", factory)
    budget = CriteriaBudget(tmp_path / "budget.json")
    seal = tmp_path / "seal.json"
    make_seal(seal, {"V2": program()}, Protocol(), "synthetic-source")
    with pytest.raises(ValueError):
        final_episode(tmp_path / "early", program(), FINAL[0], budget, "synthetic-source", seal)
    budget.close_training()
    row = final_episode(tmp_path / "final", program(), FINAL[0], budget, "synthetic-source", seal)
    assert row["evaluation_complete"] and row["raw_frames"] == FRAMES
    audit_episode(tmp_path / "final", ROOT)
    assert read_json(budget.path)["final_attempts"] == FRAMES // 4
    with pytest.raises(FileExistsError):
        final_episode(tmp_path / "final", program(), FINAL[0], budget, "synthetic-source", seal)


def test_entire_search_schedule_keeps_feedback_private_and_seals_before_final(
    tmp_path, monkeypatch
):
    from jev_atari import criteria_study as study

    packets, episodes, finals = [], [], []
    monkeypatch.setattr(study, "source_inventory", lambda _: {"synthetic": True})
    monkeypatch.setattr(study, "isolation_check", lambda *args: {"synthetic": True})
    monkeypatch.setattr(
        study.subprocess,
        "check_output",
        lambda cmd, **kwargs: "" if "status" in cmd else "synthetic-source",
    )
    binary = tmp_path / "binary"
    binary.write_text("synthetic fixture, never executed")

    def fake_propose(root, packet, budget, *args):
        packets.append(packet)
        budget.reserve("teacher")
        value = proposal()
        value["name"] = f"{packet['arm']}-{len(packets)}"
        return parse(value, packet), value

    def fake_episode(root, protocol, p, seed, frames, budget, source):
        assert seed not in FINAL
        budget.reserve("nonfinal")
        episodes.append((seed, p.name))
        return {
            "seed": seed,
            "evaluation_complete": True,
            "capped_episode_return": -4 if p.name == "pong-vertical-control-v2" else -1,
        }

    def fake_evidence(paths):
        seed = int(paths[0].name.split("-")[1])
        return {
            "split": "train",
            "episodes": [{"seed": seed}],
            "examples": [
                {"id": f"train-{seed}", "seed": seed, "next_observation": {"objects": []}},
            ],
        }

    def fake_final(root, p, seed, budget, source, seal):
        assert read_json(budget.path)["training_closed"]
        validate_seal(seal, seed, p, Protocol())
        budget.reserve("final")
        finals.append((seed, p.name))
        return {
            "seed": seed,
            "evaluation_complete": True,
            "capped_episode_return": -4 if p.name == "pong-vertical-control-v2" else -1,
        }

    monkeypatch.setattr(study, "propose", fake_propose)
    monkeypatch.setattr(study, "run_episode", fake_episode)
    monkeypatch.setattr(study, "sample_training", fake_evidence)
    monkeypatch.setattr(study, "audit_episode", lambda *args: None)
    monkeypatch.setattr(
        study, "probe", lambda *args: {k: {"eligible": True} for k in ("V2", "A", "B")}
    )
    monkeypatch.setattr(study, "final_episode", fake_final)
    root = tmp_path / "study"
    study.run(root, ROOT, binary, tmp_path)
    assert len(packets) == 12 and len(episodes) == 48 and len(finals) == 56
    assert all(p["evidence"] is None for p in packets if p["arm"] == "B")
    assert all(p["evidence"]["split"] == "train" for p in packets if p["arm"] == "A")
    assert all(set(m) == {"round", "proposal"} for p in packets for m in p["prior_edits"])
    assert read_json(root / "status.json")["status"] == "complete"
    assert read_json(root / "endpoint.json")["milestone_1_screen_met"]
    assert not read_json(root / "endpoint.json")["replicated_signal_screen_met"]
    with pytest.raises(ValueError):
        study.run(root, ROOT, binary, tmp_path)
