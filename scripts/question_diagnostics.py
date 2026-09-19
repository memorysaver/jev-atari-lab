"""Offline question adherence and separately labeled literal Python control trials."""

import argparse
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from jev_atari.environment import Protocol
from jev_atari.experiment import play
from jev_atari.io import digest, new_directory, read_json, write_json
from jev_atari.matches import aggregate_matches, match_result
from jev_atari.question_diagnostics import RULES, DiagnosticPolicy, interpret
from jev_atari.replay import replay_episode

SEEDS = (80, 81, 82, 83)
FRAMES = 20000


def metrics(rows):
    n = len(rows)
    return {
        "n": n,
        "matches": sum(r["match"] for r in rows),
        "agreement": sum(r["match"] for r in rows) / n if n else None,
        "confusion": dict(Counter(f"{r['expected']}->{r['actual']}" for r in rows)),
        "mean_probability_of_rule_action": sum(r["rule_probability"] for r in rows) / n
        if n
        else None,
    }


def analyze(study, out, repository):
    new_directory(out)
    manifest = read_json(
        repository / "experiments/pong/teacher-study-v1/teacher-study-v1.manifest.json"
    )
    expected = {f["path"]: f["sha256"] for f in manifest["files"]}
    sources = {}

    def load(relative, lines=False):
        raw = (study / relative).read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        if sha != expected[f"teacher-study-v1/run/{relative}"]:
            raise ValueError(f"Published source differs: {relative}")
        sources[relative] = sha
        return [json.loads(line) for line in raw.splitlines()] if lines else json.loads(raw)

    groups = defaultdict(list)
    with (out / "decisions.jsonl").open("x") as stream:
        for arm in ("A", "B"):
            for role in ("parent", "candidate"):
                for seed in (66, 67):
                    relative = (
                        f"round-01/{arm}/development/{role}/seed-{seed}/jev/"
                        f"seed-{seed}/transitions.jsonl"
                    )
                    for row in load(relative, True):
                        for rule in RULES:
                            d = interpret(row["observation"], rule)
                            actual = row["action"]
                            record = {
                                "source": relative,
                                "decision": row["decision"],
                                "arm": arm,
                                "role": role,
                                "seed": seed,
                                **d,
                                "expected": d["action"],
                                "actual": actual,
                                "match": actual == d["action"],
                                "rule_probability": row["prediction"]["action_probabilities"][
                                    str(d["action"])
                                ],
                            }
                            stream.write(json.dumps(record) + "\n")
                            groups[(arm, role, seed, rule)].append(record)
    trajectories = []
    for (arm, role, seed, rule), rows in groups.items():
        strata = {}
        for field in ("motion", "mode", "reflections"):
            bins = defaultdict(list)
            for row in rows:
                bins[str(row[field])].append(row)
            strata[field] = {key: metrics(values) for key, values in sorted(bins.items())}
        trajectories.append(
            {
                "arm": arm,
                "role": role,
                "seed": seed,
                "rule": rule,
                **metrics(rows),
                "strata": strata,
            }
        )
    probes = []
    for arm in ("A", "B"):
        states = {s["id"]: s["observation"] for s in load(f"round-01/{arm}/probes/inputs.json")}
        predictions = load(f"round-01/{arm}/probes/predictions.jsonl", True)
        for role in ("parent", "candidate"):
            for rule in RULES:
                rows = []
                for row in predictions:
                    if row["program_role"] != role:
                        continue
                    expected_action = interpret(states[row["id"]], rule)["action"]
                    actual = row["prediction"]["chosen_action"]
                    rows.append(
                        {
                            "actual": actual,
                            "expected": expected_action,
                            "match": actual == expected_action,
                            "rule_probability": row["prediction"]["action_probabilities"][
                                str(expected_action)
                            ],
                        }
                    )
                probes.append({"arm": arm, "role": role, "rule": rule, **metrics(rows)})
    report = {
        "kind": "question-adherence-diagnostics-v1",
        "status": "complete",
        "api_attempts": 0,
        "source_archive_sha256": manifest["sha256"],
        "source_files": sources,
        "trajectories": trajectories,
        "shared_training_probes": probes,
        "limits": "Post-hoc rule interpretations, not optimal-action labels or causal effects. "
        "Visited states differ between trajectories. Probe repeats are not independent states. "
        "B reliability wording is underspecified; both operationalizations are reported.",
    }
    write_json(out / "results.json", report)
    return report


def run_local(out):
    if subprocess.check_output(["git", "status", "--porcelain"], text=True).strip():
        raise ValueError("Freeze source in a clean worktree before control trials")
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    protocol = Protocol()
    new_directory(out)
    plan = {
        "kind": "literal-question-trial-v1",
        "source_revision": source,
        "seeds": list(SEEDS),
        "split": "train",
        "frames_per_episode": FRAMES,
        "rules": list(RULES),
        "protocol": protocol.manifest(),
        "api_attempts": 0,
        "video": True,
        "purpose": "Python operationalizations only; no Jev, teacher, selection or held-out claim.",
    }
    write_json(out / "plan.json", plan)
    report = {"status": "incomplete", "plan_hash": digest(plan), "api_attempts": 0, "episodes": []}
    try:
        for seed in SEEDS:
            for rule in RULES:
                summary = play(
                    protocol,
                    DiagnosticPolicy(rule),
                    seed=seed,
                    decisions=FRAMES // 4,
                    out=out / rule / f"seed-{seed}",
                    video=True,
                )
                report["episodes"].append(
                    {"rule": rule, "seed": seed, **summary, **match_result(summary, FRAMES)}
                )
                write_json(out / "results.json", report)
                print(
                    json.dumps(
                        {
                            "rule": rule,
                            "seed": seed,
                            "score": [summary["points_scored"], summary["points_lost"]],
                        }
                    ),
                    flush=True,
                )
        report["aggregates"] = {
            rule: aggregate_matches(
                [e for e in report["episodes"] if e["rule"] == rule], len(SEEDS)
            )
            for rule in RULES
        }
        report["status"] = "complete"
    finally:
        write_json(out / "results.json", report)
    return report


def verify_local(run, out):
    new_directory(out)
    plan, report = read_json(run / "plan.json"), read_json(run / "results.json")
    assert report["plan_hash"] == digest(plan) and report["status"] == "complete"
    assert plan["seeds"] == list(SEEDS) and plan["rules"] == list(RULES)
    assert (
        plan["frames_per_episode"] == FRAMES and plan["api_attempts"] == report["api_attempts"] == 0
    )
    assert [(e["seed"], e["rule"]) for e in report["episodes"]] == [
        (s, r) for s in SEEDS for r in RULES
    ]
    checks = []
    for entry in report["episodes"]:
        rule, seed = entry["rule"], entry["seed"]
        path = run / rule / f"seed-{seed}"
        manifest, summary = read_json(path / "manifest.json"), read_json(path / "summary.json")
        assert manifest["protocol"] == plan["protocol"] and manifest["split"] == "train"
        assert manifest["seed"] == seed and manifest["policy"] == DiagnosticPolicy(rule).name
        assert manifest["max_decisions"] == FRAMES // 4 and manifest["point_limit"] is None
        assert all(entry[k] == v for k, v in {**summary, **match_result(summary, FRAMES)}.items())
        with (path / "transitions.jsonl").open() as stream:
            for line in stream:
                row = json.loads(line)
                action, prediction = DiagnosticPolicy(rule).choose(row["observation"])
                assert row["action"] == action and row["prediction"] == prediction
        checked = replay_episode(path, out / rule / f"seed-{seed}")
        checks.append(
            {
                "rule": rule,
                "seed": seed,
                "status": checked["status"],
                "raw_frames": checked["raw_frames"],
            }
        )
    assert report["aggregates"] == {
        rule: aggregate_matches([e for e in report["episodes"] if e["rule"] == rule], len(SEEDS))
        for rule in RULES
    }
    result = {
        "status": "verified",
        "api_attempts": 0,
        "plan_hash": digest(plan),
        "results_hash": digest(report),
        "episodes": checks,
    }
    write_json(out / "verification.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["analyze", "play", "verify"])
    parser.add_argument("--study", type=Path)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    args = parser.parse_args()
    if args.operation == "analyze":
        analyze(args.study, args.out, args.repository)
    elif args.operation == "play":
        run_local(args.out)
    else:
        verify_local(args.run, args.out)
