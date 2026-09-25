# Seaquest teacher and coordinator log

The [five-round execution follow-up](execution-five-round-results-2026-09-25.md)
added two coordinator-authored same-rule wording proposals. Round three's
[signed-delta revision](../../experiments/seaquest/execution-five-round-v1/records/round-03/proposal.json)
passed its training screen and was sealed; round four's
[target-selection examples](../../experiments/seaquest/execution-five-round-v1/records/round-04/proposal.json)
were rejected for branch regressions. The selected revision then failed final
execution and gameplay gates. No wording was promoted, and the five-round budget
is closed. Neither proposal was an isolated teacher output.

No isolated Seaquest teacher has been invoked. The completed
[ten-round study](ten-round-results-2026-09-24.md) contains seven proposals authored
by the interactive coordinator from training feedback. Exact programs, hypotheses,
evidence references and risks were recorded before evaluation. Later proposals
also used source-reported manual mechanics. There was no no-feedback arm, independent
optimizer replication or external teacher transcript.

The [original protocol](ten-round-protocol.md) and separately frozen
[HTTP 520 continuation](ten-round-continuation-protocol.md) define the data splits,
budget and provenance. All ten rounds completed; no further calls remain authorized
under that allocation.

| Round | Coordinator proposal | Training mean | Selection |
| --- | --- | --- | --- |
| 2 | [Depth band and firing](../../experiments/seaquest/ten-round-v1-continuation/records/round-02/proposal.json) | 190 | Not selected |
| 3 | [Same-lane enemy facing](../../experiments/seaquest/ten-round-v1-continuation/records/round-03/proposal.json) | 350 | Selected before held-out access |
| 4 | [Always seek one diver while empty](../../experiments/seaquest/ten-round-v1-continuation/records/round-04/proposal.json) | 160 | Not selected |
| 5 | [Explicit facing wording/example](../../experiments/seaquest/ten-round-v1-continuation/records/round-05/proposal.json) | 260 | Not selected |
| 6 | [Shallower depth band](../../experiments/seaquest/ten-round-v1-continuation/records/round-06/proposal.json) | 340 | Not selected |
| 7 | [Later oxygen return](../../experiments/seaquest/ten-round-v1-continuation/records/round-07/proposal.json) | 320 | Not selected |
| 8 | [Delay one-diver collection](../../experiments/seaquest/ten-round-v1-continuation/records/round-08/proposal.json) | 280 | Not selected |

Round one measured the unchanged baseline (mean 70) on the same training starts.
Round nine evaluated the sealed round-three program: development mean 370 versus
80 baseline. Round ten used that same program: final mean 290 versus 80 baseline.
Both two-seed gates passed with no regression. This is bounded question-policy
improvement, not repeatable teacher optimization or a causal feedback result.

The earlier [fixed-question pilot](fixed-question-pilot-results-2026-09-24.md)
completed two 80-point games; all actions matched DOWN when active and NOOP
otherwise. Its [baseline program](../../examples/seaquest-policy-program.json)
and local controls were coordinator-authored, not discovered by an isolated teacher.
The pilot used a different start contract and is not the ten-round study's paired control.

Future entries follow the [teacher-round template](../templates/teacher-round.md)
and [evaluation profile](evaluation.md). Preserve proposed, executed, selected and
final-tested stages separately, including negative outcomes and technical stops.
