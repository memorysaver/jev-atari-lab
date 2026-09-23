# Matched local controls for the first Seaquest Jev pilot

Prospectively scheduled in the [pilot protocol](../../../docs/seaquest/fixed-question-pilot-protocol.md).
Random and scripted-sweep controls use training seeds 310/311, the same 3,200-frame
cap, sticky 0.25, four-frame action hold and no automatic startup controller.
They are coordinator-authored controls, not learned policies.

[Plan](plan.json), [results](results.json), [archive manifest](seaquest-pilot-v1-controls.manifest.json),
[restored verification](restored-verification.json).

| Control | Seed 310 return / frames | Seed 311 return / frames |
| --- | --- | --- |
| Random | 40 / 1,713 | 40 / 2,393 |
| Scripted sweep | 80 / 3,200 | 80 / 3,200 |

All four original trajectories replayed, then the archive was restored and each
trajectory independently replayed again. Every original raw-frame RAM/RGB hash,
reward/life/end flag and recorded action matched. This is local LFS preservation;
no remote publication or retrieval claim. The archive includes two videos and
both original and initial replay records. Zero API calls.

Reproduction uses `scripts/seaquest_calibration.py:trajectory` with `frames=3200`,
`seed` and `policy` from the plan; supply recorded JSONL rows for replay. Its original
CLI default of 8,000 frames is not the matched-pilot horizon. The fixed controls do
not inspect their semantic observations, so their v1 calibration decoder cannot
supply an action advantage over the v2 Jev observation contract.
