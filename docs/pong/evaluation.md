# Pong evaluation profile

Profile ID: `pong-evaluation-v1`, documented 2026-09-18. This is the game-specific
interpretation of the [shared framework](../evaluation-framework.md), not a frozen
configuration for the next live run. Each study must still declare its seeds,
caps, budgets, repetitions, endpoint and selection threshold before evaluation.
The [research endpoint](research-endpoint.md) defines the teacher-improvement and
feedback-benefit milestones, current evidence status and proposed finite stopping rule.

## Environment and outcome contract

Use the pinned `ALE/Pong-v5` environment. Record mode/difficulty, ROM identity,
RAM/object or RGB adapter, observation history, sticky-action probability, action
duration and reset behavior. Current controlled studies use RAM-derived objects,
mode 0, difficulty 0, sticky probability 0.25 and a four-raw-frame action duration.
Historical setup differences must remain explicit.

Keep all six native action options. In this Pong configuration, RIGHT requests
upward paddle movement and LEFT downward movement. The question may express a
preference for non-FIRE actions; the runtime must not silently mask the other options.
Keep probability argmax and its documented tie handling fixed during a question-only
comparison. See the [observation contract](../observation.md).

The observed reward is +1 for scoring and -1 for conceding. A native match ends
when either side reaches 21. See the [benchmark reference](../pong-benchmark.md)
for the pinned source and comparison limits. Teacher reflections, confidence and
estimated paddle contacts do not change this reward.

## Endpoints by study type

| Study | Outcome to declare before running | Required companion reporting |
| --- | --- | --- |
| Direct-policy question update | Paired difference in capped episodic return under a shared horizon, or a separately specified native-match endpoint | Scored/conceded points, per-seed outcomes, completion and failures |
| Native-match performance | Full-match return and win rate with explicit denominators | Scheduled/started/completed counts, unfinished games and cap returns |
| Fixed-state question probe | Argmax flips and action-distribution change on identical inputs | Repeated old/old noise, situation counts, invalid responses; no gameplay claim |
| Value-question prediction | Brier score, value MAE and observed-branch decision regret under a defined label target | Horizon, continuation, informative roots, censoring; separate online validation |
| Teacher optimizer | Selected-policy improvement versus cumulative budget over independent optimization runs | Frozen baseline, no-feedback control, rejected proposals and all costs |

The existing value pilot predicts the first point within 240 raw frames, with the
candidate action applied for four frames and a fixed tracking controller afterward.
Its Brier/MAE gate does not apply to the direct-action policy. Likewise, the original
direct pilot's five-point completion gate is not the selector for native-match
studies. A new selector must be explicitly specified rather than inheriting one by name.

## Completion, failure and inference

At a frame cap, report the score as unfinished even when the player leads. A zero
short-run reward can mean no point occurred; it does not mean a draw. Preserve API
failure prefixes and their costs without treating them as complete evaluation
episodes. Distinguish an experiment finishing its planned cap from a game finishing.

Show per-seed paired differences and uncertainty at independent seed/run level.
Do not pool full matches, capped episodes and first-point branches into one score.
For wins, report both the completed-game denominator and all scheduled games with
unknown outcomes identified. Reused historical baselines must be labeled.

Diagnostic situation categories may include approaching/departing balls, near
paddle contact, overshoot, missing observations and small/large vertical gaps.
Their extraction rules and thresholds must be frozen before a confirmatory probe.
Four-pixel rule agreement tests adherence to that rule, not strategic optimality.

## Mastery and transfer

No mastery threshold has been adopted or met. A future claim requires a predeclared
target win rate or return, sufficient complete matches, independent evaluation and
explicit uncertainty. Atari-wide comparisons must use each game's own profile;
Pong's point events, 21-point endpoint and tracking diagnostics are not generic
Atari metrics. Keep final-test evidence out of teacher input and selection.
