"""Prospective criteria-edit teacher experiment, with sealed final evaluation."""

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
from jev_atari.study import StudyBudget, parse_proposal, sample_training, teacher_packet
from jev_atari.study_runner import audit_episode, emit, evaluator_for, run_episode
from jev_atari.teacher import PROPOSAL_SCHEMA, invoke_teacher, isolation_check

KIND = "pong-criteria-teacher-v1"
TRAIN = (((100, 101), (102, 103)), ((110, 111), (112, 113)), ((120, 121), (122, 123)))
DEV = ((106, 107), (116, 117), (126, 127))
FINAL = (148, 149, 158, 159, 168, 169, 178, 179)
FRAMES = 2000
LIMITS = {
    "max_attempts": 60000,
    "nonfinal_limit": 29000,
    "final_limit": 31000,
    "teacher_limit": 16,
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


class CriteriaBudget(StudyBudget):
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
    evaluator = evaluator_for(budget, "nonfinal", 520)
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
                if prediction["response_model"] != "jev-1.13.0":
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
        "model": "jev-1.13.0",
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
    if value["protocol"] != protocol.manifest() or value["model"] != "jev-1.13.0":
        raise ValueError("Final protocol mismatch")
    if (
        program.hash not in value["program_hashes"].values()
        or program.to_dict() not in value["programs"].values()
    ):
        raise ValueError("Unsealed final program")
    return record["sha256"]


def final_episode(root, program, seed, budget, source, seal):
    # A separate final entrypoint avoids weakening the original study's sealed admission.
    from jev_atari.controls import PinnedActionPolicy
    from jev_atari.experiment import play
    from jev_atari.matches import aggregate_matches, match_result

    protocol = Protocol()
    seal_hash = validate_seal(seal, seed, program, protocol)
    if not read_json(budget.path)["training_closed"]:
        raise ValueError("Close teacher and nonfinal access before final evaluation")
    root.mkdir(parents=True, exist_ok=False)
    evaluator = evaluator_for(budget, "final", 600)
    plan = {
        "kind": KIND + "-final-episode",
        "source_revision": source,
        "protocol": protocol.manifest(),
        "split": "test",
        "seeds": [seed],
        "arms": ["jev"],
        "schedule": [{"seed": seed, "arm": "jev"}],
        "model": "jev-1.13.0",
        "program": program.to_dict(),
        "program_hash": program.hash,
        "max_frames_per_episode": FRAMES,
        "max_decisions_per_episode": FRAMES // 4,
        "max_http_attempts": 600,
        "point_limit": None,
        "final_seal_hash": seal_hash,
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
    emit("final_episode_started", seed=seed, program=program.name, path=str(root))
    try:
        summary = play(
            protocol,
            PinnedActionPolicy(evaluator, program),
            seed=seed,
            decisions=FRAMES // 4,
            out=path,
            video=True,
            evaluator=evaluator,
        )
        row = {"seed": seed, "arm": "jev", **summary, **match_result(summary, FRAMES)}
        if not row["evaluation_complete"]:
            raise ValueError("Incomplete final episode")
        report.update(status="complete", episodes=[row])
        write_json(path / "evaluation.json", row)
        emit("final_episode_complete", seed=seed, program=program.name, reward=row["reward"])
        return row
    finally:
        if report["status"] == "incomplete" and (path / "summary.json").exists():
            summary = read_json(path / "summary.json")
            report["episodes"] = [
                {"seed": seed, "arm": "jev", **summary, **match_result(summary, FRAMES)}
            ]
        report.update(
            aggregates={"jev": aggregate_matches(report["episodes"], 1)},
            api_attempts=evaluator.api.budget.used,
        )
        write_json(root / "results.json", report)
        write_json(root / "api-ledger.json", evaluator.ledger)
        evaluator.close()


def endpoint(results):
    """Frozen paired/crossed bootstrap at seed and optimizer-run level, never frame level."""
    baseline = np.array([r["capped_episode_return"] for r in results["V2"]], dtype=float)
    if (
        len(baseline) != 8
        or [r["seed"] for r in results["V2"]] != list(FINAL)
        or not all(r["evaluation_complete"] for r in results["V2"])
    ):
        raise ValueError("Incomplete final baseline")
    values = {}
    for arm in ("A", "B"):
        for run in range(3):
            rows = results[f"{arm}{run + 1}"]
            if [r["seed"] for r in rows] != list(FINAL) or not all(
                r["evaluation_complete"] for r in rows
            ):
                raise ValueError("Incomplete final arm")
        values[arm] = np.array(
            [[r["capped_episode_return"] for r in results[f"{arm}{run + 1}"]] for run in range(3)]
        )
    av2, ab = values["A"] - baseline, values["A"] - values["B"]
    rng = np.random.default_rng(20260922)
    seed_draws = rng.integers(0, 8, (20000, 8))
    run_draws = rng.integers(0, 3, (20000, 3))
    first = av2[0, seed_draws].mean(axis=1)
    a_boot = av2[run_draws[:, :, None], seed_draws[:, None, :]].mean(axis=(1, 2))
    ab_boot = ab[run_draws[:, :, None], seed_draws[:, None, :]].mean(axis=(1, 2))

    def contrast(matrix, distribution):
        return {
            "mean_gain": float(matrix.mean()),
            "interval_95_percent": np.quantile(distribution, [0.025, 0.975]).tolist(),
        }

    primary = contrast(av2[0], first)
    aggregate_a, feedback = contrast(av2, a_boot), contrast(ab, ab_boot)

    def positive(c):
        return c["mean_gain"] >= 1 and c["interval_95_percent"][0] > 0

    return {
        "kind": KIND + "-endpoint",
        "primary_A1_over_v2": primary,
        "milestone_1_screen_met": positive(primary),
        "all_A_over_v2": aggregate_a,
        "A_over_B": feedback,
        "per_run_A_over_v2": av2.mean(axis=1).tolist(),
        "per_run_A_over_B": ab.mean(axis=1).tolist(),
        "replicated_signal_screen_met": positive(aggregate_a)
        and positive(feedback)
        and bool((av2.mean(axis=1) > 0).all())
        and bool((ab.mean(axis=1) > 0).all()),
        "bootstrap": {
            "repetitions": 20000,
            "seed": 20260922,
            "method": "percentile; shared resampled seeds and paired optimizer-run IDs",
        },
        "limits": "Small-sample bootstrap precision is provisional. Three optimizer runs per arm "
        "do not establish a well-powered population feedback advantage. Report all outcomes and "
        "confirm a favorable signal in additional independent searches before milestone 2.",
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
        "model": "jev-1.13.0",
        "teacher_isolation": isolation_check(binary, INSTRUCTIONS),
        "teacher_binary": {"sha256": hashlib.sha256(binary.read_bytes()).hexdigest()},
        "probe_input_hash": digest(states),
        "probe_source": str(state_path.relative_to(repository)),
        "source_inventory": inventory,
        "authorization": "Owner requested continued experimentation toward the research "
        "endpoint on 2026-09-22. Conservative 60000-attempt stage selected.",
    }
    write_json(root / "plan.json", plan)
    budget = CriteriaBudget(root / "budget.json")
    status = {"status": "running", "plan_hash": digest(plan), "completed_rounds": []}
    write_json(root / "status.json", status)
    selected = {"V2": baseline}
    try:
        for run_index in range(3):
            incumbent = {"A": baseline, "B": baseline}
            best = {"A": 0.0, "B": 0.0}
            memory = {"A": [], "B": []}
            for round_index in range(2):
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
                for seed in TRAIN[run_index][round_index]:
                    path = rd / "training" / f"seed-{seed}"
                    run_episode(path, Protocol(), incumbent["A"], seed, FRAMES, budget, source)
                    audit_episode(path, repository)
                    training.append(path / "jev" / f"seed-{seed}")
                evidence = sample_training(training)
                a_packet = packet_for("A", round_index + 1, incumbent["A"], evidence, memory["A"])
                a_program, a_proposal = propose(
                    rd / "A/teacher", a_packet, budget, binary, auth_home
                )
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
    parser.add_argument("--backend", choices=["jev"], required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--codex-binary", type=Path, required=True)
    parser.add_argument("--auth-home", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    args = parser.parse_args()
    run(args.out, args.repository, args.codex_binary.resolve(), args.auth_home)
