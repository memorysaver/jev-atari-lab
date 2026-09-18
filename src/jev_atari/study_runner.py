"""Checkpointed, single-process execution of the approved three-round Pong study."""

import argparse
import fcntl
import json
import subprocess
import sys
import time
from pathlib import Path

from jev_atari.choice import ActionProgram, ChoiceEvaluator
from jev_atari.controls import PinnedActionPolicy
from jev_atari.environment import Protocol
from jev_atari.experiment import play, split_for_seed
from jev_atari.io import digest, read_json, write_json
from jev_atari.matches import aggregate_matches, match_result
from jev_atari.study import (
    DEV_SEEDS,
    FINAL_SEEDS,
    MODEL,
    TRAIN_SEEDS,
    AllocatedBudget,
    StudyBudget,
    parse_proposal,
    probe_report,
    sample_training,
    seal_final,
    select_policy,
    teacher_packet,
    verify_final_seal,
)
from jev_atari.teacher import invoke_teacher, isolation_check


def emit(event, **kwargs):
    print(json.dumps({"event": event, "utc_epoch": time.time(), **kwargs}), flush=True)


def evaluator_for(budget, phase, max_calls):
    evaluator = ChoiceEvaluator(model=MODEL, max_calls=max_calls)
    evaluator.api.budget = AllocatedBudget(budget, phase, max_calls)
    evaluator.api.retry_transport = True
    return evaluator


def run_episode(root, protocol, program, seed, max_frames, budget, source, *, final_seal=None):
    """An immutable single-episode match suite, with separate sealed final admission."""
    split = split_for_seed(seed)
    if split == "test":
        if final_seal is None or max_frames != 20000:
            raise ValueError("Test episode needs its frozen final seal")
        verify_final_seal(final_seal, seed, program, protocol)
    elif final_seal is not None:
        raise ValueError("Final runner accepts test seeds only")
    if root.exists():
        report = read_json(root / "results.json")
        plan = read_json(root / "plan.json")
        if (
            report["status"] != "complete"
            or plan["program_hash"] != program.hash
            or plan["seeds"] != [seed]
            or plan["max_frames_per_episode"] != max_frames
            or plan["source_revision"] != source
            or plan["protocol"] != protocol.manifest()
            or digest(plan) != report["plan_hash"]
        ):
            raise ValueError("Refuse to restart or alter existing episode")
        return report["episodes"][0]
    root.mkdir(parents=True)
    cap = max_frames // protocol.hold_frames + 500
    evaluator = evaluator_for(budget, "final" if final_seal else "nonfinal", cap)
    plan = {
        "kind": "pong-study-episode-plan-v1",
        "source_revision": source,
        "protocol": protocol.manifest(),
        "split": split,
        "seeds": [seed],
        "arms": ["jev"],
        "schedule": [{"seed": seed, "arm": "jev"}],
        "model": MODEL,
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
            PinnedActionPolicy(evaluator, program),
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


def audit_episode(root, repository):
    out = root / "audit"
    if out.exists():
        record = read_json(out / "verification.json")
        if record["results_hash"] != digest(read_json(root / "results.json")):
            raise ValueError("Stale episode audit")
        return
    subprocess.run(
        [
            sys.executable,
            str(repository / "scripts/verify_matches.py"),
            "--run",
            str(root),
            "--out",
            str(out),
        ],
        check=True,
    )


def probes(root, evidence, parent, candidate, budget):
    states = [e for e in evidence["examples"] if e["probe"]]
    if len(states) != 32:
        raise ValueError("Expected exactly 32 fixed training inputs")
    if root.exists():
        result = read_json(root / "results.json")
        if result["parent_hash"] != parent.hash or result["candidate_hash"] != candidate.hash:
            raise ValueError("Changed existing probe programs")
        return result
    root.mkdir()
    write_json(root / "inputs.json", states)
    evaluator = evaluator_for(budget, "nonfinal", 160)
    evaluator.api.trace_path = root / "model-exchanges.jsonl"
    rows = []
    try:
        with (root / "predictions.jsonl").open("w") as stream:
            for i, state in enumerate(states):
                for repeat in range(2):
                    order = [("parent", parent), ("candidate", candidate)]
                    if (i + repeat) % 2:
                        order.reverse()
                    for role, program in order:
                        result = evaluator.evaluate(state["observation"], program)
                        if result["response_model"] != MODEL:
                            raise ValueError("Probe model version changed")
                        row = {
                            "id": state["id"],
                            "program_role": role,
                            "repeat": repeat,
                            "prediction": result,
                            "answer": result["choice_answer"],
                        }
                        rows.append(row)
                        stream.write(json.dumps(row) + "\n")
                        stream.flush()
        report = {
            "parent_hash": parent.hash,
            "candidate_hash": candidate.hash,
            "inputs_hash": digest(states),
            "metrics": probe_report(rows),
        }
        write_json(root / "results.json", report)
        return report
    finally:
        write_json(root / "api-ledger.json", evaluator.ledger)
        evaluator.close()


def propose(root, packet, budget, binary, auth_home):
    if (root / "validated.json").exists():
        saved = read_json(root / "validated.json")
        if saved["packet_hash"] != digest(packet):
            raise ValueError("Teacher packet changed after proposal")
        return ActionProgram.from_dict(saved["program"]), saved["proposal"]
    current_packet = packet
    for attempt in range(1, 4):
        destination = root / f"invocation-{attempt}"
        if destination.exists():
            execution = read_json(destination / "execution.json")
            if execution["status"] != "complete" or execution["packet_hash"] != digest(
                current_packet
            ):
                raise ValueError("Refuse to repeat incomplete teacher invocation")
            value = read_json(destination / "proposal.json")
        else:
            value = invoke_teacher(
                current_packet,
                destination,
                budget,
                binary=binary,
                auth_home=auth_home,
                repair=attempt > 1,
            )
        try:
            program = parse_proposal(value, packet)
            break
        except ValueError as exc:
            write_json(destination / "validation-error.json", {"error": str(exc)})
            if attempt == 3:
                raise
            current_packet = {
                **packet,
                "technical_repair": {
                    "instruction": "Fix schema/length/evidence references only. Preserve the "
                    "same policy hypothesis; do not propose a different strategy.",
                    "invalid_proposal": value,
                    "validation_error": str(exc),
                },
            }
    write_json(
        root / "validated.json",
        {"packet_hash": digest(packet), "program": program.to_dict(), "proposal": value},
    )
    return program, value


def run_study(out, repository, binary, auth_home):
    out.mkdir(parents=True, exist_ok=True)
    lock = (out / ".run.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    source = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repository, text=True
    ).strip()
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=repository, text=True).strip():
        raise ValueError("Freeze a clean source revision before live execution")
    protocol = Protocol()
    initial = ActionProgram.from_dict(
        read_json(repository / "examples/vertical-policy-program.json")
    )
    plan = {
        "kind": "pong-teacher-study-v1",
        "source_revision": source,
        "protocol": protocol.manifest(),
        "initial_program_hash": initial.hash,
        "train_seeds": TRAIN_SEEDS,
        "development_seeds": DEV_SEEDS,
        "final_seeds": FINAL_SEEDS,
        "teacher_isolation": isolation_check(binary),
        "approval": "Owner approved the 2026-09-19 study proposal in conversation.",
    }
    # JSON roundtrip makes tuples canonical for resume comparisons.
    plan = json.loads(json.dumps(plan))
    if (out / "plan.json").exists():
        if read_json(out / "plan.json") != plan:
            raise ValueError("Study source/configuration changed")
    else:
        write_json(out / "plan.json", plan)
    budget = StudyBudget(out / "budget.json")
    state = {"status": "running", "source_revision": source, "rounds": []}
    programs = {"A": initial, "B": initial}
    memory = {"A": [], "B": []}
    try:
        for number, seeds in enumerate(TRAIN_SEEDS, 1):
            rd = out / f"round-{number:02d}"
            rd.mkdir(exist_ok=True)
            state["active_round"] = number
            write_json(out / "status.json", state)
            training = []
            for seed in seeds:
                path = rd / "training" / f"seed-{seed}"
                run_episode(path, protocol, programs["A"], seed, 10000, budget, source)
                audit_episode(path, repository)
                training.append(path / "jev" / f"seed-{seed}")
            evidence = sample_training(training)
            write_json(rd / "training-evidence.json", evidence)
            candidates, proposals, results = {}, {}, {}
            for arm in ("A", "B"):
                ar = rd / arm
                ar.mkdir(exist_ok=True)
                packet = teacher_packet(arm, number, programs[arm], evidence, memory[arm])
                candidates[arm], proposals[arm] = propose(
                    ar / "teacher", packet, budget, binary, auth_home
                )
                write_json(
                    ar / "question-changes.json",
                    {
                        "before": programs[arm].to_dict(),
                        "after": candidates[arm].to_dict(),
                        "parent_hash": programs[arm].hash,
                        "candidate_hash": candidates[arm].hash,
                        "proposal": proposals[arm],
                        "packet_hash": digest(packet),
                    },
                )
                emit("proposal_validated", round=number, arm=arm, candidate=candidates[arm].name)
                probes(ar / "probes", evidence, programs[arm], candidates[arm], budget)
                results[arm] = {"parent": [], "candidate": []}
            # Same seeds, fresh parent and candidate each round; reverse ordering on second seed.
            schedule = [(a, r) for a in ("A", "B") for r in ("parent", "candidate")]
            for i, seed in enumerate(DEV_SEEDS):
                for arm, role in schedule if i == 0 else list(reversed(schedule)):
                    program = programs[arm] if role == "parent" else candidates[arm]
                    path = rd / arm / "development" / role / f"seed-{seed}"
                    row = run_episode(path, protocol, program, seed, 20000, budget, source)
                    audit_episode(path, repository)
                    results[arm][role].append(row)
            decisions = {}
            for arm in ("A", "B"):
                decision = select_policy(results[arm]["parent"], results[arm]["candidate"])
                if decision["accepted"]:
                    programs[arm] = candidates[arm]
                decision["selected_program"] = programs[arm].to_dict()
                decision["selected_program_hash"] = programs[arm].hash
                write_json(rd / arm / "selection.json", decision)
                decisions[arm] = decision
                # No development scores or acceptance labels enter either teacher's memory.
                memory[arm].append({"round": number, "proposal": proposals[arm]})
                emit(
                    "selection",
                    round=number,
                    arm=arm,
                    accepted=decision["accepted"],
                    mean_gain=decision.get("mean_gain"),
                )
            state["rounds"].append({"round": number, "decisions": decisions})
            write_json(out / "status.json", state)
        seal = out / "final-seal.json"
        final_programs = {"A": programs["A"], "B": programs["B"], "V2": initial}
        if not seal.exists():
            seal_final(seal, final_programs, protocol, source)
        budget.close_training()
        final_rows = {name: [] for name in final_programs}
        for i, seed in enumerate(FINAL_SEEDS):
            order = list(final_programs) if i % 2 == 0 else list(reversed(final_programs))
            for name in order:
                path = out / "final" / name / f"seed-{seed}"
                row = run_episode(
                    path,
                    protocol,
                    final_programs[name],
                    seed,
                    20000,
                    budget,
                    source,
                    final_seal=seal,
                )
                audit_episode(path, repository)
                final_rows[name].append(row)
                write_json(out / "final-results.json", final_rows)
        state["status"] = "complete"
        state["final_seal_hash"] = read_json(seal)["sha256"]
    except Exception as exc:
        state.update(status="incomplete", error_type=type(exc).__name__, error=str(exc))
        emit("study_stopped", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        state["budget"] = read_json(out / "budget.json")
        write_json(out / "status.json", state)
        lock.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--codex-binary", type=Path, required=True)
    parser.add_argument("--auth-home", type=Path, required=True)
    parser.add_argument("--backend", choices=["jev"], required=True)
    args = parser.parse_args()
    run_study(args.out.resolve(), Path.cwd(), args.codex_binary.resolve(), args.auth_home.resolve())


if __name__ == "__main__":
    main()
