# C2-R2-A: criteria-edit teacher proposal

Search 2, round 2, arm A. Requested teacher: GPT-6 Astra, high reasoning, in a fresh packet-only Bubblewrap/Codex invocation. Provider model attestation is unavailable.

Visibility: **training only**. The coordinator has earlier development exposure but did not author this candidate. The current selected question indirectly reveals selection history. No development scores or final outcomes appear in this packet.

[Initial packet](../../../experiments/pong/criteria-teacher-v1/records/search-2/round-2/A/teacher/invocation-1/packet.json), hash `ebff2e6a395a73432f2c634780b9ad3e75d484e558162130075649f10090878a`. Parent program hash: `2ef87250f491fcd5a2ba72f29e3f03b6bc66c4ab7315e9e724df76352326633d`.

## Original proposal

[Exact validated proposal](../../../experiments/pong/criteria-teacher-v1/records/search-2/round-2/A/teacher/validated.json). Program: `pong-bounded-incoming-lookahead-v1`; hash `0abda786d1336f9a912a9a2bb6225aeec54e1ee5551256509eb095d2d175eb09`.

Teacher-reported hypothesis (not an observed result):

Current-height tracking can react too late to an incoming ball, especially after a wall bounce. The histories in the supplied loss windows show the ball crossing the paddle while the paddle remains below it, followed by alignment after the crossing. A bounded lookahead may initiate corrections earlier without relying on a full-flight prediction.

Operator: Replace current-height tracking for reliable incoming motion with a wall-reflected prediction capped at 24 raw frames or paddle arrival, whichever comes first. Retain the movement mapping, four-pixel deadband and fallback tracking.

Predicted changes: Expect earlier corrections along incoming trajectories and earlier reversals near predicted wall bounces. This may reduce late misses and create additional scoring opportunities. Improvement in points scored minus conceded remains untested.

Regression risks: The 24-frame horizon is unvalidated. Approximate wall positions and finite-difference velocities can bias targets; the consistency check can delay recovery after bounces. Sticky actions and the narrow deadband may still cause overshoot. Changed contact positions may produce less effective returns or longer rallies within the frame cap.

Referenced training examples: train-112-decision-495, train-112-decision-496, train-113-decision-120, train-113-decision-121, train-113-decision-251, train-113-decision-252, train-113-decision-465.

### Exact guidance

````text
Which action aligns the player paddle with the incoming ball's near-future height? Read player and ball in observation.objects. A bbox is [x, y, width, height]; vertical center is y plus half its height. Larger y means DOWN. RIGHT moves UP; LEFT moves DOWN. If player or ball is absent, choose NOOP.
Default target: the ball's current vertical center. For a ball moving right toward the player with reliable velocity, look ahead for the smaller of 24 raw frames and the time until its right edge reaches the player's left edge. That arrival time is the horizontal edge gap divided by positive horizontal velocity. Advance the ball center by vertical velocity times this lookahead. Reflect its path at approximate ball-center heights 33 and 193 if it reaches a wall; do not clamp it there. This target anticipates incoming movement while limiting distant extrapolation.
Use prediction only when velocity_valid is true and the latest two history intervals show approximately consistent horizontal and vertical motion. An interval spanning a bounce can report a misleading average; use the current center until two consistent intervals establish the new direction. Missing velocity is unknown, not zero. For leftward motion, unknown motion, or a ball whose right edge has already reached the player's left edge, use the current-center target.
If the target is more than four pixels ABOVE the player center, choose RIGHT. If more than four pixels BELOW, choose LEFT. Within four pixels, choose NOOP. Horizontal travel selects the prediction horizon, never the vertical action directly. Prefer NOOP, RIGHT and LEFT over equivalent FIRE aliases. Reconsider after the next requested four raw frames.
````

### Exact action criteria

**NOOP**

````text
Hold when the selected target is within four pixels of the player center, or player or ball is absent. For reliable incoming motion, compare with the bounded, wall-reflected future target; otherwise compare with the current ball center.
````

**FIRE**

````text
Stationary FIRE is appropriate under the same alignment or missing-object conditions as NOOP. It supplies no vertical correction; prefer NOOP when their movement effects are equivalent.
````

**RIGHT**

````text
Move UP when the selected target is more than four pixels above the player center. Use the bounded future target for reliable incoming motion and the current ball center otherwise. Rightward ball travel alone does not imply UP.
````

**LEFT**

````text
Move DOWN when the selected target is more than four pixels below the player center. Use the bounded future target for reliable incoming motion and the current ball center otherwise. DOWN increases screen y.
````

**RIGHTFIRE**

````text
Move UP with FIRE when the selected target is more than four pixels above the player center, using the same prediction and fallback rules as RIGHT. Prefer RIGHT when their vertical effects are equivalent.
````

**LEFTFIRE**

````text
Move DOWN with FIRE when the selected target is more than four pixels below the player center, using the same prediction and fallback rules as LEFT. Prefer LEFT when their vertical effects are equivalent.
````

## Observed evaluation and disposition

Development selection is not recorded in this snapshot. The proposal is not an established improvement.

All six native actions, original observations, one question and probability-argmax decoding remain available. Guidance and criteria are the allowed edits. See the [frozen protocol](../criteria-teacher-protocol.md) and [study log](../criteria-teacher-log.md).
