# C1-R1-A: criteria-edit teacher proposal

Search 1, round 1, arm A. Requested teacher: GPT-6 Astra, high reasoning, in a fresh packet-only Bubblewrap/Codex invocation. Provider model attestation is unavailable.

Visibility: **training only**. The coordinator has earlier development exposure but did not author this candidate. The current selected question indirectly reveals selection history. No development scores or final outcomes appear in this packet.

[Initial packet](../../../experiments/pong/criteria-teacher-v1/records/search-1/round-1/A/teacher/invocation-1/packet.json), hash `c4036cefeacc812d95481fb6c5bebd2b74ae7e93215ca066eba4e85c8766da5d`. Parent program hash: `2ef87250f491fcd5a2ba72f29e3f03b6bc66c4ab7315e9e724df76352326633d`.

## Original proposal

[Exact validated proposal](../../../experiments/pong/criteria-teacher-v1/records/search-1/round-1/A/teacher/validated.json). Program: `pong-reflected-intercept-v1`; hash `d62447b21d6848b75e387f43d5e553e97097a4d71664448162ba1e4687c55384`.

Teacher-reported hypothesis (not an observed result):

Tracking current height can draw the paddle toward a wall even when an incoming ball will bounce and reach the paddle elsewhere. Targeting the reflected crossing height may allow earlier positioning and reduce late pursuit. The supplied loss windows show that alignment after the ball passes the paddle cannot recover the point; they do not establish that this proposal will improve return.

Operator: Replace instantaneous ball-height tracking with reflected incoming-trajectory interception; retain the four-pixel alignment tolerance and native action preferences.

Predicted changes: Incoming diagonal balls should produce earlier movement toward their eventual crossing height, including movement opposite their current vertical direction before a wall bounce. A stable intercept target may reduce repeated chasing during approach and could reduce concessions. Outgoing-ball tracking and missing-object behavior remain as before.

Regression risks: Approximate wall limits and velocities averaged across bounces can yield incorrect intercepts, particularly over long flights. Sticky actions and paddle drift can still cause overshoot. Different contact positions may produce easier returns for the opponent or longer rallies, potentially lowering points scored within the evaluation cap even if more balls are returned.

Referenced training examples: train-101-decision-232, train-101-decision-332, train-100-decision-199, train-100-decision-332, train-101-decision-60, train-101-decision-61, train-100-decision-213.

### Exact guidance

````text
Which action should align the player paddle with the incoming ball's predicted crossing height? Read player and ball from observation.objects. A bbox is [x,y,width,height]; vertical center is y plus half height. Larger y means DOWN. RIGHT moves UP; LEFT moves DOWN.
The principal target is the ball's future height at the player's front face, rather than its current height. When ball velocity_valid is true, horizontal velocity is positive, and the ball's right edge has not passed the player's left edge, estimate travel time as the horizontal gap between those edges divided by horizontal velocity. Project the ball center vertically for that many raw frames using its vertical velocity. Account for top and bottom bounces: reflect the projected trajectory between approximate ball-center limits y=34 and y=194, repeating reflections if necessary. Do not clamp the ball at a wall or project through it. These are playfield limits, not the full image edges.
Use history to check for a recent bounce: a finite-difference velocity spanning a bounce can understate speed. If the incoming trajectory is ambiguous, use the current ball center as the target until a clear velocity is available. Also use the current ball center when velocity is missing or invalid, the ball is moving away, or it has already passed the paddle. Missing velocity is unknown, not zero.
Compare this target with the player center. Target more than four pixels ABOVE: RIGHT. More than four pixels BELOW: LEFT. Within four pixels: NOOP. If player or ball is absent, choose NOOP. Prefer NOOP, RIGHT and LEFT over their FIRE aliases, which have the same vertical effects. Request only the next four-frame action and recompute from the next observation.
````

### Exact action criteria

**NOOP**

````text
Hold when the target defined in guidance is within four pixels of the player center, or when player or ball is absent. For a clear incoming trajectory, judge the reflected crossing height rather than current ball height. Prefer this to FIRE for holding.
````

**FIRE**

````text
The same vertical hold as NOOP: appropriate when the guidance target is within four pixels of the player center or an essential object is absent. It provides no additional alignment benefit; prefer NOOP.
````

**RIGHT**

````text
Move UP when the guidance target is more than four pixels above the player center. For a clear incoming ball, use its reflected crossing height; otherwise use current ball height. Horizontal rightward travel alone does not justify this action. Prefer RIGHT to RIGHTFIRE.
````

**LEFT**

````text
Move DOWN when the guidance target is more than four pixels below the player center. For a clear incoming ball, use its reflected crossing height; otherwise use current ball height. A future top-wall bounce can justify moving down while the ball currently rises. Prefer LEFT to LEFTFIRE.
````

**RIGHTFIRE**

````text
Move UP under the same target-above condition as RIGHT: the guidance target is more than four pixels above the player center. FIRE adds no vertical advantage, so prefer RIGHT when both fit.
````

**LEFTFIRE**

````text
Move DOWN under the same target-below condition as LEFT: the guidance target is more than four pixels below the player center. FIRE adds no vertical advantage, so prefer LEFT when both fit.
````

## Observed evaluation and disposition

Disposition: **rejected**.

Paired development return gains over fresh v2: [-5.0, -4.0]; mean -4.5. Previous best development gain: +0. The previous best is historical, not a freshly rerun incumbent.

Selection is an engineering gate, not a held-out improvement claim. Final evaluation follows only after all selected programs are sealed.

All six native actions, original observations, one question and probability-argmax decoding remain available. Guidance and criteria are the allowed edits. See the [frozen protocol](../criteria-teacher-protocol.md) and [study log](../criteria-teacher-log.md).
