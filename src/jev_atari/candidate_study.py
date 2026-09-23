"""Frozen OpenRouter candidate-experience study; independent of earlier study roots."""

import argparse
import fcntl
import hashlib
import json
import subprocess
import time
from copy import deepcopy
from pathlib import Path
from statistics import mean

import numpy as np

from jev_atari.choice import ActionProgram
from jev_atari.environment import Protocol
from jev_atari.experiment import split_for_seed
from jev_atari.io import digest, read_json, write_json
from jev_atari.motion_probe import STRATA, schedule, summarize
from jev_atari.openrouter import ENDPOINT, OpenRouterChoiceEvaluator
from jev_atari.study import AllocatedBudget, StudyBudget, parse_proposal, read_rows, teacher_packet
from jev_atari.study_runner import audit_episode, emit
from jev_atari.teacher import PROPOSAL_SCHEMA, invoke_teacher, isolation_check

KIND = "pong-candidate-feedback-openrouter-v1"
MODEL = "~typesafe/jev-latest"
RESPONSE_MODEL = "typesafe/jev-1.13-20260917"
TRAIN = (((200, 201), (202, 203), (204, 205)),)
DEV = ((206, 207),)
FINAL = (248, 249, 258, 259, 268, 269, 278, 279)
FRAMES = 2000
LIMITS = {
    "max_attempts": 30000,
    "nonfinal_limit": 17000,
    "final_limit": 13000,
    "teacher_limit": 10,
    "live_seconds": 86400,
}
ACTIONS = ("NOOP", "FIRE", "RIGHT", "LEFT", "RIGHTFIRE", "LEFTFIRE")
INSTRUCTIONS = (
    "You are the experimental Pong question-policy teacher. Use only the supplied JSON packet. "
    "Do not use tools, files, web, other agents or prior conversation. Return one JSON proposal "
    "matching the schema. Improve actual points scored minus conceded by revising the one "
    "Choice question's guidance and its six action-criterion descriptions. Guidance <=2000 "
    "characters; each action criterion 1..500 characters. All six native options must remain. "
    "Describe when each available movement is appropriate using the original observation. "
    "Prefer one principal mechanistic change. No code, sensors, extra questions, action masks, "
    "weight changes or injected precomputed action. Explain a hypothesis, predicted changes "
    "and regression risks without claiming improvement. Cite only supplied example IDs; "
    "without examples use an empty evidence_ids list."
)
SCHEMA = deepcopy(PROPOSAL_SCHEMA)
SCHEMA["properties"]["action_criteria"] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {name: {"type": "string"} for name in ACTIONS},
    "required": list(ACTIONS),
}
SCHEMA["required"].append("action_criteria")


def evaluator_for(budget, phase, max_calls):
    evaluator = OpenRouterChoiceEvaluator(
        model=MODEL, expected_response_model=RESPONSE_MODEL, max_calls=max_calls
    )
    evaluator.api.budget = AllocatedBudget(budget, phase, max_calls)
    return evaluator


def candidate_evidence(episodes):
    """Bounded role-aware feedback, including rejected proposals on fresh training seeds."""
    if len(episodes) not in (2, 4):
        raise ValueError("Expected two or four training trajectories")
    coverage_count, score_count = (16, 4) if len(episodes) == 2 else (8, 2)
    examples, summaries = [], []
    for role, program, path in episodes:
        manifest = read_json(path / "manifest.json")
        seed = manifest["seed"]
        if manifest["split"] != "train" or split_for_seed(seed) != "train":
            raise ValueError("Teacher feedback must be training-only")
        if manifest["question_program"] != program.to_dict():
            raise ValueError("Feedback policy provenance mismatch")
        summary = read_json(path / "summary.json")
        rows = read_rows(path / "transitions.jsonl")
        if summary["status"] != "complete" or len(rows) < 16:
            raise ValueError("Incomplete training evidence")
        provenance = {"role": role, "program_hash": program.hash, "seed": seed}
        summaries.append({**provenance, "program": program.to_dict(), "summary": summary})
        coverage = [i * (len(rows) - 1) // (coverage_count - 1) for i in range(coverage_count)]
        scoring = [i for i, row in enumerate(rows) if any(row["rewards"])][:score_count]
        indices = sorted(set(coverage + scoring + [max(0, i - 1) for i in scoring]))
        for i in indices:
            row = rows[i]
            examples.append(
                {
                    **provenance,
                    "id": f"{role}-train-{seed}-decision-{i}",
                    "decision": i,
                    "probe": i in coverage,
                    "observation": row["observation"],
                    "executed_action": row["action"],
                    "observed_rewards_after_action": row["rewards"],
                    "next_observation": row["next_observation"],
                }
            )
    if len({e["id"] for e in examples}) != len(examples) or len(examples) > 48:
        raise ValueError("Feedback example collision or capacity exceeded")
    return {
        "split": "train",
        "sampling": "role-labelled-balanced-48-v1",
        "episodes": summaries,
        "examples": examples,
    }


class CandidateBudget(StudyBudget):
    def __init__(self, path, *, clock=time.time):
        self.path, self.clock = path, clock
        if not path.exists():
            self.save(
                {
                    "kind": KIND,
                    **LIMITS,
                    "started_at": None,
                    "attempts": 0,
                    "nonfinal_attempts": 0,
                    "final_attempts": 0,
                    "teacher_invocations": 0,
                    "teacher_repairs": 0,
                    "teacher_transport_retries": 0,
                    "training_closed": False,
                }
            )
        state = read_json(path)
        if state["kind"] != KIND or any(state[k] != v for k, v in LIMITS.items()):
            raise ValueError("Existing campaign limits differ; never reset them")

    def transport_retry(self):
        state = read_json(self.path)
        if state["teacher_transport_retries"] >= 2:
            raise ValueError("Teacher transport retry allowance exhausted")
        state["teacher_transport_retries"] += 1
        self.save(state)


def parse(value, packet):
    if not isinstance(value, dict) or set(value) != set(SCHEMA["required"]):
        raise ValueError("Incorrect criteria proposal fields")
    basic = parse_proposal({k: v for k, v in value.items() if k != "action_criteria"}, packet)
    return ActionProgram(
        name=basic.name,
        guidance=basic.guidance,
        schema_version="action-choice-program-v2",
        action_criteria=value["action_criteria"],
    )


def packet_for(arm, round_number, program, evidence, memory):
    packet = teacher_packet(arm, round_number, program, evidence, memory)
    packet["kind"] = KIND + "-packet"
    packet["contract"]["executor"] = RESPONSE_MODEL
    packet["contract"]["feedback"] = (
        "Training examples identify their generating policy and role. In later rounds, "
        "previous-candidate examples execute your previous proposal regardless of selection. "
        "Same-seed trajectories are different evolving states, not action counterfactuals."
    )
    packet["contract"]["representation"] = (
        "One native-action Choice question. Edit guidance <=2000 characters plus all six "
        "criterion descriptions <=500 characters each. Name <=100 characters. "
        "Native action meanings, observations, question read/coordinate fields and "
        "probability-argmax decoder are fixed. Criteria are text, never Python predicates."
    )
    packet["contract"]["evaluation"] = (
        "Capped return at 2000 raw frames, or earlier native termination. "
        "A fresh v2 baseline and the same development selector evaluate both arms. "
        "Development scores and final evidence are not provided to teachers."
    )
    return packet


def propose(root, packet, budget, binary, auth_home):
    if root.exists():
        saved = read_json(root / "validated.json")
        if saved["packet_hash"] != digest(packet):
            raise ValueError("Changed teacher packet; refuse reuse")
        return parse(saved["proposal"], packet), saved["proposal"]
    root.mkdir(parents=True)
    current, repairs, transport_retries = packet, 0, 0
    for number in range(1, 4):
        invocation = root / f"invocation-{number}"
        emit(
            "criteria_teacher_started",
            path=str(invocation),
            arm=packet["arm"],
            packet_hash=digest(current),
        )
        try:
            value = invoke_teacher(
                current,
                invocation,
                budget,
                binary=binary,
                auth_home=auth_home,
                repair=repairs > 0,
                instructions=INSTRUCTIONS,
                proposal_schema=SCHEMA,
            )
        except Exception:
            execution = (
                read_json(invocation / "execution.json")
                if (invocation / "execution.json").exists()
                else {}
            )
            events = (
                read_json(invocation / "events.json")
                if (invocation / "events.json").exists()
                else []
            )
            # At most one identical-packet failed-access retry per proposal, two globally.
            # Returned candidates, tools, timeouts and local preparation errors are not retryable.
            retryable = (
                execution.get("exit_code", 0) != 0
                and any(e["type"] == "turn.failed" for e in events)
                and not any(e["type"] in {"agent_message", "turn.completed"} for e in events)
                and not execution.get("unexpected_item_types")
            )
            if not retryable or transport_retries or number == 3:
                raise
            budget.transport_retry()
            transport_retries += 1
            write_json(
                invocation / "retry-decision.json",
                {
                    "reason": "Failed access without a candidate; retry identical packet once.",
                    "packet_hash": digest(current),
                    "quality_resampling": False,
                },
            )
            continue
        try:
            program = parse(value, packet)
        except ValueError as exc:
            write_json(invocation / "validation-error.json", {"error": str(exc)})
            if repairs or number == 3:
                raise
            repairs += 1
            current = {
                **packet,
                "technical_repair": {
                    "instruction": "Fix schema/length/evidence references only; "
                    "preserve hypothesis.",
                    "invalid_proposal": value,
                    "validation_error": str(exc),
                },
            }
            continue
        write_json(
            root / "validated.json",
            {
                "packet_hash": digest(packet),
                "program": program.to_dict(),
                "proposal": value,
            },
        )
        emit("criteria_teacher_complete", path=str(invocation), program=program.name)
        return program, value
    raise ValueError("Teacher proposal remained incomplete")


def probe(root, states, programs, budget):
    if root.exists():
        raise ValueError("Never resume or overwrite a probe")
    root.mkdir()
    order = schedule(states, programs)
    write_json(root / "inputs.json", states)
    write_json(root / "programs.json", {k: p.to_dict() for k, p in programs.items()})
    write_json(root / "schedule.json", order)
    evaluator = evaluator_for(budget, "nonfinal", 480)
    evaluator.api.trace_path = root / "model-exchanges.jsonl"
    rows, lookup = [], {s["id"]: s for s in states}
    report = {"status": "incomplete", "completed_predictions": 0}
    write_json(root / "results.json", report)
    try:
        with (root / "predictions.jsonl").open("x") as stream:
            for item in order:
                prediction = evaluator.evaluate(
                    lookup[item["id"]]["observation"], programs[item["program"]]
                )
                if prediction["response_model"] != RESPONSE_MODEL:
                    raise ValueError("Probe model changed")
                row = {**item, "prediction": prediction}
                rows.append(row)
                stream.write(json.dumps(row) + "\n")
                stream.flush()
        report["status"] = "complete"
    finally:
        report.update(
            completed_predictions=len(rows),
            attempts=evaluator.api.budget.used,
            metrics=summarize(states, programs, rows),
        )
        write_json(root / "api-ledger.json", evaluator.ledger)
        write_json(root / "results.json", report)
        evaluator.close()
    screens = {}
    for name in programs:
        subset = [r for r in rows if r["program"] == name]
        missing = [r for r in subset if lookup[r["id"]]["stratum"] == "missing"]
        visible = [
            r["prediction"]["chosen_action"]
            for r in subset
            if lookup[r["id"]]["stratum"] != "missing"
        ]
        screens[name] = {
            "complete": len(subset) == 160,
            "missing_hold": len(missing) == 16
            and all(r["prediction"]["chosen_action"] in (0, 1) for r in missing),
            "up_and_down_available": bool(set(visible) & {2, 4}) and bool(set(visible) & {3, 5}),
        }
        screens[name]["eligible"] = all(screens[name].values())
    write_json(root / "screen.json", screens)
    return screens


def select(baseline, candidate, seeds, best_gain):
    if [r["seed"] for r in baseline] != list(seeds) or [r["seed"] for r in candidate] != list(
        seeds
    ):
        raise ValueError("Selection needs exactly the frozen development schedule")
    if any(split_for_seed(s) != "development" for s in seeds):
        raise ValueError("Only development selects a policy")
    if not all(r["evaluation_complete"] for r in baseline + candidate):
        return {"accepted": False, "status": "incomplete"}
    gains = [
        b["capped_episode_return"] - a["capped_episode_return"]
        for a, b in zip(baseline, candidate, strict=True)
    ]
    score = mean(gains)
    accepted = min(gains) >= 0 and score >= 1 and score > best_gain
    return {
        "accepted": accepted,
        "status": "accepted" if accepted else "rejected",
        "seeds": list(seeds),
        "paired_gains_over_fresh_v2": gains,
        "mean_gain": score,
        "previous_best_gain": best_gain,
        "rule": "Nonregressing on both seeds, mean >=1 over fresh v2; "
        "strictly exceed previous best gain.",
        "limit": "Earlier selected score is historical; "
        "not a fresh candidate-versus-incumbent comparison.",
    }


def make_seal(path, programs, protocol, source):
    if path.exists():
        raise ValueError("Final seal already exists")
    value = {
        "kind": KIND + "-final-seal",
        "seeds": list(FINAL),
        "max_frames": FRAMES,
        "programs": {k: p.to_dict() for k, p in programs.items()},
        "program_hashes": {k: p.hash for k, p in programs.items()},
        "protocol": protocol.manifest(),
        "model": MODEL,
        "expected_response_model": RESPONSE_MODEL,
        "endpoint": ENDPOINT,
        "source_revision": source,
        "sharing": "Exactly identical program hashes share one fresh final trajectory per seed.",
    }
    write_json(path, {"seal": value, "sha256": digest(value)})


def validate_seal(path, seed, program, protocol):
    record = read_json(path)
    value = record["seal"]
    if digest(value) != record["sha256"] or value["kind"] != KIND + "-final-seal":
        raise ValueError("Invalid criteria study final seal")
    if value["seeds"] != list(FINAL) or seed not in FINAL or value["max_frames"] != FRAMES:
        raise ValueError("Wrong final seeds or horizon")
    if (
        value["protocol"] != protocol.manifest()
        or value["model"] != MODEL
        or value["expected_response_model"] != RESPONSE_MODEL
        or value["endpoint"] != ENDPOINT
    ):
        raise ValueError("Final protocol mismatch")
    if (
        program.hash not in value["program_hashes"].values()
        or program.to_dict() not in value["programs"].values()
    ):
        raise ValueError("Unsealed final program")
    return record["sha256"]


def run_episode(root, protocol, program, seed, max_frames, budget, source, *, final_seal=None):
    """An immutable single-episode match suite, with separate sealed final admission."""
    from jev_atari.choice import ActionPolicy
    from jev_atari.experiment import play
    from jev_atari.matches import aggregate_matches, match_result

    if max_frames != FRAMES or protocol != Protocol():
        raise ValueError("Frozen horizon/environment mismatch")
    split = split_for_seed(seed)
    if split == "test":
        if final_seal is None or max_frames != FRAMES:
            raise ValueError("Test episode needs its frozen final seal")
        validate_seal(final_seal, seed, program, protocol)
        if not read_json(budget.path)["training_closed"]:
            raise ValueError("Close training before final evaluation")
    elif final_seal is not None:
        raise ValueError("Final runner accepts test seeds only")
    if root.exists():
        raise ValueError("Never restart or overwrite an episode")
    root.mkdir(parents=True)
    cap = max_frames // protocol.hold_frames
    evaluator = evaluator_for(budget, "final" if final_seal else "nonfinal", cap)
    plan = {
        "kind": KIND + "-episode-plan",
        "source_revision": source,
        "protocol": protocol.manifest(),
        "split": split,
        "seeds": [seed],
        "arms": ["jev"],
        "schedule": [{"seed": seed, "arm": "jev"}],
        "model": MODEL,
        "model_transport": evaluator.transport_manifest,
        "program": program.to_dict(),
        "program_hash": program.hash,
        "max_frames_per_episode": max_frames,
        "max_decisions_per_episode": max_frames // 4,
        "max_http_attempts": cap,
        "point_limit": None,
        "final_seal_hash": read_json(final_seal)["sha256"] if final_seal else None,
    }
    write_json(root / "plan.json", plan)
    report = {
        "kind": "pong-match-suite-v1",
        "status": "incomplete",
        "plan_hash": digest(plan),
        "episodes": [],
    }
    write_json(root / "results.json", report)
    path = root / "jev" / f"seed-{seed}"
    evaluator.api.trace_path = path / "model-exchanges.jsonl"
    emit("episode_started", path=str(root), seed=seed, program=program.name)
    try:
        summary = play(
            protocol,
            ActionPolicy(evaluator, program),
            seed=seed,
            decisions=max_frames // 4,
            out=path,
            video=True,
            evaluator=evaluator,
        )
        row = {"seed": seed, "arm": "jev", **summary, **match_result(summary, max_frames)}
        if not row["evaluation_complete"]:
            raise ValueError("Unexpected incomplete evaluation")
        report["episodes"] = [row]
        report["status"] = "complete"
        write_json(path / "evaluation.json", row)
        emit(
            "episode_complete",
            path=str(root),
            seed=seed,
            reward=row["reward"],
            points=[row["points_scored"], row["points_lost"]],
            frames=row["raw_frames"],
        )
        return row
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        if (path / "summary.json").exists():
            summary = read_json(path / "summary.json")
            report["episodes"] = [
                {"seed": seed, "arm": "jev", **summary, **match_result(summary, max_frames)}
            ]
        raise
    finally:
        report.update(
            aggregates={"jev": aggregate_matches(report["episodes"], 1)},
            api_attempts=evaluator.api.budget.used,
        )
        write_json(root / "api-ledger.json", evaluator.ledger)
        write_json(root / "results.json", report)
        evaluator.close()


def final_episode(root, program, seed, budget, source, seal):
    return run_episode(root, Protocol(), program, seed, FRAMES, budget, source, final_seal=seal)


def endpoint(results):
    """Paired seed bootstrap for one search; no optimizer-population inference."""
    if set(results) != {"V2", "A1", "B1"}:
        raise ValueError("Expected exactly the three frozen final roles")
    for rows in results.values():
        if [r["seed"] for r in rows] != list(FINAL) or not all(
            r["evaluation_complete"] for r in rows
        ):
            raise ValueError("Incomplete final evaluation")
    values = {
        k: np.array([r["capped_episode_return"] for r in rows], dtype=float)
        for k, rows in results.items()
    }
    draws = np.random.default_rng(20260923).integers(0, len(FINAL), (20000, len(FINAL)))
    contrasts = {}
    for name, left, right in (
        ("A_over_v2", "A1", "V2"),
        ("B_over_v2", "B1", "V2"),
        ("A_over_B", "A1", "B1"),
    ):
        gains = values[left] - values[right]
        contrasts[name] = {
            "paired_gains": gains.tolist(),
            "mean_gain": float(gains.mean()),
            "interval_95_percent": np.quantile(gains[draws].mean(axis=1), [0.025, 0.975]).tolist(),
        }
    primary = contrasts["A_over_v2"]
    return {
        "kind": KIND + "-endpoint",
        "contrasts": contrasts,
        "primary": "A_over_v2",
        "milestone_1_screen_met": primary["mean_gain"] >= 1
        and primary["interval_95_percent"][0] > 0,
        "milestone_2_established": False,
        "bootstrap": {
            "repetitions": 20000,
            "seed": 20260923,
            "method": "percentile, paired seed resampling",
        },
        "limits": "One A/B search cannot establish repeatable optimizer advantage. "
        "Seed intervals are conditional on these selected programs, not teacher-run variability. "
        "Short capped episodes do not establish native-match mastery. Pong stage ends here "
        "regardless of whether the improvement screen passes.",
    }


def source_inventory(repository):
    """Identify exposure without reading previously reserved final-test trajectories."""
    requested = (
        {s for runs in TRAIN for seeds in runs for s in seeds}
        | {s for pair in DEV for s in pair}
        | set(FINAL)
    )
    existing = []
    for base in (repository / "artifacts", repository / "experiments"):
        for path in base.rglob("manifest.json"):
            # Only episode manifests, never observations or final outcomes.
            data = read_json(path)
            if data.get("seed") in requested and "protocol" in data:
                existing.append({"path": str(path.relative_to(repository)), "seed": data["seed"]})
    if existing:
        raise ValueError("Proposed seeds already have episode manifests: " + json.dumps(existing))
    return {
        "requested_seeds": sorted(requested),
        "existing_episode_manifests": existing,
        "scope": "Local artifacts and tracked experiment trees; no remote inventory claim.",
    }


def run(root, repository, binary, auth_home):
    if root.exists():
        raise ValueError("New study only; never reset or rerun an existing root")
    source = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repository, text=True
    ).strip()
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=repository, text=True).strip():
        raise ValueError("Freeze committed source and protocol before live access")
    inventory = source_inventory(repository)
    root.mkdir(parents=True)
    lock = (root / ".run.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    baseline = ActionProgram.from_dict(
        read_json(repository / "examples/vertical-policy-program.json")
    )
    state_path = repository / "experiments/pong/motion-probe-v1/inputs.json"
    states = read_json(state_path)
    if len(states) != 80 or any(split_for_seed(s["seed"]) != "train" for s in states):
        raise ValueError("Expected 80 published training diagnostic states")
    if {s["stratum"] for s in states} != set(STRATA):
        raise ValueError("Missing diagnostic strata")
    plan = {
        "kind": KIND,
        "source_revision": source,
        "limits": LIMITS,
        "training_seeds": TRAIN,
        "development_seeds": DEV,
        "final_seeds": FINAL,
        "frames": FRAMES,
        "initial_program": baseline.to_dict(),
        "initial_program_hash": baseline.hash,
        "model": MODEL,
        "expected_response_model": RESPONSE_MODEL,
        "endpoint": ENDPOINT,
        "teacher_isolation": isolation_check(binary, INSTRUCTIONS),
        "teacher_binary": {"sha256": hashlib.sha256(binary.read_bytes()).hexdigest()},
        "probe_input_hash": digest(states),
        "probe_source": str(state_path.relative_to(repository)),
        "source_inventory": inventory,
        "authorization": "Owner explicitly requested restarting experimentation on 2026-09-23. "
        "Three consecutive A/B rounds, then final evaluation and Pong stage closure; "
        "30000-attempt limit with candidate training feedback and OpenRouter.",
        "feedback_sampler": "role-labelled-balanced-48-v1",
        "max_http_retries": 0,
    }
    write_json(root / "plan.json", plan)
    budget = CandidateBudget(root / "budget.json")
    status = {"status": "running", "plan_hash": digest(plan), "completed_rounds": []}
    write_json(root / "status.json", status)
    selected = {"V2": baseline}
    try:
        for run_index in range(len(TRAIN)):
            incumbent = {"A": baseline, "B": baseline}
            best = {"A": 0.0, "B": 0.0}
            memory = {"A": [], "B": []}
            previous_a = None
            for round_index in range(len(TRAIN[run_index])):
                rd = root / f"search-{run_index + 1}" / f"round-{round_index + 1}"
                status["active"] = str(rd.relative_to(root))
                write_json(root / "status.json", status)
                # B's first real proposal is also the counted access preflight before gameplay.
                empty = {"split": "train", "examples": [], "episodes": []}
                b_packet = packet_for("B", round_index + 1, incumbent["B"], empty, memory["B"])
                b_program, b_proposal = propose(
                    rd / "B/teacher", b_packet, budget, binary, auth_home
                )
                training = []
                generators = {"incumbent": incumbent["A"]}
                if previous_a is not None:
                    generators["previous-candidate"] = previous_a
                # Always execute both roles in later rounds, even for identical hashes.
                for seed in TRAIN[run_index][round_index]:
                    for role, generator in generators.items():
                        path = rd / "training" / role / f"seed-{seed}"
                        run_episode(path, Protocol(), generator, seed, FRAMES, budget, source)
                        audit_episode(path, repository)
                        training.append((role, generator, path / "jev" / f"seed-{seed}"))
                evidence = candidate_evidence(training)
                a_packet = packet_for("A", round_index + 1, incumbent["A"], evidence, memory["A"])
                a_program, a_proposal = propose(
                    rd / "A/teacher", a_packet, budget, binary, auth_home
                )
                previous_a = a_program
                candidates = {"A": a_program, "B": b_program}
                proposals = {"A": a_proposal, "B": b_proposal}
                screens = probe(rd / "probe", states, {"V2": baseline, **candidates}, budget)
                evaluations = {"V2": [], "A": [], "B": []}
                for j, seed in enumerate(DEV[run_index]):
                    roles = ["V2", "A", "B"]
                    offset = (run_index + round_index + j) % 3
                    roles = roles[offset:] + roles[:offset]
                    for role in roles:
                        if role != "V2" and not screens[role]["eligible"]:
                            continue
                        path = rd / "development" / role / f"seed-{seed}"
                        program = baseline if role == "V2" else candidates[role]
                        row = run_episode(path, Protocol(), program, seed, FRAMES, budget, source)
                        audit_episode(path, repository)
                        evaluations[role].append(row)
                decisions = {}
                for arm in ("A", "B"):
                    decision = (
                        select(evaluations["V2"], evaluations[arm], DEV[run_index], best[arm])
                        if screens[arm]["eligible"]
                        else {"accepted": False, "status": "diagnostic-screen-failed"}
                    )
                    if decision["accepted"]:
                        incumbent[arm], best[arm] = candidates[arm], decision["mean_gain"]
                    decisions[arm] = decision
                    memory[arm].append({"round": round_index + 1, "proposal": proposals[arm]})
                write_json(
                    rd / "selection.json",
                    {
                        "decisions": decisions,
                        "selected_programs": {k: p.to_dict() for k, p in incumbent.items()},
                    },
                )
                status["completed_rounds"].append(
                    {"search": run_index + 1, "round": round_index + 1, "decisions": decisions}
                )
                write_json(root / "status.json", status)
                emit(
                    "criteria_round_complete",
                    search=run_index + 1,
                    round=round_index + 1,
                    decisions=decisions,
                )
            selected.update({f"{arm}{run_index + 1}": p for arm, p in incumbent.items()})
        make_seal(root / "final-seal.json", selected, Protocol(), source)
        budget.close_training()
        status["active"] = "final"
        write_json(root / "status.json", status)
        unique = {p.hash: p for p in selected.values()}
        final_rows = {key: [] for key in unique}
        for index, seed in enumerate(FINAL):
            hashes = list(unique)
            offset = index % len(hashes)
            for key in hashes[offset:] + hashes[:offset]:
                path = root / "final" / key / f"seed-{seed}"
                row = final_episode(
                    path, unique[key], seed, budget, source, root / "final-seal.json"
                )
                audit_episode(path, repository)
                final_rows[key].append(row)
        results = {role: final_rows[p.hash] for role, p in selected.items()}
        write_json(root / "final-results.json", results)
        write_json(root / "endpoint.json", endpoint(results))
        status.update(status="complete", active=None)
    except Exception as exc:
        status.update(status="incomplete", error_type=type(exc).__name__)
        raise
    finally:
        status["budget"] = read_json(budget.path)
        write_json(root / "status.json", status)
        lock.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=["openrouter"], required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--codex-binary", type=Path, required=True)
    parser.add_argument("--auth-home", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    args = parser.parse_args()
    run(args.out, args.repository, args.codex_binary.resolve(), args.auth_home)
