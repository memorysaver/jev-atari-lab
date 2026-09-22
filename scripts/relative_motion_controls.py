"""Run and replay a frozen zero-model-call relative-motion control diagnostic."""

import argparse
import json
import subprocess
from pathlib import Path

from jev_atari.environment import Protocol
from jev_atari.experiment import play, split_for_seed
from jev_atari.io import digest, new_directory, read_json, write_json
from jev_atari.matches import aggregate_matches, match_result
from jev_atari.relative_motion import FRAMES, RULES, SEEDS, SOURCE_HASH, RelativePolicy
from jev_atari.replay import replay_episode


def run(out, proposal):
    if subprocess.check_output(["git", "status", "--porcelain"], text=True).strip():
        raise ValueError("Commit source/protocol before local trials")
    original = read_json(proposal)
    if digest(original["program"]) != SOURCE_HASH:
        raise ValueError("Teacher source program differs from the frozen hypothesis")
    if any(split_for_seed(s) != "train" for s in SEEDS):
        raise ValueError("Training-only diagnostic")
    new_directory(out)
    write_json(out / "teacher-source.json", original)
    plan = {
        "kind": "relative-motion-controls-v1",
        "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "seeds": list(SEEDS),
        "rules": list(RULES),
        "frames_per_episode": FRAMES,
        "protocol": Protocol().manifest(),
        "split": "train",
        "source_program_hash": SOURCE_HASH,
        "api_attempts": 0,
        "limits": "Manual Python interpretations, including a bounce-guard sensitivity arm. "
        "Not Jev gameplay or a teacher-policy promotion. Not fed to the running criteria study.",
    }
    write_json(out / "plan.json", plan)
    report = {"status": "incomplete", "plan_hash": digest(plan), "api_attempts": 0, "episodes": []}
    write_json(out / "results.json", report)
    try:
        for i, seed in enumerate(SEEDS):
            order = RULES[i % 4 :] + RULES[: i % 4]
            for rule in order:
                summary = play(
                    Protocol(),
                    RelativePolicy(rule),
                    seed=seed,
                    decisions=FRAMES // 4,
                    out=out / rule / f"seed-{seed}",
                    video=True,
                )
                row = {"seed": seed, "rule": rule, **summary, **match_result(summary, FRAMES)}
                if not row["evaluation_complete"]:
                    raise ValueError("Incomplete local control episode")
                report["episodes"].append(row)
                write_json(out / "results.json", report)
                print(json.dumps({"seed": seed, "rule": rule, "reward": row["reward"]}), flush=True)
        report.update(
            status="complete",
            aggregates={
                rule: aggregate_matches(
                    [r for r in report["episodes"] if r["rule"] == rule], len(SEEDS)
                )
                for rule in RULES
            },
        )
    finally:
        write_json(out / "results.json", report)
    return report


def verify(root, out):
    new_directory(out)
    plan, report = read_json(root / "plan.json"), read_json(root / "results.json")
    assert plan["seeds"] == list(SEEDS) and plan["rules"] == list(RULES)
    assert plan["frames_per_episode"] == FRAMES and plan["protocol"] == Protocol().manifest()
    assert (
        plan["source_program_hash"]
        == digest(read_json(root / "teacher-source.json")["program"])
        == SOURCE_HASH
    )
    assert report["plan_hash"] == digest(plan) and report["api_attempts"] == 0
    order = [(s, r) for i, s in enumerate(SEEDS) for r in RULES[i % 4 :] + RULES[: i % 4]]
    assert [(r["seed"], r["rule"]) for r in report["episodes"]] == order[: len(report["episodes"])]
    for row in report["episodes"]:
        p = root / row["rule"] / f"seed-{row['seed']}"
        policy = RelativePolicy(row["rule"])
        manifest, summary = read_json(p / "manifest.json"), read_json(p / "summary.json")
        assert manifest["seed"] == row["seed"] and manifest["split"] == "train"
        assert manifest["protocol"] == plan["protocol"] and manifest["max_decisions"] == FRAMES // 4
        assert manifest["policy"] == policy.name and manifest["point_limit"] is None
        assert all(row[k] == v for k, v in summary.items())
        assert all(row[k] == v for k, v in match_result(summary, FRAMES).items())
        for line in (p / "transitions.jsonl").read_text().splitlines():
            transition = json.loads(line)
            action, prediction = policy.choose(transition["observation"])
            assert action == transition["action"] and prediction == transition["prediction"]
        replay_episode(p, out / row["rule"] / f"seed-{row['seed']}")
    if report["status"] == "complete":
        assert len(report["episodes"]) == 32 and all(
            r["evaluation_complete"] for r in report["episodes"]
        )
        assert report["aggregates"] == {
            rule: aggregate_matches(
                [r for r in report["episodes"] if r["rule"] == rule], len(SEEDS)
            )
            for rule in RULES
        }
    result = {
        "status": "verified",
        "run_status": report["status"],
        "episodes": len(report["episodes"]),
        "plan_hash": digest(plan),
        "results_hash": digest(report),
        "audit_api_attempts": 0,
    }
    write_json(out / "verification.json", result)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("operation", choices=["run", "verify"])
    p.add_argument("--proposal", type=Path)
    p.add_argument("--run", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.operation == "run":
        if a.proposal is None:
            p.error("run requires --proposal")
        run(a.out, a.proposal)
    else:
        if a.run is None:
            p.error("verify requires --run")
        print(json.dumps(verify(a.run, a.out)))
