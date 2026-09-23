"""Audit the OpenRouter candidate-feedback study, including interrupted training."""

import argparse
import json
from pathlib import Path

from verify_matches import verify as verify_episode

from jev_atari.candidate_study import (
    DEV,
    ENDPOINT,
    FINAL,
    FRAMES,
    INSTRUCTIONS,
    KIND,
    LIMITS,
    MODEL,
    RESPONSE_MODEL,
    SCHEMA,
    TRAIN,
    candidate_evidence,
    endpoint,
    packet_for,
    parse,
    select,
    validate_seal,
)
from jev_atari.choice import ActionPolicy, ActionProgram, validate_choices
from jev_atari.environment import Protocol
from jev_atari.io import digest, new_directory, read_json, write_json
from jev_atari.motion_probe import schedule, summarize


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def verify_probe(root, states, programs):
    # Teacher reconstruction visits B first; the frozen probe visits V2, A, B.
    # Rebuild that declared order independently of the caller's mapping order.
    assert set(programs) == {"V2", "A", "B"}
    programs = {name: programs[name] for name in ("V2", "A", "B")}
    assert read_json(root / "inputs.json") == states
    assert read_json(root / "programs.json") == {k: p.to_dict() for k, p in programs.items()}
    order = schedule(states, programs)
    assert read_json(root / "schedule.json") == order
    rows, exchanges = lines(root / "predictions.jsonl"), lines(root / "model-exchanges.jsonl")
    assert [e["transport"] for e in exchanges] == read_json(root / "api-ledger.json")
    assert [e["exchange_id"] for e in exchanges] == list(range(1, len(exchanges) + 1))
    assert [{k: r[k] for k in ("id", "program", "repeat")} for r in rows] == order[: len(rows)]
    lookup, cursor = {s["id"]: s for s in states}, 0
    for row in rows:
        obs = lookup[row["id"]]["observation"]
        p = programs[row["program"]]
        request = p.request(obs, MODEL)
        while cursor < len(exchanges):
            exchange = exchanges[cursor]
            cursor += 1
            assert exchange["request"] == request
            if exchange["exchange_id"] == row["prediction"]["exchange_id"]:
                break
            assert exchange["response"] is None
        else:
            raise AssertionError("Prediction lacks its original response")
        response = exchange["response"]
        assert response["model"] == RESPONSE_MODEL
        assert exchange["transport"].get("usage", {}) == response.get("usage", {})
        answer = validate_choices(response, request["questions"], prefer_probabilities=True)[
            "next_action"
        ]
        ids = {a["ale_meaning"]: a["id"] for a in obs["candidate_actions"]}
        prediction = row["prediction"]
        assert prediction["choice_answer"] == answer
        assert prediction["chosen_action"] == ids[answer["choice"]]
        assert prediction["action_probabilities"] == {
            str(ids[k]): v for k, v in answer["probabilities"].items()
        }
        assert prediction["program_hash"] == p.hash
        assert prediction["selection_rule"] == ActionPolicy.selection_rule
        assert prediction["requested_model"] == MODEL
        assert (
            prediction["response_model"] == prediction["expected_response_model"] == RESPONSE_MODEL
        )
        assert prediction["backend"] == "openrouter"
    report = read_json(root / "results.json")
    assert report["attempts"] == len(exchanges) <= 480
    assert report["completed_predictions"] == len(rows)
    assert report["metrics"] == summarize(states, programs, rows)
    if report["status"] == "complete":
        assert len(rows) == 480 and cursor == len(exchanges)
        expected = {}
        for name in programs:
            selected = [r for r in rows if r["program"] == name]
            missing = [r for r in selected if lookup[r["id"]]["stratum"] == "missing"]
            visible = {
                r["prediction"]["chosen_action"]
                for r in selected
                if lookup[r["id"]]["stratum"] != "missing"
            }
            checks = {
                "complete": len(selected) == 160,
                "missing_hold": len(missing) == 16
                and all(r["prediction"]["chosen_action"] in (0, 1) for r in missing),
                "up_and_down_available": bool(visible & {2, 4}) and bool(visible & {3, 5}),
            }
            expected[name] = {**checks, "eligible": all(checks.values())}
        assert read_json(root / "screen.json") == expected
    elif cursor < len(exchanges):
        item = order[len(rows)]
        request = programs[item["program"]].request(lookup[item["id"]]["observation"], MODEL)
        assert all(e["request"] == request for e in exchanges[cursor:])
    return exchanges


def verify(root, out, repository):
    new_directory(out)
    plan, status, budget = (
        read_json(root / name) for name in ("plan.json", "status.json", "budget.json")
    )
    assert plan["kind"] == KIND and plan["limits"] == LIMITS
    assert plan["model"] == MODEL and plan["expected_response_model"] == RESPONSE_MODEL
    assert plan["endpoint"] == ENDPOINT and plan["max_http_retries"] == 0
    assert status["plan_hash"] == digest(plan)
    assert plan["training_seeds"] == [[list(pair) for pair in run] for run in TRAIN]
    assert plan["development_seeds"] == [list(pair) for pair in DEV]
    assert plan["final_seeds"] == list(FINAL) and plan["frames"] == FRAMES
    assert all(budget[k] == v for k, v in LIMITS.items())
    assert (
        budget["attempts"]
        == budget["nonfinal_attempts"] + budget["final_attempts"]
        <= LIMITS["max_attempts"]
    )
    assert budget["nonfinal_attempts"] <= LIMITS["nonfinal_limit"]
    assert budget["final_attempts"] <= LIMITS["final_limit"]
    states = read_json(repository / plan["probe_source"])
    assert digest(states) == plan["probe_input_hash"]
    baseline = ActionProgram.from_dict(plan["initial_program"])
    assert baseline.hash == plan["initial_program_hash"]
    selected, complete_rounds, exchanges, episode_rows = {"V2": baseline}, [], [], {}
    final_attempts, replayed_episode_count = 0, 0
    for path in sorted(root.rglob("plan.json")):
        if path == root / "plan.json":
            continue
        value = read_json(path)
        if value.get("kind") not in {KIND + "-episode-plan"}:
            continue
        episode_root = path.parent
        assert value["source_revision"] == plan["source_revision"]
        assert value["max_frames_per_episode"] == FRAMES
        assert value["protocol"] == Protocol().manifest()
        if value["split"] == "test":
            assert budget["training_closed"]
            assert value["final_seal_hash"] == validate_seal(
                root / "final-seal.json",
                value["seeds"][0],
                ActionProgram.from_dict(value["program"]),
                Protocol(),
            )
        verify_episode(episode_root, out / "episodes" / episode_root.relative_to(root))
        replayed_episode_count += 1
        report = read_json(episode_root / "results.json")
        if report["status"] == "complete":
            episode_rows[str(episode_root.relative_to(root))] = report["episodes"][0]
        for trace in episode_root.glob("jev/seed-*/model-exchanges.jsonl"):
            captured = lines(trace)
            exchanges.extend(captured)
            if value["split"] == "test":
                final_attempts += len(captured)
    for search in range(len(TRAIN)):
        incumbent, best, memory = (
            {"A": baseline, "B": baseline},
            {"A": 0.0, "B": 0.0},
            {"A": [], "B": []},
        )
        previous_a = None
        for round_index in range(len(TRAIN[search])):
            rd = root / f"search-{search + 1}" / f"round-{round_index + 1}"
            if not rd.exists():
                continue
            candidate, proposals = {}, {}
            for arm in ("B", "A"):
                teacher = rd / arm / "teacher"
                if not teacher.exists():
                    continue
                evidence = {"split": "train", "examples": [], "episodes": []}
                if arm == "A":
                    generators = {"incumbent": incumbent["A"]}
                    if previous_a is not None:
                        generators["previous-candidate"] = previous_a
                    evidence = candidate_evidence(
                        [
                            (
                                role,
                                program,
                                rd / "training" / role / f"seed-{seed}" / "jev" / f"seed-{seed}",
                            )
                            for seed in TRAIN[search][round_index]
                            for role, program in generators.items()
                        ]
                    )
                packet = packet_for(arm, round_index + 1, incumbent[arm], evidence, memory[arm])
                assert read_json(teacher / "invocation-1/packet.json") == packet
                if (teacher / "validated.json").exists():
                    saved = read_json(teacher / "validated.json")
                    assert saved["packet_hash"] == digest(packet)
                    candidate[arm] = parse(saved["proposal"], packet)
                    proposals[arm] = saved["proposal"]
                    assert saved["program"] == candidate[arm].to_dict()
                    assert any(
                        read_json(p / "execution.json")["status"] == "complete"
                        and read_json(p / "proposal.json") == saved["proposal"]
                        for p in teacher.glob("invocation-*")
                        if (p / "proposal.json").exists()
                    ), "Validated candidate lacks an original completed teacher proposal"
            # Validate generating-policy provenance even when no A packet was reached.
            generators = {"incumbent": incumbent["A"]}
            if previous_a is not None:
                generators["previous-candidate"] = previous_a
            for training_plan in sorted((rd / "training").glob("*/seed-*/plan.json")):
                value = read_json(training_plan)
                role = training_plan.parent.parent.name
                assert role in generators and value["seeds"][0] in TRAIN[search][round_index]
                assert value["program"] == generators[role].to_dict()
            if "A" in candidate:
                previous_a = candidate["A"]
            if (rd / "probe").exists():
                assert set(candidate) == {"A", "B"}
                exchanges.extend(verify_probe(rd / "probe", states, {"V2": baseline, **candidate}))
            if not (rd / "selection.json").exists():
                continue
            screen = read_json(rd / "probe/screen.json")
            decisions = {}

            def rows(role, round_root=rd, seeds=DEV[search]):
                return [
                    episode_rows[
                        str((round_root / "development" / role / f"seed-{s}").relative_to(root))
                    ]
                    for s in seeds
                ]

            for arm in ("A", "B"):
                decision = (
                    select(rows("V2"), rows(arm), DEV[search], best[arm])
                    if screen[arm]["eligible"]
                    else {"accepted": False, "status": "diagnostic-screen-failed"}
                )
                decisions[arm] = decision
                if decision["accepted"]:
                    incumbent[arm], best[arm] = candidate[arm], decision["mean_gain"]
                memory[arm].append({"round": round_index + 1, "proposal": proposals[arm]})
            assert read_json(rd / "selection.json") == {
                "decisions": decisions,
                "selected_programs": {k: p.to_dict() for k, p in incumbent.items()},
            }
            complete_rounds.append(
                {"search": search + 1, "round": round_index + 1, "decisions": decisions}
            )
        selected.update({f"{arm}{search + 1}": p for arm, p in incumbent.items()})
    assert status["completed_rounds"] == complete_rounds
    teacher_count, repairs, retries = 0, 0, 0
    usage_events = []
    for execution_path in sorted(
        root.glob("search-*/round-*/[AB]/teacher/invocation-*/execution.json")
    ):
        p = execution_path.parent
        execution, packet = read_json(execution_path), read_json(p / "packet.json")
        assert execution["packet_hash"] == digest(packet)
        assert (p / "instructions.txt").read_text() == INSTRUCTIONS + "\n"
        assert read_json(p / "response-schema.json") == SCHEMA
        assert execution["requested_model"] == "gpt-6-astra"
        assert execution["requested_reasoning_effort"] == "high"
        assert execution["isolation"] == plan["teacher_isolation"]
        if "started_at" in execution:
            teacher_count += 1
            repairs += int("technical_repair" in packet)
        events = read_json(p / "events.json") if (p / "events.json").exists() else []
        usage_events.extend(
            e["usage"] for e in events if e["type"] == "turn.completed" and e.get("usage")
        )
        if execution["status"] == "complete":
            assert execution["exit_code"] == 0 and not execution.get("unexpected_item_types")
            assert any(e["type"] == "turn.completed" for e in events)
            value = read_json(p / "proposal.json")
            assert any(
                e["type"] == "agent_message" and json.loads(e["text"]) == value for e in events
            )
        if (p / "retry-decision.json").exists():
            retries += 1
            retry = read_json(p / "retry-decision.json")
            assert retry["packet_hash"] == digest(packet) and not retry["quality_resampling"]
            assert execution["exit_code"] != 0 and not execution.get("unexpected_item_types")
            assert any(e["type"] == "turn.failed" for e in events)
            assert not any(e["type"] in {"agent_message", "turn.completed"} for e in events)
            next_dir = p.with_name("invocation-" + str(int(p.name.rsplit("-", 1)[1]) + 1))
            assert read_json(next_dir / "packet.json") == packet
    assert teacher_count == budget["teacher_invocations"] <= LIMITS["teacher_limit"]
    assert repairs == budget["teacher_repairs"] <= 2
    assert retries == budget["teacher_transport_retries"] <= 2
    assert len(exchanges) == budget["attempts"]
    assert final_attempts == budget["final_attempts"]
    assert len(exchanges) - final_attempts == budget["nonfinal_attempts"]
    for exchange in exchanges:
        if exchange["response"] is not None:
            assert exchange["transport"].get("usage", {}) == exchange["response"].get("usage", {})
    ledger = [e["transport"] for e in exchanges]
    costs = {
        "jev_attempts": len(ledger),
        "jev_non_200_attempts": sum(e["status"] != 200 for e in ledger),
        "jev_input_tokens": sum((e.get("usage") or {}).get("input_tokens", 0) for e in ledger),
        "jev_output_tokens": sum((e.get("usage") or {}).get("output_tokens", 0) for e in ledger),
        "jev_attempts_without_usage": sum(not e.get("usage") for e in ledger),
        "jev_api_seconds": sum(e.get("elapsed_seconds", 0) for e in ledger),
        "teacher_invocations": teacher_count,
        "teacher_completed_usage": usage_events,
        "openrouter_reported_cost_usd": sum((e.get("usage") or {}).get("cost", 0) for e in ledger),
        "billing": "Successful-response OpenRouter usage costs; "
        "failed-call billing and teacher USD unavailable.",
    }
    write_json(out / "costs.json", costs)
    if (root / "final-seal.json").exists():
        seal = read_json(root / "final-seal.json")["seal"]
        assert len(complete_rounds) == 3 and budget["training_closed"]
        assert seal["programs"] == {k: p.to_dict() for k, p in selected.items()}
        assert seal["program_hashes"] == {k: p.hash for k, p in selected.items()}
        assert seal["source_revision"] == plan["source_revision"]
    if status["status"] == "complete":
        expected = {
            role: [episode_rows[f"final/{p.hash}/seed-{s}"] for s in FINAL]
            for role, p in selected.items()
        }
        assert read_json(root / "final-results.json") == expected
        assert read_json(root / "endpoint.json") == endpoint(expected)
    result = {
        "kind": KIND + "-audit",
        "status": "verified",
        "study_status": status["status"],
        "completed_rounds": len(complete_rounds),
        "episode_count": len(episode_rows),
        "completed_episode_count": len(episode_rows),
        "replayed_episode_count": replayed_episode_count,
        "incomplete_episode_count": replayed_episode_count - len(episode_rows),
        "final_evaluation_verified": status["status"] == "complete",
        "source_revision": plan["source_revision"],
        "plan_hash": digest(plan),
        "status_hash": digest(status),
        "budget_hash": digest(budget),
        "costs_hash": digest(costs),
        "audit_api_attempts": 0,
        "scope": "Original Jev requests/responses, complete and incomplete episode replay, "
        "teacher packets/proposals and completed development selections. Final outcomes and "
        "endpoint verified only when final_evaluation_verified is true.",
    }
    write_json(out / "verification.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(verify(args.run, args.out, args.repository)))
