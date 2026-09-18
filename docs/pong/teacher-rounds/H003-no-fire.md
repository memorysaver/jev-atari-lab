# H003: Explicit FIRE guidance

Retrospective entry, recorded 2026-09-18; manual development-informed follow-up.
Exact original proposal/diff:
[no-fire-question-proposal.json](../../../experiments/no-fire-question-proposal.json).
Full results: [no-FIRE follow-up](../../pong-no-fire-2026-09-18.md).

## Teacher and input

- Source: interactive coding assistant responding to a user-requested clarification.
- Exact teacher model/version and complete input transcript: not recorded.
- Prior development results were already in context. This is not a train-only round.
- No external teacher API was used. Existing data already had zero FIRE-variant
  choices; the proposal did not address an observed FIRE-selection failure.

## Question change and hypothesis

Parent `pong-vertical-control-v2`:
`2ef87250f491fcd5a2ba72f29e3f03b6bc66c4ab7315e9e724df76352326633d`.

Candidate `pong-vertical-control-no-fire-v3`:
`840e739a781112d299f044e6a026bf6642edad45741ed1222b8a98790bad3d54`.

Replace a non-FIRE preference with explicit definitions of FIRE combinations and
an instruction to choose RIGHT, LEFT or NOOP. Keep all six options selectable,
the 4px rule, criteria, observation and decoder unchanged. The hypothesis was
clearer policy interpretation, not a validated prediction of higher return.

## Evaluation and decision

Frozen [follow-up protocol](../../no-fire-rerun-protocol.md), Jev `jev-1.13.0`,
development seeds 36/37/46/47, 2,000 frames per episode. V2 is a reused historical
baseline. Aggregate return changed from -3 to -5; per-seed differences were
+1, +1, -5, +1. Mean confidence rose from 0.5786 to 0.6087 and literal-rule agreement
from 66.85% to 70.15%. Both policies selected zero FIRE variants. Diagnostics were
measured on each policy's visited states, not identical-input probes.

Disposition: not promoted. Do not reinterpret the original proposal's unevaluated
creation-time status as its final result. The follow-up supplies the outcome.

Combined usage: 2,089 of 2,200 Jev HTTP attempts, 3,625,672 input tokens and 143,259
output tokens. A transport failure left an 87-decision prefix; a separate recorded
continuation restarted that seed, and one HTTP 529 was retried. All partial work
remains in the [results](../../../experiments/pong-no-fire-study-results.json) and
[archive manifest](../../../experiments/pong-no-fire-study-2026-09-18.manifest.json).
Interactive teacher cost was not recorded; no teacher API cost was incurred.

## Lesson to test

Higher confidence and closer instruction adherence did not imply better aggregate
return in this sample. Use same-input repeated probes to isolate wording effects,
then evaluate reward independently. Four reused development seeds do not establish
a reliable causal advantage for either wording.
