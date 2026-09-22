"""Render recorded teacher proposals and dispositions; never infer missing dialogue."""

import argparse
from pathlib import Path

from jev_atari.io import digest, new_directory, read_json, write_json


def render(root, out):
    new_directory(out)
    status = read_json(root / "status.json")
    records = []
    for search in range(1, 4):
        for number in range(1, 3):
            rd = root / f"search-{search}" / f"round-{number}"
            selection = (
                read_json(rd / "selection.json") if (rd / "selection.json").exists() else None
            )
            for arm in ("A", "B"):
                teacher = rd / arm / "teacher"
                if not teacher.exists():
                    continue
                entry_id = f"C{search}-R{number}-{arm}"
                packet = read_json(teacher / "invocation-1/packet.json")
                invocations = [
                    read_json(p) for p in sorted(teacher.glob("invocation-*/execution.json"))
                ]
                prefix = (
                    "../../../experiments/pong/criteria-teacher-v1/records/"
                    f"search-{search}/round-{number}/{arm}/teacher"
                )
                record = {
                    "id": entry_id,
                    "packet_hash": digest(packet),
                    "arm": arm,
                    "parent_hash": packet["current_program_hash"],
                    "visibility": packet["visibility"],
                    "invocations": invocations,
                    "decision": selection["decisions"][arm] if selection else None,
                }
                text = [
                    f"# {entry_id}: criteria-edit teacher proposal\n",
                    f"Search {search}, round {number}, arm {arm}. Requested teacher: GPT-6 Astra, "
                    "high reasoning, in a fresh packet-only Bubblewrap/Codex invocation. "
                    "Provider model attestation is unavailable.\n",
                    f"Visibility: **{packet['visibility']}**. The coordinator has earlier "
                    "development exposure but did not author this candidate. The current selected "
                    "question indirectly reveals selection history. No development scores or final "
                    "outcomes appear in this packet.\n",
                    f"[Initial packet]({prefix}/invocation-1/packet.json), hash "
                    f"`{record['packet_hash']}`. Parent program hash: `{record['parent_hash']}`.\n",
                    "## Original proposal\n",
                ]
                if (teacher / "validated.json").exists():
                    saved = read_json(teacher / "validated.json")
                    assert saved["packet_hash"] == record["packet_hash"]
                    p = saved["proposal"]
                    record.update(
                        program_hash=digest(saved["program"]), program=saved["program"], proposal=p
                    )
                    text.extend(
                        [
                            f"[Exact validated proposal]({prefix}/validated.json). "
                            f"Program: `{p['name']}`; "
                            f"hash `{record['program_hash']}`.\n",
                            "Teacher-reported hypothesis (not an observed result):\n",
                            p["hypothesis"] + "\n",
                            "Operator: " + p["operator"] + "\n",
                            "Predicted changes: " + p["predicted_changes"] + "\n",
                            "Regression risks: " + p["regression_risks"] + "\n",
                            "Referenced training examples: "
                            + (", ".join(p["evidence_ids"]) or "none")
                            + ".\n",
                            "### Exact guidance\n",
                            "````text\n" + p["guidance"] + "\n````\n",
                            "### Exact action criteria\n",
                        ]
                    )
                    for name, description in p["action_criteria"].items():
                        text.extend([f"**{name}**\n", "````text\n" + description + "\n````\n"])
                else:
                    text.append(
                        "No validated candidate is recorded. Retain the actual invocation "
                        "status; do not invent a proposal or transcript.\n"
                    )
                text.append("## Observed evaluation and disposition\n")
                if selection:
                    decision = selection["decisions"][arm]
                    text.append(f"Disposition: **{decision['status']}**.\n")
                    if "mean_gain" in decision:
                        pairs = decision["paired_gains_over_fresh_v2"]
                        text.append(
                            f"Paired development return gains over fresh v2: {pairs}; "
                            f"mean {decision['mean_gain']:+g}. Previous best development gain: "
                            f"{decision['previous_best_gain']:+g}. The previous best is "
                            "historical, not a freshly rerun incumbent.\n"
                        )
                    text.append(
                        "Selection is an engineering gate, not a held-out improvement claim. "
                        "Final evaluation follows only after all selected programs are sealed.\n"
                    )
                else:
                    text.append(
                        "Development selection is not recorded in this snapshot. "
                        "The proposal is not an established improvement.\n"
                    )
                text.append(
                    "All six native actions, original observations, one question and "
                    "probability-argmax decoding remain available. Guidance and criteria "
                    "are the allowed edits. See the "
                    "[frozen protocol](../criteria-teacher-protocol.md) "
                    "and [study log](../criteria-teacher-log.md).\n"
                )
                (out / f"{entry_id}.md").write_text("\n".join(text))
                records.append(record)
    summary = {
        "kind": "criteria-teacher-rendered-records-v1",
        "study_status": status["status"],
        "status_hash": digest(status),
        "records": records,
        "note": "Original proposals and observed dispositions only; no inferred reasoning.",
    }
    write_json(out / "records.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = render(args.run, args.out)
    print(f"Rendered {len(result['records'])} recorded teacher entries.")
