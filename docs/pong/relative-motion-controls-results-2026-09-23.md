# Relative-motion literal controls: 2026-09-23

The teacher-inspired Python relative-motion rule improved mean capped return by
**+1.5** over current-center tracking on eight fresh training seeds. Results were
mixed: four gains, two ties and two regressions. All 32 episodes reached the
2,000-frame cap; **zero native matches completed**. This is a local strategy
diagnostic, not Jev improvement, a teacher-policy promotion or final-test evidence.

[Frozen protocol](relative-motion-controls-protocol.md) ·
[Reviewed local evidence](../../experiments/pong/relative-motion-controls-v1/README.md).

## Observed results

Cells show points scored:lost and capped return in parentheses. The four rules
share original observations, sticky actions 0.25, a four-frame hold and a four-pixel
deadband. Relative forecasts use two raw frames for both ball and player; the
ball-only ablation omits player forecasting. The unguarded variant omits the
ambiguous bounce-history fallback. All planned seeds and arms are shown.

| Seed | Track | Ball only | Relative | Unguarded relative | Relative gain |
| --- | ---: | ---: | ---: | ---: | ---: |
| 130 | 0:3 (-3) | 1:0 (+1) | 2:0 (+2) | 2:0 (+2) | +5 |
| 131 | 0:5 (-5) | 1:1 (+0) | 0:0 (+0) | 0:0 (+0) | +5 |
| 132 | 1:1 (+0) | 1:4 (-3) | 1:1 (+0) | 0:2 (-2) | +0 |
| 133 | 1:4 (-3) | 0:1 (-1) | 2:0 (+2) | 0:3 (-3) | +5 |
| 134 | 2:1 (+1) | 1:1 (+0) | 2:0 (+2) | 2:0 (+2) | +1 |
| 135 | 1:0 (+1) | 3:3 (+0) | 1:0 (+1) | 2:0 (+2) | +0 |
| 140 | 2:2 (+0) | 2:1 (+1) | 2:3 (-1) | 1:2 (-1) | -1 |
| 141 | 3:0 (+3) | 0:1 (-1) | 1:1 (+0) | 0:1 (-1) | -3 |

| Rule | Mean capped return | Mean paired gain over track |
| --- | ---: | ---: |
| track-4 | -0.750 | 0 |
| ball-lookahead-2 | -0.375 | +0.375 |
| relative-lookahead-2 | +0.750 | +1.500 |
| relative-unguarded-2 | -0.125 | +0.625 |

Relative motion exceeded ball-only forecasting by +1.125 on average. Keeping the
bounce guard exceeded its unguarded sensitivity arm by +0.875. These are descriptive
comparisons on the same eight training seeds, with no inferential claim. In
particular, relative motion regressed by -1 and -3 on seeds 140 and 141. Better
mean return here does not establish robust improvement across seeds or horizons.

## Provenance, cost and interpretation

The running criteria study's isolated C1-R2-A teacher authored
`pong-relative-motion-lookahead-v1`. Its original validated proposal is preserved
in the evidence. The coordinator subsequently wrote these explicit Python
interpretations, including a declared sensitivity analysis of ambiguous bounce
wording. They are not extra isolated teacher proposals. Source and protocol were
committed at `82ab2b3ffa03fbed56bb897db1fbef966ad1a5c5` before any local rollout.

Training seeds 130,131,132,133,134,135,140,141 were checked unused locally and do
not overlap the running criteria study. Rule order rotates across seeds. The run
used **64,000 controlled raw frames, 16,000 controller decisions, 32 videos and
zero Jev or teacher calls**; reset frames are separate in each episode summary.
All native-match completion rates are 0/8; completed-match win rates are undefined.

An offline audit replayed all 32 trajectories, checked original observations,
frames and rewards, recomputed each rule's action and diagnostic prediction, and
reconstructed aggregates. Results and an audit receipt are preserved with the
archive. A separate SHA-256-checked restoration and full replay of the extracted
archive also passed. This is local verification; no remote push or retrieval occurred.

The rule's short forecast plausibly helps brake paddle motion, but this study
does not isolate every mechanism: approximate ball bounds, clipped player boxes,
velocity uncertainty and sticky actions remain. Different actions create different
subsequent states. Comparing these returns with Jev's different development seeds
cannot establish a causal execution deficit. No significance, generalized benefit,
native-win or solved-game claim follows.

These results stay outside the current criteria-study teacher packets. That study
continues under its original frozen selector and final-test protocol. A future
study may investigate this mechanism prospectively after the current study ends.
