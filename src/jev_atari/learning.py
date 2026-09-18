"""Offline question optimization with strict train/development separation.

This first implementation learns finite-horizon heuristic-continuation predictions.
It does not claim TD learning, Q* convergence, or online score improvement.
"""

import json
import os
from pathlib import Path

from jev_atari.experiment import dataset_coverage, evaluate, require_disjoint
from jev_atari.io import new_directory, write_json
from jev_atari.models import CallBudget, JsonAPI, ModelError
from jev_atari.program import ANCHORS, QuestionProgram

TEACHER_SYSTEM = """You optimize a structured question program for Atari Pong.
Use ONLY the provided TRAIN outcomes and errors. Observations contain facts; do not
change the sensor, action space, target horizon, continuation policy, or reward anchors.
Do not include root IDs, seeds, labels for individual states, or suggested executable code
in the program. Distill generalizable evidence conditions, including counterexamples.
Propose at most 3 candidates. Return JSON only:
{"candidates": [{"name": "short-version-name", "guidance": "at most 4000 characters",
"outcome_guidance": ["loss evidence hint", "no-event evidence hint", "gain evidence hint"]}]}
Each evidence hint is at most 1000 characters. Outcome definitions are immutable.
Candidate programs will be independently evaluated on a held-out development set.
You are not allowed to redefine losing/winning or use predictions as observed outcomes.
Censored outcomes are unknown, not zero, and do not establish that no event occurred.
"""


def teacher_packet(train: dict, program: QuestionProgram, report: dict | None = None) -> dict:
    if train["manifest"]["split"] != "train":
        raise ValueError("Teacher packets may contain training data only")
    if program.horizon_frames != train["manifest"]["horizon_frames"]:
        raise ValueError("Program and training data horizons differ")
    if report is not None and (
        report["dataset_hash"] != train["manifest"]["dataset_hash"]
        or report["program_hash"] != program.hash
    ):
        raise ValueError("Feedback must match this training dataset and program")
    reports = {r["root_id"]: r for r in report["rows"]} if report else {}
    roots = train["roots"]
    # Retain successes and failures, rare outcomes and action contrasts in nine slots.
    if report:
        ordered = sorted(roots, key=lambda r: reports[r["root_id"]]["brier"], reverse=True)
    else:
        ordered = roots
    chosen = {r["root_id"]: r for r in ordered[:4] + ordered[-2:]}

    def labels(root):
        return {o["label"] for o in root["outcomes"].values() if not o["censored"]}

    for label in (-1, 0, 1):
        if not any(label in labels(root) for root in chosen.values()):
            match = next((root for root in ordered if label in labels(root)), None)
            if match is not None:
                chosen[match["root_id"]] = match
    if not any(len(labels(root)) > 1 for root in chosen.values()):
        match = next((root for root in ordered if len(labels(root)) > 1), None)
        if match is not None:
            chosen[match["root_id"]] = match
    for root in ordered:
        if len(chosen) >= 9:
            break
        chosen[root["root_id"]] = root
    roots = list(chosen.values())
    examples = []
    for root in roots:
        example = {"observation": root["observation"], "observed_outcomes": root["outcomes"]}
        if root["root_id"] in reports:
            example["prediction"] = reports[root["root_id"]]["prediction"]
        examples.append(example)
    return {
        "kind": "teacher-training-packet-v1",
        "split": "train",
        "training_dataset_hash": train["manifest"]["dataset_hash"],
        "training_coverage": dataset_coverage(train),
        "example_selection": "up to nine: worst/best errors, outcome coverage, action contrast",
        "protocol": train["manifest"]["protocol"],
        "program": program.to_dict(),
        "immutable_outcome_anchors": ANCHORS,
        "continuation_policy": train["manifest"]["continuation_policy"],
        "instructions": TEACHER_SYSTEM,
        "examples": examples,
        "feedback_backend": report["backend"] if report else None,
    }


def parse_candidates(payload: dict, current: QuestionProgram) -> list[QuestionProgram]:
    if set(payload) != {"candidates"} or not isinstance(payload["candidates"], list):
        raise ValueError("Expected only a candidates array")
    if not 1 <= len(payload["candidates"]) <= 3:
        raise ValueError("One to three candidates are required")
    candidates = []
    for proposal in payload["candidates"]:
        if set(proposal) != {"name", "guidance", "outcome_guidance"}:
            raise ValueError("Teacher can change name, guidance and outcome hints only")
        candidates.append(
            QuestionProgram.from_dict(
                {
                    **proposal,
                    "horizon_frames": current.horizon_frames,
                    "schema_version": current.schema_version,
                }
            )
        )
    if len({p.hash for p in candidates}) != len(candidates):
        raise ValueError("Duplicate candidate programs")
    return candidates


class OpenRouterTeacher:
    def __init__(self, model: str, max_calls: int):
        self.model = model
        self.api = JsonAPI(
            "https://openrouter.ai/api/v1/chat/completions",
            os.environ.get("OPENROUTER_API_KEY", ""),
            CallBudget(max_calls),
        )

    def propose(self, packet: dict) -> dict:
        if packet["split"] != "train":
            raise ValueError("Refusing non-training teacher input")
        answer = self.api.post(
            {
                "model": self.model,
                "max_tokens": 3000,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": TEACHER_SYSTEM},
                    {"role": "user", "content": json.dumps(packet)},
                ],
            }
        )
        try:
            return json.loads(answer["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError, ValueError):
            raise ModelError("Teacher did not return a JSON proposal") from None

    def close(self):
        self.api.close()


def select_candidate(baseline: dict, candidates: list[dict], min_improvement: float) -> dict:
    """Development gate only; final test is never a candidate-selection signal."""
    if min_improvement <= 0:
        raise ValueError("min_improvement must be positive and chosen before evaluation")
    all_reports = [baseline, *candidates]
    for report in all_reports:
        if report["split"] != "development":
            raise ValueError("Selection is permitted on development data only")
        for field in (
            "dataset_hash",
            "backend",
            "requested_model",
            "response_models",
            "protocol_hash",
        ):
            if report[field] != baseline[field]:
                raise ValueError(f"Incomparable candidate evaluation: {field}")
    winner = baseline
    decisions = []
    for report in candidates:
        brier_gain = baseline["metrics"]["brier"] - report["metrics"]["brier"]
        no_mae_regression = report["metrics"]["mae"] <= baseline["metrics"]["mae"] + 1e-12
        old_regret, new_regret = (
            baseline["metrics"]["sampled_regret"],
            report["metrics"]["sampled_regret"],
        )
        no_regret_regression = old_regret is None or (
            new_regret is not None and new_regret <= old_regret
        )
        eligible = brier_gain >= min_improvement and no_mae_regression and no_regret_regression
        rejection_reasons = []
        if brier_gain < min_improvement:
            rejection_reasons.append("insufficient_brier_improvement")
        if not no_mae_regression:
            rejection_reasons.append("mae_regression")
        if not no_regret_regression:
            rejection_reasons.append("sampled_regret_regression")
        decisions.append(
            {
                "program_hash": report["program_hash"],
                "brier_gain": brier_gain,
                "eligible": eligible,
                "rejection_reasons": rejection_reasons,
            }
        )
        if eligible and report["metrics"]["brier"] < winner["metrics"]["brier"]:
            winner = report
    return {
        "accepted": winner["program_hash"] != baseline["program_hash"],
        "winner_program_hash": winner["program_hash"],
        "program": winner["program"],
        "min_brier_improvement": min_improvement,
        "candidates": decisions,
        "backend": baseline["backend"],
        "claim": "offline development selection only; confirm online and on final test",
    }


def optimize_round(
    train: dict,
    development: dict,
    program: QuestionProgram,
    evaluator,
    *,
    out: Path,
    min_improvement: float,
    proposals: dict | None = None,
    teacher=None,
    train_report: dict | None = None,
) -> dict:
    require_disjoint(train, development)
    if (proposals is None) == (teacher is None):
        raise ValueError("Provide either imported proposals or a teacher, exclusively")
    if train_report is not None:
        validate_training_report(train, program, evaluator, train_report)
    new_directory(out)
    status = {
        "status": "incomplete",
        "backend": evaluator.backend,
        "input_program_hash": program.hash,
        "train_dataset_hash": train["manifest"]["dataset_hash"],
        "development_dataset_hash": development["manifest"]["dataset_hash"],
        "reused_train_evaluation": train_report is not None,
    }
    write_json(out / "status.json", status)
    write_json(out / "input-program.json", program.to_dict())
    try:
        if train_report is None:
            train_report = evaluate(train, program, evaluator)
        write_json(out / "train-evaluation.json", train_report)
        packet = teacher_packet(train, program, train_report)
        write_json(out / "teacher-packet.json", packet)
        if teacher:
            proposals = teacher.propose(packet)
        write_json(out / "proposals.json", proposals)
        candidates = parse_candidates(proposals, program)
        write_json(
            out / "question-changes.json",
            {
                "kind": "question-changes-v1",
                "parent_program_hash": program.hash,
                "teacher_source": teacher.model if teacher else "imported-proposal",
                "teacher_input": "teacher-packet.json",
                "proposal": "proposals.json",
                "candidates": [
                    {
                        "program": candidate.to_dict(),
                        "program_hash": candidate.hash,
                        "changed_fields": {
                            key: {"before": program.to_dict()[key], "after": value}
                            for key, value in candidate.to_dict().items()
                            if value != program.to_dict()[key]
                        },
                    }
                    for candidate in candidates
                ],
            },
        )
        baseline = evaluate(development, program, evaluator)
        write_json(out / "development-baseline.json", baseline)
        if baseline["response_models"] != train_report["response_models"]:
            raise ValueError("Model version changed between training and development")
        reports = []
        for index, candidate in enumerate(candidates):
            report = evaluate(development, candidate, evaluator)
            write_json(out / f"development-candidate-{index}.json", report)
            reports.append(report)
        selection = select_candidate(baseline, reports, min_improvement)
        write_json(out / "selection.json", selection)
        write_json(out / "selected-program.json", selection["program"])
        status["status"] = "complete"
        status["accepted"] = selection["accepted"]
        return selection
    finally:
        write_json(out / "status.json", status)
        write_json(out / "jev-ledger.json", evaluator.ledger)
        if teacher:
            write_json(out / "teacher-ledger.json", teacher.api.ledger)


def validate_training_report(
    train: dict, program: QuestionProgram, evaluator, report: dict
) -> None:
    """Reject stale or partial feedback before reusing it instead of paid train calls."""
    expected = {
        "kind": "question-evaluation-v1",
        "split": "train",
        "dataset_hash": train["manifest"]["dataset_hash"],
        "protocol_hash": train["manifest"]["protocol"]["protocol_hash"],
        "program_hash": program.hash,
        "backend": evaluator.backend,
        "requested_model": evaluator.model,
    }
    for field, value in expected.items():
        if report.get(field) != value:
            raise ValueError(f"Reused training evaluation mismatch: {field}")
    if QuestionProgram.from_dict(report["program"]).hash != program.hash:
        raise ValueError("Reused training evaluation program differs")
    models = report["response_models"]
    if len(models) != 1 or not isinstance(models[0], str) or not models[0]:
        raise ValueError("Reused training evaluation must have exactly one response model")
    roots = {root["root_id"]: root for root in train["roots"]}
    rows = report["rows"]
    if len(rows) != len(roots) or {row["root_id"] for row in rows} != set(roots):
        raise ValueError("Reused training evaluation must cover every root exactly once")
    for row in rows:
        prediction = row["prediction"]
        if row["root_fingerprint"] != roots[row["root_id"]]["root_fingerprint"]:
            raise ValueError("Reused training evaluation root fingerprint differs")
        for field, value in (
            ("program_hash", program.hash),
            ("backend", evaluator.backend),
            ("requested_model", evaluator.model),
            ("response_model", models[0]),
        ):
            if prediction[field] != value:
                raise ValueError(f"Reused training prediction mismatch: {field}")
