# C2-R2-B: criteria-edit teacher proposal

Search 2, round 2, arm B. Requested teacher: GPT-6 Astra, high reasoning, in a fresh packet-only Bubblewrap/Codex invocation. Provider model attestation is unavailable.

Visibility: **no empirical feedback**. The coordinator has earlier development exposure but did not author this candidate. The current selected question indirectly reveals selection history. No development scores or final outcomes appear in this packet.

[Initial packet](../../../experiments/pong/criteria-teacher-v1/records/search-2/round-2/B/teacher/invocation-1/packet.json), hash `07d5e91a8c878560fad906885d87e2f9737c9ea361d64d789f066428852d7c4c`. Parent program hash: `2ef87250f491fcd5a2ba72f29e3f03b6bc66c4ab7315e9e724df76352326633d`.

## Original proposal

[Exact validated proposal](../../../experiments/pong/criteria-teacher-v1/records/search-2/round-2/B/teacher/validated.json). Program: `pong-bounded-incoming-lead`; hash `d7ca441f97d284800b14cdb3de92f3591ba965db50245c8b5c4931e4cdb64619`.

Teacher-reported hypothesis (not an observed result):

A short lead during incoming motion may reduce the lag of current-height tracking while limiting errors from long-range extrapolation. The eight-frame cap is an untested design choice, not an empirically selected value.

Operator: Replace the current-ball target with a bounded incoming projection when recent motion supports it; preserve the four-pixel deadband, movement semantics and fallback behavior.

Predicted changes: The paddle should begin correcting toward an approaching ball's near-future height earlier, with smaller anticipatory deviations than unrestricted arrival prediction. This could increase successful returns and improve points scored minus conceded, but no improvement is established.

Regression risks: Eight frames may provide insufficient lead for steep incoming trajectories. Noisy velocity, rebound ambiguity and sticky actions may cause incorrect corrections or overshoot. Additional returns may remain easy for the opponent and need not improve point differential.

Referenced training examples: none.

### Exact guidance

````text
Which action best aligns the player paddle with a short-term incoming ball target? Read player and ball in observation.objects. A bbox is [x, y, width, height]; its vertical center is y plus half its height. Larger y means DOWN. RIGHT moves the player UP; LEFT moves it DOWN.
The principal change is bounded anticipation. Start with the current ball center as the target. Use available finite-difference motion or observation.history to estimate ball velocity only when timing and recent motion are clear. Missing velocity is unknown, not zero. If the ball is moving toward the right-side player, estimate the time until the ball's right edge reaches the player's left face. Project its vertical center forward by that time or eight raw frames, whichever is shorter. Never project beyond contact. This limited lead avoids relying on a full long-distance trajectory. If a wall rebound could occur within that interval, use the projection only when the boundary and reflected motion are supported by the observation or history; otherwise retain the current ball center. After a direction reversal, use only motion from after the reversal. If motion is uncertain, the ball is traveling away, or it has already passed the contact plane, retain the current ball center.
Choose LEFT when the target is more than four pixels below the player center, RIGHT when more than four pixels above, and NOOP within four pixels. If player or ball is absent, choose NOOP. Horizontal position or direction alone never selects vertical movement. Prefer non-FIRE actions when firing has no distinct supported benefit. Reassess after the next four raw frames.
````

### Exact action criteria

**NOOP**

````text
Hold when the target is within four pixels of the player center, or player or ball is absent. The target is the supported incoming projection capped at eight raw frames and contact time; otherwise it is the current ball center. Prefer NOOP over equivalent stationary FIRE.
````

**FIRE**

````text
Remain stationary with FIRE when the target is within four pixels of the player center and the observation supports a distinct benefit from firing. It supplies no vertical correction; prefer NOOP when firing is equivalent or player or ball is absent.
````

**RIGHT**

````text
Move UP when the target is more than four pixels above the player center. Use the supported incoming projection capped at eight raw frames and contact time, otherwise the current ball center. Rightward ball motion alone does not justify moving up.
````

**LEFT**

````text
Move DOWN when the target is more than four pixels below the player center. Use the supported incoming projection capped at eight raw frames and contact time, otherwise the current ball center. Reassess after four raw frames.
````

**RIGHTFIRE**

````text
Move UP with FIRE when the same target used for RIGHT is more than four pixels above the player center and firing has a distinct benefit supported by the observation. Prefer RIGHT when the two actions provide equivalent movement.
````

**LEFTFIRE**

````text
Move DOWN with FIRE when the same target used for LEFT is more than four pixels below the player center and firing has a distinct benefit supported by the observation. Prefer LEFT when the two actions provide equivalent movement.
````

## Observed evaluation and disposition

Development selection is not recorded in this snapshot. The proposal is not an established improvement.

All six native actions, original observations, one question and probability-argmax decoding remain available. Guidance and criteria are the allowed edits. See the [frozen protocol](../criteria-teacher-protocol.md) and [study log](../criteria-teacher-log.md).
