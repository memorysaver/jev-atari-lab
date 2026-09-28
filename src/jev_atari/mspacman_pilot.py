"""Bounded Ms. Pac-Man collection and deterministic offline audit. No implicit API."""

import argparse
import hashlib
import json
import random
import subprocess
import time
from collections import Counter
from importlib.metadata import version
from pathlib import Path

import ale_py.roms
import imageio.v2 as imageio

from jev_atari.arcade import make_game
from jev_atari.experiment import split_for_seed
from jev_atari.io import new_directory, read_json, write_json
from jev_atari.mspacman import NAMES, Observer, literal

PREFIX = 272


def revision():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def frame_record(env, reward, terminated, truncated):
    ram, rgb = env.unwrapped.ale.getRAM(), env.unwrapped.ale.getScreenRGB()
    return {
        "ram": ram.tolist(),
        "rgb_sha256": hashlib.sha256(rgb.tobytes()).hexdigest(),
        "reward": float(reward),
        "lives": env.unwrapped.ale.lives(),
        "terminated": bool(terminated),
        "truncated": bool(truncated),
    }


def play(path, seed, rule, *, cap=4096, hold=8, policy=None):
    if cap < 1 or hold < 1 or rule not in {"random", "pellet", "avoid", "direct", "two-stage"}:
        raise ValueError("Invalid episode contract")
    if (policy is not None) != (rule in {"direct", "two-stage"}):
        raise ValueError("Model episodes require an explicit policy")
    new_directory(path)
    rng = random.Random(seed)
    start = time.monotonic()
    s = {
        "status": "incomplete",
        "frames": 0,
        "controlled_frames": 0,
        "reward": 0.0,
        "prefix_reward": 0.0,
        "decisions": 0,
        "life_losses": 0,
        "terminated": False,
        "truncated": False,
    }
    action_counts, branches, checks_total = Counter(), Counter(), Counter()
    writer = None
    try:
        with make_game("MsPacman") as env, (path / "transitions.jsonl").open("x") as log:
            env.reset(seed=seed)
            assert tuple(env.unwrapped.get_action_meanings()) == NAMES
            initial_rgb = env.unwrapped.ale.getScreenRGB()
            imageio.imwrite(path / "initial.png", initial_rgb)
            observer = Observer(initial_rgb, hold)
            write_json(
                path / "manifest.json",
                {
                    "kind": "mspacman-episode-v1",
                    "seed": seed,
                    "split": split_for_seed(seed),
                    "rule": rule,
                    "controlled_cap": cap,
                    "hold": hold,
                    "prefix": PREFIX,
                    "sticky": 0.25,
                    "mode": 0,
                    "difficulty": 0,
                    "fps": 60,
                    "source_revision": revision(),
                    "source_hashes": {
                        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in (Path(__file__), Path(__file__).with_name("mspacman.py"))
                    },
                    "rom_sha256": hashlib.sha256(
                        ale_py.roms.get_rom_path("ms_pacman").read_bytes()
                    ).hexdigest(),
                    "versions": {p: version(p) for p in ("ale-py", "gymnasium", "numpy")},
                    "transport": policy.manifest if policy else {"backend": "local", "attempts": 0},
                },
            )
            if policy:
                policy.trace(path)
            writer = imageio.get_writer(
                path / "episode.mp4",
                fps=60,
                codec="libx264",
                macro_block_size=1,
                ffmpeg_log_level="error",
            )
            obs, checks = observer.observe(env.unwrapped.ale.getRAM(), initial_rgb, 0)
            lives = env.unwrapped.ale.lives()
            while s["frames"] < PREFIX + cap:
                controlled = s["frames"] >= PREFIX
                count = (
                    min(hold, PREFIX + cap - s["frames"])
                    if controlled
                    else min(hold, PREFIX - s["frames"])
                )
                prediction = None
                if not controlled:
                    action, branch = 0, "prefix"
                elif policy:
                    prediction = policy.choose(obs, rule)
                    action, branch = prediction["action"], "model"
                elif rule == "random":
                    action, branch = rng.randrange(len(NAMES)), "random"
                else:
                    action, branch = literal(obs, observer.maze, rule)
                frames = []
                for _ in range(count):
                    _, reward, terminated, truncated, _ = env.step(action)
                    frames.append(frame_record(env, reward, terminated, truncated))
                    rgb = env.unwrapped.ale.getScreenRGB()
                    writer.append_data(rgb)
                    s["frames"] += 1
                    s["controlled_frames"] += int(controlled)
                    s["reward" if controlled else "prefix_reward"] += float(reward)
                    new_lives = env.unwrapped.ale.lives()
                    s["life_losses"] += max(0, lives - new_lives)
                    lives = new_lives
                    if terminated or truncated:
                        break
                nxt, next_checks = observer.observe(env.unwrapped.ale.getRAM(), rgb, s["frames"])
                log.write(
                    json.dumps(
                        {
                            "controlled": controlled,
                            "observation": obs,
                            "checks": checks,
                            "action": action,
                            "branch": branch,
                            "prediction": prediction,
                            "frames": frames,
                            "next_observation": nxt,
                            "next_checks": next_checks,
                        }
                    )
                    + "\n"
                )
                log.flush()
                if controlled:
                    s["decisions"] += 1
                    action_counts[NAMES[action]] += 1
                    branches[branch] += 1
                    checks_total["observations"] += 1
                    checks_total["player_supported"] += int(checks["player_pixels"] > 0)
                    if checks["player_pixels"] > 0:
                        checks_total["supported_on_graph"] += int(checks["graph_error"] <= 3)
                    if s["decisions"] % 128 == 0:
                        print(
                            json.dumps(
                                {
                                    "episode": str(path),
                                    "decisions": s["decisions"],
                                    "reward": s["reward"],
                                }
                            ),
                            flush=True,
                        )
                obs, checks = nxt, next_checks
                s.update(terminated=terminated, truncated=truncated)
                if terminated or truncated or obs["maze_id"] != 0:
                    break
            s.update(
                status="complete",
                end_reason="native_termination"
                if s["terminated"]
                else "environment_truncation"
                if s["truncated"]
                else "unsupported_maze_change"
                if obs["maze_id"] != 0
                else "frame_cap",
            )
    finally:
        if writer:
            writer.close()
        s.update(
            wall_seconds=time.monotonic() - start,
            action_histogram=dict(action_counts),
            branches=dict(branches),
            observation_checks=dict(checks_total),
        )
        if policy:
            s["resources"] = policy.resources()
        write_json(path / "summary.json", s)
    print(json.dumps({"episode": str(path), "summary": s}), flush=True)
    return s


def audit(path):
    m, s = read_json(path / "manifest.json"), read_json(path / "summary.json")
    count, reward, prefix_reward, decisions, life_losses = 0, 0.0, 0.0, 0, 0
    rng = random.Random(m["seed"])
    with make_game("MsPacman", m["sticky"]) as env:
        env.reset(seed=m["seed"])
        observer = Observer(env.unwrapped.ale.getScreenRGB(), m["hold"])
        obs, checks = observer.observe(
            env.unwrapped.ale.getRAM(), env.unwrapped.ale.getScreenRGB(), 0
        )
        lives = env.unwrapped.ale.lives()
        for line in (path / "transitions.jsonl").open():
            row = json.loads(line)
            assert row["observation"] == obs and row["checks"] == checks
            assert row["controlled"] == (count >= m["prefix"])
            assert 1 <= len(row["frames"]) <= m["hold"]
            if not row["controlled"]:
                assert row["action"] == 0 and row["prediction"] is None
            elif m["rule"] == "random":
                assert row["action"] == rng.randrange(len(NAMES))
            elif m["rule"] in {"pellet", "avoid"}:
                assert (row["action"], row["branch"]) == literal(obs, observer.maze, m["rule"])
            else:
                assert row["prediction"]["action"] == row["action"]
            decisions += int(row["controlled"])
            for expected in row["frames"]:
                _, r, t, tr, _ = env.step(row["action"])
                assert frame_record(env, r, t, tr) == expected
                count += 1
                if row["controlled"]:
                    reward += r
                else:
                    prefix_reward += r
                new_lives = env.unwrapped.ale.lives()
                life_losses += max(0, lives - new_lives)
                lives = new_lives
            obs, checks = observer.observe(
                env.unwrapped.ale.getRAM(), env.unwrapped.ale.getScreenRGB(), count
            )
            assert row["next_observation"] == obs and row["next_checks"] == checks
    assert count == s["frames"] and decisions == s["decisions"]
    assert reward == s["reward"] and prefix_reward == s["prefix_reward"]
    assert life_losses == s["life_losses"]
    video = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-count_frames",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=nb_read_frames,r_frame_rate",
                "-of",
                "json",
                str(path / "episode.mp4"),
            ],
            text=True,
        )
    )["streams"][0]
    assert int(video["nb_read_frames"]) == count and video["r_frame_rate"] == "60/1"
    return {
        "path": str(path),
        "frames": count,
        "decisions": decisions,
        "reward": reward,
        "raw_frame_replay": True,
        "observation_replay": True,
        "video_frames": count,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["calibrate", "audit"])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "calibrate":
        new_directory(args.out)
        write_json(
            args.out / "plan.json",
            {
                "seeds": [510, 511],
                "rules": ["random", "pellet", "avoid"],
                "cap": 4096,
                "hold": 8,
                "api_attempts": 0,
            },
        )
        results = []
        for rule in ("random", "pellet", "avoid"):
            for seed in (510, 511):
                path = args.out / rule / f"seed-{seed}"
                results.append({"rule": rule, "seed": seed, "summary": play(path, seed, rule)})
        write_json(args.out / "results.json", results)
    else:
        results = [audit(p.parent) for p in sorted(args.out.rglob("manifest.json"))]
        write_json(args.out / "audit.json", results)
        print(json.dumps(results))


if __name__ == "__main__":
    main()
