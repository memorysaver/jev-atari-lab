# Seaquest research

Started 2026-09-24 after the owner closed the [Pong stage](../pong/candidate-feedback-results-2026-09-24.md).
The [first fixed-question Jev pilot](fixed-question-pilot-results-2026-09-24.md)
completed two native games at 80 points each. All 1,108 decisions matched DOWN when
objects were active and NOOP otherwise. Original and restored evidence replayed;
reported cost was US$0.119, with zero isolated teacher calls.

The initial calibration exposed animation/visibility errors. Observation v2 passed
its frozen pixel-support gate on four fresh training trajectories, while retained
box disagreements and unvalidated object identities limit its interpretation.

- [Pilot results](fixed-question-pilot-results-2026-09-24.md): actions, matched controls, costs and limitations.
- [Pilot protocol](fixed-question-pilot-protocol.md): frozen question and execution budget.
- [Observation v2 results](observation-v2-results-2026-09-24.md) and [protocol](observation-v2-protocol.md).
- [Initial calibration results](calibration-results-2026-09-24.md) and [protocol](calibration-protocol.md).
- [Evaluation profile](evaluation.md): environment, observation limits and endpoints.
- [Teacher log](teacher-log.md): no isolated proposals yet.
- [Selection rationale](../next-atari-game-2026-09-23.md).

The next research question is whether state-dependent action criteria can resolve
the observed action collapse. Any next study needs a separate frozen budget and
measured state diversity. The pilot's unused capacity is closed.

Seaquest is a new development game, not a held-out transfer evaluation. We do not
carry a claim of Pong mastery or teacher-learning benefit into this experiment.
