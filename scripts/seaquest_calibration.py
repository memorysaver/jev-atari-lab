"""Bounded, zero-model-call Seaquest mapping calibration with exact recorded-action replay."""

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
from jev_atari.io import digest, new_directory, write_json
from jev_atari.seaquest import EXTRACTOR, UPSTREAM, decode, pixel_checks

SEEDS = (300, 301)
POLICIES = ("noop", "fire", "random", "scripted-sweep")
FRAMES = 8000
HOLD = 4


def action_for(policy, decision, names, rng):
    if policy == "random":
        return rng.randrange(len(names))
    if policy == "scripted-sweep":
        # Fixed open-loop coverage routine, not an optimized or teacher-authored policy.
        name = ("DOWNFIRE", "RIGHTFIRE", "UPFIRE", "LEFTFIRE")[(decision // 100) % 4]
    else:
        name = {"noop": "NOOP", "fire": "FIRE"}[policy]
    return names.index(name)


def trajectory(path, seed, policy, *, recorded=None, video=False, frames=FRAMES):
    new_directory(path)
    env = make_game("Seaquest", sticky=0.25)
    rng = random.Random(seed)
    writer = None
    stats = {
        "seed": seed,
        "policy": policy,
        "reward": 0.0,
        "controlled_frames": 0,
        "decisions": 0,
        "life_losses": 0,
        "oxygen_pixel_matches": 0,
        "pixel_checks": 0,
        "player_boxes": 0,
        "player_boxes_with_color": 0,
        "terminated": False,
        "truncated": False,
        "api_attempts": 0,
    }
    oxygen, divers, kinds, actions = set(), set(), Counter(), Counter()
    reference = iter(recorded) if recorded is not None else None
    start = time.monotonic()
    try:
        env.reset(seed=seed)
        names = env.unwrapped.get_action_meanings()
        initial = decode(env.unwrapped.ale.getRAM())
        write_json(path / "initial.json", initial)
        lives = env.unwrapped.ale.lives()
        if video:
            writer = imageio.get_writer(
                path / "episode.mp4",
                fps=60,
                codec="libx264",
                macro_block_size=1,
                ffmpeg_log_level="error",
            )
        with (path / "transitions.jsonl").open("x") as stream:
            for decision in range((frames + HOLD - 1) // HOLD):
                before = decode(env.unwrapped.ale.getRAM())
                expected = next(reference, None) if reference is not None else None
                if reference is not None and expected is None:
                    raise ValueError("Replay is missing an action")
                action = (
                    expected["action"] if expected else action_for(policy, decision, names, rng)
                )
                raw = []
                for _ in range(min(HOLD, frames - stats["controlled_frames"])):
                    _, reward, terminated, truncated, _ = env.step(action)
                    rgb = env.unwrapped.ale.getScreenRGB().copy()
                    ram = env.unwrapped.ale.getRAM()
                    new_lives = env.unwrapped.ale.lives()
                    raw.append(
                        {
                            "ram_bytes": ram.tolist(),
                            "rgb_sha256": hashlib.sha256(rgb.tobytes()).hexdigest(),
                            "reward": float(reward),
                            "lives": new_lives,
                            "terminated": terminated,
                            "truncated": truncated,
                        }
                    )
                    stats["controlled_frames"] += 1
                    stats["reward"] += float(reward)
                    stats["life_losses"] += max(0, lives - new_lives)
                    lives = new_lives
                    if writer:
                        writer.append_data(rgb)
                    if terminated or truncated:
                        break
                after = decode(ram)
                checks = pixel_checks(after, rgb)
                row = {
                    "decision": decision,
                    "observation": before,
                    "action": action,
                    "action_name": names[action],
                    "frames": raw,
                    "next_observation": after,
                    "pixel_checks": checks,
                }
                if expected is not None and row != expected:
                    raise ValueError(f"Replay mismatch at decision {decision}")
                stream.write(json.dumps(row) + "\n")
                stats["decisions"] += 1
                actions[names[action]] += 1
                oxygen.add(after["oxygen_raw"])
                divers.add(after["carried_divers_raw"])
                kinds.update(o["kind"] for o in after["objects"])
                stats["pixel_checks"] += 1
                stats["oxygen_pixel_matches"] += int(checks["oxygen_width_matches_ram"])
                if checks["player_color_pixels_inside_box"] is not None:
                    stats["player_boxes"] += 1
                    stats["player_boxes_with_color"] += int(
                        checks["player_color_pixels_inside_box"] > 0
                    )
                stats.update(terminated=terminated, truncated=truncated)
                if terminated or truncated:
                    break
        if reference is not None and next(reference, None) is not None:
            raise ValueError("Replay has unexecuted recorded actions")
        stats.update(
            status="complete",
            oxygen_raw_values=sorted(oxygen),
            carried_diver_raw_values=sorted(divers),
            object_counts=dict(kinds),
            action_counts=dict(actions),
            horizon_reached=stats["controlled_frames"] == frames,
        )
    finally:
        env.close()
        if writer:
            writer.close()
        write_json(path / "summary.json", {**stats, "wall_seconds": time.monotonic() - start})
    return stats


def action_effects():
    """Matched reset/warmup for each native action; sticky zero isolates requested effects."""
    rows = []
    for action in range(18):
        env = make_game("Seaquest", sticky=0)
        try:
            env.reset(seed=300)
            names = env.unwrapped.get_action_meanings()
            for _ in range(128):
                env.step(names.index("NOOP"))
            for _ in range(40):
                env.step(names.index("DOWN"))
            before = decode(env.unwrapped.ale.getRAM())
            for _ in range(16):
                env.step(action)
            after = decode(env.unwrapped.ale.getRAM())
            first = next((o for o in before["objects"] if o["kind"] == "player"), None)
            last = next((o for o in after["objects"] if o["kind"] == "player"), None)
            rows.append(
                {
                    "action": action,
                    "name": names[action],
                    "before": before,
                    "after": after,
                    "player_delta_xy": [last["bbox"][i] - first["bbox"][i] for i in (0, 1)]
                    if first and last
                    else None,
                }
            )
        finally:
            env.close()
    return rows


def run(root):
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if subprocess.check_output(["git", "status", "--porcelain"], text=True).strip():
        raise ValueError("Freeze calibration source before collecting data")
    new_directory(root)
    env = make_game("Seaquest")
    try:
        plan = {
            "kind": "seaquest-calibration-v1",
            "source_revision": source,
            "game": "ALE/Seaquest-v5",
            "extractor": EXTRACTOR,
            "upstream": UPSTREAM,
            "seeds": SEEDS,
            "split": "train",
            "policies": POLICIES,
            "max_controlled_frames_per_episode": FRAMES,
            "hold_frames": HOLD,
            "sticky": 0.25,
            "frameskip": 1,
            "reset_noops": 0,
            "automatic_fire": False,
            "mode": 0,
            "difficulty": 0,
            "action_names": env.unwrapped.get_action_meanings(),
            "rom_sha256": hashlib.sha256(
                ale_py.roms.get_rom_path("seaquest").read_bytes()
            ).hexdigest(),
            "versions": {p: version(p) for p in ("ale-py", "gymnasium", "numpy")},
            "max_api_attempts": 0,
            "action_probe_frames": 18 * 184,
            "limits": "Training-only calibration; no learned strategy "
            "or validated event-cause detector.",
        }
    finally:
        env.close()
    write_json(root / "plan.json", plan)
    report = {"status": "incomplete", "plan_hash": digest(plan), "episodes": [], "api_attempts": 0}
    try:
        write_json(root / "action-effects.json", action_effects())
        for policy in POLICIES:
            for seed in SEEDS:
                path = root / policy / f"seed-{seed}"
                summary = trajectory(path, seed, policy, video=seed == SEEDS[0])
                with (path / "transitions.jsonl").open() as stream:
                    replay = trajectory(
                        root / "replay" / policy / f"seed-{seed}",
                        seed,
                        policy,
                        recorded=(json.loads(line) for line in stream),
                    )
                if summary != replay:
                    raise ValueError("Replayed metrics mismatch")
                report["episodes"].append({**summary, "replay_verified": True})
                write_json(root / "results.json", report)
                print(
                    json.dumps(
                        {
                            "policy": policy,
                            "seed": seed,
                            "reward": summary["reward"],
                            "frames": summary["controlled_frames"],
                            "replay_verified": True,
                        }
                    ),
                    flush=True,
                )
        report["status"] = "complete"
    finally:
        write_json(root / "results.json", report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    run(parser.parse_args().out)
