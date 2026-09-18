# Teacher study v1: diagnostic-parser continuation

This is an implementation incident and explicit continuation addendum to the
[frozen protocol](teacher-study-protocol.md). The original protocol, source
revision, stopped status and model evidence remain preserved. No experimental
hypothesis, proposal, split, gate, model, budget or deadline changes.

## Incident

The initial runner at `94ceb931b883b89e970786eee29f49ecb819faac` completed and
replayed both round-one training episodes: seed 60 scored 6:10 and seed 61 scored
4:9, each capped at 10,000 frames. Those caps are unfinished native games.
At the stop, accounting recorded 5,000 Jev HTTP attempts and one teacher invocation.
No development or final evaluation had started.

Teacher A returned one final JSON proposal, followed by `turn.completed`, and
exited with code zero. The recorder incorrectly classified an `error` item as
non-message tool activity and raised before saving `proposal.json`. Its original
`events.json` retained the single complete response and usage; `execution.json`
retained the unexpected item type. The specific diagnostic message was discarded
by the old recorder and cannot be reconstructed. We do not infer its cause.

The [Codex noninteractive documentation](https://learn.chatgpt.com/docs/non-interactive-mode)
distinguishes error events from command and tool execution. The corrected parser
records diagnostic markers separately, still rejects command/tool activity
(including started-only items), and requires a completed turn. Teacher inputs,
requested model/high settings, filesystem isolation and tool restrictions are
unchanged.

## Continuation rules

Recover only the original single JSON response with the original packet hash,
zero exit code, completed turn and precisely the recorded diagnostic-only
failure. Validate its original schema, length and evidence references. A separate
`recovery.json` records the original hashes and exact proposal; never overwrite
the failed execution record or ask for another candidate.

The recovered proposal is `pong-intercept-target-v1`, program hash
`afc839f55b05a44af75ee372ee28fce9ebdd1a02c3bd6d2170580f7e3fdea498`.
Its strategy uses reflected predicted arrival height for an incoming ball and
current-height tracking otherwise. This is a teacher hypothesis awaiting the
predeclared probes and development evaluation, not an improvement claim.

Before continuation, save a receipt containing the original stopped status and
budget, original plan hash, hashes of every existing immutable study file, and
the new clean source revision. Explicitly pass this receipt to the runner.
Completed original episodes may then be reused; new episodes record the corrected
source revision. The original root plan remains unchanged.

The global start remains Unix epoch `1789748981.6822329`. All HTTP and teacher
counts carry forward, including the original teacher call. The offline parser
repair uses zero new model calls and consumes no teacher resampling allowance.
The original 24-hour deadline, 220,000-attempt ceiling, final reservation and
maximum eight teacher invocations remain in force.

Publication must include the stop and continuation receipts, both runner logs,
original failed metadata, exact recovered response and all subsequent evidence.
The aggregate audit must accept only these registered source revisions and check
the preserved artifact hashes. This technical intervention and missing original
diagnostic message must remain explicit limitations in the final report.
