"""Audit every original Seaquest research response, action, frame and recorded video."""

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

from seaquest_observation_check import verify_episode

from jev_atari.choice import validate_choices
from jev_atari.io import digest, new_directory, read_json, write_json
from jev_atari.seaquest_pilot import MODEL, PIN
from jev_atari.seaquest_research import MAX_CALLS, PREFIX_DECISIONS, load_program, prefix_actions


def verify(root, out):
    new_directory(out)
    plan, report, budget = [read_json(root / f"{n}.json") for n in ("plan", "results", "budget")]
    assert report["plan_hash"] == digest(plan)
    assert budget["used"] <= budget["max_calls"] == MAX_CALLS
    if "continuation_revision" in plan:
        original_budget = read_json(root / "continuation" / "predecessor-budget.json")
        assert budget["started_at"] == original_budget["started_at"]
        assert budget["used"] >= original_budget["used"]
        assert digest(original_budget) == plan["predecessor_budget_hash"]
    index, episodes, ledger, round_attempts = 0, [], [], Counter()
    for round_path in sorted(root.glob("round-[0-9][0-9]")):
        number = int(round_path.name.split("-")[1])
        round_plan = read_json(round_path / "plan.json")
        result = read_json(round_path / "results.json")
        assert result["plan_hash"] == digest(round_plan)
        for job in round_plan["jobs"]:
            path = round_path / job["role"] / f"seed-{job['seed']}"
            if not path.exists():
                continue
            summary, manifest = read_json(path / "summary.json"), read_json(path / "manifest.json")
            program = load_program(job["program"])
            assert program.hash == job["program_hash"] == manifest["program_hash"]
            assert manifest["program"] == job["program"] and manifest["seed"] == job["seed"]
            assert manifest["source_revision"] == round_plan["source_revision"]
            assert manifest["source_revision"] in {
                plan["source_revision"],
                plan.get("continuation_revision"),
            }
            if (path / "continuation.json").exists():
                continuation = read_json(path / "continuation.json")
                assert continuation["source_revision"] == plan["continuation_revision"]
                assert continuation["program_hash"] == program.hash
                assert continuation["predecessor_manifest_hash"] == digest(manifest)
                assert continuation["predecessor_summary_hash"] == digest(
                    read_json(path / "predecessor-summary.json")
                )
                for name, record in continuation["predecessor_files"].items():
                    target = path / ("predecessor-episode.mp4" if name == "episode.mp4" else name)
                    assert (
                        hashlib.sha256(target.read_bytes()[: record["bytes"]]).hexdigest()
                        == record["sha256"]
                    )
                assert read_json(path / "continuation-replay.json")["status"] == "verified"
            assert manifest["model_transport"]["expected_response_model"] == PIN
            rows = [json.loads(s) for s in (path / "transitions.jsonl").read_text().splitlines()]
            trace = path / "model-exchanges.jsonl"
            exchanges = (
                [json.loads(s) for s in trace.read_text().splitlines()] if trace.exists() else []
            )
            assert [e["transport"] for e in exchanges] == read_json(path / "api-ledger.json")
            assert len(exchanges) == summary["api_attempts"]
            round_attempts[str(number)] += len(exchanges)
            pending = iter(exchanges)
            hist, controlled_frames, controlled_reward = Counter(), 0, 0
            for i, row in enumerate(rows):
                if i < PREFIX_DECISIONS:
                    assert row["phase"] == "prefix" and row["prediction"] is None
                    assert row["action"] == prefix_actions(job["seed"])[i]
                    continue
                assert row["phase"] == "control"
                if i == PREFIX_DECISIONS:
                    assert row["observation"] == read_json(path / "controlled-start.json")
                request = program.request(row["observation"], MODEL)
                for exchange in pending:
                    index += 1
                    assert exchange["exchange_id"] == index and exchange["request"] == request
                    if exchange["exchange_id"] == row["prediction"]["exchange_id"]:
                        break
                    assert exchange["response"] is None
                else:
                    raise AssertionError("Executed action lacks original model response")
                response, prediction = exchange["response"], row["prediction"]
                assert response["model"] == prediction["response_model"] == PIN
                assert (
                    prediction["requested_model"] == MODEL
                    and prediction["program_hash"] == program.hash
                )
                assert (
                    prediction["usage"]
                    == response.get("usage", {})
                    == exchange["transport"].get("usage", {})
                )
                answer = validate_choices(
                    response, request["questions"], prefer_probabilities=True
                )["next_action"]
                assert answer == prediction["choice_answer"]
                ids = {a["ale_meaning"]: a["id"] for a in row["observation"]["candidate_actions"]}
                assert row["action"] == prediction["chosen_action"] == ids[answer["choice"]]
                hist[answer["choice"]] += 1
                controlled_frames += len(row["frames"])
                controlled_reward += sum(f["reward"] for f in row["frames"])
            remaining = list(pending)
            assert not remaining or summary["status"] == "incomplete"
            for exchange in remaining:
                index += 1
                assert exchange["exchange_id"] == index
            assert dict(hist) == summary["action_histogram"]
            assert sum(hist.values()) == summary["agent_decisions"]
            assert controlled_frames == summary["controlled_frames"]
            assert controlled_reward == summary["controlled_reward"]
            assert summary["reward"] == sum(f["reward"] for row in rows for f in row["frames"])
            assert summary["prefix_reward"] == summary["reward"] - controlled_reward
            destination = out / round_path.name / job["role"] / f"seed-{job['seed']}"
            replay = verify_episode(path, destination)
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
                        str(path / "episode.mp4"),
                    ],
                    text=True,
                )
            )["streams"][0]
            assert int(video["nb_read_frames"]) == summary["frames"]
            assert (video["width"], video["height"], video["r_frame_rate"]) == (160, 210, "60/1")
            episodes.append(
                {
                    "round": number,
                    "role": job["role"],
                    "seed": job["seed"],
                    "replay": replay,
                    "video": video,
                }
            )
            ledger.extend(e["transport"] for e in exchanges)
        if result["status"] == "complete":
            assert result["episodes"] == [
                {
                    "role": job["role"],
                    "seed": job["seed"],
                    "summary": read_json(
                        round_path / job["role"] / f"seed-{job['seed']}" / "summary.json"
                    ),
                }
                for job in round_plan["jobs"]
            ]
    assert index == budget["used"] and dict(round_attempts) == budget["round_attempts"]
    if report["status"] == "complete":
        assert len(report["rounds"]) == report["stopped_after_round"] == 10 and budget["closed"]
        assert len(episodes) == 24
    costs = {
        "attempts": len(ledger),
        "non_200": sum(e["status"] != 200 for e in ledger),
        "input_tokens": sum((e.get("usage") or {}).get("input_tokens", 0) for e in ledger),
        "output_tokens": sum((e.get("usage") or {}).get("output_tokens", 0) for e in ledger),
        "reported_cost_usd": sum((e.get("usage") or {}).get("cost", 0) for e in ledger),
        "api_seconds": sum(e["elapsed_seconds"] for e in ledger),
        "isolated_teacher_calls": 0,
    }
    write_json(out / "costs.json", costs)
    result = {
        "status": "verified",
        "study_status": report["status"],
        "episodes": episodes,
        "plan_hash": digest(plan),
        "report_hash": digest(report),
        "costs_hash": digest(costs),
        "audit_api_attempts": 0,
        "scope": "Original API requests/responses, action decoding, raw-frame "
        "replay and video frame counts",
    }
    write_json(out / "verification.json", result)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(verify(args.run, args.out)))
