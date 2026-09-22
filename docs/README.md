# Research and experiments

Jev Atari Lab has two connected goals: work toward mastering every game in the
[pinned Atari scope](games.md), and discover effective **teacher-driven optimizers
for structured question policies**. Atari provides environments in which proposed
optimization patterns can be measured, challenged and reproduced.

As directed by the project owner on 2026-09-18, **this directory is the canonical
home for this project's research ideas, hypotheses, methods, decisions and paper
planning**. Readers do not need access to a private research repository. Historical
notes elsewhere remain provenance; new project research belongs here. Original
machine-readable evidence and immutable LFS archives remain in
[experiments/](../experiments/README.md); code and tests retain their own directories.

Latest: [compact wording results](pong/wording-probe-results-2026-09-22.md). The same-rule
restatement regressed from 76/160 to 62/160 agreement and failed its prospective screen.
All 480 fresh responses are retained locally; no gameplay or final test was run.

## Research map

Active continuation: the [criteria-edit teacher protocol](pong/criteria-teacher-protocol.md)
uses three independent A/B searches, two rounds and sealed final evaluation within
60,000 Jev attempts. The [study log](pong/criteria-teacher-log.md) records isolated proposals.

| Document | Purpose | Status |
| --- | --- | --- |
| [Research direction](research-direction.md) | Two goals, hypotheses, current evidence and limits | Adopted project direction |
| [Teacher optimizer](teacher-optimizer.md) | What is optimized, optimizer components, round records and pattern discovery | Design; first implemented teacher study incomplete |
| [Evaluation framework](evaluation-framework.md) | Edit, behavior, outcome and cost measures; controls and uncertainty | Proposed framework; some underlying logging exists |
| [Research roadmap and paper plan](research-roadmap.md) | Staged studies and evidence required for paper claims | Planned studies; no new live run authorized by this document |
| [Related work](related-work.md) | Primary sources and boundaries of novelty claims | Targeted review; methods not reproduced |
| [Research provenance](research-provenance.md) | Origins, ownership transition and implementation decisions | Historical record |

## Experimental evidence

Game-specific research starts at [Pong](pong/README.md), with its own
[evaluation profile](pong/evaluation.md) and [teacher log](pong/teacher-log.md).
The [Pong research endpoint](pong/research-endpoint.md) distinguishes teacher-authored
policy improvement from a repeatable benefit of experience feedback; neither is
established by the current evidence.
The approved [longitudinal teacher study](pong/teacher-study-plan.md) has a
[frozen protocol](pong/teacher-study-protocol.md) and an explicit
[parser continuation record](pong/teacher-study-continuation.md). Its
[incomplete results](pong/teacher-study-results-2026-09-20.md) lead to a
[proposed strategy-versus-execution study](pong/teacher-study-next.md).
For new games, use the shared [evaluation-profile](templates/game-evaluation.md)
and [teacher-round](templates/teacher-round.md) templates. Outcomes and mastery
criteria are game-specific; provenance, cost and evidence requirements are shared.

| Experiment | What it establishes | What remains open |
| --- | --- | --- |
| [First teacher study](pong/teacher-study-results-2026-09-20.md) | Audited A/B proposals, behavioral probes and rejection; technical stop in round two | Multi-round learning and final generalization |
| [Value pilot](pilot-2026-09-18.md) | A question revision improved Brier score but regressed MAE and was rejected | Improved control or TD learning |
| [Score/Choice comparison](choice-ablation-2026-09-18.md) | Offline representation comparison | General representation superiority |
| [Direct-policy pilot](policy-online-2026-09-18.md) | Real Jev-controlled Pong trajectories | Complete-match performance |
| [Fixed-frame controls](pong-controls-2026-09-18.md) | Existing Jev and Python rules differ in actions and short-run return | Experience-driven learning |
| [No-FIRE revision](pong-no-fire-2026-09-18.md) | Higher confidence/adherence did not improve aggregate return | Reliable causal effect of the wording |
| [Match calibration](pong-match-calibration-2026-09-18.md) | Nine local training episodes and duration/censoring evidence | A reliably stronger interception controller |
| [Long Jev trial](pong-match-feasibility-2026-09-18.md) | 20,000-frame fixed-policy run ending at 7:18, unfinished | Native completion, wins and population performance |

Experiment protocols remain frozen with their reports. Later research directions
must not retroactively change budgets, gates, data splits or interpretations of
those runs. A video is evidence of one execution, not a learning curve.

## Reproduction and environment contracts

- [Pong benchmark interpretation](pong-benchmark.md) and [game coverage](games.md).
- [Observation contract](observation.md) and [Pong protocol](protocol.md).
- [Replay guide](replay.md), [validation history](validation.md), and
  [artifact journal](../experiments/README.md).
- Frozen protocols: [fixed-frame controls](pong-controls-protocol.md),
  [no-FIRE follow-up](no-fire-rerun-protocol.md), and
  [native-match feasibility](pong-matches-protocol.md).

Use explicit evidence labels in new research: **observed** for our executed runs,
**source-reported** for external performance claims, **proposed** for unrun methods,
and **unconfirmed** for unresolved conclusions. Link claims to a report, source,
program version and experiment revision as appropriate. Preserve negative results.

The [question execution diagnostics protocol](pong/question-diagnostics-protocol.md) freezes the next offline
adherence analysis and separate literal Python strategy trials. No new model calls.

[Question diagnostics results](pong/question-diagnostics-results-2026-09-20.md): low interception-rule adherence,
16 separate literal-control episodes and no new model calls.

The [stratified motion probe](pong/motion-probe-protocol.md) freezes a three-question behavior comparison
on existing training states, capped at 520 Jev attempts, with no gameplay promotion.

[Motion probe results](pong/motion-probe-results-2026-09-21.md): 480 fresh Jev responses; explicit reliability
wording regressed despite better coverage of rare motion-conflict states.
