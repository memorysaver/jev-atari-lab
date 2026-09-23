"""Replay a preserved Seaquest calibration without model calls or new policy sampling."""

import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

import ale_py.roms
from seaquest_calibration import FRAMES, HOLD, POLICIES, SEEDS, action_effects, trajectory

from jev_atari.io import digest, new_directory, read_json, write_json
from jev_atari.seaquest import EXTRACTOR, UPSTREAM


def verify(root, out):
    plan = read_json(root / "plan.json")
    report = read_json(root / "results.json")
    assert plan["kind"] == "seaquest-calibration-v1"
    assert plan["game"] == "ALE/Seaquest-v5" and plan["split"] == "train"
    assert plan["extractor"] == EXTRACTOR and plan["upstream"] == UPSTREAM
    assert plan["seeds"] == list(SEEDS) and plan["policies"] == list(POLICIES)
    assert plan["max_controlled_frames_per_episode"] == FRAMES
    assert plan["hold_frames"] == HOLD and plan["frameskip"] == 1 and plan["sticky"] == 0.25
    assert plan["mode"] == plan["difficulty"] == plan["reset_noops"] == 0
    assert not plan["automatic_fire"] and plan["max_api_attempts"] == 0
    assert plan["versions"] == {p: version(p) for p in plan["versions"]}
    assert (
        plan["rom_sha256"]
        == hashlib.sha256(ale_py.roms.get_rom_path("seaquest").read_bytes()).hexdigest()
    )
    assert report["status"] == "complete" and report["plan_hash"] == digest(plan)
    assert report["api_attempts"] == 0 and len(report["episodes"]) == 8
    assert [(e["policy"], e["seed"]) for e in report["episodes"]] == [
        (p, seed) for p in POLICIES for seed in SEEDS
    ]
    assert action_effects() == read_json(root / "action-effects.json")
    new_directory(out)
    for row in report["episodes"]:
        source = root / row["policy"] / f"seed-{row['seed']}"
        target = out / row["policy"] / f"seed-{row['seed']}"
        with (source / "transitions.jsonl").open() as stream:
            replay = trajectory(
                target, row["seed"], row["policy"], recorded=(json.loads(line) for line in stream)
            )
        assert row == {**replay, "replay_verified": True}
        assert read_json(source / "initial.json") == read_json(target / "initial.json")
        summary = read_json(source / "summary.json")
        assert {k: v for k, v in summary.items() if k != "wall_seconds"} == replay
    result = {
        "kind": "seaquest-calibration-audit-v1",
        "status": "verified",
        "episodes": 8,
        "plan_hash": digest(plan),
        "results_hash": digest(report),
        "replay_frames": sum(e["controlled_frames"] for e in report["episodes"]),
        "action_probe_frames": 3312,
        "api_attempts": 0,
        "scope": "Recorded action/raw-frame/observation replay and recomputed metrics; "
        "this does not establish full semantic correctness or learning.",
    }
    write_json(out / "verification.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.run, args.out)))
