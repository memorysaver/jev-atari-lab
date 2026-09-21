# Pong research

Pong is the current test environment for the teacher-driven question optimizer.
Its small action space makes it a useful starting point, but neither mastery nor
repeatable multi-round learning has been established.

See the [first teacher study results](teacher-study-results-2026-09-20.md): one completed
round, both candidates rejected, and a technical stop before a second proposal.
The [next research design](teacher-study-next.md) separates strategy quality from
Jev question execution. No new live study is launched by that document.

## Start here

- [Research endpoint and evidence status](research-endpoint.md): what would establish
  teacher-driven improvement, the stronger feedback claim, and what is still missing.
- [Evaluation profile](evaluation.md): Pong outcomes, diagnostics, stopping rules
  and the distinction between policy and value-prediction studies.
- [Teacher log](teacher-log.md): each proposal's evidence, change and disposition.
- [Approved longitudinal teacher study](teacher-study-plan.md): three rounds,
  a no-trajectory-feedback control and final evaluation; see its
  [frozen execution protocol](teacher-study-protocol.md) and
  [diagnostic-parser continuation](teacher-study-continuation.md).
- [Published evidence](../../experiments/pong/README.md): locations of replay data,
  original model exchanges and archives.
- Shared research: [optimizer design](../teacher-optimizer.md),
  [evaluation framework](../evaluation-framework.md) and
  [roadmap](../research-roadmap.md).

## Directory contract

```text
docs/pong/
  README.md
  evaluation.md
  teacher-log.md
  teacher-rounds/<entry-id>.md
artifacts/pong/<study-id>/<round-id>/    # Local, ignored working evidence
experiments/pong/<study-id>/            # Future reviewed JSON and LFS archives
```

The directories describe different views of the same experiment. A teacher entry
links to exact questions, context, evidence and results; it does not replace raw
records. New studies should use these game-specific paths. Existing reports,
videos and archives retain their original paths and checksums. Their links below
provide one Pong entry point without rewriting historical evidence.

The CLI already accepts explicit output paths, but does not automatically route
commands by game or create the new human-readable teacher entries. Until that
integration exists, create an entry with the [shared template](../templates/teacher-round.md)
before a new proposal and publish its outcome after evaluation.

## Current experimental reference

The latest long trial used `pong-vertical-control-v2`, Jev `jev-1.13.0`, all six
native actions and probability argmax. It reached 7:18 at the 20,000-frame cap on
development seed 56. That run is unfinished. V2 is a selected experimental reference,
not a policy promoted by the earlier five-point pilot gate; that gate rejected
promotion because its candidate windows were incomplete. V3 is not promoted.

The automated study runner now records fixed-input comparisons and isolated teacher
proposals. Its first study retained v2 in both arms and stopped on a failed teacher
invocation in round two. Final tests were not run. See the linked result report.

## Historical studies

| Study | Report | Teacher change? |
| --- | --- | --- |
| Value-question pilot | [Offline prediction and selection](../pilot-2026-09-18.md) | Yes; rejected for MAE regression |
| Question representation | [Score/Choice comparison](../choice-ablation-2026-09-18.md) | Representation experiment; not a consecutive teacher round |
| Direct-policy pilot | [Vertical-control proposal](../policy-online-2026-09-18.md) | Yes; not promoted by its gate |
| Fixed-frame controls | [Four policies, four seeds](../pong-controls-2026-09-18.md) | No; existing programs |
| No-FIRE follow-up | [Manual wording revision](../pong-no-fire-2026-09-18.md) | Yes; development-informed, not promoted |
| Local match calibration | [Nine local episodes](../pong-match-calibration-2026-09-18.md) | No Jev or teacher calls |
| Long Jev trial | [20,000-frame feasibility](../pong-match-feasibility-2026-09-18.md) | No; unchanged v2 |

Observation and replay contracts remain in [observation.md](../observation.md),
[protocol.md](../protocol.md) and [replay.md](../replay.md). Historical run protocols
stay frozen; this directory does not alter their selection gates or results.

The [question execution diagnostics protocol](question-diagnostics-protocol.md) freezes the next offline
adherence analysis and separate literal Python strategy trials. No new model calls.

[Question diagnostics results](question-diagnostics-results-2026-09-20.md): low interception-rule adherence,
16 separate literal-control episodes and no new model calls.

The [stratified motion probe](motion-probe-protocol.md) freezes a three-question behavior comparison
on existing training states, capped at 520 Jev attempts, with no gameplay promotion.

[Motion probe results](motion-probe-results-2026-09-21.md): 480 fresh Jev responses; explicit reliability
wording regressed despite better coverage of rare motion-conflict states.
