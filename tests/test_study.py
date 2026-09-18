import json
from pathlib import Path

import httpx
import pytest
from test_controls import make_evaluator

from jev_atari.choice import ActionProgram
from jev_atari.environment import Protocol
from jev_atari.io import read_json
from jev_atari.models import BudgetExceeded, JsonAPI, ModelError
from jev_atari.study import (
    MODEL,
    AllocatedBudget,
    StudyBudget,
    js_divergence,
    parse_proposal,
    probe_report,
    sample_training,
    seal_final,
    select_policy,
    teacher_packet,
    verify_final_seal,
)
from jev_atari.study_runner import probes, run_episode
from jev_atari.teacher import bubblewrap, teacher_config


def test_budget_reservations_survive_restart_and_reserve_final(tmp_path):
    path = tmp_path / "budget.json"
    budget = StudyBudget(path, clock=lambda: 100)
    allocated = AllocatedBudget(budget, "nonfinal", 2)
    allocated.reserve()
    allocated.reserve()
    with pytest.raises(BudgetExceeded):
        allocated.reserve()
    state = read_json(path)
    state.update(attempts=154000, nonfinal_attempts=154000)
    budget.save(state)
    restarted = StudyBudget(path, clock=lambda: 101)
    with pytest.raises(BudgetExceeded):
        restarted.reserve("nonfinal")
    restarted.reserve("final")
    assert read_json(path)["attempts"] == 154001
    assert read_json(path)["final_attempts"] == 1
    expired = StudyBudget(path, clock=lambda: 86500)
    with pytest.raises(BudgetExceeded):
        expired.reserve("teacher")
    assert read_json(path)["teacher_invocations"] == 0


def test_teacher_limit_and_invalid_phase_do_not_reserve(tmp_path):
    budget = StudyBudget(tmp_path / "budget.json", clock=lambda: 100)
    with pytest.raises(ValueError):
        budget.reserve("unknown")
    for _ in range(8):
        budget.reserve("teacher")
    with pytest.raises(BudgetExceeded):
        budget.reserve("teacher")
    assert read_json(budget.path)["attempts"] == 0


def test_sealing_training_blocks_new_teacher_and_jev_work(tmp_path):
    budget = StudyBudget(tmp_path / "budget.json")
    budget.close_training()
    for phase in ("teacher", "teacher_repair", "nonfinal"):
        with pytest.raises(BudgetExceeded):
            budget.reserve(phase)
    budget.reserve("final")
    assert read_json(budget.path)["final_attempts"] == 1


def test_two_technical_repairs_share_teacher_limit(tmp_path):
    budget = StudyBudget(tmp_path / "budget.json")
    budget.reserve("teacher_repair")
    budget.reserve("teacher_repair")
    with pytest.raises(BudgetExceeded):
        budget.reserve("teacher_repair")
    assert read_json(budget.path)["teacher_invocations"] == 2


def test_transient_transport_retry_is_recorded_and_globally_charged(tmp_path):
    budget = StudyBudget(tmp_path / "budget.json")
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ReadTimeout("synthetic test timeout")
        return httpx.Response(200, json={"model": MODEL})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    api = JsonAPI(
        "https://example.invalid",
        "synthetic-key",
        AllocatedBudget(budget, "nonfinal", 3),
        client=client,
        retry_transport=True,
    )
    api.trace_path = tmp_path / "exchanges.jsonl"
    try:
        assert api.post({"model": MODEL})["model"] == MODEL
        assert [r["status"] for r in api.ledger] == ["transport_error", 200]
        assert read_json(budget.path)["attempts"] == 2
        assert len(api.trace_path.read_text().splitlines()) == 2
    finally:
        api.close()


def evidence(seed=60):
    return {
        "split": "train",
        "episodes": [{"seed": seed}],
        "examples": [
            {
                "id": "example-1",
                "seed": seed,
                "observation": {"objects": []},
                "next_observation": {"objects": []},
                "observed_rewards_after_action": [-1],
            }
        ],
    }


def proposal():
    return {
        "name": "candidate",
        "guidance": "Choose NOOP.",
        "hypothesis": "A hypothesis",
        "operator": "clarification",
        "evidence_ids": [],
        "predicted_changes": "Fewer moves",
        "regression_risks": "Missing the ball",
    }


def test_teacher_packets_exclude_development_and_control_feedback():
    for seed in (66, 68):
        with pytest.raises(ValueError):
            teacher_packet("A", 1, ActionProgram(), evidence(seed), [])
    with pytest.raises(ValueError):
        teacher_packet("A", 1, ActionProgram(), evidence(), [{"selection": "accepted"}])
    a = teacher_packet("A", 1, ActionProgram(), evidence(), [])
    b = teacher_packet("B", 1, ActionProgram(), evidence(), [])
    assert a["evidence"]["examples"][0]["observed_rewards_after_action"] == [-1]
    assert b["evidence"] is None and "example-1" not in json.dumps(b)
    bad = {**proposal(), "evidence_ids": ["example-1"]}
    assert parse_proposal(bad, a).name == "candidate"
    with pytest.raises(ValueError):
        parse_proposal(bad, b)
    with pytest.raises(ValueError):
        parse_proposal({**proposal(), "guidance": "x" * 2001}, a)


def test_gate_rejects_regression_and_never_selects_on_final_test():
    old = [
        {"seed": seed, "evaluation_complete": True, "capped_episode_return": 0} for seed in (66, 67)
    ]
    new = [{**old[0], "capped_episode_return": -1}, {**old[1], "capped_episode_return": 10}]
    assert not select_policy(old, new)["accepted"]
    new[0]["capped_episode_return"] = 0
    assert select_policy(old, new)["accepted"]
    new[0]["evaluation_complete"] = False
    assert select_policy(old, new)["status"] == "inconclusive"
    old[0]["seed"] = 68
    with pytest.raises(ValueError):
        select_policy(old, new)


def test_final_seal_disallows_changed_program_or_environment(tmp_path):
    path = tmp_path / "seal.json"
    program = ActionProgram()
    seal_final(path, {"A": program, "B": program, "V2": program}, Protocol(), "test-source")
    assert verify_final_seal(path, 68, program, Protocol())
    with pytest.raises(ValueError):
        verify_final_seal(path, 66, program, Protocol())
    with pytest.raises(ValueError):
        verify_final_seal(path, 68, ActionProgram(guidance="different"), Protocol())
    with pytest.raises(ValueError):
        verify_final_seal(path, 68, program, Protocol(sticky=0))
    with pytest.raises(ValueError):
        run_episode(tmp_path / "test", Protocol(), program, 68, 20000, None, "test-source")


def test_probe_noise_is_separate_from_program_change():
    assert js_divergence({"up": 1, "down": 0}, {"up": 0, "down": 1}) == 1
    rows = []
    for role in ("parent", "candidate"):
        for repeat in (0, 1):
            action = "up" if role == "parent" else "down"
            rows.append(
                {
                    "id": "x",
                    "program_role": role,
                    "repeat": repeat,
                    "answer": {
                        "choice": action,
                        "probabilities": {"up": int(action == "up"), "down": int(action == "down")},
                    },
                }
            )
    report = probe_report(rows)
    assert report["parent_candidate"]["action_flip_fraction"] == 1
    assert report["parent_repeat"]["action_flip_fraction"] == 0


def test_real_episode_probe_and_replay_with_mock_http(tmp_path, monkeypatch):
    from jev_atari import study_runner

    created = []

    def fake_factory(budget, phase, cap):
        ev = make_evaluator(monkeypatch, cap, response_model=MODEL)
        ev.model = MODEL
        ev.api.budget = AllocatedBudget(budget, phase, cap)
        created.append(ev)
        return ev

    monkeypatch.setattr(study_runner, "evaluator_for", fake_factory)
    budget = StudyBudget(tmp_path / "budget.json")
    program, protocol = ActionProgram(), Protocol(noop_max=0)
    training = []
    for seed in (60, 61):
        root = tmp_path / f"seed-{seed}"
        row = run_episode(root, protocol, program, seed, 64, budget, "mock-only")
        assert row["evaluation_complete"] and row["raw_frames"] == 64
        study_runner.audit_episode(root, Path(__file__).resolve().parents[1])
        training.append(root / "jev" / f"seed-{seed}")
    dataset = sample_training(training)
    assert len([e for e in dataset["examples"] if e["probe"]]) == 32
    result = probes(tmp_path / "probes", dataset, program, program, budget)
    assert result["metrics"]["parent_candidate"]["action_flip_fraction"] == 0
    assert read_json(budget.path)["attempts"] == 160
    # Resume reuses completed evidence rather than issuing requests again.
    run_episode(tmp_path / "seed-60", protocol, program, 60, 64, budget, "mock-only")
    assert read_json(budget.path)["attempts"] == 160


def test_failed_episode_cannot_be_restarted(tmp_path, monkeypatch):
    from jev_atari import study_runner

    ev = make_evaluator(monkeypatch, 1, response_model="wrong-model")
    monkeypatch.setattr(study_runner, "evaluator_for", lambda *args: ev)
    budget = StudyBudget(tmp_path / "budget.json")
    path = tmp_path / "episode"
    with pytest.raises(ModelError):
        run_episode(path, Protocol(), ActionProgram(), 60, 64, budget, "mock-only")
    assert read_json(path / "results.json")["status"] == "incomplete"
    with pytest.raises(ValueError, match="restart"):
        run_episode(path, Protocol(), ActionProgram(), 60, 64, budget, "mock-only")


def test_teacher_filesystem_mounts_and_tools_exclude_host_context(tmp_path):
    command = bubblewrap(Path("/binary"), tmp_path / "private", tmp_path / "work")
    assert "/home/memorysaver" not in command
    assert "--clearenv" in command and "--unshare-pid" in command
    config = teacher_config()
    assert 'model = "gpt-6-astra"' in config and 'model_reasoning_effort = "high"' in config
    for feature in ("shell_tool", "multi_agent", "plugins", "apps", "memories"):
        assert f"{feature} = false" in config
    assert 'web_search = "disabled"' in config
