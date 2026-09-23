# Seaquest evaluation profile v1: calibration stage

## Environment and observation

Use installed `ALE/Seaquest-v5`, ale-py 0.11.2, mode 0, difficulty 0, native 18-action
space. Record ROM SHA-256 and locked dependency versions in every study plan.
Step one raw frame at a time, four-frame action hold, sticky probability 0.25;
separate deterministic action-effect checks use sticky zero and are not score
comparisons. No automatic FIRE, reset no-ops or life-loss controller in trajectories.
Termination is native; frame caps are explicit, not wins or completed levels.

`seaquest-ram-calibration-v1` is an **experimental** semantic extractor adapted
from MIT-licensed OCAtari revision `99c874675df6b76a33a80b57776c123fbcd051af`.
See [notice](../../THIRD_PARTY_NOTICES.md) and
[upstream mapping](https://github.com/k4ntz/OC_Atari/blob/99c874675df6b76a33a80b57776c123fbcd051af/ocatari/ram/seaquest.py).
It exposes player/enemy/diver/projectile boxes, player facing, oxygen-bar raw level,
carried-diver count and reserve-life byte. Missing player during its animation is
represented by no player object. Out-of-range diver counts map to null, preserving
raw values for diagnostics. Slot identities are not proven persistent object tracks.
No motion estimator or final Jev observation/history contract has been adopted yet.

Independently compare RAM oxygen width with grey pixels in its screen bar and
check for player-colored pixels inside the proposed player box. Neither check
validates every enemy box, collected-diver meaning, animation or hidden state.
Lives and rewards come from ALE, never from inferred object semantics. Oxygen-loss
cause, rescue success, threat and optimal-action labels remain unimplemented.

Exploratory local startup checks found movement ignored during early oxygen fill;
128 initial NOOP frames followed by 40 DOWN frames allowed clean directional
checks. These observations motivate the separate calibration action probes, not
an automatic startup advantage for a model or a frozen benchmark conclusion.

## Outcomes and controls

Native capped return is the future primary policy outcome; choose a paid-study
horizon after measuring whether it exposes oxygen/resource decisions. The initial
8,000-frame training cap is for calibration only. Secondary diagnostics: native
life losses, oxygen coverage, carried-diver raw values and screen consistency.
Do not label life losses as oxygen-caused without an independently validated detector.
Mastery criterion, critic target and teacher endpoint: **not yet adopted**.

Local controls are NOOP, FIRE, uniformly random native actions, and a fixed
DOWNFIRE/RIGHTFIRE/UPFIRE/LEFTFIRE sweep changing direction every 100 decisions.
The sweep is a coordinator-authored coverage routine, not learned behavior.
Record startup idle behavior; a nonmoving high-survival run is not task success.

Future teacher studies need a frozen model/transport, question schema, packet sampler,
matched proposal opportunities, independent training/development/final seeds and
measured token/API budgets. Use fresh own-candidate experience and a no-feedback
control; do not confuse sequential edits with independent optimizer replications.
Per-frame checks are correlated instrumentation observations, not independent
samples of policy skill. Raw scores are not directly comparable to Pong's scores.

## Subsequent observation v2 and fixed-question pilot

The preceding v1 profile records the initial calibration contract. The separate
[observation v2 protocol](observation-v2-protocol.md) adds explicit animation/end
unavailability and three-snapshot object history; its bounded pixel-support gate
[passed](observation-v2-results-2026-09-24.md). This does not validate exact object
identity, box shape/recall or cause-of-death semantics.

The [fixed-question pilot protocol](fixed-question-pilot-protocol.md) adopted a
3,200-frame native-capped return and explicit transport/model pin for two training
seeds. The [completed result](fixed-question-pilot-results-2026-09-24.md) records
80 points per seed with collapsed DOWN/NOOP behavior. It is a dedicated pilot;
the generic CLI still exposes raw RAM for Seaquest. No teacher endpoint, mastery
criterion or final evaluation has been adopted.

## Completed ten-round research contract

The [ten-round protocol](ten-round-protocol.md), with its documented
[exact-state continuation](ten-round-continuation-protocol.md), subsequently adopted
separate training/development/final seeds and a fixed 256-frame seeded startup
prefix. Control then ran for at most 800 decisions/3,200 raw frames or native end.
Controlled native return excludes prefix reward; all frames are recorded.

The highest training mean among seven coordinator proposals selected one program
before development. Each held-out two-seed gate required mean paired gain >=20
with no regression. Both gates [passed](ten-round-results-2026-09-24.md): development
+290, final +210. Matched prefix/start equality and actual distinct seed starts were
verified. This is a bounded policy-improvement endpoint, not mastery, an isolated
teacher endpoint, causal feedback benefit or independent optimizer replication.
All ten rounds and 24 videos are preserved; the allocation is closed.
