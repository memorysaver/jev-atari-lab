"""Persistent limits and evidence contracts for the approved Pong teacher study."""

import json
import math
import os
import time
from pathlib import Path
from statistics import mean

from jev_atari.choice import ActionProgram
from jev_atari.experiment import split_for_seed
from jev_atari.io import digest, read_json, write_json
from jev_atari.models import BudgetExceeded

MODEL = "jev-1.13.0"
TRAIN_SEEDS = ((60, 61), (62, 63), (64, 65))
DEV_SEEDS = (66, 67)
FINAL_SEEDS = (68, 69, 78, 79)


class StudyBudget:
    """Single-writer durable reservation before requests, including final allocation."""

    def __init__(self, path: Path, *, clock=time.time):
        self.path, self.clock = path, clock
        if not path.exists():
            self.save(
                {
                    "kind": "pong-study-budget-v1",
                    "max_attempts": 220000,
                    "nonfinal_limit": 154000,
                    "final_limit": 66000,
                    "teacher_limit": 8,
                    "live_seconds": 86400,
                    "started_at": None,
                    "attempts": 0,
                    "nonfinal_attempts": 0,
                    "final_attempts": 0,
                    "teacher_invocations": 0,
                    "teacher_repairs": 0,
                    "training_closed": False,
                }
            )

    def save(self, value):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        with temporary.open("w") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(self.path)

    def close_training(self):
        state = read_json(self.path)
        state["training_closed"] = True
        self.save(state)

    def reserve(self, phase):
        if phase not in {"nonfinal", "final", "teacher", "teacher_repair"}:
            raise ValueError("Unknown budget phase")
        state = read_json(self.path)
        if state["training_closed"] and phase != "final":
            raise BudgetExceeded("Training and teacher access sealed before final evaluation")
        now = self.clock()
        if state["started_at"] is not None and now >= state["started_at"] + state["live_seconds"]:
            raise BudgetExceeded("Study live deadline exhausted")
        if phase in {"teacher", "teacher_repair"}:
            if state["teacher_invocations"] >= state["teacher_limit"]:
                raise BudgetExceeded("Teacher invocation limit exhausted")
            if phase == "teacher_repair":
                if state["teacher_repairs"] >= 2:
                    raise BudgetExceeded("Technical repair allowance exhausted")
                state["teacher_repairs"] += 1
            state["teacher_invocations"] += 1
        else:
            key = f"{phase}_attempts"
            if state["attempts"] >= state["max_attempts"] or state[key] >= state[f"{phase}_limit"]:
                raise BudgetExceeded("Study HTTP allocation exhausted")
            state["attempts"] += 1
            state[key] += 1
        if state["started_at"] is None:
            state["started_at"] = now
        self.save(state)


class AllocatedBudget:
    """The normal evaluator budget interface with a durable global reservation."""

    def __init__(self, study: StudyBudget, phase: str, max_calls: int):
        self.study, self.phase, self.max_calls, self.used = study, phase, max_calls, 0

    def reserve(self):
        if self.used >= self.max_calls:
            raise BudgetExceeded("Operation attempt limit exhausted")
        self.study.reserve(self.phase)
        self.used += 1


def read_rows(path):
    with Path(path).open() as stream:
        return [json.loads(line) for line in stream]


def sample_training(episode_paths: list[Path]) -> dict:
    """Deterministic coverage plus the end of each of up to four scoring windows."""
    examples, summaries = [], []
    for path in episode_paths:
        manifest = read_json(path / "manifest.json")
        seed = manifest["seed"]
        if manifest["split"] != "train" or split_for_seed(seed) != "train":
            raise ValueError("Teacher evidence must be training-only")
        summary = read_json(path / "summary.json")
        if summary["status"] != "complete":
            raise ValueError("Incomplete training episode")
        rows = read_rows(path / "transitions.jsonl")
        if len(rows) < 16:
            raise ValueError("Need at least sixteen training decisions")
        summaries.append({"seed": seed, "summary": summary})
        # Sixteen evenly spaced inputs per episode define the shared 32-state probe.
        coverage = [i * (len(rows) - 1) // 15 for i in range(16)]
        event_indices = [i for i, row in enumerate(rows) if any(row["rewards"])][:4]
        indices = sorted(set(coverage + [max(0, i - 1) for i in event_indices] + event_indices))
        for i in indices:
            row = rows[i]
            examples.append(
                {
                    "id": f"train-{seed}-decision-{i}",
                    "seed": seed,
                    "decision": i,
                    "probe": i in coverage,
                    "observation": row["observation"],
                    "executed_action": row["action"],
                    "observed_rewards_after_action": row["rewards"],
                    "next_observation": row["next_observation"],
                }
            )
    return {
        "split": "train",
        "sampling": "coverage16-and-first4-score-windows-v1",
        "episodes": summaries,
        "examples": examples,
    }


def teacher_packet(arm, round_number, program, evidence, memory):
    if arm not in {"A", "B"} or round_number not in {1, 2, 3}:
        raise ValueError("Unknown study arm/round")
    if evidence["split"] != "train" or any(
        split_for_seed(e["seed"]) != "train" for e in evidence["examples"]
    ):
        raise ValueError("Non-training evidence")
    if any(split_for_seed(e["seed"]) != "train" for e in evidence["episodes"]):
        raise ValueError("Non-training summary")
    if any(set(item) != {"round", "proposal"} for item in memory):
        raise ValueError("Memory may contain prior proposals only, not development outcomes")
    visible_evidence = {
        **evidence,
        "examples": [
            {
                **{k: v for k, v in item.items() if k != "next_observation"},
                "next_objects": item["next_observation"]["objects"],
            }
            for item in evidence["examples"]
        ],
    }
    packet = {
        "kind": "pong-policy-teacher-packet-v1",
        "arm": arm,
        "round": round_number,
        "current_program": program.to_dict(),
        "current_program_hash": program.hash,
        "contract": {
            "objective": "Improve actual points scored minus conceded in ALE Pong.",
            "executor": MODEL,
            "representation": "One Choice question; guidance <=2000 characters; name <=100.",
            "fixed": "RAM-derived boxes and finite-difference history; six actions; argmax; "
            "4 raw frames per decision; sticky=0.25; weights, sensors and reward fixed.",
            "semantics": "Player is right paddle. RIGHT moves up, LEFT down. y increases down. "
            "All six options remain available. State has objects, history and "
            "candidate_actions. Missing velocity is unknown. Native match ends at 21.",
            "prior_knowledge": "Starting question is a hand-written vertical tracking rule. "
            "You may reason from game mechanics; do not assume an edit works.",
        },
        "prior_edits": memory,
        "evidence": visible_evidence if arm == "A" else None,
        "visibility": "training only" if arm == "A" else "no empirical feedback",
    }
    return packet


def parse_proposal(value, packet):
    required = {
        "name",
        "guidance",
        "hypothesis",
        "operator",
        "evidence_ids",
        "predicted_changes",
        "regression_risks",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("Incorrect teacher proposal fields")
    for key in required - {"evidence_ids"}:
        if not isinstance(value[key], str) or not 1 <= len(value[key]) <= 2000:
            raise ValueError("Invalid proposal text")
    allowed = {e["id"] for e in (packet["evidence"] or {}).get("examples", [])}
    if not isinstance(value["evidence_ids"], list) or any(
        not isinstance(x, str) or x not in allowed for x in value["evidence_ids"]
    ):
        raise ValueError("Unknown or inaccessible evidence reference")
    return ActionProgram(name=value["name"], guidance=value["guidance"])


def select_policy(parent_rows, candidate_rows):
    if [e["seed"] for e in parent_rows] != list(DEV_SEEDS) or [
        e["seed"] for e in candidate_rows
    ] != list(DEV_SEEDS):
        raise ValueError("Only fixed development seeds may select a policy")
    if not all(e["evaluation_complete"] for e in parent_rows + candidate_rows):
        return {"status": "inconclusive", "accepted": False, "reason": "incomplete_evaluation"}
    pairs = [
        {
            "seed": old["seed"],
            "parent": old["capped_episode_return"],
            "candidate": new["capped_episode_return"],
            "gain": new["capped_episode_return"] - old["capped_episode_return"],
        }
        for old, new in zip(parent_rows, candidate_rows, strict=True)
    ]
    gain = mean(p["gain"] for p in pairs)
    accepted = gain >= 1 and all(p["gain"] >= 0 for p in pairs)
    return {
        "status": "accepted" if accepted else "rejected",
        "accepted": accepted,
        "pairs": pairs,
        "mean_gain": gain,
        "rule": "both seeds nonregressing and mean gain >=1; engineering gate",
    }


def js_divergence(p, q):
    if set(p) != set(q):
        raise ValueError("Different probability options")
    total = 0.0
    for key in p:
        a, b = p[key], q[key]
        m = (a + b) / 2
        if a:
            total += a * math.log2(a / m) / 2
        if b:
            total += b * math.log2(b / m) / 2
    return total


def probe_report(rows):
    groups = {}
    for row in rows:
        groups.setdefault(row["id"], {})[(row["program_role"], row["repeat"])] = row["answer"]
    result = {}
    for name, left, right in (
        ("parent_candidate", ("parent", 0), ("candidate", 0)),
        ("parent_repeat", ("parent", 0), ("parent", 1)),
        ("candidate_repeat", ("candidate", 0), ("candidate", 1)),
    ):
        pairs = [(group[left], group[right]) for group in groups.values()]
        result[name] = {
            "count": len(pairs),
            "action_flip_fraction": mean(a["choice"] != b["choice"] for a, b in pairs),
            "mean_js_bits": mean(
                js_divergence(a["probabilities"], b["probabilities"]) for a, b in pairs
            ),
        }
    return result


def seal_final(path, programs, protocol, source_revision):
    if path.exists():
        raise ValueError("Final seal already exists")
    value = {
        "kind": "pong-study-final-seal-v1",
        "seeds": list(FINAL_SEEDS),
        "programs": {k: p.to_dict() for k, p in programs.items()},
        "program_hashes": {k: p.hash for k, p in programs.items()},
        "protocol": protocol.manifest(),
        "model": MODEL,
        "max_frames": 20000,
        "source_revision": source_revision,
    }
    write_json(path, {"seal": value, "sha256": digest(value)})


def verify_final_seal(path, seed, program, protocol):
    record = read_json(path)
    value = record["seal"]
    if digest(value) != record["sha256"] or value["kind"] != "pong-study-final-seal-v1":
        raise ValueError("Invalid final seal")
    if value["seeds"] != list(FINAL_SEEDS) or seed not in FINAL_SEEDS:
        raise ValueError("Seed outside final seal")
    if value["protocol"] != protocol.manifest() or value["model"] != MODEL:
        raise ValueError("Final protocol mismatch")
    if (
        program.hash not in value["program_hashes"].values()
        or program.to_dict() not in value["programs"].values()
    ):
        raise ValueError("Program outside final seal")
    return record["sha256"]
