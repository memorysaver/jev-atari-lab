"""Verify native-match evidence, including capped and interrupted episodes, without API calls."""

import argparse
import json
from pathlib import Path

from jev_atari.choice import ActionPolicy, ActionProgram, validate_choices
from jev_atari.environment import Pong, Protocol
from jev_atari.io import digest, read_json, write_json
from jev_atari.matches import aggregate_matches, match_result
from jev_atari.policies import HeuristicPolicy, InterceptPolicy, RandomPolicy
from jev_atari.replay import replay_episode


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def verify(root, out):
    if out.exists():
        raise ValueError("Output already exists")
    plan, report = read_json(root / "plan.json"), read_json(root / "results.json")
    assert digest(plan) == report["plan_hash"]
    assert report["api_attempts"] <= plan["max_http_attempts"]
    episodes = report["episodes"]
    assert [{k: e[k] for k in ("seed", "arm")} for e in episodes] == plan["schedule"][
        : len(episodes)
    ]
    if report["status"] == "complete":
        assert len(episodes) == len(plan["schedule"])
        assert all(e["evaluation_complete"] for e in episodes)
    assert report["aggregates"] == {
        arm: aggregate_matches([e for e in episodes if e["arm"] == arm], len(plan["seeds"]))
        for arm in plan["arms"]
    }
    checks, all_exchanges = [], []
    for episode in episodes:
        arm, seed = episode["arm"], episode["seed"]
        path = root / arm / f"seed-{seed}"
        manifest, summary = read_json(path / "manifest.json"), read_json(path / "summary.json")
        assert manifest["protocol"] == plan["protocol"]
        transport = plan.get("model_transport")
        expected_model = plan["model"]
        if transport is not None:
            from jev_atari.openrouter import ENDPOINT

            assert transport["backend"] == "openrouter" and transport["endpoint"] == ENDPOINT
            assert transport["requested_model"] == plan["model"]
            assert transport["expected_response_model"].startswith("typesafe/")
            assert transport["max_retries"] == 0
            assert transport["max_api_calls"] == plan["max_http_attempts"]
            assert manifest["model_transport"] == transport
            expected_model = transport["expected_response_model"]
        assert manifest["seed"] == seed and manifest["split"] == plan["split"]
        assert manifest["point_limit"] is None
        assert manifest["max_decisions"] == plan["max_decisions_per_episode"]
        assert all(episode[k] == v for k, v in summary.items())
        assert all(
            episode[k] == v
            for k, v in match_result(summary, plan["max_frames_per_episode"]).items()
        )
        rows = lines(path / "transitions.jsonl")
        scored = sum(r > 0 for row in rows for r in row["rewards"])
        lost = sum(r < 0 for row in rows for r in row["rewards"])
        assert scored == summary["points_scored"] and lost == summary["points_lost"]
        assert scored - lost == summary["reward"]
        captured = []
        if arm == "jev":
            program = ActionProgram.from_dict(plan["program"])
            assert program.hash == plan["program_hash"]
            assert manifest["question_program"] == program.to_dict()
            captured = lines(path / "model-exchanges.jsonl")
            assert [x["transport"] for x in captured] == read_json(path / "api-ledger.json")
            assert len(captured) == summary["api_attempts"]
            pending = iter(captured)
            for row in rows:
                prediction = row["prediction"]
                # Retries refer to the same still-unexecuted observation.
                for exchange in pending:
                    assert exchange["request"] == program.request(row["observation"], plan["model"])
                    if exchange["exchange_id"] == prediction["exchange_id"]:
                        break
                    assert exchange["response"] is None
                else:
                    raise AssertionError("Recorded action lacks its model response")
                assert exchange["response"]["model"] == expected_model
                assert prediction["response_model"] == expected_model
                assert prediction["requested_model"] == plan["model"]
                if transport is not None:
                    assert prediction["backend"] == "openrouter"
                    assert prediction["expected_response_model"] == expected_model
                    assert prediction["usage"] == exchange["response"].get("usage", {})
                assert prediction["program_hash"] == program.hash
                assert prediction["selection_rule"] == ActionPolicy.selection_rule
                answer = validate_choices(
                    exchange["response"],
                    exchange["request"]["questions"],
                    prefer_probabilities=True,
                )["next_action"]
                ids = {a["ale_meaning"]: a["id"] for a in row["observation"]["candidate_actions"]}
                assert answer == prediction["choice_answer"]
                assert row["action"] == prediction["chosen_action"] == ids[answer["choice"]]
            remaining = list(pending)
            if remaining:
                assert summary["status"] == "incomplete"
                if rows:
                    state = rows[-1]["next_observation"]
                else:
                    with Pong(
                        Protocol(
                            **{
                                k: plan["protocol"][k]
                                for k in ("hold_frames", "sticky", "observation", "noop_max")
                            }
                        )
                    ) as env:
                        state = env.reset(seed)
                assert all(x["request"] == program.request(state, plan["model"]) for x in remaining)
            all_exchanges.extend(captured)
        else:
            policy = {
                "random": lambda seed=seed: RandomPolicy(seed),
                "track-4px": lambda: HeuristicPolicy(4),
                "intercept": InterceptPolicy,
            }[arm]()
            assert manifest["policy"] == policy.name
            for row in rows:
                action, prediction = policy.choose(row["observation"])
                assert action == row["action"] and prediction == row["prediction"]
        replay = replay_episode(path, out / arm / f"seed-{seed}")
        checks.append(
            {"arm": arm, "seed": seed, "captured_exchanges": len(captured), "replay": replay}
        )
        print(arm, seed, "verified", flush=True)
    assert [x["exchange_id"] for x in all_exchanges] == list(range(1, report["api_attempts"] + 1))
    assert [x["transport"] for x in all_exchanges] == read_json(root / "api-ledger.json")
    audit = {
        "kind": "pong-match-audit-v1",
        "status": "verified",
        "audit_api_attempts": 0,
        "plan_hash": digest(plan),
        "results_hash": digest(report),
        "episodes": checks,
    }
    write_json(out / "verification.json", audit)
    return audit


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    verify(args.run, args.out)
