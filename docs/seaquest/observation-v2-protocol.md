# Seaquest observation v2: prospective validation and pilot gate

2026-09-24, before fresh validation trajectories. The owner requested continued
research. Pong remains closed. This stage fixes a measured visibility limitation,
checks fresh training experience, and admits only a small instrumentation pilot
if its prespecified gate passes. It does not authorize a teacher optimization study.

## Representation change

Preserve the original calibration decoder and evidence. New `seaquest-objects-v2`
suppresses object positions during **any nonzero player animation byte** and on
native termination/truncation, since animation RAM can contain stale positions.
Discard boxes wholly beyond the right screen edge. Oxygen and carried-diver values
remain as before; their meanings and unseen ranges retain calibration limitations.

Use three previous object snapshots with explicit raw-frame timestamps, not an
invented velocity or preferred action. Clear history during unavailable states,
on native life loss and at reset. IDs identify RAM slots, not guaranteed persistent
entities; a subtype change or teleport must not be treated as continuous motion.
All 18 native actions remain available, four-frame hold and sticky 0.25. No hidden
startup controller, automatic FIRE, reward shaping or action mask.

Independent screen diagnostics use OCAtari's pinned color definitions, including
the white player variant. [Upstream](https://github.com/k4ntz/OC_Atari/blob/99c874675df6b76a33a80b57776c123fbcd051af/ocatari/vision/seaquest.py).
Checks count expected-color pixels inside proposed boxes. They are a necessary
local sanity check, **not** proof of bounding-box precision, object identity,
recall, complete enemy coverage or rescue-event semantics.

## Fresh validation

Seeds **302,303**, training only, two fixed policies (random native actions and the
original four-direction FIRE sweep), each up to **8,000 raw frames** or native end.
Maximum 32,000 collection frames and 32,000 separate recorded-action replay frames;
zero model calls. Reset no-ops zero; no automatic
FIRE. These seeds differ from calibration seeds 300/301. Record source commit,
ROM/dependency identity, full original per-frame RAM/RGB hash/reward/lives/end flags,
observations, screen checks and results. Do not change the mapping during collection.
Any failure remains incomplete, with no automatic rerun of the same root.

Gate for proceeding to a small fixed-question pilot:

- Oxygen screen-width agreement: 100% of decision-end observations.
- Player: at least 1,000 active box observations and at least 99% color support.
- Shark, diver and player missile: each at least 20 box observations and at least
  95% color support. Report other object types separately; unvisited types remain
  unvalidated. A passed gate does not establish full-game readiness.
- Unit tests must verify history clears on animation/end/life loss, and the original
  decoder remains unchanged. Raw-frame replay must match before a live pilot.

Failure ends this stage with preserved evidence and an explicit next diagnostic;
never lower the gate post hoc to launch a paid experiment. Before live access,
a separate committed pilot protocol must freeze the exact question, fresh training
seeds, response-model pin, retry allowances, durable call budget, horizon and stop.
No teacher invocation, development selection, final-test use or learning claim in
this observation validation stage.
