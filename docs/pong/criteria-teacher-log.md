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

## First development seed, 2026-09-23 local time

On seed 106 at the shared 2,000-frame cap, fresh v2 scored 2:0 (return +2),
the A candidate scored 1:4 (return -3), and the B candidate scored 1:3 (return -2).
The paired candidate gains are -5 and -4. Both candidates therefore fail the
prospective nonregression condition on this seed. The remaining scheduled seed
must still complete before recording the full round and starting the next one.
This is one development comparison, not a population estimate or final-test result.

The original 480 diagnostic responses passed an additional offline request/response
audit. B's seed-106 episode recorded one 60.01-second transport failure and its
successful bounded retry, with 501 attempts for 500 decisions. The episode replay
verified. No episode restart, clock reset or model substitution was performed.
The in-progress source of truth remains the live operation records, not this snapshot.

## Search 1 round 1 completed

All eight scheduled episodes and the 480-query probe completed. Both candidates
were rejected; both arms retain v2 for round two.

| Development seed | Fresh v2 return | A return | B return | A gain | B gain |
| --- | ---: | ---: | ---: | ---: | ---: |
| 106 | +2 | -3 | -2 | -5 | -4 |
| 107 | -2 | -6 | -1 | -4 | +1 |
| Mean | 0 | -4.5 | -1.5 | -4.5 | -1.5 |

A separate offline round audit replayed the eight episodes, validated all original
probe exchanges, reconstructed both teacher packets from training data, matched
the selected candidates to their original teacher outputs, and recomputed both
rejections. Its local receipt is `artifacts/pong/criteria-C1R1-audit/verification.json`.
The receipt covers this completed round only, not the still-running study's global
budget or future final evaluation. Round use: 4,481 Jev attempts and two teacher
invocations. The audit made zero model calls.

Round two has started. B proposed `pong-bounded-incoming-lead`; A's next proposal
will receive new v2 training trajectories from seeds 102/103. Detailed development
outcomes stay outside both teacher packets. The selected current v2 and prior
proposals still expose indirect selection history, as declared in the protocol.
