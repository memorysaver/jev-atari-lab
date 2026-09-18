# Pong teacher log

This is the human-readable entry point for teacher proposals and their measured
outcomes. Entries distinguish a teacher's stated hypothesis from observed results.
They record reviewable inputs, outputs and a concise rationale, not an inferred
transcript or hidden reasoning.

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
currently serves the value-learning path; it is not an automatic direct-policy
teacher loop. See [learning.py](../../src/jev_atari/learning.py) and
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
The human-readable log is maintained explicitly for now, not emitted by the CLI.
