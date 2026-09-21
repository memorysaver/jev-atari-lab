# Pong teacher log

This is the human-readable entry point for teacher proposals and their measured
outcomes. Entries distinguish a teacher's stated hypothesis from observed results.
They record reviewable inputs, outputs and a concise rationale, not an inferred
transcript or hidden reasoning.

## Isolated automated study

| ID | Intervention | Outcome |
| --- | --- | --- |
| [T001-A](teacher-rounds/T001-A.md) | Training-informed incoming intercept | Rejected; mean paired development gain -11.5 |
| [T001-B](teacher-rounds/T001-B.md) | No-feedback four-frame lookahead | Rejected; +4 mean but one seed regressed |
| [T002-A](teacher-rounds/T002-A.md) | No proposal: teacher invocation failed | Study incomplete; no final evaluation |

Read the [study report](teacher-study-results-2026-09-20.md). `T` entries record
fresh isolated requests with exact packets and outputs, not inferred transcripts.
The renderer `scripts/render_teacher_rounds.py` emits completed proposal records;
failed operations require an explicit entry such as T002-A.

## Manual diagnostic revisions

| ID | Intervention and provenance | Observed result |
| --- | --- | --- |
| [D001](teacher-rounds/D001-motion-reliability.md) | Explicit history-based reliability; coordinator with prior development exposure | Negative probe result; not promoted |

D001 is a separate bounded diagnostic, not a resumed isolated teacher round.
Its 480 fresh Jev responses and all regressions are preserved in the linked report.

## Existing records

| ID | Track and modification | Teacher provenance | Disposition |
| --- | --- | --- | --- |
| [H001](teacher-rounds/H001-value-first-event.md) | Value question: finite horizon and first-event semantics | Interactive assistant; imported proposal based on training feedback | Rejected: value MAE regression |
| [H002](teacher-rounds/H002-vertical-control.md) | Direct policy: coordinates, action semantics and 4px tracking | Interactive assistant; imported proposal based on training feedback | Not promoted: incomplete five-point windows |
| [H003](teacher-rounds/H003-no-fire.md) | Direct policy: explicit FIRE guidance | Interactive assistant with development evidence in context | Not promoted after follow-up |

`H` means a retrospective historical entry, documented on 2026-09-18. These are
not three consecutive rounds of an isolated optimizer. Unknown teacher model
versions, exact context and unrecorded costs stay unknown. The research role was
called Astra in the project discussion; that label is not a verified provider
model/version for a historical request. No external teacher API was used in these
three revisions.

The [question-history JSON](../../experiments/question-history.json) contains the
complete before/after programs for H001/H002. The
[no-FIRE proposal](../../experiments/no-fire-question-proposal.json) does so for H003.
That proposal's creation-time `proposed-not-evaluated` status remains historical;
the linked follow-up supplies its later outcome.

## What the runtime currently saves

| Path within a chosen run output directory | Available behavior |
| --- | --- |
| `teacher-packet.json` | The value-learning `learn` command saves its training packet |
| `proposals.json`, `question-changes.json` | `learn` saves imported/generated proposals and parsed candidate changes |
| `teacher-exchanges.jsonl`, `teacher-ledger.json` | The optional external teacher path records requests/responses and its ledger when invoked |
| `selection.json`, `selected-program.json` | Existing value and short online selection commands save gate outcomes |
| `question-changes.json` from `select-policy` | Saves the direct-policy diff, but does not recover the teacher's identity/context |

Writes depend on the stage reached; failures can leave an incomplete run. Inspect
status and ledgers, not only a filename. The optional external teacher adapter
currently serves the value-learning path; it is separate from the automatic direct-policy
loop in `study_runner.py` used by the new study. See [learning.py](../../src/jev_atari/learning.py) and
[CLI wiring](../../src/jev_atari/cli.py).

## New entries

Use the [teacher-round template](../templates/teacher-round.md). Identify entries
by study, round and candidate; proposals branching from the same parent are not
successive policy versions. Record the teacher context before generating a proposal,
then append the evaluation and decision. Commit proposal/protocol evidence before
live evaluation. Git history preserves the transition; do not replace original
programs, exchanges or frozen gates.

For each entry preserve: actual teacher identity and invocation mode; exact visible
packet and hash; training/development exposure; parent/candidate and exact diff;
hypothesis and expected behavior; the Pong profile and frozen study protocol;
per-seed results, failures and cost; selection reason; and a bounded lesson for
future testing. Use `not recorded`, `not run` or `not applicable` explicitly.

Human-authored/imported proposals need their own provenance even when there is no
HTTP transcript. Unknown interactive-teacher cost is not zero. A no-change model
evaluation belongs in the study journal and may be linked as later evidence; it
must not create a fictitious teacher update.

Future working records go under `artifacts/pong/<study-id>/<round-id>/`; reviewed
publication belongs under [experiments/pong/](../../experiments/pong/README.md).
The dedicated study renderer creates proposal entries from original artifacts;
this index and failed-operation entries are maintained explicitly.
