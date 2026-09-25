"""Offline verification of five-round source states, exchanges, controls and full videos."""

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

from seaquest_observation_check import verify_episode

from jev_atari.choice import validate_choices
from jev_atari.io import digest, new_directory, read_json, write_json
from jev_atari.seaquest_execution import (
    MAX_ATTEMPTS,
    ROUND_LIMITS,
    execution_gate,
    literal,
    probe_metrics,
)
from jev_atari.seaquest_pilot import MODEL, PIN
from jev_atari.seaquest_research import NAMES, load_program, paired_gate, prefix_actions


def lines(path):
    return [json.loads(x) for x in path.read_text().splitlines()]


def verify(root, out):
    new_directory(out)
    plan, report, budget = [
        read_json(root / f"{name}.json") for name in ("plan", "results", "budget")
    ]
    assert (
        report["status"] == "complete" and report["stopped_after_round"] == 5 and budget["closed"]
    )
    assert len(report["rounds"]) == 5 and report["plan_hash"] == digest(plan)
    assert budget["used"] <= MAX_ATTEMPTS
    packets = {
        name: read_json(root / name) for name in ("training-packet.json", "final-packet.json")
    }
    assert digest(packets["training-packet.json"]) == plan["training_packet_hash"]
    source_audits = []
    for name, packet in packets.items():
        traces = {}
        for entry in packet["sources"]:
            rel = Path(entry["path"]).relative_to(plan["artifact_root"])
            p = root / rel
            assert hashlib.sha256(p.read_bytes()).hexdigest() == entry["sha256"]
            traces[entry["path"]] = lines(p)
            manifest = read_json(p.parent / "manifest.json")
            assert manifest["split"] == packet["split"]
            if name == "training-packet.json":
                source_audits.append(
                    verify_episode(p.parent, out / "sources" / p.parent.parent.name / p.parent.name)
                )
        assert len({r["id"] for r in packet["rows"]}) == len(packet["rows"])
        assert dict(Counter(r["stratum"] for r in packet["rows"])) == packet["selected"]
        assert all(n <= 16 for n in packet["selected"].values())
        for row in packet["rows"]:
            original = traces[row["source"]][row["transition_index"]]
            assert original["phase"] == "control" and original["observation"] == row["observation"]
            assert digest(row["observation"]) == row["id"]
            assert literal(row["observation"], "late-diver") == (
                row["stratum"],
                row["late_diver_branch"],
            )
    global_index = 0
    all_ledger = []
    round_counts = Counter()
    episodes = []
    probes = []

    def audit_predictions(path, decisions, programs):
        nonlocal global_index
        exchanges = lines(path / "model-exchanges.jsonl")
        ledger = read_json(path / "api-ledger.json")
        assert [x["transport"] for x in exchanges] == ledger
        pending = iter(exchanges)
        for observation, prediction, program in decisions:
            request = program.request(observation, MODEL)
            for exchange in pending:
                global_index += 1
                assert exchange["exchange_id"] == global_index and exchange["request"] == request
                if exchange["exchange_id"] == prediction["exchange_id"]:
                    break
                assert exchange["response"] is None
            else:
                raise AssertionError("Prediction lacks original exchange")
            response = exchange["response"]
            assert response["model"] == prediction["response_model"] == PIN
            answer = validate_choices(response, request["questions"], prefer_probabilities=True)[
                "next_action"
            ]
            assert answer == prediction["choice_answer"]
            assert prediction["chosen_action"] == NAMES.index(answer["choice"])
            assert prediction["program_hash"] == program.hash
            assert (
                prediction["usage"]
                == response.get("usage", {})
                == exchange["transport"].get("usage", {})
            )
        assert not list(pending)
        all_ledger.extend(ledger)
        return len(ledger)

    for number in range(1, 6):
        r = root / f"round-{number:02d}"
        result = read_json(r / "results.json")
        assert result["status"] == "complete"
        assert {k: v for k, v in result.items() if k != "events"} == report["rounds"][number - 1]
        for event in result["events"]:
            p = root / event["path"]
            if event["kind"] == "probe":
                packet = packets[event["packet"]]
                pp = read_json(p / "plan.json")
                assert pp["packet_hash"] == digest(packet)
                programs = {role: load_program(v["program"]) for role, v in pp["programs"].items()}
                assert all(
                    programs[role].hash == v["program_hash"] for role, v in pp["programs"].items()
                )
                rows = lines(p / "predictions.jsonl")
                decisions = []
                index = 0
                for i, state in enumerate(packet["rows"]):
                    roles = list(programs) if i % 2 == 0 else list(reversed(programs))
                    for role in roles:
                        row = rows[index]
                        index += 1
                        assert row["role"] == role and row["state_id"] == state["id"]
                        rule = pp["programs"][role]["rule"]
                        assert row["rule"] == rule
                        assert literal(state["observation"], rule) == (
                            row["expected"],
                            row["branch"],
                        )
                        assert row["actual"] == row["prediction"]["choice_answer"]["choice"]
                        decisions.append((state["observation"], row["prediction"], programs[role]))
                assert index == len(rows)
                round_counts[str(number)] += audit_predictions(p, decisions, programs)
                metrics = probe_metrics(rows)
                assert metrics == read_json(p / "metrics.json") == result["probe_metrics"]
                if number in (3, 4):
                    assert execution_gate(metrics) == result["screen"]
                if number == 5:
                    assert execution_gate(metrics) == result["execution_gate"]
                probes.append(
                    {"round": number, "states": len(packet["rows"]), "predictions": len(rows)}
                )
            else:
                summary = read_json(p / "summary.json")
                manifest = read_json(p / "manifest.json")
                assert summary == event["summary"] and summary["status"] == "complete"
                assert manifest["source_revision"] == plan["source_revision"]
                program = load_program(manifest["program"])
                assert program.hash == manifest["program_hash"]
                rows = lines(p / "transitions.jsonl")
                decisions = []
                hist = Counter()
                controlled_frames = 0
                reward = 0
                for i, row in enumerate(rows):
                    if i < 64:
                        assert row["phase"] == "prefix" and row["prediction"] is None
                        assert row["action"] == prefix_actions(event["seed"])[i]
                        continue
                    assert row["phase"] == "control"
                    if i == 64:
                        assert row["observation"] == read_json(p / "controlled-start.json")
                    pred = row["prediction"]
                    assert pred["chosen_action"] == row["action"]
                    hist[NAMES[row["action"]]] += 1
                    controlled_frames += len(row["frames"])
                    reward += sum(f["reward"] for f in row["frames"])
                    if event["local"]:
                        expected, branch = literal(row["observation"], event["rule"])
                        assert pred["kind"] == "local-literal-control" and pred["model_calls"] == 0
                        assert row["action"] == NAMES.index(expected) and pred["branch"] == branch
                    else:
                        decisions.append((row["observation"], pred, program))
                assert (
                    dict(hist) == summary["action_histogram"]
                    and sum(hist.values()) == summary["agent_decisions"]
                )
                assert (
                    controlled_frames == summary["controlled_frames"]
                    and reward == summary["controlled_reward"]
                )
                if event["local"]:
                    assert summary["api_attempts"] == 0 and read_json(p / "api-ledger.json") == []
                else:
                    count = audit_predictions(p, decisions, {"episode": program})
                    assert count == summary["api_attempts"]
                    round_counts[str(number)] += count
                replay = verify_episode(p, out / event["path"])
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
                            "stream=nb_read_frames,width,height,r_frame_rate",
                            "-of",
                            "json",
                            str(p / "episode.mp4"),
                        ],
                        text=True,
                    )
                )["streams"][0]
                assert int(video["nb_read_frames"]) == summary["frames"] and (
                    video["width"],
                    video["height"],
                    video["r_frame_rate"],
                ) == (160, 210, "60/1")
                episodes.append(
                    {
                        "round": number,
                        "role": event["role"],
                        "seed": event["seed"],
                        "local": event["local"],
                        "summary": summary,
                        "replay": replay,
                        "video": video,
                    }
                )
    assert len(episodes) == 10 and sum(e["local"] for e in episodes) == 6 and len(probes) == 4
    assert global_index == budget["used"] and dict(round_counts) == budget["round_attempts"]
    assert all(v <= ROUND_LIMITS[int(k)] for k, v in round_counts.items())
    seal = read_json(root / "finalist-seal.json")
    eligible = [r for r in report["rounds"] if r["round"] in (3, 4) and r["screen"]["passed"]]
    chosen = (
        max(
            eligible, key=lambda r: (r["probe_metrics"]["candidate"]["movement_macro"], -r["round"])
        )
        if eligible
        else None
    )
    assert seal["selected_round"] == (chosen["round"] if chosen else 2)
    selected = (
        read_json(root / f"round-{chosen['round']:02d}" / "proposal.json")["program"]
        if chosen
        else plan["programs"]["late-diver"]
    )
    assert seal["program"] == selected and seal["program_hash"] == load_program(selected).hash
    final = read_json(root / "round-05/results.json")
    games = [e for e in final["events"] if e["kind"] == "episode" and not e["local"]]
    assert paired_gate(games) == final["gameplay_gate"]
    for seed in plan["final_seeds"]:
        paths = [
            root / "round-05" / role / f"seed-{seed}"
            for role in ("literal-reference", "baseline", "candidate")
        ]
        starts = [read_json(p / "controlled-start.json") for p in paths]
        assert starts[0] == starts[1] == starts[2]
        prefixes = [lines(p / "transitions.jsonl")[:64] for p in paths]
        assert prefixes[0] == prefixes[1] == prefixes[2]
        assert read_json(paths[2] / "manifest.json")["program"] == seal["program"]
    assert final["wording_improvement_gate"] == (
        seal["distinct_candidate"]
        and final["execution_gate"]["passed"]
        and final["gameplay_gate"]["passed"]
    )
    costs = {
        "attempts": len(all_ledger),
        "failed_attempts": sum(x["status"] != 200 for x in all_ledger),
        "input_tokens": sum((x.get("usage") or {}).get("input_tokens", 0) for x in all_ledger),
        "output_tokens": sum((x.get("usage") or {}).get("output_tokens", 0) for x in all_ledger),
        "reported_cost_usd": sum((x.get("usage") or {}).get("cost", 0) for x in all_ledger),
        "api_seconds": sum(x["elapsed_seconds"] for x in all_ledger),
        "isolated_teacher_calls": 0,
    }
    write_json(out / "costs.json", costs)
    result = {
        "status": "verified",
        "plan_hash": digest(plan),
        "report_hash": digest(report),
        "costs_hash": digest(costs),
        "episodes": episodes,
        "probes": probes,
        "source_replays": source_audits,
        "audit_api_calls": 0,
        "selected_round": seal["selected_round"],
        "wording_improvement_gate": final["wording_improvement_gate"],
    }
    write_json(out / "verification.json", result)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(verify(args.run, args.out)))
