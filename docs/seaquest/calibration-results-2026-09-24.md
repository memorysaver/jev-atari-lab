# Seaquest calibration results, 2026-09-24

**Eight local trajectories completed and replayed; zero model calls.** This starts
Seaquest instrumentation work after Pong closure. It does not establish learned
behavior or a fully validated semantic policy adapter.

[Frozen calibration protocol](calibration-protocol.md) ·
[Evaluation profile](evaluation.md) ·
[Reviewed local evidence](../../experiments/seaquest/calibration-v1/README.md)

## Observed local controls

| Control | Seed 300: return / frames | Seed 301: return / frames | Outcome |
| --- | --- | --- | --- |
| NOOP | 0 / 8,000 | 0 / 8,000 | Frame cap, no life loss |
| FIRE | 0 / 8,000 | 0 / 8,000 | Frame cap, no life loss |
| Random native actions | 20 / 1,377 | 140 / 2,561 | Native termination; four lives lost each |
| Fixed scripted sweep | 140 / 5,785 | 120 / 4,013 | Native termination; four lives lost each |

Both stationary controls remain at the surface without scoring. Their long survival
is not task competence, so survival alone is unsuitable as the primary endpoint.
The moving controls collect score but lose all lives. This gives some behavioral
variation; two training seeds and these hand-written controls do not establish
that Jev policies or teacher optimizers will separate reliably.

The swept actions are fixed DOWNFIRE/RIGHTFIRE/UPFIRE/LEFTFIRE intervals, not a
teacher discovery. In the separate matched-state action checks, all 18 native
actions had the expected directional signs: cardinal movement changed one coordinate
by 16 pixels over 16 frames, diagonals changed both by 16, and NOOP/FIRE had zero
position change. Those checks use sticky zero; the eight trajectories use sticky
0.25. They do not establish firing effectiveness or collision-free movement.

## Observation checks and retained failures

- Oxygen-bar RAM width matched the independent screen-color width on **11,437 /
  11,437** decision-end observations. This supports that display mapping in visited
  states, not a calibrated time-to-death or an oxygen-caused-death detector.
- The extractor proposed a player box in **11,213** observations; the expected
  player color occurred inside it in **11,067**. All **146 disagreements** are
  retained: **142** have nonzero animation bytes (15..23), and **four** are terminal
  frames with animation byte zero. These expose a visibility/animation limitation
  in the upstream-derived mapping; they must not be scored as Jev errors.
- Carried-diver raw values reached 0 and 1 in some moving trajectories, but never
  2..6. Full capacity, unloading/rescue cycles and flashing HUD behavior remain
  unvalidated. The current check does not prove the diver counter's semantics.
- Enemy/diver/projectile objects are extracted, but their boxes, subtype changes,
  identities and motion histories have not received independent screen validation.

The mapping stays at its frozen `seaquest-ram-calibration-v1` implementation; no
post-result edits changed this suite's observations. Before a paid pilot, make a
new version with an explicit player-visibility/animation contract, test it on fresh
training traces, and validate moving objects and motion-history resets. Treat
terminal frames separately. Do not infer policy readiness from the oxygen result.

## Resources and reproduction

Frozen source: `c71c7b4`, complete revision in the archived plan. Eight original
trajectories used **45,736 controlled frames / 11,437 decisions**, and the original
recorded-action replays used a separate **45,736 frames**. Eighteen action probes
used **3,312 frames** (128 initial NOOPs, 40 DOWN, 16 tested action per reset).
The calibration suite therefore used **94,784 emulator frames**, excluding earlier
unit/startup checks and later independent archive audits. API/teacher costs: zero.

Each raw frame records RAM, RGB hash, reward, lives and termination/truncation.
Each decision records the semantic observation, native action, next observation
and pixel checks. Four videos (seed 300, one per control) use simulation time.
The checksummed archive includes original and initial replay records; restoration
and an additional independent recorded-action replay verify preservation. The latter
adds 45,736 replay frames and repeats 3,312 action-probe frames, separately counted.
No ROM or emulator snapshot is distributed. Git LFS preservation is local; remote
publication and retrieval are not claimed.

## Next experiment boundary

Keep native score primary and report lives/resource-cycle diagnostics separately.
The 8,000-frame cap reaches termination for the moving local controls, but idle
surface behavior can consume the whole budget without exercising rescue decisions.
A paid pilot must explicitly check active play and situation coverage. More games
or longer episodes alone would not fix an incomplete observation contract.

The immediate next step is a versioned visibility/motion validation pass, followed
by a small fixed-question Jev pilot with prospective call limits and bounded
same-state transport retries. Only after that pilot should a train/development/final
teacher study begin. No Seaquest teacher or live executor was invoked in this phase.
