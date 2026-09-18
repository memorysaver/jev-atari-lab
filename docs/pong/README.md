# Pong research

Pong is the current test environment for the teacher-driven question optimizer.
Its small action space makes it a useful starting point, but neither mastery nor
repeatable multi-round learning has been established.

## Start here

- [Evaluation profile](evaluation.md): Pong outcomes, diagnostics, stopping rules
  and the distinction between policy and value-prediction studies.
- [Teacher log](teacher-log.md): each proposal's evidence, change and disposition.
- [Proposed longitudinal teacher study](teacher-study-plan.md): three rounds,
  a no-trajectory-feedback control and final evaluation; awaiting owner approval.
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

Next, implement repeated fixed-input comparisons and complete round records before
running the proposed three-round teacher pilot. Freeze a new study protocol and
use a fresh teacher context for train-only proposals. The current interactive
conversation has already seen development results.

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
