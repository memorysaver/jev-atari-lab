# C2-R1-A: criteria-edit teacher proposal

Search 2, round 1, arm A. Requested teacher: GPT-6 Astra, high reasoning, in a fresh packet-only Bubblewrap/Codex invocation. Provider model attestation is unavailable.

Visibility: **training only**. The coordinator has earlier development exposure but did not author this candidate. The current selected question indirectly reveals selection history. No development scores or final outcomes appear in this packet.

[Initial packet](../../../experiments/pong/criteria-teacher-v1/records/search-2/round-1/A/teacher/invocation-1/packet.json), hash `23d20460f00109863cad11ea8bcb83460fbe9d82fb94860aa17561aaec0e6ae4`. Parent program hash: `2ef87250f491fcd5a2ba72f29e3f03b6bc66c4ab7315e9e724df76352326633d`.

## Original proposal

[Exact validated proposal](../../../experiments/pong/criteria-teacher-v1/records/search-2/round-1/A/teacher/validated.json). Program: `pong-incoming-intercept-v1`; hash `be587c32ec9bde125a35b8ec5207e2258be30efb406591bc5badacebbb24c854`.

Teacher-reported hypothesis (not an observed result):

Tracking current ball height can leave the paddle behind a sloped incoming trajectory or draw it toward a wall before a bounce. Predicting the crossing height may allow earlier positioning and fewer late corrections. Supplied loss windows show missed crossings followed by apparent alignment only after the ball has passed the paddle; they motivate this hypothesis but do not establish that the edit improves return.

Operator: Replace the incoming-ball current-height target with a velocity-based, wall-reflected crossing-height target; retain the existing movement mapping, four-pixel deadband and fallback tracking.

Predicted changes: Expect earlier movement toward incoming crossing heights, including movement opposite the ball's current vertical offset when a bounce changes the destination. This may reduce conceded points and create more return opportunities. Whether points scored minus conceded improves requires evaluation.

Regression risks: Approximate wall and collision coordinates can bias predictions. Finite-difference velocity around bounces can remain misleading despite the history check. Sticky movement and the unchanged narrow deadband can cause overshoot around a stationary target. More centered returns may prolong rallies without increasing points scored within the frame cap.

Referenced training examples: train-110-decision-266, train-110-decision-178, train-110-decision-179, train-111-decision-59, train-111-decision-60, train-111-decision-166.

### Exact guidance

````text
Align the player paddle with the incoming ball's predicted crossing height. Read player and ball in observation.objects. A bbox is [x, y, width, height]; vertical center is y plus half the height. Larger y means DOWN. RIGHT moves UP; LEFT moves DOWN.
Use the ball's current vertical center as the default target. When ball velocity is valid, horizontal velocity is positive, and the ball is still left of the player, predict its height when its right edge reaches the player's left edge: remaining horizontal gap divided by horizontal velocity gives time in raw frames; advance the ball center vertically by vertical velocity times that time. Account for top and bottom bounces by reflecting the projected path at approximate ball-center heights 34 and 194, repeating reflections if needed. Do not clamp the ball trajectory at a wall. Use history to check that the latest velocity represents steady travel: if the most recent interval contains a bounce or disagrees substantially with the preceding interval, use the current ball center until a consistent outgoing velocity is observed. Missing velocity is unknown, not zero. For a leftward ball, unknown motion, or a ball already beyond the paddle, retain the current-center target.
Compare the target with the player's current vertical center. Target more than four pixels ABOVE: RIGHT. Target more than four pixels BELOW: LEFT. Within four pixels: NOOP. If player or ball is absent, NOOP. Horizontal position and velocity determine whether and how far to predict, never the up/down action directly. Prefer NOOP, RIGHT and LEFT over their equivalent FIRE aliases. Act for the next requested four raw frames, then recompute from the next observation.
````

### Exact action criteria

**NOOP**

````text
Hold when the selected target is within four pixels of the player center, or when player or ball is absent. For a reliable incoming trajectory, judge alignment against the reflected crossing height, even if the current ball height differs.
````

**FIRE**

````text
Stationary FIRE alias: appropriate under the same alignment or missing-object conditions as NOOP. It adds no vertical correction; prefer NOOP when their movement effects are equivalent.
````

**RIGHT**

````text
Move UP when the selected target is more than four pixels above the player center. Use the predicted crossing height for reliable incoming motion and the current ball center otherwise. Rightward ball travel alone is not a reason to move up.
````

**LEFT**

````text
Move DOWN when the selected target is more than four pixels below the player center. Use the predicted crossing height for reliable incoming motion and the current ball center otherwise. Downward means increasing screen y.
````

**RIGHTFIRE**

````text
Move UP with FIRE when the same target-above-center condition as RIGHT applies. This is an upward movement alias; prefer RIGHT when their vertical effects are equivalent.
````

**LEFTFIRE**

````text
Move DOWN with FIRE when the same target-below-center condition as LEFT applies. This is a downward movement alias; prefer LEFT when their vertical effects are equivalent.
````

## Observed evaluation and disposition

Disposition: **rejected**.

Paired development return gains over fresh v2: [-5.0, -6.0]; mean -5.5. Previous best development gain: +0. The previous best is historical, not a freshly rerun incumbent.

Selection is an engineering gate, not a held-out improvement claim. Final evaluation follows only after all selected programs are sealed.

All six native actions, original observations, one question and probability-argmax decoding remain available. Guidance and criteria are the allowed edits. See the [frozen protocol](../criteria-teacher-protocol.md) and [study log](../criteria-teacher-log.md).
