"""Prospective fresh-training visibility/box support gate; no model calls."""

import argparse
import hashlib
import json
import random
import subprocess
from collections import Counter
from importlib.metadata import version
from pathlib import Path

import ale_py.roms

from jev_atari.arcade import make_game
from jev_atari.io import digest, new_directory, write_json
from jev_atari.seaquest_observation import SCHEMA, Observer, screen_checks

SEEDS = (302, 303)
POLICIES = ("random", "sweep")
FRAMES = 8000


def episode(seed, policy, path):
    new_directory(path)
    observer, rng = Observer(), random.Random(seed)
    counts, supported = Counter(), Counter()
    summary = {
        "seed": seed,
        "policy": policy,
        "frames": 0,
        "decisions": 0,
        "reward": 0,
        "oxygen_checks": 0,
        "oxygen_matches": 0,
        "unavailable_states": 0,
        "life_losses": 0,
    }
    with make_game("Seaquest") as env, (path / "transitions.jsonl").open("x") as stream:
        env.reset(seed=seed)
        names = env.unwrapped.get_action_meanings()
        lives = env.unwrapped.ale.lives()
        obs = observer.observe(env.unwrapped.ale.getRAM(), raw_frame=0, lives=lives, names=names)
        for decision in range(FRAMES // 4):
            action = (
                rng.randrange(18)
                if policy == "random"
                else names.index(
                    ("DOWNFIRE", "RIGHTFIRE", "UPFIRE", "LEFTFIRE")[(decision // 100) % 4]
                )
            )
            frames = []
            for _ in range(4):
                _, reward, terminated, truncated, _ = env.step(action)
                ram = env.unwrapped.ale.getRAM()
                rgb = env.unwrapped.ale.getScreenRGB()
                next_lives = env.unwrapped.ale.lives()
                frames.append(
                    {
                        "ram": ram.tolist(),
                        "rgb_hash": hashlib.sha256(rgb.tobytes()).hexdigest(),
                        "reward": float(reward),
                        "lives": next_lives,
                        "terminated": terminated,
                        "truncated": truncated,
                    }
                )
                summary["frames"] += 1
                summary["reward"] += float(reward)
                summary["life_losses"] += max(0, lives - next_lives)
                lives = next_lives
                if terminated or truncated:
                    break
            next_obs = observer.observe(
                ram,
                raw_frame=summary["frames"],
                lives=lives,
                names=names,
                ended=terminated or truncated,
            )
            checks = screen_checks(next_obs, rgb)
            summary["oxygen_checks"] += 1
            summary["oxygen_matches"] += checks["oxygen_matches"]
            summary["unavailable_states"] += next_obs["object_state"] != "active"
            for obj in checks["objects"]:
                counts[obj["kind"]] += 1
                supported[obj["kind"]] += obj["color_pixels"] > 0
            stream.write(
                json.dumps(
                    {
                        "observation": obs,
                        "action": action,
                        "frames": frames,
                        "next_observation": next_obs,
                        "checks": checks,
                    }
                )
                + "\n"
            )
            obs = next_obs
            summary["decisions"] += 1
            if terminated or truncated:
                break
    summary.update(
        status="complete", objects=dict(counts), supported=dict(supported), api_attempts=0
    )
    write_json(path / "summary.json", summary)
    return summary


def verify_episode(path, out):
    from jev_atari.io import read_json

    summary = read_json(path / "summary.json")
    observer, count, raw_frame = Observer(), 0, 0
    with make_game("Seaquest") as env, (path / "transitions.jsonl").open() as stream:
        env.reset(seed=summary["seed"])
        names = env.unwrapped.get_action_meanings()
        obs = observer.observe(
            env.unwrapped.ale.getRAM(), raw_frame=0, lives=env.unwrapped.ale.lives(), names=names
        )
        for line in stream:
            row = json.loads(line)
            assert row["observation"] == obs
            for expected in row["frames"]:
                _, reward, terminated, truncated, _ = env.step(row["action"])
                rgb = env.unwrapped.ale.getScreenRGB()
                ram = env.unwrapped.ale.getRAM()
                assert expected == {
                    "ram": ram.tolist(),
                    "rgb_hash": hashlib.sha256(rgb.tobytes()).hexdigest(),
                    "reward": float(reward),
                    "lives": env.unwrapped.ale.lives(),
                    "terminated": terminated,
                    "truncated": truncated,
                }
                raw_frame += 1
            obs = observer.observe(
                ram,
                raw_frame=raw_frame,
                lives=env.unwrapped.ale.lives(),
                names=names,
                ended=terminated or truncated,
            )
            assert obs == row["next_observation"] and screen_checks(obs, rgb) == row["checks"]
            count += 1
    assert count == summary["decisions"] and raw_frame == summary["frames"]
    result = {
        "status": "verified",
        "decisions": count,
        "raw_frames": raw_frame,
        "api_attempts": 0,
        "summary_hash": digest(summary),
    }
    write_json(out / "verification.json", result)
    return result


def run(root):
    if subprocess.check_output(["git", "status", "--porcelain"], text=True).strip():
        raise ValueError("Commit source/protocol before fresh validation")
    new_directory(root)
    plan = {
        "kind": "seaquest-observation-check-v2",
        "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "seeds": SEEDS,
        "policies": POLICIES,
        "frames": FRAMES,
        "schema": SCHEMA,
        "versions": {p: version(p) for p in ("ale-py", "gymnasium", "numpy")},
        "rom_sha256": hashlib.sha256(ale_py.roms.get_rom_path("seaquest").read_bytes()).hexdigest(),
        "api_attempts": 0,
        "gate": "oxygen 100%; player >=1000 observations and >=99% color support; "
        "shark/diver/player_missile each >=20 observations and >=95% color support. "
        "Other unobserved object classes remain unvalidated.",
    }
    write_json(root / "plan.json", plan)
    rows = []
    write_json(
        root / "results.json",
        {"status": "incomplete", "plan_hash": digest(plan), "api_attempts": 0},
    )
    for policy in POLICIES:
        for seed in SEEDS:
            path = root / policy / f"seed-{seed}"
            rows.append(episode(seed, policy, path))
            verify_episode(path, root / "replay" / policy / f"seed-{seed}")
            write_json(
                root / "results.json",
                {
                    "status": "incomplete",
                    "plan_hash": digest(plan),
                    "episodes": rows,
                    "api_attempts": 0,
                },
            )
    counts, supported = Counter(), Counter()
    for row in rows:
        counts.update(row["objects"])
        supported.update(row["supported"])
    gates = {
        "oxygen": sum(r["oxygen_checks"] for r in rows) == sum(r["oxygen_matches"] for r in rows)
    }
    for kind, minimum, rate in (
        ("player", 1000, 0.99),
        ("shark", 20, 0.95),
        ("diver", 20, 0.95),
        ("player_missile", 20, 0.95),
    ):
        gates[kind] = counts[kind] >= minimum and supported[kind] / max(1, counts[kind]) >= rate
    report = {
        "status": "complete",
        "plan_hash": digest(plan),
        "episodes": rows,
        "objects": dict(counts),
        "supported": dict(supported),
        "gates": gates,
        "pilot_gate_passed": all(gates.values()),
        "api_attempts": 0,
        "limits": "Color support within a proposed box is not exact shape, identity, recall, "
        "or event-semantics validation. No claim for unvisited subtypes or full rescue cycles.",
    }
    write_json(root / "results.json", report)
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    run(p.parse_args().out)
