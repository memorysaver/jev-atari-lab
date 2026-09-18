"""Plot actual match trajectories, without extending terminated or failed episodes.

Optional rendering dependency: uv run --with matplotlib==3.10.7 python scripts/plot_matches.py
"""

import argparse
import json
from pathlib import Path


def plot(root, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plan = json.loads((root / "plan.json").read_text())
    report = json.loads((root / "results.json").read_text())
    figure, axis = plt.subplots(figsize=(10, 5.3), layout="constrained")
    colors = {"random": "#777777", "track-4px": "#0072B2", "intercept": "#D55E00", "jev": "#009E73"}
    for episode in report["episodes"]:
        path = root / episode["arm"] / f"seed-{episode['seed']}" / "transitions.jsonl"
        x, y = [0], [0]
        frame, score = 0, 0
        for line in path.read_text().splitlines():
            row = json.loads(line)
            for reward in row["rewards"]:
                frame += 1
                score += reward
                if reward:
                    x.append(frame)
                    y.append(score)
        x.append(frame)
        y.append(score)
        assert score == episode["reward"] and frame == episode["raw_frames"]
        ending = "native end" if episode["native_match_complete"] else episode["end_reason"]
        label = f"{episode['arm']} (seed {episode['seed']}; {ending})"
        axis.step(x, y, where="post", label=label, color=colors[episode["arm"]], linewidth=2)
        marker = "o" if episode["native_match_complete"] else "x"
        axis.scatter([frame], [score], color=colors[episode["arm"]], marker=marker, s=45, zorder=4)
    axis.axhline(0, color="#aaaaaa", linewidth=0.7)
    axis.set(
        xlabel="Controlled emulator frames (reset frames excluded)",
        ylabel="Cumulative reward (points scored minus conceded)",
        title="Pong match feasibility: cumulative score during play",
        xlim=(0, plan["max_frames_per_episode"] * 1.02),
        ylim=(-22, 22),
    )
    axis.grid(alpha=0.2)
    axis.legend(loc="upper left", fontsize=9)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=180)
    plt.close(figure)
    print(json.dumps({"output": str(output), "matplotlib": matplotlib.__version__}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    plot(args.run, args.out)
