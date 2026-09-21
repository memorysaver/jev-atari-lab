# D001: explicit motion reliability (manual diagnostic revision)

Status: **negative diagnostic result; not promoted**. This entry renders guidance
frozen before the live calls. Precise-versus-ambiguous conservative-rule agreement
fell from 6/16 to 1/16 in the primary motion-conflict stratum, and from 99/160 to
73/160 overall. See the linked report for all strata and limitations. This is not a teacher-study-v1 continuation or a promoted
policy. The author is the interactive coordinator, with prior development results
in context. There was no isolated teacher invocation or model-weight update.

The original B question left "reliably" and "evident bounce" underspecified.
This intervention chooses the conservative operationalization tested in the
previous Python control study. The hypothesis is that an explicit history test
will make Jev's action more consistent with that rule on ambiguous motion states.
A longer definition may also impair basic directional decisions or timing logic.

Inputs are 80 stratified states selected from published training trajectories.
Rewards, successor observations, reference actions and stratum labels are not
passed to Jev. The coordinator's earlier development exposure is not erased by
using training states for this diagnostic evaluation.

## Exact guidance before and after

### Before: original B question

```text
Which action should vertically align the player paddle with the ball's near-term position? Read player and ball in observation.objects. A bbox is [x, y, width, height]; its vertical center is y + height/2. Larger y means LOWER. If either object is absent, choose NOOP. Start with the current ball center as the target. When available finite-difference history reliably indicates that the ball is moving toward the right-side player, advance the target by the estimated vertical displacement over the next decision (4 raw frames). Respect the history's time units; do not treat displacement per observation as displacement per raw frame. Use the latest motion segment after an evident bounce. If direction, timing or vertical velocity is unknown, use the current ball center. For a ball moving away, also use its current center. If the target is more than four pixels BELOW the player center, choose LEFT (DOWN). If more than four pixels ABOVE, choose RIGHT (UP). Otherwise choose NOOP. Screen side and horizontal direction alone never determine UP or DOWN. Prefer the non-FIRE option when a FIRE alias gives the same movement. Act for the next requested duration, then reconsider.
```

### After: manual precise question

```text
Choose the next action for the player paddle. Read player and ball in observation.objects. A bbox is [x,y,width,height]; center_y=y+height/2. Larger y means down. If either bbox is missing, choose NOOP. Initially target=current ball center_y. Use a four-raw-frame lookahead ONLY if all these conditions hold: (1) ball.velocity_valid is true and ball.velocity=[vx,vy] is known in pixels per raw frame; (2) vx>0, toward the player; (3) the last THREE observation.history samples each have a visible ball bbox and strictly increasing offset_raw_frames; (4) for BOTH x and y, the two consecutive position changes across those three samples have a nonnegative product. A negative product means a direction reversal. Zero is allowed. If any condition fails or is unknown, keep target=current ball center_y. If all hold, target=current ball center_y+vy*4. Do not multiply by the history sample interval again; the supplied velocity is already per raw frame. Do not predict further ahead or add wall reflection. Compute gap=target-player center_y. If gap < -4 choose RIGHT (UP). If gap > 4 choose LEFT (DOWN). Otherwise choose NOOP. These action names have vertical effects in Pong. Horizontal direction only gates lookahead; it does not select UP or DOWN. Prefer the non-FIRE action for the same vertical movement. Act for four frames, then reconsider the new observation.
```

Only name/guidance changes. Jev 1.13.0, original observation, native six-action
criteria and probability argmax stay fixed. A Python reference labels the audit;
it never supplies Jev's action or modifies its probabilities.

## Evaluation and record

The [frozen protocol](../motion-probe-protocol.md) limits execution to 520 HTTP
attempts and four hours; 80 states, three questions and two repeats require at
most 480 successful responses. No gameplay, promotion or final-test access.
Exact [programs](../../../experiments/pong/motion-probe-v1/programs.json),
[provenance](../../../experiments/pong/motion-probe-v1/provenance.json) and the
[results report](../motion-probe-results-2026-09-21.md) preserve the intervention
and observed outcome. An improved diagnostic score would not establish better
Pong play or an effective learned teacher optimizer.
