"""Run the frozen Ms. Pac-Man pilot with an explicit bounded OpenRouter backend."""

import argparse
import json
from pathlib import Path

from jev_atari.io import digest, new_directory, write_json
from jev_atari.mspacman_pilot import play, revision
from jev_atari.mspacman_questions import MAX_CALLS, MODEL, PIN, PROGRAM, Policy, reference_intent


def build_packet(calibration):
    selected = {"evade": [], "collect": []}
    hashes = set()
    for rule in ("avoid", "pellet", "random"):
        for seed in (510, 511):
            per_group = {"evade": 0, "collect": 0}
            for line in (calibration / rule / f"seed-{seed}" / "transitions.jsonl").open():
                row = json.loads(line)
                if not row["controlled"]:
                    continue
                obs = row["observation"]
                intent = reference_intent(obs)
                group = (
                    "collect"
                    if intent == "PELLETS"
                    else "evade"
                    if intent.startswith("ghost-")
                    else None
                )
                key = digest(obs)
                if (
                    group
                    and len(selected[group]) < 12
                    and per_group[group] < 6
                    and key not in hashes
                ):
                    selected[group].append(
                        {
                            "source_rule": rule,
                            "seed": seed,
                            "observation": obs,
                            "observation_hash": key,
                            "reference_intent": intent,
                            "group": group,
                        }
                    )
                    per_group[group] += 1
                    hashes.add(key)
    if any(len(rows) != 12 for rows in selected.values()):
        raise ValueError("Insufficient balanced training observations")
    return selected["evade"] + selected["collect"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--backend", choices=["openrouter"], required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--expected-response-model", required=True)
    parser.add_argument("--max-calls", type=int, required=True)
    args = parser.parse_args()
    if (args.model, args.expected_response_model, args.max_calls) != (MODEL, PIN, MAX_CALLS):
        raise ValueError("Arguments must match the frozen live protocol")
    new_directory(args.out)
    packet = build_packet(args.calibration)
    write_json(args.out / "packet.json", packet)
    write_json(args.out / "program.json", PROGRAM)
    plan = {
        "source_revision": revision(),
        "program_hash": digest(PROGRAM),
        "packet_hash": digest(packet),
        "backend": args.backend,
        "model": MODEL,
        "pin": PIN,
        "max_calls": MAX_CALLS,
        "seeds": [516, 517],
        "controlled_cap": 2048,
        "hold": 8,
        "final_test": "not run; seeds 518/519 remain unused",
        "probes": 24,
        "max_planned_attempts": 1608,
    }
    write_json(args.out / "plan.json", plan)
    policy = None
    reason = "incomplete"
    try:
        policy = Policy(args.out)
        policy.trace(args.out / "probes")
        with (args.out / "probes" / "results.jsonl").open("x") as log:
            for index, item in enumerate(packet):
                for arm in ("direct", "two-stage"):
                    result = policy.choose(item["observation"], arm)
                    log.write(json.dumps({"index": index, "arm": arm, "prediction": result}) + "\n")
                    log.flush()
                if index % 6 == 5:
                    print(
                        json.dumps({"probes_complete": index + 1, "calls": policy.budget.used}),
                        flush=True,
                    )
        write_json(args.out / "probes" / "resources.json", policy.resources())
        results = []
        # Alternate model arm order across starts. No edits after any probe or held-out result.
        for seed in (516, 517):
            arms = ("direct", "two-stage") if seed == 516 else ("two-stage", "direct")
            for arm in ("random", "pellet", "avoid", *arms):
                path = args.out / "episodes" / arm / f"seed-{seed}"
                summary = play(path, seed, arm, cap=2048, policy=policy if arm in arms else None)
                results.append({"seed": seed, "arm": arm, "summary": summary})
                write_json(args.out / "results.json", results)
        reason = "completed"
    except Exception as exc:
        # JsonAPI errors suppress credential-bearing response text.
        write_json(
            args.out / "failure.json",
            {"exception_type": type(exc).__name__, "reason": "Stopped without fallback or retries"},
        )
        raise
    finally:
        if policy:
            write_json(args.out / "api-ledger.json", policy.api.ledger)
            policy.budget.close(reason)
            policy.api.close()
        write_json(
            args.out / "closure.json",
            {"status": reason, "unused_capacity_closed": True, "isolated_teacher_calls": 0},
        )


if __name__ == "__main__":
    main()
