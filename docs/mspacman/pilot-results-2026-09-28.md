# Ms. Pac-Man pilot: local calibration completed, model comparison interrupted

Observed on 2026-09-28. [Calibration protocol](calibration-protocol.md) was frozen
at `ef3be18`; [live protocol](pilot-protocol.md) and exact questions at `fa721b6`.
The owner authorized a small pilot. No isolated teacher was invoked.

## Local strategy and observation calibration

Six episodes used training seeds 510/511, sticky probability 0.25, eight-frame
actions, a 272-frame NOOP prefix and up to 4,096 controlled raw frames.
Native rewards during the prefix are reported separately in the original records.

| Local controller | Seed 510 return | Seed 511 return | Mean | Life losses (510/511) |
| --- | ---: | ---: | ---: | --- |
| Random native actions | 300 | 300 | 300 | 3 / 3 |
| Pellet pursuit | 730 | 550 | 640 | 3 / 3 |
| Pellet pursuit with nearby-ghost avoidance | 1760 | 700 | 1230 | 1 / 3 |

Five games ended natively. Ghost-aware seed 510 reached the cap with one lost
life. This is an observed local strategy contrast on two starts, not proof of
mastery, sustainable survival or a model improvement. The score can include
rewards outside the regular-pellet representation, such as incidental power-pellet
interactions; it is not a validated count of pellets or ghosts consumed.

All 1,890 controlled observations had player-color support and positions within
three pixels of the first-maze corridor graph. Zero-stickiness automated action
checks covered all nine native inputs after startup; direction effects were
consistent with the first-maze geometry. NOOP can retain motion. These checks do
not prove a collision model or fully validate ghost vulnerability and occlusion.

Regular pellets are detected from initial pixel components and current color
support. Occlusion can remove one from the visible list without proving it was
eaten. Ghost positions are RAM slots with normal/blue/unknown appearance. Fruit
and power-pellet state are omitted; maze changes explicitly stop this version.
Only bounded first-maze validity is claimed.

All **16,717 raw frames** and six videos replayed with exact RAM, RGB-hash,
reward/life and observation equality. Video counts matched at 60 fps, totaling
278.617 seconds. Original and restored archive audits agreed after normalizing
artifact paths. [Videos and calibration evidence](../../experiments/mspacman/calibration-v1/README.md).

## Frozen model comparison and interruption

The prospective comparison uses one direct action question versus a model-selected
intent followed by an action question. Both receive the same original observations
and all nine native actions; no rule controller replaces their decisions.
The two-stage arm uses up to twice as many requests, so the design does not isolate
equal-compute decomposition benefit. Exact Python-action agreement also has valid
shortest-route tie ambiguity and is only a diagnostic.

A 24-state training packet was frozen, balanced 12 evade/12 collect, with hash
`a36a792d2a1a1067df6a7382c613465cbea96f448846778b27c527e592f505ec`.
No successful probe result was received. The very first direct-arm request failed
at transport after approximately 0.002 seconds. A separate DNS diagnostic returned
`gaierror -3: Temporary failure in name resolution` for `openrouter.ai` in the
current network-restricted execution environment. No provider response/status was
received; this is not evidence of a provider service outage or model failure.

- HTTP attempts reserved: **1**; successful responses: **0**.
- Model-controlled actions/episodes/videos: **0**.
- Development seeds 516/517 were not run; final seeds 518/519 remain untouched.
- No retries, fallback provider, model substitution, or weight updates.
- Provider-reported cost is **unavailable**. The accounting field sums to zero
  because no usage record arrived; this does not establish a zero charge.
- The 1,700-attempt allocation is closed, with 1,699 attempts unused.
- **No conclusion about direct versus two-stage Jev performance is available.**

The original request matches the frozen program and first packet observation.
The failed exchange, budget, prompts, packet and closure are preserved in an
11-file checksummed archive; restored offline verification passed.
[Interrupted evidence](../../experiments/mspacman/direct-vs-target-v1-interrupted/README.md).

## What is ready next

The local strategy spread supports attempting the planned model pilot once the
execution environment can reach OpenRouter. Preserve this interruption as v1;
write a separately named prospective continuation/allocation instead of reopening
its closed budget. The unchanged prompts and packet can be reused with declared
provenance because no model answers or development data were observed. Recheck
transport and response identity under that new bounded protocol.

No more model experiments are authorized by this report itself. This result does
not establish automated teacher improvement or cross-game transfer.
