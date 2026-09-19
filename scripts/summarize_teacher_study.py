"""Build descriptive, offline tables from an audited terminal teacher study.

No model calls; no post-hoc candidate selection. Development is selection data.
"""

import argparse
import csv
import json
from pathlib import Path

from jev_atari.io import read_json, write_json
from jev_atari.matches import aggregate_matches


def costs(directory):
    rows = []
    for path in sorted(directory.rglob("model-exchanges.jsonl")):
        with path.open() as stream:
            rows.extend(json.loads(line)["transport"] for line in stream)
    return {
        "http_attempts": len(rows),
        "non_200_attempts": sum(r.get("status") != 200 for r in rows),
        "api_elapsed_seconds": sum(r["elapsed_seconds"] for r in rows),
        "reported_input_tokens": sum((r.get("usage") or {}).get("input_tokens", 0) for r in rows),
        "reported_output_tokens": sum((r.get("usage") or {}).get("output_tokens", 0) for r in rows),
        "attempts_without_usage": sum(not r.get("usage") for r in rows),
        "monetary_cost": None,
    }


def summarize(root, audit, out):
    verification = read_json(audit / "verification.json")
    status, budget = read_json(root / "status.json"), read_json(root / "budget.json")
    from jev_atari.io import digest

    assert verification["status"] == "verified"
    assert verification["budget_hash"] == digest(budget)
    assert verification["study_status"] == status["status"]
    if out.exists():
        raise ValueError("Output exists; preserve original reports")
    out.mkdir(parents=True)
    episodes, rounds = [], []
    cumulative = 0
    for directory in sorted(root.glob("round-*")):
        number = int(directory.name.split("-")[1])
        round_cost = costs(directory)
        cumulative += round_cost["http_attempts"]
        record = {
            "round": number,
            "cost": round_cost,
            "training_cost": costs(directory / "training"),
            "cumulative_nonfinal_http_attempts": cumulative,
            "arms": {},
        }
        for arm in ("A", "B"):
            path = directory / arm
            row = {"cost": costs(path)}
            for name, relative in [
                ("question_changes", "question-changes.json"),
                ("probe", "probes/results.json"),
                ("selection", "selection.json"),
            ]:
                p = path / relative
                row[name] = read_json(p) if p.exists() else None
            observed = {}
            for role in ("parent", "candidate"):
                results = []
                for p in sorted((path / "development" / role).glob("seed-*/results.json")):
                    results.extend(read_json(p)["episodes"])
                observed[role] = results
            row["development"] = observed
            row["development_aggregates"] = {
                role: aggregate_matches(rows, 2) for role, rows in observed.items()
            }
            selection = row["selection"]
            row["selected_development_mean"] = None
            if selection is not None:
                selected_rows = observed["candidate" if selection["accepted"] else "parent"]
                assert len(selected_rows) == 2 and all(
                    r["evaluation_complete"] for r in selected_rows
                )
                row["selected_development_mean"] = (
                    sum(r["capped_episode_return"] for r in selected_rows) / 2
                )
            record["arms"][arm] = row
        rounds.append(record)
    for p in sorted(root.rglob("results.json")):
        report = read_json(p)
        if report.get("kind") != "pong-match-suite-v1":
            continue
        for row in report["episodes"]:
            episodes.append(
                {
                    "path": str(p.parent.relative_to(root)),
                    **{
                        k: row.get(k)
                        for k in [
                            "seed",
                            "points_scored",
                            "points_lost",
                            "capped_episode_return",
                            "raw_frames",
                            "decisions",
                            "evaluation_complete",
                            "native_match_complete",
                            "outcome",
                            "end_reason",
                            "api_attempts",
                        ]
                    },
                }
            )
    teacher = []
    for path in sorted(root.glob("round-*/[AB]/teacher/invocation-*/execution.json")):
        execution = read_json(path)
        events = (
            read_json(path.parent / "events.json") if (path.parent / "events.json").exists() else []
        )
        teacher.append(
            {
                "path": str(path.parent.relative_to(root)),
                "execution_status": execution["status"],
                "requested_model": execution["requested_model"],
                "requested_reasoning_effort": execution["requested_reasoning_effort"],
                "provider_response_model": execution.get("provider_response_model"),
                "wall_seconds": execution.get("wall_seconds"),
                "completed_turn_usage": [
                    e.get("usage") for e in events if e["type"] == "turn.completed"
                ],
                "diagnostic_markers": sum(
                    e["type"] in {"error", "diagnostic_error"} for e in events
                ),
                "offline_recovery": (path.parent / "recovery.json").exists(),
            }
        )
    final = read_json(root / "final-results.json") if (root / "final-results.json").exists() else {}
    paired = []
    for left, right in [("A", "V2"), ("A", "B"), ("B", "V2")]:
        left_rows = {r["seed"]: r for r in final.get(left, [])}
        right_rows = {r["seed"]: r for r in final.get(right, [])}
        rows = [
            {
                "seed": seed,
                "difference": left_rows[seed]["capped_episode_return"]
                - right_rows[seed]["capped_episode_return"],
            }
            for seed in sorted(left_rows.keys() & right_rows.keys())
            if left_rows[seed]["evaluation_complete"] and right_rows[seed]["evaluation_complete"]
        ]
        paired.append(
            {
                "comparison": f"{left} minus {right}",
                "paired_seeds": rows,
                "mean_paired_difference": sum(x["difference"] for x in rows) / len(rows)
                if rows
                else None,
                "n": len(rows),
            }
        )
    assert costs(root)["http_attempts"] == budget["attempts"]
    report = {
        "study_status": status["status"],
        "budget": budget,
        "rounds": rounds,
        "total_executor_cost": costs(root),
        "episodes": episodes,
        "final": final,
        "paired_final": paired,
        "teacher_invocations": teacher,
        "final_aggregates": {
            arm: aggregate_matches(final.get(arm, []), 4) for arm in ("A", "B", "V2")
        },
        "limitations": [
            "One optimizer run per arm; no replicated optimizer-level uncertainty estimate.",
            "Development scores are reused for selection and are not generalization estimates.",
            "Capped returns are not native-match wins; report completion and win denominators.",
            "Missing billing data is unavailable, not zero monetary cost.",
            "Teacher usage and invocation accounting are separate from Jev HTTP attempts.",
        ],
    }
    write_json(out / "descriptive-results.json", report)
    if episodes:
        with (out / "episodes.csv").open("w") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(episodes[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(episodes)
    return report


def plot(report, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), layout="constrained")
    for arm, color in [("A", "#0072B2"), ("B", "#D55E00")]:
        points = [r for r in report["rounds"] if r["arms"][arm]["selection"] is not None]
        axes[0].plot(
            [r["cumulative_nonfinal_http_attempts"] for r in points],
            [r["arms"][arm]["selected_development_mean"] for r in points],
            marker="o" if arm == "A" else "s",
            markersize=8 if arm == "A" else 5,
            markerfacecolor="none",
            linestyle="-" if arm == "A" else "--",
            color=color,
            label=f"{arm}: selected policy",
        )
        for r in points:
            candidates = r["arms"][arm]["development"]["candidate"]
            score = sum(e["capped_episode_return"] for e in candidates) / len(candidates)
            x = r["cumulative_nonfinal_http_attempts"]
            accepted = r["arms"][arm]["selection"]["accepted"]
            axes[0].scatter([x], [score], marker="^" if accepted else "x", color=color)
            axes[0].annotate(
                f"R{r['round']} " + ("accepted" if accepted else "rejected"),
                (x, score),
                xytext=(-4 if r is points[-1] else 4, 8 if arm == "A" else -14),
                ha="right" if r is points[-1] else "left",
                textcoords="offset points",
                fontsize=8,
                color=color,
            )
    axes[0].set(
        title="Development: selected and proposed questions",
        xlabel="Cumulative study nonfinal Jev HTTP attempts",
        ylabel="Mean capped return on development seeds 66/67",
    )
    for arm, color in [("A", "#0072B2"), ("B", "#D55E00"), ("V2", "#777777")]:
        rows = report["final"].get(arm, [])
        if rows:
            axes[1].plot(
                [str(r["seed"]) for r in rows],
                [r["capped_episode_return"] for r in rows],
                marker="o",
                markersize={"A": 10, "B": 7, "V2": 4}[arm],
                markerfacecolor="none",
                linestyle={"A": "-", "B": "--", "V2": ":"}[arm],
                label=arm,
                color=color,
            )
    axes[1].set(
        title="Final: frozen policies, held-out seeds", xlabel="Seed", ylabel="Capped return"
    )
    for ax in axes:
        ax.axhline(0, color="#999999", linewidth=0.7)
        ax.grid(alpha=0.2)
        ax.margins(x=0.08, y=0.12)
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(fontsize=8)
    fig.suptitle("Exploratory teacher study: development selects; final evaluates")
    fig.savefig(output, dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("run", "audit", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()
    result = summarize(args.run, args.audit, args.out)
    if args.plot:
        plot(result, args.out / "teacher-study.png")
