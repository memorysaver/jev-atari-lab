"""Offline Freeway replay, API/action, video and frozen-study audit."""

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from statistics import mean

from jev_atari.arcade import make_game
from jev_atari.choice import validate_choices
from jev_atari.experiment import split_for_seed
from jev_atari.freeway import NAMES, FreewayProgram, Observer, literal, prefix_length, screen_checks
from jev_atari.freeway_research import LIMITS, context_stratum
from jev_atari.io import digest, read_json, write_json
from jev_atari.seaquest_pilot import MODEL, PIN


def exchanges(path, program=None):
    rows = [json.loads(line) for line in path.open()] if path.exists() else []
    result = {}
    for row in rows:
        assert row["request"]["model"] == MODEL
        if row["response"] is None:
            continue
        assert row["response"]["model"] == PIN
        obs = row["request"]["state"]["observation"]
        if program:
            assert row["request"] == program.request(obs, row["request"]["model"])
        answer = validate_choices(
            row["response"], row["request"]["questions"], prefer_probabilities=True
        )
        result[row["exchange_id"]] = (obs, NAMES.index(answer["next_action"]["choice"]))
    return rows, result


def episode(path):
    m, s = read_json(path / "manifest.json"), read_json(path / "summary.json")
    assert s["status"] == "complete"
    assert m["split"] == split_for_seed(m["seed"])
    program = FreewayProgram.from_dict(m["program"]) if m["program"] else None
    if program:
        assert program.hash == m["program_hash"]
    api, successful = exchanges(path / "model-exchanges.jsonl", program)
    ledger = read_json(path / "api-ledger.json")
    assert [r["transport"] for r in api] == ledger and len(api) == s["api_attempts"]
    observer = Observer(m["hold"])
    frames = decisions = 0
    reward = prefix = 0.0
    counts = Counter()
    import random

    rng = random.Random(m["seed"])
    with make_game("Freeway") as env:
        env.reset(seed=m["seed"])
        obs = observer.observe(env.unwrapped.ale.getRAM(), 0)
        for line in (path / "transitions.jsonl").open():
            row = json.loads(line)
            assert row["observation"] == obs
            controlled = frames >= prefix_length(m["seed"])
            assert row["phase"] == ("control" if controlled else "prefix")
            if controlled:
                decisions += 1
                counts[NAMES[row["action"]]] += 1
                if program:
                    observed, action = successful.pop(row["prediction"]["exchange_id"])
                    assert (
                        observed == obs
                        and action == row["action"] == row["prediction"]["chosen_action"]
                    )
                    assert row["prediction"]["program_hash"] == program.hash
                elif m["rule"] == "random":
                    assert row["action"] == rng.randrange(3)
                else:
                    assert (row["action"], row["branch"]) == literal(obs, m["rule"])
            else:
                assert row["action"] == 0 and row["prediction"] is None
            assert len(row["frames"]) <= m["hold"]
            for expected in row["frames"]:
                _, r, t, tr, _ = env.step(row["action"])
                ram, rgb = env.unwrapped.ale.getRAM(), env.unwrapped.ale.getScreenRGB()
                assert expected == dict(
                    ram=ram.tolist(),
                    rgb_hash=hashlib.sha256(rgb.tobytes()).hexdigest(),
                    reward=float(r),
                    terminated=t,
                    truncated=tr,
                )
                frames += 1
                if controlled:
                    reward += r
                else:
                    prefix += r
            obs = observer.observe(ram, frames, t or tr)
            assert row["next_observation"] == obs and row["checks"] == screen_checks(obs, rgb)
    assert not successful
    assert frames == s["frames"] and decisions == s["decisions"]
    assert reward == s["reward"] and prefix == s["prefix_reward"]
    assert dict(counts) == s["action_histogram"]
    assert t == s["terminated"] and tr == s["truncated"]
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
    assert int(video["nb_read_frames"]) == frames and video["r_frame_rate"] == "60/1"
    return dict(
        path=str(path),
        seed=m["seed"],
        frames=frames,
        decisions=decisions,
        reward=reward,
        api_attempts=len(api),
        native_ended=t,
        video_sha256=hashlib.sha256((path / "episode.mp4").read_bytes()).hexdigest(),
    )


def verify(root, out):
    reports = []
    plan = read_json(root / "plan.json")
    for p in sorted(root.glob("round-*/*/manifest.json")):
        number = int(p.parent.parent.name.split("-")[1])
        manifest = read_json(p)
        assert manifest["seed"] in (
            plan["train"] if number <= 8 else plan["development"] if number == 9 else plan["final"]
        )
        if number >= 2:
            assert manifest["source_revision"] == plan["source_revision"]
        verified = episode(p.parent)
        verified["path"] = str(p.parent.relative_to(root))
        reports.append(verified)
        print(json.dumps({"verified": str(p.parent)}), flush=True)
    attempts = []
    for p in sorted(root.glob("round-*/probe")):
        pack = read_json(p / "packet.json")
        states = {r["id"]: r for r in pack["rows"]}
        for row in states.values():
            assert row["id"] == digest(row["observation"])
            assert (row["expected"], row["branch"]) == literal(row["observation"])
            assert row["stratum"] == context_stratum(row["observation"])
        api, success = exchanges(p / "model-exchanges.jsonl")
        assert [r["transport"] for r in api] == read_json(p / "api-ledger.json")
        proposal = FreewayProgram.from_dict(read_json(p.parent / "proposal.json")["program"])
        programs = {"reference": FreewayProgram(), "candidate": proposal}
        calls = {r["exchange_id"]: r for r in api}
        rows = [json.loads(line) for line in (p / "responses.jsonl").open()]
        for row in rows:
            state = states[row["state_id"]]
            exchange = row["prediction"]["exchange_id"]
            obs, action = success.pop(exchange)
            assert obs == state["observation"] and action == row["actual"]
            assert row["expected"] == state["expected"] and row["stratum"] == state["stratum"]
            program = programs[row["role"]]
            call = calls[exchange]
            assert call["request"] == program.request(obs, call["request"]["model"])
        assert not success
        for role, metric in read_json(p / "metrics.json").items():
            own = [r for r in rows if r["role"] == role]
            assert len(own) == metric["n"] and len({r["state_id"] for r in own}) == len(states)
            assert sum(r["actual"] == r["expected"] for r in own) == metric["matches"]
            rates = []
            for key, value in metric["by_branch_motion"].items():
                group = [r for r in own if r["stratum"] == key]
                hits = sum(r["actual"] == r["expected"] for r in group)
                assert value == dict(n=len(group), matches=hits, rate=hits / len(group))
                rates.append(value["rate"])
            assert metric["macro"] == mean(rates)
    for p in sorted(root.glob("round-*/*/model-exchanges.jsonl")):
        attempts.extend(json.loads(line) for line in p.open())
    ids = [r["exchange_id"] for r in attempts]
    budget = read_json(root / "budget.json")
    assert sorted(ids) == list(range(1, budget["used"] + 1))
    assert budget["closed"] and budget["used"] <= 16000
    assert all(n <= LIMITS[int(k)] for k, n in budget["round_attempts"].items())
    selection = read_json(root / "selection.json")
    training_ids = {r["id"] for r in read_json(root / "training-packet.json")["rows"]}
    for number in (9, 10):
        held_out = read_json(root / f"round-{number:02}" / "probe/packet.json")
        assert not training_ids.intersection(r["id"] for r in held_out["rows"])
    trials = [read_json(root / f"round-{n:02}" / "result.json") for n in range(3, 9)]
    best = max(trials, key=lambda r: (r["mean_reward"], -r["round"]))
    assert selection["round"] == best["round"]
    assert selection["program_hash"] == FreewayProgram.from_dict(selection["program"]).hash
    for n in range(2, 11):
        result = read_json(root / f"round-{n:02}" / "result.json")
        assert result["status"] == "complete" and result["round"] == n
        for e in result["episodes"]:
            actual = read_json(root / f"round-{n:02}" / Path(e["path"]).name / "summary.json")
            assert all(e[k] == v for k, v in actual.items())
        assert result["mean_reward"] == mean(
            e["reward"] for e in result["episodes"] if e["role"] == "candidate"
        )
        if n >= 9:
            assert (
                read_json(root / f"round-{n:02}" / "proposal.json")["program_hash"]
                == selection["program_hash"]
            )
            episodes = result["episodes"]
            seeds = sorted({e["seed"] for e in episodes})
            gains = [
                next(e["reward"] for e in episodes if e["seed"] == s and e["role"] == "candidate")
                - next(e["reward"] for e in episodes if e["seed"] == s and e["role"] == "reference")
                for s in seeds
            ]
            assert result["gate"] == dict(
                passed=mean(gains) >= 1 and min(gains) >= 0,
                paired_gains=gains,
                mean_gain=mean(gains),
            )
    costs = [(r["transport"].get("usage") or {}).get("cost", 0) for r in attempts]
    completion = read_json(root / "completion.json")
    assert completion["rounds"] == 10 and completion["budget_closed"]
    assert completion["promoted"] == all(
        read_json(root / f"round-{n:02}" / "result.json")["gate"]["passed"] for n in (9, 10)
    )
    report = dict(
        status="verified",
        episodes=reports,
        episode_count=len(reports),
        raw_frames=sum(r["frames"] for r in reports),
        api_attempts=len(attempts),
        successful_responses=sum(r["response"] is not None for r in attempts),
        reported_cost_usd=sum(costs),
        rounds=10,
        budget_closed=True,
    )
    write_json(out, report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.root, args.out)), flush=True)
