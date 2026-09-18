# Online direct-policy pilot — 2026-09-18

A guidance revision based on training failures produced much better short-run defense:
the original direct policy lost five points quickly on both development seeds; the
candidate survived 500 decisions on each, with one point scored and none lost in total.
Neither candidate episode reached the predeclared five-point stopping target, so the
automatic gate did not promote it. This is promising control evidence, not a completed
match benchmark or proof of reinforcement-learning convergence.

## Design fixed before development

- Jev `jev-1.13.0`, RAM observations/history, sticky 0.25, four raw frames per action.
- All six original ALE actions remain available. Jev chooses every action itself;
  there is no heuristic continuation or fallback during a model episode.
- Baseline training seeds 20/21; compare baseline and one candidate on development
  seeds 26/27. No final-test episodes were used.
- Each episode stops after five scored/lost point events or 500 decisions, whichever
  comes first. End reasons and actual raw frames are recorded separately.
- Only the policy name/guidance can change. No sensor, action-option, hold-duration,
  model-weight or reward changes. One candidate was frozen before development feedback.
- The gate requires all paired episodes to complete five-point windows, total net
  reward improvement of at least two, and no per-seed reward regression.
- Combined HTTP cap: 2,000. Unused training allowance was reassigned to development
  without increasing that cap. All failed requests and diagnostics count.

The current implementation and report are committed together. Local records are under
`artifacts/policy-online-v1/`, including the plan, train feedback, proposal provenance,
API ledgers, episode traces, videos, audited baseline and final selection.

## What training revealed

Baseline seed 20 lost five points after 198 decisions; seed 21 did so after 202.
Both scored zero. In many observations the ball was far below the paddle, yet the
model requested action `RIGHT`, which actually moves the paddle UP in Atari Pong.
The paddle often remained at the top of the screen. Confusion between player side,
joystick labels and vertical direction is a plausible explanation, not a proven
mechanistic account of the model.

The interactive assistant used only these training trajectories to write
[vertical-policy-program.json](../examples/vertical-policy-program.json). Its core rule:

- Compare ball and player bounding-box center y; larger y means lower on the screen.
- Ball more than four pixels below: request `LEFT` to move DOWN.
- Ball more than four pixels above: request `RIGHT` to move UP.
- Within four pixels or missing ball/player: request `NOOP`.
- The player's right-side location and horizontal ball motion do not determine the
  vertical action. Prefer non-FIRE options when they have the same movement effect.

The rule is expressed in the question, not an action override in Python. It resembles
the already available tracking heuristic, whose deadband is two pixels. This is a
teacher-authored policy rule informed by failures, not discovery of a novel strategy
or a policy-gradient update. The external teacher API was not used.

## Actual development episodes

[Watch or download the Jev candidate replay (MP4)](media/jev-vertical-policy-seed-27.mp4).
This is development seed 27 using `jev-1.13.0` and the vertical-control question:
500 decisions, 2,000 raw frames, one point scored and none lost. The right paddle is
controlled by Jev's action probabilities. Playback is approximately 33.3 seconds at
60 simulation frames per second; API waiting time is excluded. The episode ends at
the decision cap, not at the end of a full match. This curated copy is identical to
the local `development-candidate-resumed/seed-27/replay.mp4` artifact.

The same episode limits apply to all policies; the different stopping times below
must remain visible. Scores are player points / points lost, not complete match scores.

| Policy | Seed | Scored / lost | Decisions | Raw frames | Stop reason | Estimated right-paddle returns |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| Original direct Choice | 26 | 0 / 5 | 198 | 790 | Five points | 0 |
| Original direct Choice | 27 | 0 / 5 | 204 | 816 | Five points | 0 |
| Vertical-control candidate | 26 | 0 / 0 | 500 | 2,000 | Decision cap | 8 |
| Vertical-control candidate | 27 | 1 / 0 | 500 | 2,000 | Decision cap | 7 |
| Local tracking heuristic | 26 | 0 / 1 | 500 | 2,000 | Decision cap | 7 |
| Local tracking heuristic | 27 | 0 / 5 | 324 | 1,296 | Five points | 2 |

Raw frames exclude reset no-ops in this table. Returns are inferred from rightward-to-
leftward ball velocity changes near the right paddle; they are a diagnostic proxy and
may miss contacts. They are not reward shaping or an official ALE collision counter.

Across visible-ball development decisions, baseline movement opposed the instantaneous
vertical gap on 181 of 254 decisions; candidate movement did so on 0 of 960. This helps
explain adherence to the requested tracking rule. It is not a universal correctness
metric: an anticipatory interception policy can intentionally oppose the current gap.

The candidate has a positive short-run signal on both development seeds and scored a
point on seed 27. Two seeds and unequal completed point windows cannot establish a
general win-rate improvement or sample efficiency. A fixed-duration paired comparison
and longer games are appropriate next experiments.

## Gate outcome

`select-policy` returned `accepted=false`, solely for `incomplete_point_windows`.
The candidate reached the 500-decision cap with fewer than five point events in both
episodes. Its observed net rewards were higher, but the predeclared completion condition
was not satisfied. The threshold was not relaxed after seeing the result, and the
default question program was not replaced. The candidate remains explicitly runnable
with `--program examples/vertical-policy-program.json`.

## Provider inconsistency and recovery

The initial training run stopped after 85 executed decisions because a response failed
Choice validation; that exact response was not retained. Three diagnostic requests for
the same state passed. Floating-point tail values were observed, so numerical ties now
allow 1e-12 error, and bounded numeric diagnostics were added to failure ledgers.

A later candidate response established a separate, larger inconsistency: the provider
returned `choice=NOOP` with P(NOOP)=0.46, while P(LEFT)=0.47. This exceeds floating-point
tie error. For direct policies the client now selects the maximum of the validated
probability distribution, retaining the provider's choice on numerical ties. It records
the original choice and a disagreement flag instead of silently treating it as argmax.
Unknown options and malformed distributions still stop execution. The categorical
critic's strict choice validation was not changed in this pilot.

All 402 already executed development-baseline actions were audited and found to satisfy
the new probability selection rule; an `audited-suite.json` preserves that fact without
overwriting the original suite. Accepted trajectory prefixes were replayed from their
original seeds, checking observations, program, pinned model and actions at every step.
This retained 85 training and 187 candidate predictions without paying for them again.
The candidate's guidance remained fixed. Four subsequent candidate decisions had a
provider-choice discrepancy resolved by the probability rule and recorded in the trace.

## Cost and validation

- Actual HTTP attempts: **1,807**, all HTTP 200: 1,802 action predictions, two rejected
  responses, and three diagnostics. Failed/diagnostic work is included; no cap expansion.
- Provider-reported tokens: **2,881,301 input / 123,809 output**.
- Summed HTTP wall time: **529.326 seconds**. Billing was not queried.
- Emulator work: **15,544 raw frames**, including reset no-ops, local baselines and
  replayed prefixes. Do not confuse this total with the duration of one episode.
- **60 tests passed**, covering point stopping, split restrictions, per-episode ledgers,
  verified prefix replay, numerical ties, provider-choice disagreement, sanitized failure
  diagnostics and the observation-derived return counter.

## Run the candidate

```bash
uv run --env-file "$HOME/.config/typesafe/credentials.env" jev-atari policy-suite \
  --policy jev-action --program examples/vertical-policy-program.json \
  --seeds 26 27 --model jev-1.13.0 --max-api-calls 1050 \
  --decisions 500 --point-limit 5 --video --out artifacts/vertical-policy-repro
```

Use a fresh output path. To compare programs, collect baseline and candidate suites
with the same explicit settings and run `select-policy --baseline .../suite.json
--candidate .../suite.json --out ...`. The full plan and intermediate evidence are
preserved locally. The prompt hash is:

```text
2ef87250f491fcd5a2ba72f29e3f03b6bc66c4ab7315e9e724df76352326633d
```
