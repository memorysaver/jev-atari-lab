"""Bounded ten-round Freeway study; proposals are coordinator-authored."""

import argparse
import json
import random
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from jev_atari.freeway import FreewayProgram, literal, play
from jev_atari.io import digest, new_directory, read_json, write_json
from jev_atari.models import BudgetExceeded
from jev_atari.seaquest_research import ResearchEvaluator

ROOT = Path("artifacts/freeway/ten-round-v1")
TRAIN, DEV, FINAL = (410, 411), (416, 417), (418, 419)
MAX_CALLS = 16000
LIMITS = {2: 1300, **{n: 1400 for n in range(3, 9)}, 9: 3000, 10: 3000}


class Budget:
    def __init__(self, path, number, clock=time.time):
        self.path, self.number, self.clock = path, number, clock
        if not path.exists():
            write_json(
                path,
                dict(
                    max_calls=MAX_CALLS,
                    used=0,
                    started_at=None,
                    closed=False,
                    round_attempts={},
                    live_seconds=86400,
                ),
            )
        self.max_calls, self.used = MAX_CALLS, read_json(path)["used"]

    def reserve(self):
        s, now = read_json(self.path), self.clock()
        key = str(self.number)
        if (
            s["closed"]
            or s["used"] >= MAX_CALLS
            or s["round_attempts"].get(key, 0) >= LIMITS[self.number]
            or (s["started_at"] is not None and now >= s["started_at"] + 86400)
        ):
            raise BudgetExceeded("Freeway allocation exhausted or closed")
        s["started_at"] = s["started_at"] if s["started_at"] is not None else now
        s["used"] += 1
        s["round_attempts"][key] = s["round_attempts"].get(key, 0) + 1
        write_json(self.path, s)
        self.used = s["used"]


def context_stratum(obs):
    action, branch = literal(obs)
    if not obs["history"]:
        return "unknown-history"
    py = obs["player"][1]
    ahead = [c for c in obs["cars"] if c["bbox"][1] + 10 <= py]
    if not ahead:
        return "above-traffic"
    c = max(ahead, key=lambda c: c["bbox"][1])
    x = c["bbox"][0]
    old = obs["history"][-1]["cars"][c["lane"]]["bbox"][0]
    dx = (x - old + 80) % 160 - 80
    motion = "approaching" if (x + 4 - 47) * dx < 0 else "receding" if dx else "stationary"
    return f"{branch}/{motion}"


def packet(paths, split):
    buckets = defaultdict(dict)
    sources = []
    for p in sorted(paths):
        if read_json(p / "manifest.json")["split"] != split:
            raise ValueError("Packet split mismatch")
        sources.append(str(p))
        for line in (p / "transitions.jsonl").open():
            row = json.loads(line)
            if row["phase"] != "control":
                continue
            obs = row["observation"]
            label, branch = literal(obs)
            stratum = context_stratum(obs)
            fingerprint = digest(obs)
            buckets[stratum][fingerprint] = dict(
                id=fingerprint,
                observation=obs,
                expected=label,
                branch=branch,
                stratum=stratum,
                source=str(p),
            )
    rows = []
    for stratum, bucket in sorted(buckets.items()):
        options = sorted(bucket.values(), key=lambda r: r["id"])
        random.Random("freeway-v1-" + stratum).shuffle(options)
        rows.extend(options[:8])
    random.Random(260926).shuffle(rows)
    return dict(
        kind="freeway-branch-motion-packet-v1",
        split=split,
        sources=sources,
        available={k: len(v) for k, v in buckets.items()},
        selected=dict(Counter(r["stratum"] for r in rows)),
        rows=rows,
    )


def probe(path, pack, programs, evaluator):
    new_directory(path)
    write_json(path / "packet.json", pack)
    evaluator.api.trace_path = path / "model-exchanges.jsonl"
    start = len(evaluator.ledger)
    rows = []
    try:
        with (path / "responses.jsonl").open("x") as log:
            for i, state in enumerate(pack["rows"]):
                roles = list(programs)
                if i % 2:
                    roles.reverse()
                for role in roles:
                    program = programs[role]
                    result = evaluator.evaluate(state["observation"], program)
                    row = dict(
                        state_id=state["id"],
                        stratum=state["stratum"],
                        branch=state["branch"],
                        expected=state["expected"],
                        role=role,
                        actual=result["chosen_action"],
                        prediction=result,
                    )
                    rows.append(row)
                    log.write(json.dumps(row) + "\n")
                    log.flush()
    finally:
        write_json(path / "api-ledger.json", evaluator.ledger[start:])
    metrics = {}
    for role in programs:
        own = [r for r in rows if r["role"] == role]
        groups = {}
        for key in sorted({r["stratum"] for r in own}):
            group = [r for r in own if r["stratum"] == key]
            hits = sum(r["actual"] == r["expected"] for r in group)
            groups[key] = dict(n=len(group), matches=hits, rate=hits / len(group))
        metrics[role] = dict(
            n=len(own),
            matches=sum(r["actual"] == r["expected"] for r in own),
            by_branch_motion=groups,
            macro=mean(v["rate"] for v in groups.values()),
        )
    write_json(path / "metrics.json", metrics)
    return metrics


def revision():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def run(number, proposal=None, rationale=None):
    if number not in range(2, 11):
        raise ValueError("Round must be 2..10")
    for n in range(1, number):
        if not (ROOT / f"round-{n:02}" / "result.json").exists():
            raise ValueError("Previous round not complete")
    root = new_directory(ROOT / f"round-{number:02}")
    source = revision()
    if number == 2:
        write_json(
            ROOT / "plan.json",
            dict(
                source_revision=source,
                rounds=10,
                train=TRAIN,
                development=DEV,
                final=FINAL,
                max_calls=MAX_CALLS,
                round_limits=LIMITS,
                coordinator_proposals=6,
                isolated_teacher_calls=0,
            ),
        )
    elif read_json(ROOT / "plan.json")["source_revision"] != source:
        raise ValueError("Frozen source revision changed")
    baseline = FreewayProgram()
    if number == 2:
        candidate = baseline
        pack = packet(
            [p.parent for p in (ROOT / "round-01").glob("*hold-16*/manifest.json")], "train"
        )
        write_json(ROOT / "training-packet.json", pack)
    elif number <= 8:
        candidate = FreewayProgram.from_dict(read_json(proposal))
        pack = read_json(ROOT / "training-packet.json")
    else:
        if number == 9:
            trials = [read_json(ROOT / f"round-{n:02}" / "result.json") for n in range(3, 9)]
            winner = max(trials, key=lambda r: (r["mean_reward"], -r["round"]))
            selected = read_json(ROOT / f"round-{winner['round']:02}" / "proposal.json")
            write_json(
                ROOT / "selection.json",
                dict(
                    round=winner["round"],
                    training_mean=winner["mean_reward"],
                    program=selected["program"],
                    program_hash=selected["program_hash"],
                    source_revision=source,
                    selection="Highest training native mean; earlier round wins ties",
                    sealed_before_development=True,
                ),
            )
        candidate = FreewayProgram.from_dict(read_json(ROOT / "selection.json")["program"])
        pack = None
    write_json(
        root / "proposal.json",
        dict(
            round=number,
            program=candidate.to_dict(),
            program_hash=candidate.hash,
            source_revision=source,
            author="interactive-coordinator" if 3 <= number <= 8 else "frozen-protocol",
            isolated_teacher_calls=0,
            rationale=rationale or "Frozen baseline/held-out comparison",
            available_feedback=[
                str(ROOT / f"round-{n:02}" / "result.json") for n in range(1, min(number, 9))
            ],
            final_data_used=False,
        ),
    )
    evaluator = ResearchEvaluator(Budget(ROOT / "budget.json", number))
    try:
        episodes = []
        if number <= 8:
            programs = {"reference": baseline}
            if number != 2:
                programs["candidate"] = candidate
            metrics = probe(root / "probe", pack, programs, evaluator)
            for seed in TRAIN:
                path = root / f"candidate-seed-{seed}"
                episodes.append(
                    dict(
                        path=str(path),
                        role="candidate",
                        **play(path, seed, program=candidate, evaluator=evaluator, source=source),
                    )
                )
        else:
            seeds, split = (DEV, "development") if number == 9 else (FINAL, "final_test")
            # split_for_seed calls its final split "final"; check source dynamically.
            from jev_atari.experiment import split_for_seed

            split = split_for_seed(seeds[0])
            local = []
            for seed in seeds:
                for rule in ["up", "predictive"]:
                    path = root / f"local-{rule}-seed-{seed}"
                    episodes.append(
                        dict(
                            path=str(path),
                            role=f"local-{rule}",
                            **play(path, seed, rule=rule, source=source),
                        )
                    )
                    local.append(path)
            pack = packet(local, split)
            if {r["id"] for r in pack["rows"]} & {
                r["id"] for r in read_json(ROOT / "training-packet.json")["rows"]
            }:
                raise ValueError("Training/held-out observation overlap")
            metrics = probe(
                root / "probe", pack, {"reference": baseline, "candidate": candidate}, evaluator
            )
            for index, seed in enumerate(seeds):
                roles = [("reference", baseline), ("candidate", candidate)]
                if index % 2:
                    roles.reverse()
                for role, program in roles:
                    path = root / f"{role}-seed-{seed}"
                    episodes.append(
                        dict(
                            path=str(path),
                            role=role,
                            **play(path, seed, program=program, evaluator=evaluator, source=source),
                        )
                    )
        result = dict(
            round=number,
            status="complete",
            episodes=episodes,
            probe=metrics,
            mean_reward=mean(r["reward"] for r in episodes if r["role"] == "candidate"),
        )
        if number >= 9:
            gains = [
                next(r["reward"] for r in episodes if r["seed"] == s and r["role"] == "candidate")
                - next(r["reward"] for r in episodes if r["seed"] == s and r["role"] == "reference")
                for s in seeds
            ]
            result["gate"] = dict(
                passed=mean(gains) >= 1 and min(gains) >= 0,
                paired_gains=gains,
                mean_gain=mean(gains),
            )
        write_json(root / "result.json", result)
        if number == 10:
            state = read_json(ROOT / "budget.json")
            state["closed"] = True
            write_json(ROOT / "budget.json", state)
            write_json(
                ROOT / "completion.json",
                dict(
                    status="complete",
                    rounds=10,
                    promoted=read_json(ROOT / "round-09/result.json")["gate"]["passed"]
                    and result["gate"]["passed"],
                    budget_closed=True,
                    isolated_teacher_calls=0,
                ),
            )
        print(json.dumps(result), flush=True)
    finally:
        evaluator.api.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--proposal", type=Path)
    parser.add_argument("--rationale")
    args = parser.parse_args()
    run(args.round, args.proposal, args.rationale)
