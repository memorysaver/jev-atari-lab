# Pong fixed-frame controls — 2026-09-18

The existing vertical-control Jev question achieved **-3 net reward**, compared
with **-14 for the literal 4px Python rule**, **-15 for the 2px Python rule**, and
**-52 for the original Jev question**, across four development seeds with equal
2,000-frame horizons. The Jev candidate matched the literal 4px rule on only
**66.85% of its decisions**. Better aggregate play therefore does not mean exact
execution of the written rule.

This is a controlled comparison of existing policies, not a new teacher round.
No question was revised, no weights were updated, and no final-test seeds were used.

## Frozen design

The [protocol](pong-controls-protocol.md) and implementation were committed as
`c415207e8061762abe280c1832c56df987c022d2` before live execution.
The [saved plan](../experiments/pong-controls-v1-plan.json) contains exact programs,
hashes, schedule, dependency versions, ROM hash and the shared 4,400-attempt budget.

All arms used seeds 36, 37, 46 and 47; RAM object observations; action hold 4;
sticky actions 0.25; Jev `jev-1.13.0`; and 500 decisions per episode. There was no
five-point cutoff. All 16 episodes reached 2,000 controlled raw frames, with no
native termination, environment truncation or absorbing tail. Reset NOOPs were
accounted for separately. Jev's execution order alternated by seed.

The state contains bounding boxes and history, not a precomputed center gap or
recommended action. The 4px question asks Jev to calculate center y and compare
the gap; the Python arm performs that calculation directly on the same fields.

## Results

Each cell below is **points scored / points lost**, not a full-match score.

| Seed | Original Jev | Vertical Jev | Python 4px | Python 2px |
| --- | ---: | ---: | ---: | ---: |
| 36 | 0 / 13 | 0 / 2 | 0 / 4 | 0 / 7 |
| 37 | 0 / 13 | 1 / 2 | 1 / 1 | 1 / 2 |
| 46 | 0 / 13 | 2 / 0 | 0 / 8 | 0 / 4 |
| 47 | 0 / 13 | 0 / 2 | 2 / 4 | 0 / 3 |
| **Total** | **0 / 52** | **3 / 6** | **3 / 17** | **1 / 16** |
| **Net reward** | **-52** | **-3** | **-14** | **-15** |

Each arm executed 8,000 controlled frames and 2,000 decisions. Vertical Jev's
per-seed net-reward differences from Python 4px were **+2, -1, +10, 0**: two wins,
one loss and one tie. Most of the aggregate advantage came from seed 46.
Python 4px improved over Python 2px by just one net point overall, with a large
regression on seed 46. These observations do not establish a universally better
deadband or a statistically reliable Jev advantage.

The full [machine-readable results](../experiments/pong-controls-v1-results.json)
include per-episode costs, control diagnostics and paired differences.

## The question is not an exact executable rule

Evaluating Python's 4px rule on each Jev-visited state gives:

| Seed | Matching decisions | Agreement |
| --- | ---: | ---: |
| 36 | 329 / 500 | 65.8% |
| 37 | 362 / 500 | 72.4% |
| 46 | 320 / 500 | 64.0% |
| 47 | 326 / 500 | 65.2% |
| **Total** | **1,337 / 2,000** | **66.85%** |

Post-hoc inspection classified the 663 disagreements: 612 were Jev requesting
NOOP when the rule requested movement, 49 were movement inside the rule's hold
band, and two were the opposite movement direction. This describes behavior;
it does not identify model intent, arithmetic errors, or the causal value of waiting.
No counterfactual rollouts were performed.

The [first disagreement in seed 36](../experiments/pong-controls-v1-decision-15.json)
preserves the original model input and output. At decision 15, the observed ball
center was 129.0 and paddle center 144.5: gap -15.5px. The literal rule requests
RIGHT/up, but Jev assigned NOOP probability 0.43 and RIGHT probability 0.34.
Probability argmax selected NOOP. Its next four frame rewards were all zero,
which does not establish which action had better future value.

The decoder was unchanged. Three candidate and two original-policy responses had
a provider `choice` that disagreed with probability argmax; the predeclared decoder
used the validated probabilities and retained the original response. These five
cases are distinct from the much larger rule-adherence difference.

## Cost

| Arm | HTTP attempts | Input tokens | Output tokens | Summed HTTP seconds |
| --- | ---: | ---: | ---: | ---: |
| Original Jev | 2,000 | 2,953,317 | 136,760 | 514.985 |
| Vertical Jev | 2,000 | 3,368,371 | 137,298 | 514.702 |
| Both Python arms | 0 | 0 | 0 | 0 |
| **Total** | **4,000** | **6,321,688** | **274,058** | **1,029.687** |

All 4,000 requests returned HTTP 200 and valid pinned-model predictions. There
were no retries, failures, paid diagnostics or teacher requests; 400 permitted
attempts remained unused. Provider billing was not queried. Total experiment
emulation was 32,000 controlled frames plus 132 reset frames; verification replay
work is separate. Each video shows 33.33 seconds of simulation, excluding API waits.

Both Python arms completed their four recorded episodes in about 2.7–2.8 seconds
each on this machine, including logging/video. Jev's additional API cost buys
better aggregate reward in this sample, not a compute-efficiency advantage over
the handwritten controls. No server-side compute claim is made.

## Videos and preserved evidence

These videos all use **seed 36, the first predeclared seed**, rather than selecting
the candidate's highest-scoring episode:

- [Original Jev](media/pong-controls-v1-jev-original-seed-36.mp4).
- [Vertical Jev](media/pong-controls-v1-jev-vertical-seed-36.mp4).
- [Python 4px](media/pong-controls-v1-python-4px-seed-36.mp4).
- [Python 2px](media/pong-controls-v1-python-2px-seed-36.mp4).

The [LFS archive](../experiments/pong-controls-v1-2026-09-18.tar.gz) preserves all
16 videos, every decision input/output, every controlled frame, exact question
programs, ledgers, diagnostics, and verification records. Its
[manifest](../experiments/pong-controls-v1-2026-09-18.manifest.json) records every
member's SHA-256. No original experiment artifact was overwritten.

All 16 episodes passed independent emulator replay with matching observations,
rewards and raw RAM/RGB hashes. All 4,000 captured exchanges matched the saved
program/state, and decoded to the recorded actions. The global exchange IDs and
per-episode ledgers reconciled. Auditing made no API requests.

```bash
git lfs pull
uv run python scripts/restore_experiments.py \
  --manifest experiments/pong-controls-v1-2026-09-18.manifest.json \
  --out restored-controls
uv run python scripts/verify_controls.py \
  --run restored-controls/pong-controls-v1 --out artifacts/controls-audit
```

## What this supports next

The vertical question has a useful short-run control signal relative to the weak
original question and the two tested handwritten controls. However, the policy
actually executed by Jev differs substantially from the literal rule. A future
study should separate instruction execution from experience-driven improvement,
retain a stronger handwritten control, and use fresh test seeds and repeated runs.

The planned teacher-learning study must use an isolated train-only context and
compare experience-based revisions with an equal-proposal-budget control without
trajectory feedback. This run establishes neither that learning loop nor TD/value
learning. The original value-based track remains a separate research objective.
