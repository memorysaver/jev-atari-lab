# Freeway evaluation profile v1

Identity: ALE/Freeway-v5, pinned environment versions and ROM hash in every
manifest, mode 0 / difficulty 0, three native actions NOOP/UP/DOWN. Observation
freeway-objects-v1 contains the left chicken, ten lane boxes, and three timed
snapshots. Car wrap and collision recovery limit motion inference. Left-edge
boxes at x<=0 can be invisible; bounding boxes do not certify collision geometry.

The [frozen protocol](ten-round-protocol.md) defines 16-frame actions, sticky 0.25,
seeded NOOP startup, 9,000-frame ceiling and native termination. Native reward
counts successful road crossings. Primary endpoint is controlled native return;
prefix return, end reason, action histogram and duration are separate diagnostics.
Timer completion is not mastery; no mastery target has been adopted.

Compare generic Jev, coordinator revisions, always-UP and predictive waiting with
the same native actions and observations. Local controls do not use model calls.
Matched-state adherence labels denote a declared heuristic, not optimal choices.
Report branch/motion composition and coverage, including absent DOWN-rule labels.

Training/development/final seeds are disjoint. Only training feedback informs
proposals. Independent units are seeded episodes, not correlated frames. Report
raw per-game scores; do not compare raw scores with Pong or Seaquest. Two held-out
seeds per split and one adaptive search cannot establish optimizer reliability.

Official mechanics: https://ale.farama.org/environments/freeway/
