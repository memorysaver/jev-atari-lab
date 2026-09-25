"""Five-round separation of literal strategy quality and Jev rule execution."""

import argparse
import hashlib
import json
import random
import shutil
import time
from collections import Counter
from pathlib import Path
from statistics import mean
from types import SimpleNamespace

from jev_atari.io import digest, new_directory, read_json, write_json
from jev_atari.models import BudgetExceeded
from jev_atari.seaquest_pilot import MODEL, PIN
from jev_atari.seaquest_research import (
    NAMES,
    ResearchEvaluator,
    load_program,
    paired_gate,
    play_episode,
    source_revision,
)
from jev_atari.study import StudyBudget

TRAIN = (320, 321)
FINAL = (348, 349)
ROUND_LIMITS = {1: 0, 2: 400, 3: 400, 4: 400, 5: 4800}
MAX_ATTEMPTS = 6000
MOVEMENT = ("UPFIRE", "DOWNFIRE", "LEFTFIRE", "RIGHTFIRE")
STRATA = ("NOOP", "FIRE", *MOVEMENT)
SOURCE = Path("artifacts/seaquest/ten-round-v1-continuation")
REVIEWED = Path("experiments/seaquest/ten-round-v1-continuation/records")


def center(obj):
    x, y, w, h = obj["bbox"]
    return x + w / 2, y + h / 2


def literal(observation, rule):
    """Return the intended action/branch, never an optimal-action claim."""
    if rule not in {"simple", "late-diver"}:
        raise ValueError("Unknown literal rule")
    p = next((o for o in observation["objects"] if o["kind"] == "player"), None)
    if observation["object_state"] != "active" or p is None:
        return "NOOP", "unavailable"
    y, oxygen, carried = p["bbox"][1], observation["oxygen_raw"], observation["carried_divers"]
    if carried is None:
        raise ValueError("Literal control requires a valid carried-diver reading")
    if y <= 46 and oxygen < 60:
        return "FIRE", "refill"
    if y > 46 and (carried == 6 or (oxygen <= 20 and (rule == "simple" or carried >= 1))):
        return "UPFIRE", "return"
    px, py = center(p)
    divers = [o for o in observation["objects"] if o["kind"] == "diver"]
    if rule == "late-diver" and carried == 0 and oxygen <= 32 and divers:
        target = min(divers, key=lambda d: abs(center(d)[0] - px) + abs(center(d)[1] - py))
        dx, dy = center(target)[0] - px, center(target)[1] - py
        if dy > 5:
            return "DOWNFIRE", "seek-down"
        if dy < -5:
            return "UPFIRE", "seek-up"
        if dx > 5:
            return "RIGHTFIRE", "seek-right"
        if dx < -5:
            return "LEFTFIRE", "seek-left"
        return "FIRE", "seek-contact"
    if y < 86:
        return "DOWNFIRE", "hunt-depth-down"
    if y > 100:
        return "UPFIRE", "hunt-depth-up"
    enemies = [
        o
        for o in observation["objects"]
        if o["kind"] in {"shark", "enemy_submarine"} and abs(center(o)[1] - py) <= 12
    ]
    if enemies:
        target = min(enemies, key=lambda e: abs(center(e)[0] - px))
        if center(target)[0] < px and p["facing"] == "right":
            return "LEFTFIRE", "hunt-turn-left"
        if center(target)[0] > px and p["facing"] == "left":
            return "RIGHTFIRE", "hunt-turn-right"
    return "FIRE", "hunt-fire"


class ExecutionBudget:
    def __init__(self, path, number, *, clock=time.time):
        self.path, self.number, self.clock = path, number, clock
        if not path.exists():
            StudyBudget.save(
                self,
                dict(
                    max_calls=MAX_ATTEMPTS,
                    used=0,
                    started_at=None,
                    live_seconds=86400,
                    round_attempts={},
                    closed=False,
                ),
            )
        state = read_json(path)
        self.used, self.max_calls = state["used"], state["max_calls"]

    def reserve(self):
        state, now = read_json(self.path), self.clock()
        key = str(self.number)
        if (
            state["closed"]
            or state["used"] >= MAX_ATTEMPTS
            or state["round_attempts"].get(key, 0) >= ROUND_LIMITS[self.number]
            or (state["started_at"] is not None and now >= state["started_at"] + 86400)
        ):
            raise BudgetExceeded("Five-round execution study allocation exhausted/closed")
        state["started_at"] = state["started_at"] or now
        state["used"] += 1
        state["round_attempts"][key] = state["round_attempts"].get(key, 0) + 1
        StudyBudget.save(self, state)
        self.used = state["used"]


class LiteralEvaluator:
    backend = "local-literal-control"
    transport_manifest = {"backend": backend, "model_calls": 0, "not_a_model_prediction": True}

    def __init__(self, rule):
        self.rule = rule
        self.ledger = []
        self.api = SimpleNamespace(trace_path=None, budget=SimpleNamespace(used=0))

    def evaluate(self, observation, program):
        name, branch = literal(observation, self.rule)
        return {
            "kind": "local-literal-control",
            "rule": self.rule,
            "branch": branch,
            "chosen_action": NAMES.index(name),
            "choice_answer": {"choice": name},
            "program_hash": program.hash,
            "model_calls": 0,
        }


def build_packet(paths, *, split):
    """Freeze up to sixteen unique observations per late-diver action stratum."""
    buckets = {a: [] for a in STRATA}
    seen, sources = set(), []
    for path in sorted(paths):
        manifest = read_json(path / "manifest.json")
        if manifest["split"] != split:
            raise ValueError("Wrong split in probe packet source")
        trace = path / "transitions.jsonl"
        sources.append(
            {"path": str(trace), "sha256": hashlib.sha256(trace.read_bytes()).hexdigest()}
        )
        rows = [json.loads(line) for line in trace.read_text().splitlines()]
        for index, row in enumerate(rows):
            if row["phase"] != "control":
                continue
            obs = row["observation"]
            fingerprint = digest(obs)
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            action, branch = literal(obs, "late-diver")
            buckets[action].append(
                {
                    "id": fingerprint,
                    "source": str(trace),
                    "transition_index": index,
                    "seed": manifest["seed"],
                    "observation": obs,
                    "stratum": action,
                    "late_diver_branch": branch,
                }
            )
    selected = []
    for i, action in enumerate(STRATA):
        rows = sorted(buckets[action], key=lambda r: r["id"])
        random.Random(250925 + i).shuffle(rows)
        selected.extend(rows[:16])
    random.Random(250926).shuffle(selected)
    return {
        "kind": "matched-seaquest-observation-packet-v1",
        "split": split,
        "sources": sources,
        "sampling": "Up to 16 unique states per late-diver expected action; fixed RNG",
        "available": {a: len(rows) for a, rows in buckets.items()},
        "selected": dict(Counter(r["stratum"] for r in selected)),
        "rows": selected,
        "limits": "Stratified diagnostic, not occupancy-weighted performance. "
        "Labels never enter model state.",
    }


def probe_metrics(rows):
    result = {}
    for role in sorted({r["role"] for r in rows}):
        own = [r for r in rows if r["role"] == role]
        counts = {}
        for name in STRATA:
            group = [r for r in own if r["expected"] == name]
            hits = sum(r["actual"] == name for r in group)
            counts[name] = {
                "n": len(group),
                "matches": hits,
                "rate": hits / len(group) if group else None,
            }
        movement = [counts[a]["rate"] for a in MOVEMENT if counts[a]["n"]]
        result[role] = {
            "n": len(own),
            "matches": sum(r["actual"] == r["expected"] for r in own),
            "by_expected_action": counts,
            "movement_macro": mean(movement) if movement else None,
            "movement_coverage": all(counts[a]["n"] >= 8 for a in MOVEMENT),
        }
    return result


def execution_gate(metrics):
    a, b = metrics["reference"], metrics["candidate"]
    gain = (
        b["movement_macro"] - a["movement_macro"]
        if a["movement_macro"] is not None and b["movement_macro"] is not None
        else None
    )
    changes = {
        name: b["by_expected_action"][name]["rate"] - a["by_expected_action"][name]["rate"]
        for name in MOVEMENT
        if a["by_expected_action"][name]["rate"] is not None
        and b["by_expected_action"][name]["rate"] is not None
    }
    return {
        "passed": a["movement_coverage"]
        and b["movement_coverage"]
        and gain >= 0.05 - 1e-12
        and min(changes.values()) >= -0.10 - 1e-12,
        "movement_macro_gain": gain,
        "action_rate_changes": changes,
    }


def probe(path, packet, arms, evaluator):
    new_directory(path)
    plan = {
        "packet_hash": digest(packet),
        "programs": {
            role: {"program": program.to_dict(), "program_hash": program.hash, "rule": rule}
            for role, (program, rule) in arms.items()
        },
        "order": "Alternate role order on successive packet states",
    }
    write_json(path / "plan.json", plan)
    evaluator.api.trace_path = path / "model-exchanges.jsonl"
    start = len(evaluator.ledger)
    predictions = []
    try:
        with (path / "predictions.jsonl").open("x") as stream:
            for i, row in enumerate(packet["rows"]):
                order = list(arms) if i % 2 == 0 else list(reversed(arms))
                for role in order:
                    program, rule = arms[role]
                    prediction = evaluator.evaluate(row["observation"], program)
                    expected, branch = literal(row["observation"], rule)
                    record = {
                        "state_id": row["id"],
                        "role": role,
                        "rule": rule,
                        "expected": expected,
                        "branch": branch,
                        "actual": prediction["choice_answer"]["choice"],
                        "prediction": prediction,
                    }
                    predictions.append(record)
                    stream.write(json.dumps(record) + "\n")
                    stream.flush()
    finally:
        write_json(path / "api-ledger.json", evaluator.ledger[start:])
        write_json(path / "metrics.json", probe_metrics(predictions))
    return probe_metrics(predictions)


def initialize(root):
    source = source_revision()
    for manifest in Path("artifacts/seaquest").rglob("manifest.json"):
        if read_json(manifest).get("seed") in FINAL:
            raise ValueError("Fresh final seed already exposed")
    original = read_json(REVIEWED / "plan.json")
    programs = {
        name: read_json(REVIEWED / f"round-{n:02d}" / "proposal.json")["program"]
        for name, n in (("simple", 3), ("late-diver", 8))
    }
    new_directory(root)
    sources = []
    for n in (3, 8):
        for seed in TRAIN:
            original_path = SOURCE / f"round-{n:02d}" / "candidate" / f"seed-{seed}"
            copied = root / "sources" / f"round-{n:02d}" / f"seed-{seed}"
            copied.mkdir(parents=True)
            for filename in ("manifest.json", "summary.json", "transitions.jsonl"):
                shutil.copy2(original_path / filename, copied / filename)
            sources.append(copied)
    packet = build_packet(sources, split="train")
    if not packet["rows"]:
        raise ValueError("No training observations")
    write_json(root / "training-packet.json", packet)
    plan = {
        "kind": "seaquest-execution-five-round-v1",
        "artifact_root": str(root),
        "source_study": str(SOURCE),
        "source_revision": source,
        "rounds": 5,
        "train_seeds": TRAIN,
        "final_seeds": FINAL,
        "programs": programs,
        "training_packet_hash": digest(packet),
        "max_attempts": MAX_ATTEMPTS,
        "round_limits": ROUND_LIMITS,
        "live_seconds": 86400,
        "model": MODEL,
        "response_model": PIN,
        "authorship": "Interactive coordinator; zero isolated teacher calls",
        "environment": {
            k: original[k]
            for k in (
                "schema",
                "mode",
                "difficulty",
                "sticky",
                "frameskip",
                "hold_frames",
                "rom_sha256",
                "versions",
                "prefix",
            )
        },
        "episode_cap": "800 actor decisions after 256 fixed prefix frames; "
        "native termination first",
        "gate": "Movement macro agreement +0.05; each movement stratum n>=8; "
        "no stratum loses >0.10. Final gameplay mean gain>=20 and no seed regression.",
        "selection": "Eligible round 3/4 variant with highest candidate movement macro; "
        "earliest tie. Otherwise unchanged late-diver reference.",
        "limits": "Same-rule wording study, not teacher-feedback benefit; "
        "no final data used in proposals",
    }
    write_json(root / "plan.json", plan)
    ExecutionBudget(root / "budget.json", 1)
    write_json(
        root / "results.json", {"status": "running", "plan_hash": digest(plan), "rounds": []}
    )


def run_round(root, number, proposal_path=None):
    source = source_revision()
    plan, report = read_json(root / "plan.json"), read_json(root / "results.json")
    if source != plan["source_revision"] or report["status"] != "running":
        raise ValueError("Source changed or study stopped")
    if not 1 <= number <= 5 or number != len(report["rounds"]) + 1:
        raise ValueError("Execute exactly five rounds in order")
    simple, reference = (load_program(plan["programs"][key]) for key in ("simple", "late-diver"))
    candidate, proposal = None, None
    if number in (3, 4):
        proposal = read_json(proposal_path)
        if set(proposal) != {
            "origin",
            "hypothesis",
            "program",
            "evidence",
            "risks",
            "intended_rule",
        }:
            raise ValueError("Full proposal provenance required")
        if (
            proposal["origin"] != "interactive-coordinator-training-feedback"
            or proposal["intended_rule"] != "late-diver"
        ):
            raise ValueError("Only same-rule coordinator wording revisions allowed")
        for value in proposal["evidence"]:
            p = Path(value)
            if p.name != "results.json" or p.parent.parent.resolve() != root.resolve():
                raise ValueError("Evidence must be this study's completed training rounds")
            n = int(p.parent.name.split("-")[1])
            if not 1 <= n < number or read_json(p)["status"] != "complete":
                raise ValueError("Future/incomplete evidence forbidden")
        candidate = load_program(proposal["program"])
        if candidate.schema_version != reference.schema_version:
            raise ValueError("Keep the original action-criteria schema")
    path = root / f"round-{number:02d}"
    new_directory(path)
    if proposal is not None:
        write_json(path / "proposal.json", proposal)
    result = {"round": number, "status": "incomplete", "events": []}
    write_json(path / "results.json", result)
    evaluator, budget = None, ExecutionBudget(root / "budget.json", number)

    def episode(role, seed, program, rule, *, local=False):
        ep = path / role / f"seed-{seed}"
        ev = LiteralEvaluator(rule) if local else evaluator
        summary = play_episode(ep, seed, ev, source, program)
        result["events"].append(
            {
                "kind": "episode",
                "path": str(ep.relative_to(root)),
                "role": role,
                "seed": seed,
                "rule": rule,
                "local": local,
                "summary": summary,
            }
        )
        write_json(path / "results.json", result)
        return ep

    def run_probe(packet, arms, packet_path):
        metrics = probe(path / "probe", packet, arms, evaluator)
        result["events"].append(
            {
                "kind": "probe",
                "path": str((path / "probe").relative_to(root)),
                "packet": packet_path,
            }
        )
        result["probe_metrics"] = metrics
        return metrics

    try:
        if number == 1:
            for name, program in (("simple", simple), ("late-diver", reference)):
                for seed in TRAIN:
                    episode("literal-" + name, seed, program, name, local=True)
        else:
            evaluator = ResearchEvaluator(budget)
            if number == 2:
                run_probe(
                    read_json(root / "training-packet.json"),
                    {
                        "reference": (reference, "late-diver"),
                        "simple": (simple, "simple"),
                    },
                    "training-packet.json",
                )
            elif number in (3, 4):
                metrics = run_probe(
                    read_json(root / "training-packet.json"),
                    {
                        "reference": (reference, "late-diver"),
                        "candidate": (candidate, "late-diver"),
                    },
                    "training-packet.json",
                )
                result["screen"] = execution_gate(metrics)
            else:
                eligible = [
                    r for r in report["rounds"] if r["round"] in (3, 4) and r["screen"]["passed"]
                ]
                selected = (
                    max(
                        eligible,
                        key=lambda r: (
                            r["probe_metrics"]["candidate"]["movement_macro"],
                            -r["round"],
                        ),
                    )
                    if eligible
                    else None
                )
                candidate = (
                    load_program(
                        read_json(root / f"round-{selected['round']:02d}" / "proposal.json")[
                            "program"
                        ]
                    )
                    if selected
                    else reference
                )
                seal = {
                    "selected_round": selected["round"] if selected else 2,
                    "program": candidate.to_dict(),
                    "program_hash": candidate.hash,
                    "distinct_candidate": candidate.hash != reference.hash,
                    "sealed_before_final_access": True,
                }
                write_json(root / "finalist-seal.json", seal)
                final_sources = [
                    episode("literal-reference", seed, reference, "late-diver", local=True)
                    for seed in FINAL
                ]
                packet = build_packet(final_sources, split="test")
                write_json(root / "final-packet.json", packet)
                metrics = run_probe(
                    packet,
                    {
                        "reference": (reference, "late-diver"),
                        "candidate": (candidate, "late-diver"),
                    },
                    "final-packet.json",
                )
                result["execution_gate"] = execution_gate(metrics)
                for seed in FINAL:
                    episode("baseline", seed, reference, "late-diver")
                    episode("candidate", seed, candidate, "late-diver")
                games = [e for e in result["events"] if e["kind"] == "episode" and not e["local"]]
                result["gameplay_gate"] = paired_gate(games)
                result["wording_improvement_gate"] = (
                    seal["distinct_candidate"]
                    and result["execution_gate"]["passed"]
                    and result["gameplay_gate"]["passed"]
                )
        result["status"] = "complete"
        report["rounds"].append({k: v for k, v in result.items() if k != "events"})
        if number == 5:
            report.update(status="complete", stopped_after_round=5)
            state = read_json(budget.path)
            state["closed"] = True
            StudyBudget.save(budget, state)
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        report["status"] = "incomplete-technical-stop"
        raise
    finally:
        if evaluator is not None:
            evaluator.close()
        write_json(path / "results.json", result)
        report["budget"] = read_json(budget.path)
        write_json(root / "results.json", report)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--initialize", action="store_true")
    p.add_argument("--round", type=int)
    p.add_argument("--proposal", type=Path)
    p.add_argument("--backend", choices=["openrouter"], required=True)
    args = p.parse_args()
    initialize(args.root) if args.initialize else run_round(args.root, args.round, args.proposal)
