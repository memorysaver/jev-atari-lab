# C1-R2-B: criteria-edit teacher proposal

Search 1, round 2, arm B. Requested teacher: GPT-6 Astra, high reasoning, in a fresh packet-only Bubblewrap/Codex invocation. Provider model attestation is unavailable.

Visibility: **no empirical feedback**. The coordinator has earlier development exposure but did not author this candidate. The current selected question indirectly reveals selection history. No development scores or final outcomes appear in this packet.

[Initial packet](../../../experiments/pong/criteria-teacher-v1/records/search-1/round-2/B/teacher/invocation-1/packet.json), hash `2994d56d92072efa6ed2dd796638908daed617c80dfb982e555ca457cf4a78b3`. Parent program hash: `2ef87250f491fcd5a2ba72f29e3f03b6bc66c4ab7315e9e724df76352326633d`.

## Original proposal

[Exact validated proposal](../../../experiments/pong/criteria-teacher-v1/records/search-1/round-2/B/teacher/validated.json). Program: `pong-bounded-incoming-lead`; hash `2c4a0278c33e6f00e3d329fc48d7fa5debadf578fff894819d7838395b0cd11c`.

Teacher-reported hypothesis (not an observed result):

A four-frame lead may reduce the lag of current-height tracking during incoming diagonal flight. Bounding prediction to the next decision may also reduce sensitivity to uncertain distant bounces compared with the prior full-arrival projection. Neither benefit has been measured.

Operator: Replace the guidance and all six criteria with bounded incoming-lead targeting while retaining the four-pixel alignment threshold and native action meanings.

Predicted changes: During reliable incoming flight, the paddle should begin vertical corrections slightly earlier. Predictions should stay close to the observed ball height, with current-height tracking retained when motion is uncertain or outgoing. More timely returns could improve points scored minus conceded.

Regression risks: Finite-difference motion can miss a recent collision, and even a short projection can cross a wall bounce. Leading the ball may cause unnecessary movement when it already overlaps the paddle. Sticky actions can prolong corrections. A four-frame horizon may be too short to address difficult interceptions, and additional returns may not yield additional points.

Referenced training examples: none.

### Exact guidance

````text
Which action should vertically align the player paddle with the ball over the next decision? Read player and ball from observation.objects and motion information from the supplied history. A bbox is [x, y, width, height]; its vertical center is y + height/2. Larger y means lower. RIGHT moves the player UP; LEFT moves it DOWN.
Use a short incoming lead as the principal change. Start with the current ball center as the target. When recent history establishes consistent rightward motion toward the player and a usable vertical velocity, project the ball center forward by four raw frames. If the ball will reach the player's left edge sooner, project only until contact: use the horizontal gap between the ball's right edge and the player's left edge divided by horizontal speed. Never project beyond four raw frames. Convert velocities and durations to matching units; if their timing is unclear, retain the current ball center.
Use the projected height only when the recent motion supports continued flight over that short interval. Account for a wall reflection only if its location is established by the supplied observation/history. If a bounce or reset makes the projection uncertain, retain the current ball center. Missing velocity is unknown, not zero. When the ball moves away, retain its current center as the target.
Choose RIGHT when the target is more than four pixels above the player center, LEFT when it is more than four pixels below, and NOOP within four pixels. If player or ball is absent, choose NOOP. Horizontal motion selects whether to use prediction; it does not directly select UP or DOWN. Prefer non-FIRE actions over FIRE aliases with equivalent movement. Reconsider after each decision.
````

### Exact action criteria

**NOOP**

````text
Choose when the selected target is within four pixels of the player center, or player or ball is absent. The target is the credible short incoming projection defined in the guidance, otherwise the current ball center. Prefer NOOP over equivalent stationary FIRE.
````

**FIRE**

````text
Stationary alternative when the selected target is within four pixels of the player center, or player or ball is absent. FIRE supplies no vertical correction; prefer NOOP when their movement effects are equivalent.
````

**RIGHT**

````text
Move UP when the selected target is more than four pixels above the player center. Use the credible incoming projection capped at four raw frames, otherwise current ball height. Rightward ball motion alone does not justify moving up. Prefer RIGHT over equivalent RIGHTFIRE.
````

**LEFT**

````text
Move DOWN when the selected target is more than four pixels below the player center. Use the credible incoming projection capped at four raw frames, otherwise current ball height. Larger y means lower. Prefer LEFT over equivalent LEFTFIRE.
````

**RIGHTFIRE**

````text
Move UP with FIRE when the selected target is more than four pixels above the player center, using exactly the same target as RIGHT. Prefer RIGHT when both produce equivalent vertical movement.
````

**LEFTFIRE**

````text
Move DOWN with FIRE when the selected target is more than four pixels below the player center, using exactly the same target as LEFT. Prefer LEFT when both produce equivalent vertical movement.
````

## Observed evaluation and disposition

Disposition: **rejected**.

Paired development return gains over fresh v2: [-4.0, 0.0]; mean -2. Previous best development gain: +0. The previous best is historical, not a freshly rerun incumbent.

Selection is an engineering gate, not a held-out improvement claim. Final evaluation follows only after all selected programs are sealed.

All six native actions, original observations, one question and probability-argmax decoding remain available. Guidance and criteria are the allowed edits. See the [frozen protocol](../criteria-teacher-protocol.md) and [study log](../criteria-teacher-log.md).
