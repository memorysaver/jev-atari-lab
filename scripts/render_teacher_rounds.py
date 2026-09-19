"""Render English teacher logs from original study records; never propose policies."""

import argparse
import difflib
from pathlib import Path

from jev_atari.io import read_json


def render(root, out):
    out.mkdir(parents=True, exist_ok=True)
    created = []
    for path in sorted(root.glob("round-*/[AB]/question-changes.json")):
        arm = path.parent.name
        number = int(path.parent.parent.name.split("-")[1])
        entry = f"T{number:03d}-{arm}"
        changes = read_json(path)
        proposal = changes["proposal"]
        teacher = path.parent / "teacher"
        invocations = sorted(teacher.glob("invocation-*"))
        first = invocations[0]
        packet = read_json(first / "packet.json")
        execution = read_json(first / "execution.json")
        recovery = (first / "recovery.json").exists()
        selection_file = path.parent / "selection.json"
        selection = read_json(selection_file) if selection_file.exists() else None
        selection_status = (
            ("accepted" if selection["accepted"] else "rejected") if selection else "evaluating"
        )
        if selection and selection.get("status") == "inconclusive":
            selection_status = "inconclusive"
        prefix = f"../../../experiments/pong/teacher-study-v1/records/round-{number:02d}/{arm}"
        before, after = changes["before"], changes["after"]
        lines = [
            f"# {entry}: {after['name']}",
            "",
            "## Identity and status",
            "",
            f"- Study: `teacher-study-v1`; round {number}; arm {arm}; direct policy.",
            f"- Status: **{selection_status}**. This document is rendered from "
            f"prospective runtime records.",
            f"- Parent: `{before['name']}`, hash `{changes['parent_hash']}`.",
            f"- Candidate: `{after['name']}`, hash `{changes['candidate_hash']}`.",
            f"- Original teacher start: Unix epoch `{execution.get('started_at')}`.",
            "",
            "## Teacher and visible evidence",
            "",
            "Requested teacher: `gpt-6-astra`, reasoning `high`, via an isolated "
            "native Codex process.",
            "Provider-level response model attestation is unavailable. Requested settings are not",
            "independent proof of backend model identity.",
            "",
            f"[Original packet]({prefix}/teacher/invocation-1/packet.json) ·",
            f"[Original execution metadata]({prefix}/teacher/invocation-1/execution.json) ·",
            f"[Original response events]({prefix}/teacher/invocation-1/events.json) ·",
            f"[Validated proposal]({prefix}/teacher/validated.json)",
            "",
            f"Packet hash: `{changes['packet_hash']}`.",
            "",
            "The process could not mount the host home or repository. Only the prepared packet,",
            "fixed instructions and schema entered the teacher context; shell, web, "
            "apps and memory",
            "tools were disabled. Prior-edit memory contained proposals, without "
            "development scores",
            "or acceptance labels. The selected current question indirectly reveals "
            "selection history.",
            "",
        ]
        if arm == "A":
            seeds = [e["seed"] for e in packet["evidence"]["episodes"]]
            lines += [
                f"Training seeds: {', '.join(map(str, seeds))}. The deterministic packet combines",
                "evenly spaced decisions with the first four scoring windows per episode.",
                "Observed subsequent rewards are teacher feedback, not future policy inputs.",
                "",
            ]
        else:
            lines += [
                "This control received no empirical trajectories or outcomes. Its game contract,",
                "current question and prior proposals are preserved in the original packet.",
                "",
            ]
        lines += [
            "Referenced evidence IDs: "
            + (", ".join(f"`{e}`" for e in proposal["evidence_ids"]) or "none")
            + ".",
            "",
        ]
        if recovery:
            lines += [
                "The original invocation was falsely rejected by the diagnostic-event parser.",
                "Its one completed response was recovered offline without another model call.",
                "The original failure record remains unchanged; the diagnostic text "
                "is unavailable.",
                "See the [continuation addendum](../teacher-study-continuation.md) and",
                f"[recovery receipt]({prefix}/teacher/invocation-1/recovery.json).",
                "",
            ]
        lines += [
            "## Proposed intervention",
            "",
            "**Operator:** " + proposal["operator"],
            "",
            "**Teacher hypothesis:** " + proposal["hypothesis"],
            "",
            "**Predicted changes:** " + proposal["predicted_changes"],
            "",
            "**Regression risks:** " + proposal["regression_risks"],
            "",
            "The paragraphs above preserve the teacher’s stated rationale; they are "
            "not observed results.",
            "",
            "### Exact parent guidance",
            "",
            "```text",
            before["guidance"],
            "```",
            "",
            "### Exact candidate guidance",
            "",
            "```text",
            after["guidance"],
            "```",
            "",
            "Only the question program name/guidance changes. Jev 1.13.0, observations, all six",
            "actions, argmax decoding, four-frame duration and environment settings stay fixed.",
            "",
            "## Frozen evaluation",
            "",
            "See the [frozen protocol](../teacher-study-protocol.md). Each proposal receives",
            "32 training inputs with two repeats per parent/candidate, then fresh development",
            "episodes on seeds 66/67 capped at 20,000 frames. Retain only if neither seed",
            "regresses and the mean paired gain is at least +1. This is an engineering gate,",
            "not a significance test. Final seeds are excluded from teacher and selector feedback.",
            "",
            "## Observed results",
            "",
        ]
        probe_file = path.parent / "probes/results.json"
        if probe_file.exists():
            metrics = read_json(probe_file)["metrics"]
            lines += [
                "| Comparison | Action flip fraction | Mean JS divergence (bits) |",
                "| --- | ---: | ---: |",
            ]
            for name in ("parent_candidate", "parent_repeat", "candidate_repeat"):
                m = metrics[name]
                lines += [f"| {name} | {m['action_flip_fraction']:.5f} | {m['mean_js_bits']:.6f} |"]
            lines += [
                "",
                "Probe differences describe policy behavior and repeated-query variation; they",
                "do not establish better gameplay.",
                "",
            ]
        else:
            lines += ["Fixed-input probes are not complete.", ""]
        lines += [
            "| Seed | Role | Points scored:lost | Capped return | Native complete |",
            "| --- | --- | ---: | ---: | --- |",
        ]
        completed = 0
        for seed in (66, 67):
            for role in ("parent", "candidate"):
                p = path.parent / "development" / role / f"seed-{seed}" / "results.json"
                if p.exists():
                    result = read_json(p)
                    if result["status"] == "complete":
                        r = result["episodes"][0]
                        completed += 1
                        lines += [
                            f"| {seed} | {role} | {r['points_scored']}:{r['points_lost']} |"
                            f" {r['capped_episode_return']:+g} | {r['native_match_complete']} |"
                        ]
                        continue
                lines += [f"| {seed} | {role} | unavailable | unavailable | unavailable |"]
        lines += [
            "",
            f"{completed}/4 development evaluations complete. A frame cap is not a "
            f"native-match win.",
            "",
        ]
        if selection:
            lines += [
                f"Selected program: `{selection['selected_program']['name']}`.",
                f"Selected hash: `{selection['selected_program_hash']}`.",
                f"[Exact gate record]({prefix}/selection.json).",
                "",
                "This is one step in one exploratory optimizer run. Selection data "
                "cannot establish",
                "generalization or a repeatable optimizer mechanism. See the study "
                "report for final",
                "evaluation, all resource costs and incomplete/failed operations.",
                "",
            ]
        else:
            lines += [
                "No selection result is available yet. Do not infer improvement from a proposal",
                "or its action-probability changes.",
                "",
            ]
        lines += [
            "Original traces, API exchanges, videos and replay audits are preserved in the",
            "[study evidence directory](../../../experiments/pong/teacher-study-v1/README.md).",
            "Exact executor/teacher costs and per-round cumulative accounting are reported in",
            "the study’s machine-readable descriptive results. Unavailable billing "
            "is not zero cost.",
            "",
        ]
        dest = out / f"{entry}.md"
        dest.write_text("\n".join(lines))
        (out / f"{entry}.diff").write_text(
            "".join(
                difflib.unified_diff(
                    (before["guidance"] + "\n").splitlines(keepends=True),
                    (after["guidance"] + "\n").splitlines(keepends=True),
                    fromfile="parent-guidance",
                    tofile="candidate-guidance",
                )
            )
        )
        created.append(str(dest))
    return created


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    print("\n".join(render(a.run, a.out)))
