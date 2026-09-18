# Teacher round template

Copy this structure to `docs/<game>/teacher-rounds/<entry-id>.md`, fill it in and
link it from that game's teacher log. This is a documentation template, not an
executed proposal, a JSON schema or an automatically generated runtime log.
Replace placeholders with actual records; unavailable values are not zero.

## Identity and status

- Entry, study, round and candidate IDs; parent entry/program ID.
- Recorded/proposed/evaluated timestamps with timezone; code/optimizer revision.
- Track: direct policy, value prediction or another explicitly defined contract.
- Status: planned, proposed, evaluating, accepted, rejected or inconclusive.
- Provenance: prospective, retrospective, imported or external model invocation.

## Teacher and visible evidence

- Actual teacher provider/model/version if available; requested versus returned ID.
- For an interactive assistant, record that invocation mode and known identity;
  never infer a historical version from the assistant's current name.
- System instructions, visible packet and public proposal/response artifact paths
  and hashes; sampling settings and evidence-selection rule.
- Evidence IDs, split, source trajectories and any previous development exposure.
- Context isolation method, prior memory, accepted/rejected proposals visible.
- If no exact transcript exists, say so. Do not reconstruct one as an original.

## Proposed intervention

- Full parent/candidate program artifacts and hashes; exact changed fields/diff.
- Edit operator and target component; changed versus held-fixed contracts.
- Evidence-based problem description and concise stated rationale.
- Hypothesis, predicted action changes, applicable situations and regression risks.
- Required validation and the condition that would disconfirm the hypothesis.

## Frozen evaluation plan

- Game profile version and study-protocol path/hash.
- Train/development/final-test separation; teacher and selector visibility.
- Primary endpoint, seed/repeat counts, episode caps and selection rule.
- Probe set/hash, old/new repeats, noise comparison and situation definitions.
- Teacher/Jev attempt caps, retry/stop rules and total environment budget.
- Record the proposal and protocol before results; do not revise the gate afterward.

## Observed results and resources

- Per-seed old/new scores, paired differences, denominators and uncertainty.
- Completion, truncation, failed attempts, missing evaluations and deviations.
- Probe action flips/distribution changes and repeated-query noise, or `not run`.
- Teacher and executor calls/tokens/costs separately; actual versus estimated cost.
- Environment collection/branch/evaluation/replay frames separately; simulation
  time, API time and end-to-end time separately.
- Machine-readable results, original exchanges, videos, archive manifest and audit.

## Selection and bounded lesson

- Selected program/hash; accepted/rejected/inconclusive and measured reason.
- Separate algorithmic gate outcome from a later manual research-reference choice.
- Which hypothesis survived or failed; alternative explanations and regressions.
- Evidence level: exploratory association, replicated pattern or controlled mechanism.
- Applicable conditions, contradictory cases and proposed next comparison.
- Later evidence is appended with dates/links; original run artifacts stay immutable.
