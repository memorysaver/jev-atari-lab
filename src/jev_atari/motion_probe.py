"""Training-only, stratified fixed-input Jev diagnostics with a durable call cap."""

import hashlib
import json
import time
from collections import Counter
from pathlib import Path

from jev_atari.choice import ActionProgram
from jev_atari.io import digest, new_directory, read_json, write_json
from jev_atari.models import BudgetExceeded
from jev_atari.question_diagnostics import RULES, interpret

MODEL = "jev-1.13.0"
LIMIT = 520
STRATA = (
    "missing",
    "unknown-motion",
    "outgoing",
    "stationary-x",
    "incoming-uncertain-conflict",
    "incoming-uncertain-same",
    "incoming-stable-conflict",
    "incoming-stable-same-up",
    "incoming-stable-same-down",
    "incoming-stable-same-hold",
)
PRECISE = ActionProgram(
    name="pong-explicit-motion-reliability-v1",
    guidance=(
        "Choose the next action for the player paddle. Read player and ball in "
        "observation.objects. "
        "A bbox is [x,y,width,height]; center_y=y+height/2. Larger y means down. "
        "If either bbox is missing, choose NOOP. Initially target=current ball center_y. "
        "Use a four-raw-frame lookahead ONLY if all these conditions hold: "
        "(1) ball.velocity_valid is true and ball.velocity=[vx,vy] is known in pixels "
        "per raw frame; "
        "(2) vx>0, toward the player; "
        "(3) the last THREE observation.history samples each have a visible ball bbox and strictly "
        "increasing offset_raw_frames; "
        "(4) for BOTH x and y, the two consecutive position changes across those three samples "
        "have a nonnegative product. A negative product means a direction reversal. "
        "Zero is allowed. "
        "If any condition fails or is unknown, keep target=current ball center_y. "
        "If all hold, target=current ball center_y+vy*4. Do not multiply by the history sample "
        "interval again; the supplied velocity is already per raw frame. Do not predict further "
        "ahead or add wall reflection. "
        "Compute gap=target-player center_y. If gap < -4 choose RIGHT (UP). "
        "If gap > 4 choose LEFT (DOWN). Otherwise choose NOOP. "
        "These action names have vertical effects in Pong. Horizontal direction only gates "
        "lookahead; it does not select UP or DOWN. Prefer the non-FIRE action for the same "
        "vertical movement. Act for four frames, then reconsider the new observation."
    ),
)


def classify(observation):
    base = interpret(observation, "v2")
    short = interpret(observation, "lookahead")
    safe = interpret(observation, "lookahead-conservative")
    if base["mode"] == "missing-object":
        return "missing"
    if base["motion"] == "unknown":
        return "unknown-motion"
    if base["motion"] in ("outgoing", "stationary-x"):
        return base["motion"]
    if safe["mode"] != "lookahead":
        return "incoming-uncertain-" + ("conflict" if short["action"] != safe["action"] else "same")
    if base["action"] != safe["action"]:
        return "incoming-stable-conflict"
    return "incoming-stable-same-" + {0: "hold", 2: "up", 3: "down"}[safe["action"]]


class ProbeBudget:
    """Reserve before transmission. Existing output is never restarted or reset."""

    max_calls = LIMIT

    def __init__(self, path, clock=time.time):
        if path.exists():
            raise ValueError("Budget already exists")
        self.path, self.clock, self.used, self.started_at = path, clock, 0, None
        self.save()

    def save(self):
        write_json(
            self.path,
            {
                "max_calls": LIMIT,
                "used": self.used,
                "started_at": self.started_at,
                "live_seconds": 14400,
            },
        )

    def reserve(self):
        now = self.clock()
        if self.used >= LIMIT or self.started_at is not None and now - self.started_at >= 14400:
            raise BudgetExceeded("Motion probe attempt or four-hour limit reached")
        if self.started_at is None:
            self.started_at = now
        self.used += 1
        self.save()


def prepare(source: Path, out: Path, repository: Path):
    new_directory(out)
    manifest = read_json(
        repository
        / "experiments/pong/question-diagnostics-v1/question-diagnostics-v1.manifest.json"
    )
    checksums = {f["path"]: f["sha256"] for f in manifest["files"]}
    sources, unique, selected = {}, {}, {s: {} for s in STRATA}
    for rule in RULES:
        for seed in (80, 81, 82, 83):
            folder = Path(rule) / f"seed-{seed}"
            paths = [folder / "manifest.json", folder / "transitions.jsonl"]
            for rel in paths:
                raw = (source / rel).read_bytes()
                sha = hashlib.sha256(raw).hexdigest()
                if sha != checksums[f"question-diagnostics-v1/local/{rel}"]:
                    raise ValueError("Source does not match published training archive")
                sources[str(rel)] = sha
            meta = read_json(source / paths[0])
            if meta["seed"] != seed or meta["split"] != "train":
                raise ValueError("Non-training source")
            with (source / paths[1]).open() as stream:
                for line in stream:
                    row = json.loads(line)
                    obs = row["observation"]
                    key = digest(obs)
                    if key in unique:
                        continue
                    stratum = classify(obs)
                    unique[key] = stratum
                    bucket = selected[stratum]
                    if len(bucket) < 8 or key < max(bucket):
                        bucket[key] = {
                            "id": key,
                            "stratum": stratum,
                            "observation": obs,
                            "source": str(paths[1]),
                            "seed": seed,
                            "decision": row["decision"],
                            "rule_actions": {r: interpret(obs, r)["action"] for r in RULES},
                        }
                        if len(bucket) > 8:
                            del bucket[max(bucket)]
    states = [selected[s][key] for s in STRATA for key in sorted(selected[s])]
    old = read_json(
        repository / "experiments/pong/teacher-study-v1/records/round-01/B/question-changes.json"
    )["after"]
    programs = {
        "v2": read_json(repository / "examples/vertical-policy-program.json"),
        "ambiguous": old,
        "precise": PRECISE.to_dict(),
    }
    coverage = {
        "unique_training_states": len(unique),
        "pool_counts": dict(Counter(unique.values())),
        "selected_counts": dict(Counter(s["stratum"] for s in states)),
        "hash_uniform_32_counts": dict(Counter(unique[k] for k in sorted(unique)[:32])),
        "limits": "Stratification intentionally changes state frequencies. Missing "
        "strata are not backfilled.",
    }
    write_json(out / "inputs.json", states)
    write_json(out / "programs.json", programs)
    write_json(out / "coverage.json", coverage)
    write_json(
        out / "provenance.json",
        {
            "source_archive_sha256": manifest["sha256"],
            "source_files": sources,
            "proposal_author": "Interactive coordinator; has seen prior development results.",
            "proposal_kind": "Manual operationalization, not an isolated teacher or "
            "learned update.",
            "hypothesis": "Explicit reliability tests may increase agreement with the "
            "conservative rule, especially when recent motion reverses.",
            "limits": "Action agreement is not optimality or gameplay return. No "
            "promotion or final access.",
        },
    )
    return states, programs


def schedule(states, programs):
    names = list(programs)
    result = []
    for i, state in enumerate(states):
        for repeat in range(2):
            offset = (i + repeat) % len(names)
            for name in names[offset:] + names[:offset]:
                result.append({"id": state["id"], "program": name, "repeat": repeat})
    return result


def summarize(states, programs, rows):
    lookup = {s["id"]: s for s in states}
    results = []
    for name in programs:
        for stratum in ("all", *STRATA):
            subset = [
                r
                for r in rows
                if r["program"] == name
                and (stratum == "all" or lookup[r["id"]]["stratum"] == stratum)
            ]
            targets = {
                rule: sum(
                    r["prediction"]["chosen_action"] == lookup[r["id"]]["rule_actions"][rule]
                    for r in subset
                )
                for rule in RULES
            }
            pairs = {}
            for row in subset:
                pairs.setdefault(row["id"], {})[row["repeat"]] = row["prediction"]["chosen_action"]
            complete = [v for v in pairs.values() if len(v) == 2]
            results.append(
                {
                    "program": name,
                    "stratum": stratum,
                    "responses": len(subset),
                    "states": len(pairs),
                    "matches": targets,
                    "agreement": {
                        r: n / len(subset) if subset else None for r, n in targets.items()
                    },
                    "repeat_pairs": len(complete),
                    "repeat_action_flips": sum(v[0] != v[1] for v in complete),
                }
            )
    return results
