# Interrupted original Seaquest ten-round allocation

The original [protocol](../../../docs/seaquest/ten-round-protocol.md) stopped on
HTTP 520 in round 4 seed 321, after 76 model decisions in that episode. Rounds
1..3 and round 4 seed 320 completed. This original batch remains incomplete.

All eight full/partial trajectories, original successful responses, failed-request
metadata and full/partial MP4s are retained. Every trajectory and video frame count
passed the [stop audit](stop-verification.json). A successful retry of HTTP 529 and
the terminal HTTP 520 remain in [cost/accounting records](stop-costs.json).

- [Original plan](plan.json), [results](results.json), [budget](budget.json), [closure](closure.json).
- [Archive manifest](seaquest-ten-round-v1-interrupted.manifest.json).
- [Prospective continuation](../../../docs/seaquest/ten-round-continuation-protocol.md).

The continuation inherits existing attempts and deadline; it must not double-count
these imported records as new calls or relabel this original batch complete.
The archive was restored and all eight trajectories/videos passed an identical
[restored audit](restored-verification.json). Local evidence only; no remote
publication or retrieval claim.
