# Freeway coordinator log

The [ten-round protocol](ten-round-protocol.md) allocates six adaptive question
revisions, authored by the interactive coordinator. Zero isolated teacher calls.
Each round's immutable proposal.json records wording, hash, rationale, source
revision and prior feedback paths before any associated evaluation.

Round 1 observed native completion for all twelve local games. At hold 16, random
scored 0/0; always-UP 27/22; reactive waiting 22/21; predictive waiting 27/28.
At hold 8, always-UP scored 27/22 and predictive waiting 30/25. Thus motion-aware
waiting has a limited observed mean advantage, with strong always-UP performance.
No model experiment or learning claim follows from this local calibration alone.

## Six completed training revisions

| Round | Hypothesis | Native training mean | Disposition |
| --- | --- | ---: | --- |
| 3 | Explicit lane-entry prediction may elicit waiting | 24.5 | Sealed by primary score; tied baseline |
| 4 | Three concrete training examples may make overlap calculations executable | 19.5 | Retained negative result |
| 5 | Analytic swept interval may simplify predicted overlap | 18 | Retained negative result |
| 6 | Reactive four-inequality rule removes prediction burden | 12.5 | Strategy change; many false waits |
| 7 | Select one lane explicitly before the reactive x check | 19 | Own-rule diagnostic improved, score below baseline |
| 8 | Restore prediction after successful lane lookup formulation | 10 | Waiting improved, above-traffic branch regressed |

Round 7's lane-binding hypothesis is an interpretation, not a verified internal
mechanism. Reactive own-rule metrics are explicitly post-hoc and never change the
frozen primary selection. Round 9 sealed round 3 before development access; round
10 must use that same program regardless of development outcome.

## Closed evaluation

Development: generic and selected Jev both 27/19, mean 23, gain zero.
Final: both 23/26, mean 24.5, gain zero. Both gates failed; no revision promoted.
Predictive local controls scored 30/29 development and 29/29 final. All four
held-out model pairs collapsed to UP throughout. Exactly ten rounds completed;
11,711 attempts consumed, 4,289 unused attempts closed.

[Full results and lessons](ten-round-results-2026-09-26.md).
