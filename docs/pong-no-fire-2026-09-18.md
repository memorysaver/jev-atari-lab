# No-FIRE question follow-up — 2026-09-18

The no-FIRE v3 question achieved **-5 aggregate net reward**, versus
**-3** for the historical v2 question, across four 2,000-frame development
episodes. These are short episodes, not full matches. The candidate is **not promoted**.

## What changed

The [exact proposal](../experiments/no-fire-question-proposal.json) changes only
the guidance and version name. It explains FIRE button combinations and explicitly
requests RIGHT/up, LEFT/down, or NOOP/no movement. All six native actions remain
selectable, including FIRE variants. The 4px guidance, object observations, criteria,
probability-argmax decoder and Jev `jev-1.13.0` stay unchanged. There is no mask or
confidence fallback. This is a manual question edit after development feedback,
not a train-only teacher learning round or a weight update.

The [frozen protocol](no-fire-rerun-protocol.md) and runner were committed as
`5be5e06b6ed317d992deef0f5b8fea867eec6b16`. The v2 baseline is reused from the
[prior comparison](pong-controls-2026-09-18.md), not freshly sampled alongside v3.
Model sampling and changed trajectories can affect differences. These seeds have
already been inspected and are not an independent test set.

## Every seed

Cells are points scored / conceded over 2,000 raw frames (500 decisions).
The final column is v3 minus v2 net reward.

| Seed | Historical v2 | No-FIRE v3 | Net change |
| --- | ---: | ---: | ---: |
| 36 | 0 / 2 | 3 / 4 | +1 |
| 37 | 1 / 2 | 0 / 0 | +1 |
| 46 | 2 / 0 | 0 / 3 | -5 |
| 47 | 0 / 2 | 1 / 2 | +1 |
| **Aggregate return** | **-3** | **-5** | **-2** |
| **Mean short-episode return** | **-0.75** | **-1.25** | **-0.50** |

See [what counts as better Pong performance](pong-benchmark.md) for full-match
scoring and evaluation limits. No full-match win rate is inferred from these clips.

The per-seed changes were +1, +1, -5, and +1. Three small gains did not offset
the larger regression on seed 46. This sample does not establish a reliable
advantage for either wording.

## Behavior and confidence

Each column covers 2,000 decisions on that policy's own visited states, rather than
matched input states. Threshold counts are descriptive and do not gate actions.

| Diagnostic | Historical v2 | No-FIRE v3 |
| --- | ---: | ---: |
| NOOP fraction | 65.00% | 63.80% |
| FIRE variants | 0 | 0 |
| 4px rule agreement | 66.85% | 70.15% |
| Mean confidence | 0.5786 | 0.6087 |
| Confidence < 0.3 | 56 | 23 |
| Confidence < 0.5 | 844 | 763 |
| Mean top-two probability margin | 0.4148 | 0.4491 |
| Top-two margin < 0.1 | 283 | 246 |

Mean confidence rose from 0.5786 to 0.6087 and rule agreement from 66.85% to
70.15%, while aggregate return fell from -3 to -5. Better-looking diagnostics did
not translate into a better aggregate score in this sample.

Confidence is not a measured probability of winning or choosing an optimal action.
Rule agreement measures execution of a written heuristic, not its strategic quality.
Both the old comparison and this question retain the full action set; any improvement
cannot automatically be attributed to eliminating FIRE choices that were already absent.

## Interruption, continuation, and costs

The first run completed seeds 36 and 37. On seed 46, the 1,088th HTTP attempt
failed at the transport layer after about 60 seconds, before another action executed.
Its 87 decisions / 348 frames remain an incomplete prefix. Seed 47 was not started
in that run. No zero-reward tail or full-horizon score was invented for the failure.

A [separate continuation plan](../experiments/pong-no-fire-continuation-plan.json)
restarted seed 46 from its original reset and then ran seed 47 with an unchanged
program/protocol. Its cap was the remaining 1,112 attempts. The original plan stopped
on error as specified; restarting in another run is an explicitly recorded procedural
deviation. Exchange IDs are local to each run and must be read with the run path.
The prefix is excluded from fixed-horizon scores and retained in costs and replay.

Combined use: **2089 / 2,200 HTTP attempts**, including the failed
request and restarted prefix. The continuation also encountered one HTTP 529
response and retried the same request within its budget. HTTP status counts: `{"200": 2087, "529": 1, "transport_error": 1}`.
Provider-reported usage totals **3,625,672 input tokens** and
**143,259 output tokens** across successful responses;
a failed request may have unreported provider billing. Summed HTTP time was
**613.169 seconds**. No billing endpoint or teacher API was used.
Each completed video contains 33.33 seconds of simulation, excluding API waits.

## Evidence and replay

[Watch seed 36](media/pong-no-fire-v3-seed-36.mp4), the first predeclared seed.
The [results index](../experiments/pong-no-fire-study-results.json) contains all
selected episodes, the interrupted prefix, diagnostics, costs and audit results.
The [LFS archive](../experiments/pong-no-fire-study-2026-09-18.tar.gz) contains both
original run directories, all five videos including the interrupted prefix, original
request/response bodies, frames, trajectories, ledgers, question versions, the
continuation plan and audits. Its
[manifest](../experiments/pong-no-fire-study-2026-09-18.manifest.json) checks every file.
The creation-time proposal record and previous published archives remain unchanged.

All four complete episodes and the failed prefix passed emulator replay. Every
successful model exchange matched its saved program and observation and decoded
to the recorded action. The failed request matched the next unexecuted state.
Per-run exchange IDs and ledgers reconciled. Offline auditing makes no API calls.

```bash
git lfs pull
uv run python scripts/restore_experiments.py \
  --manifest experiments/pong-controls-v1-2026-09-18.manifest.json \
  --out restored-controls
uv run python scripts/restore_experiments.py \
  --manifest experiments/pong-no-fire-study-2026-09-18.manifest.json \
  --out restored-no-fire
uv run python scripts/verify_no_fire.py \
  --source restored-no-fire/pong-no-fire-study \
  --baseline restored-controls/pong-controls-v1 \
  --out artifacts/no-fire-audit
```
