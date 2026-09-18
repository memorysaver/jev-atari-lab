"""CLI entry point. Default activities never call a paid model."""

import argparse
import json
from pathlib import Path

from jev_atari.arcade import ArcadeActionProgram, arcade_play, inventory, resolve_game
from jev_atari.choice import ActionPolicy, ActionProgram, ChoiceEvaluator, OutcomeChoiceProgram
from jev_atari.controls import run_control_comparison
from jev_atari.environment import Protocol
from jev_atari.experiment import (
    collect,
    dataset_coverage,
    doctor,
    evaluate,
    evaluate_actions,
    load_dataset,
    play,
)
from jev_atari.io import new_directory, read_json, write_json
from jev_atari.learning import OpenRouterTeacher, optimize_round, teacher_packet
from jev_atari.models import JevEvaluator, MockEvaluator, ModelError, ValuePolicy
from jev_atari.online import (
    ReplayPrefixEvaluator,
    policy_feedback,
    run_policy_suite,
    select_policy_candidate,
)
from jev_atari.policies import HeuristicPolicy, RandomPolicy
from jev_atari.program import DEFAULT_PROGRAM, QuestionProgram


def add_protocol(parser):
    parser.add_argument("--sticky", type=float, default=0.25)
    parser.add_argument("--hold-frames", type=int, default=4)
    parser.add_argument("--observation", choices=["ram", "vision"], default="ram")
    parser.add_argument("--noop-max", type=int, default=30)


def add_model(parser, *, allow_mock=True):
    parser.add_argument(
        "--backend", choices=["jev", "mock"] if allow_mock else ["jev"], required=True
    )
    parser.add_argument("--model", default="jev-1.13.0", help="Use a pinned Jev model for studies")
    parser.add_argument("--max-api-calls", type=int, required=True, help="Includes retry attempts")
    parser.add_argument("--program", type=Path)


def program_from(args):
    if args.command == "evaluate-actions" or getattr(args, "policy", None) == "jev-action":
        return ActionProgram.from_dict(read_json(args.program)) if args.program else ActionProgram()
    program = (
        QuestionProgram.from_dict(read_json(args.program)) if args.program else DEFAULT_PROGRAM
    )
    return (
        OutcomeChoiceProgram(program)
        if getattr(args, "primitive", "score") == "choice"
        else program
    )


def evaluator_from(args):
    choice = (
        args.command == "evaluate-actions"
        or getattr(args, "policy", None) == "jev-action"
        or getattr(args, "primitive", "score") == "choice"
    )
    if choice:
        if args.backend != "jev":
            raise ValueError("Choice experiments require --backend jev; mocks only run in tests")
        evaluator = ChoiceEvaluator(model=args.model, max_calls=args.max_api_calls)
        evaluator.api.trace_path = args.out / "model-exchanges.jsonl"
        return evaluator
    if args.backend == "mock":
        return MockEvaluator(args.max_api_calls)
    evaluator = JevEvaluator(model=args.model, max_calls=args.max_api_calls)
    evaluator.api.trace_path = args.out / "model-exchanges.jsonl"
    return evaluator


def main() -> None:
    parser = argparse.ArgumentParser(description="Jev Atari question-learning lab")
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("games", help="List installed Atari games; optionally smoke-test every ROM")
    p.add_argument("--check", action="store_true")
    p.add_argument("--frames", type=int, default=8)
    p.add_argument("--out", type=Path)
    p = subs.add_parser("arcade-play", help="Experimental raw-RAM control of any registered game")
    p.add_argument("--game", required=True)
    p.add_argument("--policy", choices=["random", "jev-action"], default="random")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--frames", type=int, default=2000)
    p.add_argument("--hold-frames", type=int, default=4)
    p.add_argument("--sticky", type=float, default=0.25)
    p.add_argument("--program", type=Path)
    p.add_argument("--model", default="jev-1.13.0")
    p.add_argument("--max-api-calls", type=int)
    p.add_argument("--video", action="store_true")
    p.add_argument("--out", type=Path, required=True)
    p = subs.add_parser("inspect-step", help="Show one decision's model input/output and outcome")
    p.add_argument("--episode", type=Path, required=True)
    p.add_argument("--decision", type=int, required=True)
    p.add_argument("--exchanges", type=Path, help="Suite-level model-exchanges.jsonl, if needed")
    p = subs.add_parser("replay", help="Verify a recorded Pong episode without model calls")
    p.add_argument("--episode", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--video", action="store_true")
    p = subs.add_parser("doctor", help="Real emulator replay/action validation; no model")
    add_protocol(p)
    p.add_argument("--out", type=Path)
    p = subs.add_parser("play", help="Play Pong and write auditable trajectories")
    add_protocol(p)
    p.add_argument(
        "--policy",
        choices=["random", "heuristic", "jev", "jev-action", "mock"],
        default="heuristic",
    )
    p.add_argument("--primitive", choices=["score", "choice"], default="score")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--decisions", type=int, default=1000)
    p.add_argument("--point-limit", type=int, help="Stop after this many scored/lost points")
    p.add_argument("--video", action="store_true")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--program", type=Path)
    p.add_argument("--model", default="jev-1.13.0")
    p.add_argument("--max-api-calls", type=int)
    p = subs.add_parser(
        "policy-suite", help="Online direct-policy trials with bounded point windows"
    )
    add_protocol(p)
    p.add_argument("--policy", choices=["heuristic", "jev-action"], required=True)
    p.add_argument("--seeds", type=int, nargs="+", required=True)
    p.add_argument("--decisions", type=int, default=500)
    p.add_argument("--point-limit", type=int, default=5)
    p.add_argument("--replay-prefix", type=Path, help="Replay a verified interrupted first episode")
    p.add_argument("--program", type=Path)
    p.add_argument("--model", default="jev-1.13.0")
    p.add_argument("--max-api-calls", type=int)
    p.add_argument("--video", action="store_true")
    p.add_argument("--out", type=Path, required=True)
    p = subs.add_parser("policy-feedback", help="Export training-only online trajectory contexts")
    p.add_argument("--suite", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = subs.add_parser(
        "compare-controls", help="Four paired Pong controls at a fixed frame horizon"
    )
    add_protocol(p)
    p.add_argument("--backend", choices=["jev"], required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--max-api-calls", type=int, required=True)
    p.add_argument("--baseline-program", type=Path, required=True)
    p.add_argument("--candidate-program", type=Path, required=True)
    p.add_argument("--seeds", type=int, nargs="+", required=True)
    p.add_argument("--frames", type=int, default=2000)
    p.add_argument("--source-revision", help="Source commit used for the experiment")
    p.add_argument("--video", action="store_true")
    p.add_argument("--out", type=Path, required=True)
    p = subs.add_parser("select-policy", help="Apply the paired online development reward gate")
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = subs.add_parser(
        "collect", help="Branch real ALE snapshots, with frozen heuristic continuation"
    )
    add_protocol(p)
    p.add_argument("--seeds", type=int, nargs="+", required=True)
    p.add_argument("--split", choices=["train", "development", "test"], required=True)
    p.add_argument("--roots-per-seed", type=int, default=6)
    p.add_argument("--warmup", type=int, default=120)
    p.add_argument("--stride", type=int, default=31)
    p.add_argument("--horizon", type=int, default=240)
    p.add_argument("--behavior", choices=["mixed", "heuristic", "random"], default="mixed")
    p.add_argument("--out", type=Path, required=True)
    p = subs.add_parser("inspect", help="Report branch label coverage without model calls")
    p.add_argument("--dataset", type=Path, required=True)
    p = subs.add_parser("evaluate", help="Score one question program on a frozen branch dataset")
    add_model(p)
    p.add_argument("--primitive", choices=["score", "choice"], default="score")
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = subs.add_parser("evaluate-actions", help="Evaluate one direct action Choice per state")
    add_model(p, allow_mock=False)
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = subs.add_parser(
        "teacher-packet", help="Export train-only feedback for a teacher or manual editing"
    )
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--program", type=Path)
    p.add_argument("--evaluation", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p = subs.add_parser(
        "learn", help="One bounded propose/evaluate/select round; never uses test data"
    )
    add_model(p)
    p.add_argument("--train", type=Path, required=True)
    p.add_argument("--development", type=Path, required=True)
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--proposals", type=Path, help="Import a manually supplied teacher proposal JSON"
    )
    source.add_argument("--teacher-model", help="OpenRouter model ID; requires OPENROUTER_API_KEY")
    p.add_argument("--max-teacher-calls", type=int, default=1)
    p.add_argument("--min-improvement", type=float, default=0.01)
    p.add_argument("--train-evaluation", type=Path, help="Reuse a matching complete train report")
    p.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    evaluator, teacher = None, None
    try:
        if args.command in {"doctor", "play", "collect", "policy-suite", "compare-controls"}:
            protocol = Protocol(args.hold_frames, args.sticky, args.observation, args.noop_max)
        if args.command == "games":
            if args.out and args.out.exists():
                raise ValueError("Output already exists")
            result = inventory(check=args.check, frames=args.frames)
            if args.out:
                write_json(args.out, result)
        elif args.command == "arcade-play":
            game = resolve_game(args.game)
            program = None
            if args.policy == "jev-action":
                if not args.max_api_calls or args.max_api_calls < 1:
                    raise ValueError("Jev policy requires a positive --max-api-calls")
                program = (
                    ArcadeActionProgram.from_dict(read_json(args.program))
                    if args.program
                    else ArcadeActionProgram(game_id=game["env_id"])
                )
                evaluator = ChoiceEvaluator(model=args.model, max_calls=args.max_api_calls)
                evaluator.api.trace_path = args.out / "model-exchanges.jsonl"
            elif args.program or args.max_api_calls:
                raise ValueError("Random policy does not use --program or --max-api-calls")
            result = arcade_play(
                args.game,
                policy=args.policy,
                seed=args.seed,
                frames=args.frames,
                hold=args.hold_frames,
                sticky=args.sticky,
                out=args.out,
                evaluator=evaluator,
                program=program,
                video=args.video,
            )
        elif args.command == "inspect-step":
            from jev_atari.replay import inspect_step

            result = inspect_step(args.episode, args.decision, args.exchanges)
        elif args.command == "replay":
            from jev_atari.replay import replay_episode

            result = replay_episode(args.episode, args.out, video=args.video)
        elif args.command == "doctor":
            result = doctor(protocol)
            if args.out:
                write_json(args.out, result)
        elif args.command in {"play", "policy-suite"}:
            if args.policy in {"jev", "jev-action", "mock"}:
                if not args.max_api_calls:
                    raise ValueError("Model policies require --max-api-calls")
                args.backend = "jev" if args.policy == "jev-action" else args.policy
                evaluator = evaluator_from(args)
                if getattr(args, "replay_prefix", None):
                    evaluator = ReplayPrefixEvaluator(evaluator, args.replay_prefix)
                policy_class = ActionPolicy if args.policy == "jev-action" else ValuePolicy
                policy = policy_class(evaluator, program_from(args))
            else:
                policy = (
                    HeuristicPolicy() if args.policy == "heuristic" else RandomPolicy(args.seed)
                )
            common = dict(
                decisions=args.decisions,
                out=args.out,
                video=args.video,
                evaluator=evaluator,
                point_limit=args.point_limit,
            )
            result = (
                play(protocol, policy, seed=args.seed, **common)
                if args.command == "play"
                else run_policy_suite(protocol, policy, seeds=args.seeds, **common)
            )
        elif args.command == "compare-controls":
            baseline = ActionProgram.from_dict(read_json(args.baseline_program))
            candidate = ActionProgram.from_dict(read_json(args.candidate_program))
            evaluator = ChoiceEvaluator(model=args.model, max_calls=args.max_api_calls)

            def show_progress(episode):
                print(
                    json.dumps(
                        {
                            "completed_episode": {
                                key: episode[key] for key in ("arm", "seed", "reward", "raw_frames")
                            }
                        }
                    ),
                    flush=True,
                )

            result = run_control_comparison(
                protocol,
                baseline=baseline,
                candidate=candidate,
                seeds=args.seeds,
                frames=args.frames,
                evaluator=evaluator,
                out=args.out,
                video=args.video,
                source_revision=args.source_revision,
                on_episode=show_progress,
            )
        elif args.command == "policy-feedback":
            if args.out.exists():
                raise ValueError("Output already exists")
            packet = policy_feedback(args.suite)
            write_json(args.out, packet)
            result = {"packet": str(args.out), "examples": len(packet["examples"])}
        elif args.command == "select-policy":
            baseline, candidate = read_json(args.baseline), read_json(args.candidate)
            result = select_policy_candidate(baseline, candidate)
            new_directory(args.out)
            write_json(args.out / "selection.json", result)
            write_json(args.out / "selected-program.json", result["selected_program"])
            before, after = baseline["program"], candidate["program"]
            write_json(
                args.out / "question-changes.json",
                {
                    "kind": "online-question-changes-v1",
                    "before": before,
                    "after": after,
                    "changed_fields": {
                        key: {"before": before.get(key), "after": value}
                        for key, value in after.items()
                        if value != before.get(key)
                    },
                    "teacher_source": "not-recorded-by-selector; retain the proposal provenance",
                    "accepted": result["accepted"],
                    "rejection_reasons": result["rejection_reasons"],
                },
            )
        elif args.command == "collect":
            result = collect(
                protocol,
                seeds=args.seeds,
                split=args.split,
                roots_per_seed=args.roots_per_seed,
                warmup=args.warmup,
                stride=args.stride,
                horizon=args.horizon,
                out=args.out,
                behavior=args.behavior,
            )
        elif args.command == "inspect":
            result = dataset_coverage(load_dataset(args.dataset))
        elif args.command in {"evaluate", "evaluate-actions"}:
            data = load_dataset(args.dataset)
            program = program_from(args)
            evaluator = evaluator_from(args)
            new_directory(args.out)
            try:
                evaluate_fn = evaluate_actions if args.command == "evaluate-actions" else evaluate
                with (args.out / "predictions.jsonl").open("w") as row_log:

                    def save_row(row):
                        row_log.write(json.dumps(row, allow_nan=False) + "\n")
                        row_log.flush()

                    report = evaluate_fn(data, program, evaluator, on_row=save_row)
                write_json(args.out / "evaluation.json", report)
                result = {
                    "metrics": report["metrics"],
                    "backend": report["backend"],
                    "interpretation": report["interpretation"],
                }
            finally:
                write_json(args.out / "api-ledger.json", evaluator.ledger)
        elif args.command == "teacher-packet":
            packet = teacher_packet(
                load_dataset(args.dataset),
                program_from(args),
                read_json(args.evaluation) if args.evaluation else None,
            )
            if args.out.exists():
                raise ValueError("Output already exists")
            write_json(args.out, packet)
            result = {
                "packet": str(args.out),
                "examples": len(packet["examples"]),
                "split": "train",
            }
        else:
            # Validate datasets before constructing paid clients.
            from jev_atari.experiment import require_disjoint

            train, dev = load_dataset(args.train), load_dataset(args.development)
            require_disjoint(train, dev)
            if args.min_improvement <= 0:
                raise ValueError("min-improvement must be positive")
            evaluator = evaluator_from(args)
            if args.teacher_model:
                if args.backend == "mock":
                    raise ValueError(
                        "Do not spend teacher calls optimizing synthetic mock feedback"
                    )
                teacher = OpenRouterTeacher(args.teacher_model, args.max_teacher_calls)
                teacher.api.trace_path = args.out / "teacher-exchanges.jsonl"
            result = optimize_round(
                train,
                dev,
                program_from(args),
                evaluator,
                out=args.out,
                min_improvement=args.min_improvement,
                proposals=read_json(args.proposals) if args.proposals else None,
                teacher=teacher,
                train_report=read_json(args.train_evaluation) if args.train_evaluation else None,
            )
        print(json.dumps(result, indent=2, allow_nan=False))
    except (ValueError, ModelError, FileExistsError, KeyError, TypeError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    finally:
        if evaluator:
            evaluator.close()
        if teacher:
            teacher.close()


if __name__ == "__main__":
    main()
