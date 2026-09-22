"""A fixed-rule wording comparison on previously inspected training observations."""

from jev_atari.choice import ActionProgram
from jev_atari.io import digest, read_json, write_json
from jev_atari.motion_probe import PRECISE, STRATA
from jev_atari.motion_probe import prepare as prepare_motion

KIND = "wording-probe-v1"
COMPACT = ActionProgram(
    name="pong-compact-motion-reliability-v1",
    guidance=(
        "Read ball and player in observation.objects. For bbox [x,y,w,h], center_y=y+h/2; "
        "y increases down. Missing ball or player bbox: NOOP. Otherwise target=ball center_y. "
        "Set target=ball center_y+4*vy only when ALL are true: ball.velocity_valid=true; "
        "ball.velocity=[vx,vy] is known in pixels/raw-frame with vx>0; the last three "
        "observation.history samples have ball bboxes and strictly increasing "
        "offset_raw_frames; their two consecutive x changes have product>=0 AND their "
        "two consecutive y changes have product>=0 (zero allowed). Any false or unknown "
        "condition: keep current-height target. No extra time scaling or wall reflection. "
        "gap=target-player center_y. gap < -4: RIGHT (UP); gap > 4: LEFT (DOWN); "
        "otherwise NOOP. Use non-FIRE actions. Horizontal motion only gates lookahead. "
        "Act for four raw frames, then reconsider."
    ),
)


def programs_for(repository):
    return {
        "v2": read_json(repository / "examples/vertical-policy-program.json"),
        "expanded": PRECISE.to_dict(),
        "compact": COMPACT.to_dict(),
    }


def validate_pack(pack, repository):
    """Reject edits to prepared requests before spending live capacity."""
    states = read_json(pack / "inputs.json")
    published = read_json(repository / "experiments/pong/motion-probe-v1/inputs.json")
    if states != published:
        raise ValueError("Wording probe must use the frozen, previously inspected training states")
    if read_json(pack / "programs.json") != programs_for(repository):
        raise ValueError("Wording programs differ from frozen source")
    if read_json(pack / "provenance.json") != provenance(repository, states):
        raise ValueError("Wording provenance differs from frozen source")
    if read_json(pack / "coverage.json") != read_json(
        repository / "experiments/pong/motion-probe-v1/coverage.json"
    ):
        raise ValueError("Wording coverage differs from frozen source")
    if any(s["observation"]["control"]["requested_hold_frames"] != 4 for s in states):
        raise ValueError("The frozen rule requires four-frame actions")
    return states


def provenance(repository, states):
    parent = read_json(repository / "experiments/pong/motion-probe-v1/provenance.json")
    return {
        "kind": KIND,
        "source_archive_sha256": parent["source_archive_sha256"],
        "source_files": parent["source_files"],
        "input_hash": digest(states),
        "proposal_author": "Interactive coordinator; prior development and motion-probe results "
        "were in context. Exact interactive model version and token cost were not recorded.",
        "proposal_kind": "Manual diagnostic compression, not an isolated teacher invocation.",
        "hypothesis": "Compact wording of the same conservative rule may improve execution "
        "while preserving fallback and stable directional behavior.",
        "exposure": "The same 80 states were inspected in motion-probe-v1. This is exploratory "
        "training reuse, not held-out confirmation. No final-test access.",
        "limits": "Wording, length and redundancy change together. This does not isolate "
        "length, prove semantic equivalence inside the model or establish gameplay benefit.",
    }


def prepare(source, out, repository):
    # Reconstruct selection from checksummed training trajectories, not prior model answers.
    states, _ = prepare_motion(source, out, repository)
    programs = programs_for(repository)
    write_json(out / "programs.json", programs)
    write_json(out / "provenance.json", provenance(repository, states))
    validate_pack(out, repository)
    return states, programs


def screen(report):
    """Predeclared descriptive screen; it neither promotes nor launches a policy."""
    metrics = {(r["program"], r["stratum"]): r for r in report["metrics"]}
    rule = "lookahead-conservative"

    def meets(stratum, threshold):
        row = metrics[("compact", stratum)]
        return row["responses"] == 16 and row["states"] == 8 and row["agreement"][rule] >= threshold

    compact, expanded = (metrics[(p, "all")] for p in ("compact", "expanded"))
    complete = report["status"] == "complete" and report["completed_predictions"] == 480
    difference = (
        compact["agreement"][rule] - expanded["agreement"][rule]
        if compact["responses"] and expanded["responses"]
        else None
    )
    checks = {
        "complete_schedule": complete,
        "overall_at_least_80_percent": compact["responses"] == 160
        and compact["agreement"][rule] >= 0.8,
        "overall_gain_at_least_10_points": difference is not None and difference >= 0.1 - 1e-12,
        "missing_objects_all_correct": meets("missing", 1.0),
        **{f"{s}_at_least_75_percent": meets(s, 0.75) for s in STRATA if s != "missing"},
    }
    return {
        "kind": KIND,
        "status": "eligible-for-separate-study-design" if all(checks.values()) else "not-eligible",
        "primary_contrast": "Compact minus freshly evaluated expanded conservative-rule agreement",
        "overall_difference": difference,
        "checks": checks,
        "limits": "Descriptive thresholds on reused training states, not significance, "
        "optimality, policy promotion or authorization for gameplay calls.",
    }
