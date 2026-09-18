from copy import deepcopy

import pytest

from jev_atari.environment import Protocol
from jev_atari.experiment import (
    collect,
    dataset_coverage,
    evaluate,
    load_dataset,
    require_disjoint,
    split_for_seed,
)
from jev_atari.io import read_json, write_json
from jev_atari.learning import (
    optimize_round,
    parse_candidates,
    select_candidate,
    teacher_packet,
    validate_training_report,
)
from jev_atari.models import BudgetExceeded, MockEvaluator
from jev_atari.program import QuestionProgram


@pytest.fixture
def datasets(tmp_path):
    paths = []
    for seed, split in ((0, "train"), (6, "development"), (8, "test")):
        out = tmp_path / split
        collect(
            Protocol(),
            seeds=[seed],
            split=split,
            roots_per_seed=2,
            warmup=100,
            stride=31,
            horizon=24,
            out=out,
        )
        paths.append(out / "dataset.json")
    return [load_dataset(p) for p in paths]


@pytest.fixture
def program():
    return QuestionProgram("small", 24, "Read current ball and paddle motion.")


def test_seed_partition_and_same_lineage_rejection(datasets):
    train, dev, final = datasets
    assert [split_for_seed(s) for s in (0, 6, 8, 10)] == ["train", "development", "test", "train"]
    require_disjoint(train, dev)
    with pytest.raises(ValueError, match="never final-test"):
        require_disjoint(train, final)
    bad = deepcopy(dev)
    bad["roots"][0]["root_fingerprint"] = train["roots"][0]["root_fingerprint"]
    with pytest.raises(ValueError, match="overlap"):
        require_disjoint(train, bad)


def test_teacher_only_sees_train_and_matching_feedback(datasets, program):
    train, dev, final = datasets
    report = evaluate(train, program, MockEvaluator(10))
    packet = teacher_packet(train, program, report)
    assert packet["split"] == "train"
    assert len(packet["examples"]) == 2
    for invalid in (dev, final):
        with pytest.raises(ValueError, match="training data only"):
            teacher_packet(invalid, program)


def test_complete_offline_round_with_synthetic_feedback_is_labeled(datasets, program, tmp_path):
    train, dev, _ = datasets
    proposal = {
        "candidates": [
            {
                "name": "try-1",
                "guidance": "Account for wall reflections.",
                "outcome_guidance": ["", "", ""],
            }
        ]
    }
    selection = optimize_round(
        train,
        dev,
        program,
        MockEvaluator(6),
        out=tmp_path / "round",
        min_improvement=0.01,
        proposals=proposal,
    )
    assert selection["backend"] == "mock"
    assert not selection["accepted"]  # mock never fabricates a gain from a wording change
    assert read_json(tmp_path / "round/status.json")["status"] == "complete"
    assert read_json(tmp_path / "round/selected-program.json")["name"] == "small"


def test_budget_failure_never_publishes_selected_program(datasets, program, tmp_path):
    train, dev, _ = datasets
    proposal = {
        "candidates": [
            {"name": "try-1", "guidance": "Motion matters.", "outcome_guidance": ["", "", ""]}
        ]
    }
    out = tmp_path / "incomplete"
    with pytest.raises(BudgetExceeded):
        optimize_round(
            train, dev, program, MockEvaluator(1), out=out, min_improvement=0.01, proposals=proposal
        )
    assert read_json(out / "status.json")["status"] == "incomplete"
    assert not (out / "selected-program.json").exists()


def test_evaluation_checkpoints_completed_rows_before_budget_failure(datasets, program):
    saved = []
    with pytest.raises(BudgetExceeded):
        evaluate(datasets[0], program, MockEvaluator(1), on_row=saved.append)
    assert len(saved) == 1
    assert saved[0]["root_id"] == datasets[0]["roots"][0]["root_id"]


def test_teacher_cannot_change_target_horizon(program):
    with pytest.raises(ValueError, match="can change"):
        parse_candidates(
            {
                "candidates": [
                    {
                        "name": "bad",
                        "guidance": "x",
                        "outcome_guidance": ["", "", ""],
                        "horizon_frames": 1,
                    }
                ]
            },
            program,
        )


def test_program_rejects_string_instead_of_outcome_array():
    with pytest.raises(ValueError, match="must be an array"):
        QuestionProgram.from_dict(
            {"name": "bad", "horizon_frames": 24, "guidance": "x", "outcome_guidance": "abc"}
        )


def test_selection_requires_real_improvement_and_rejects_test_split(datasets, program):
    _, dev, _ = datasets
    baseline = evaluate(dev, program, MockEvaluator(10))
    improved = deepcopy(baseline)
    improved["metrics"]["brier"] -= 0.1
    improved["program_hash"] = "hypothetical-improvement"
    assert select_candidate(baseline, [improved], 0.01)["accepted"]
    improved["metrics"]["mae"] += 1
    selection = select_candidate(baseline, [improved], 0.01)
    assert not selection["accepted"]
    assert selection["candidates"][0]["rejection_reasons"] == ["mae_regression"]
    improved["split"] = "test"
    with pytest.raises(ValueError, match="development"):
        select_candidate(baseline, [improved], 0.01)


def test_tampered_dataset_is_rejected(datasets, tmp_path):
    data = deepcopy(datasets[0])
    data["roots"][0]["outcomes"]["0"]["label"] = 10
    path = tmp_path / "tampered.json"
    write_json(path, data)
    with pytest.raises(ValueError, match="integrity"):
        load_dataset(path)


def test_reusing_train_feedback_spends_only_development_calls(datasets, program, tmp_path):
    train, dev, _ = datasets
    report = evaluate(train, program, MockEvaluator(2))
    evaluator = MockEvaluator(4)
    optimize_round(
        train,
        dev,
        program,
        evaluator,
        out=tmp_path / "reuse",
        min_improvement=0.01,
        proposals={
            "candidates": [
                {"name": "try", "guidance": "Watch motion.", "outcome_guidance": ["", "", ""]}
            ]
        },
        train_report=report,
    )
    assert evaluator.budget.used == 4
    assert read_json(tmp_path / "reuse/status.json")["reused_train_evaluation"]


@pytest.mark.parametrize("tamper", ["model", "dataset", "partial", "duplicate", "prediction"])
def test_invalid_reused_report_is_rejected(datasets, program, tamper):
    train = datasets[0]
    evaluator = MockEvaluator(2)
    report = evaluate(train, program, evaluator)
    if tamper == "model":
        report["requested_model"] = "different"
    elif tamper == "dataset":
        report["dataset_hash"] = "different"
    elif tamper == "partial":
        report["rows"].pop()
    elif tamper == "duplicate":
        report["rows"][1] = deepcopy(report["rows"][0])
    else:
        report["rows"][0]["prediction"]["program_hash"] = "different"
    with pytest.raises(ValueError, match="Reused training"):
        validate_training_report(train, program, evaluator, report)


def test_coverage_and_regret_distinguish_informative_roots(datasets, program):
    train = deepcopy(datasets[0])
    # All actions at the first root lose. Only action 1 at the second root wins.
    for index, root in enumerate(train["roots"]):
        for action, outcome in root["outcomes"].items():
            outcome.update(label=1 if index == 1 and action == "1" else -1, censored=False)
    coverage = dataset_coverage(train)
    assert coverage["labels"] == {"-1": 11, "0": 0, "1": 1}
    assert coverage["missing_labels"] == [0]
    assert coverage["roots_with_action_difference"] == 1
    report = evaluate(train, program, MockEvaluator(2))
    assert report["metrics"]["sampled_regret"] == 1
    assert report["metrics"]["informative_sampled_regret"] == 2


def test_collector_can_follow_heuristic_and_records_coverage(tmp_path):
    from jev_atari.environment import Pong
    from jev_atari.policies import HEURISTIC_VERSION, HeuristicPolicy

    protocol = Protocol()
    collect(
        protocol,
        seeds=[0],
        split="train",
        roots_per_seed=1,
        warmup=140,
        stride=31,
        horizon=24,
        behavior="heuristic",
        out=tmp_path / "heuristic",
    )
    data = load_dataset(tmp_path / "heuristic/dataset.json")
    assert data["manifest"]["behavior"] == HEURISTIC_VERSION
    with Pong(protocol) as env:
        observation = env.reset(0)
        for _ in range(140):
            observation = env.step(HeuristicPolicy().choose(observation)[0]).observation
    assert data["roots"][0]["observation"] == observation
    assert read_json(tmp_path / "heuristic/coverage.json")["roots"] == 1


def test_teacher_packet_keeps_rare_gain_and_action_contrast(datasets, program):
    train = deepcopy(datasets[0])
    template = train["roots"][0]
    train["roots"] = []
    for index in range(12):
        root = deepcopy(template)
        root["root_id"] = f"root-{index}"
        for action, outcome in root["outcomes"].items():
            outcome.update(label=1 if index == 6 and action == "1" else 0, censored=False)
        train["roots"].append(root)
    report = evaluate(train, program, MockEvaluator(12))
    # Put the only gain example in the middle of the error ranking.
    for index, row in enumerate(report["rows"]):
        row["brier"] = index / 12
    packet = teacher_packet(train, program, report)
    assert len(packet["examples"]) == 9
    assert any(
        {o["label"] for o in example["observed_outcomes"].values()} == {0, 1}
        for example in packet["examples"]
    )
