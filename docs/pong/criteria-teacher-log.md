# Criteria-edit teacher log

Status: prepared before live access, 2026-09-22. Three independent searches with
two A/B rounds follow the [frozen protocol](criteria-teacher-protocol.md).

A receives training trajectories/outcomes; B receives proposal-only memory. The
requested teacher is GPT-6 Astra with high reasoning in packet-only filesystem
isolation. Provider model attestation is unavailable. The coordinator has earlier
development exposure and designs the method, not the evaluated candidates.

No proposal exists at protocol preparation time. Entries will render exact packet
and program hashes, guidance and all six criteria, hypothesis/evidence references,
predicted changes/regression risks, invocation status, probes, selections and
costs from saved artifacts. IDs are `C<search>-R<round>-<arm>`. Do not invent missing
transcripts or infer unrecorded reasoning. Manual D001/D002 entries stay separate.

The edit space now includes all six action-criterion descriptions. It adds no
question, sensor, action mask or decoder change. Observed gameplay return is the
endpoint; question adherence alone is not success.

## Execution started

The live run started from frozen source `4b61d87` in
`artifacts/pong/criteria-teacher-v1/`. Read its `status.json`, `budget.json` and
per-operation records for current progress; this paragraph is not a live counter.
The first B invocation completed with `pong-incoming-intercept`; the first A
invocation completed with `pong-reflected-intercept-v1` after replayed training
episodes on seeds 100 and 101. These are hypotheses awaiting development selection.

The first training episodes used unchanged v2 and scored 3:1 and 0:5 within 2,000
controlled frames. They are training evidence, not candidate improvement or native
match wins. Both teacher invocations completed without a repair or access retry.
Final evidence is sealed only after all scheduled selections; it has not been used
to author these proposals.

The offline auditor was added separately after the live source freeze. It does not
change the running experiment. `scripts/verify_criteria_study.py` reconstructs
original requests/responses, training packets, development decisions, replay and
sealed final comparisons without making model calls. Its synthetic tampering test
rejects changed actions, criteria and viability-screen records.
