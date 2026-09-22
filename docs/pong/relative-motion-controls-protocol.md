# Relative-motion literal controls v1

Frozen before these local trials, 2026-09-23. This separate **zero-model-call**
diagnostic follows the isolated teacher's C1-R2-A proposal in the running
[criteria study](criteria-teacher-protocol.md). It does not alter that study's
proposals, packets, model budget, selector or final evaluation, and its results
are not supplied to that study's teachers.

The source program is `pong-relative-motion-lookahead-v1`, hash
`67d2e249f331df8db6fe21a26369487bea5bd93ed2e36332e597fe859f5feef4`.
The coordinator has seen its proposal and prior development results and authors
the Python operationalizations. These are diagnostic interpretations, not Jev
actions, an isolated teacher revision or a promotion. The runner copies the exact
original teacher record before executing any controls.

## Rules and ambiguity

Use four literal Python controllers with all native actions available, choosing
non-FIRE movements, a four-pixel deadband and the unchanged observation adapter:

- `track-4`: current ball center minus current player center.
- `ball-lookahead-2`: forecast only the ball center by twice its valid vertical
  velocity in pixels/raw-frame; keep current player center.
- `relative-lookahead-2`: the same ball forecast and an independent two-raw-frame
  forecast of the player center using its valid supplied vertical velocity.
- `relative-unguarded-2`: the same relative forecast, omitting the bounce-history
  guard as a sensitivity analysis of ambiguous teacher wording.

Unknown/invalid velocity uses that object's current center; missing either bbox
means NOOP. Ball forecasts reflect repeatedly between the teacher's approximate
center bounds **32 and 194**; these are not adopted as validated physical bounds.
Player forecasts are not reflected or clamped. Current bbox heights are preserved;
the supplied velocities track bbox coordinates and can be distorted by clipping.
Forecast horizons are exactly two raw frames, not two observations or hold periods.

The guarded interpretations detect a vertical sign reversal across the last two
segments of the last three visible, strictly time-ordered history samples. When
observed, keep current ball center; otherwise forecast if its velocity is valid.
Missing history does not itself prove a reversal. Horizontal reversal alone does
not activate this guard. This is one operationalization of the teacher's ambiguous
"velocity spans that bounce" condition, not proof of its uniquely intended meaning.

## Execution and measurement

Freeze source in Git before trials. Use training seeds
**130,131,132,133,134,135,140,141**, checked unused in local episode manifests. None
overlaps the running criteria study's training, development or final seeds.
Run all four rules on each seed, rotating order by seed index modulo four.
Each episode caps at **2,000 controlled raw frames** or earlier native termination:
**32 episodes, at most 64,000 controlled frames**, with **zero Jev/teacher calls**.
Use default Pong Protocol, sticky 0.25, four-frame actions and reset NOOPs 0..30.
Do not overwrite or resume an existing output directory or expand the schedule.

Report every seed's return/points and paired differences to track-4; aggregate
return and completion denominators; the ball-only ablation and guard sensitivity.
Primary descriptive contrast: relative-lookahead-2 minus track-4 capped return.
No significance, native-win, Jev improvement or final-generalization claim. These
are fresh training trajectories; comparison with different Jev development states
cannot establish a causal execution deficit by itself.

Record original teacher source, source revision, protocol, rule definitions,
decisions, predictions, rewards, raw-frame evidence and videos in
`artifacts/pong/relative-motion-controls-v1/`. Replay all episodes and recompute
every chosen action and aggregate without model access. Reviewed local evidence
belongs under `experiments/pong/relative-motion-controls-v1/`; archives/videos
use LFS. Remote publication/retrieval is not implied by running this diagnostic.

Whatever the result, finish the running criteria study under its own frozen
protocol. These local results may inform a separately designed future study.
