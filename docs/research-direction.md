# Research direction

Updated 2026-09-18. This is the adopted project direction. Method proposals below
are research questions, not completed learning results. Start at the
[research index](README.md) for current evidence and document status.

## Two goals

1. **The Atari challenge:** work toward mastering every game in the pinned ALE
   scope with Jev, publishing reproducible attempts, limitations and per-game
   success criteria. A boot check, a short clip and mastery are different milestones.
2. **The optimizer research:** discover how a teacher should turn environment
   experience into effective structured-question updates, and identify repeatable
   optimization patterns that generalize under a measured resource budget.

The second goal is a central research objective in its own right. A higher game
score is an outcome to explain; the intended paper contribution is evidence about
which optimizer mechanisms work, when they work, and what they cost. Negative
results can narrow that explanation even when no game is solved.

The project's research ideas and paper planning live in `docs/`. The
[provenance record](research-provenance.md) documents the transition from earlier
private notes. Public research must be understandable without those notes.

## System and learning target

A teacher proposes question changes from training evidence. Fixed-version Jev
answers the questions; the environment supplies observed outcomes. A selector
evaluates candidates and retains or rejects them. The learned artifact is the
external question program. The initial study fixes both teacher and Jev weights.

Let theta be the question program and p_theta the returned action distribution.
The current direct policy executes probability argmax, not a sample from p_theta:

`policy_theta(observation, history) = argmax_a p_theta(a | observation, history)`.

Its objective is expected observed return under a predeclared evaluation protocol.
Observations and history need not be a complete Markov state. Model confidence,
rule agreement and textual explanations are diagnostic signals, not reward labels.

The [teacher optimizer](teacher-optimizer.md) includes evidence selection, credit
assignment, proposal generation, candidate selection, memory and budget allocation.
Choosing a teacher model is one experimental factor, not the entire optimizer.

## Two execution tracks

| Track | Question output | Learning target and boundary |
| --- | --- | --- |
| Direct policy | One Choice over available actions | Improve actual rollout return through question changes; current videos use this track |
| Value-based | Structured judgments about consequences of each action | Learn estimates tied to a specified return, horizon and continuation; requires prediction/decision validation |

The original value-based idea remains central: strong reasoning turns experience
into questions that a fixed executor can reuse, with a hoped-for cost advantage
that still needs measurement. A structured critic may
retain several judgments before aggregation, but their scales must correspond to
an explicit target. Arbitrary confidence/cost/correctness scores do not become Q
values merely by being added together.

The implemented critic predicts the first scoring event within 240 raw frames:
the candidate action occupies the first four frames and a fixed Python heuristic
controls the remainder. It is not a frame-240 position forecast or
an optimal Q-function. Jev-continuation branching, learned aggregation, retrieval,
and TD targets are separate future ablations. Neither text revision nor the
current direct policy alone establishes Q-learning.

## Falsifiable hypotheses

| ID | Hypothesis | Required comparison or counterevidence |
| --- | --- | --- |
| H1 | Experience improves teacher proposals | Same teacher and proposal/evaluation budget, with versus without trajectory feedback |
| H2 | An optimizer mechanism improves the search | Same teacher, executor, starting question and evidence access; ablate the mechanism and compare a relevant optimizer baseline |
| H3 | Credit assignment improves useful edits | Trajectory-only feedback versus controlled action branches; charge all branch frames/calls and specify continuation |
| H4 | Structured representation helps | Single guidance versus modular/structured variants with matched information and accounted execution cost |
| H5 | Improvements accumulate and transfer | Independent optimization runs, regression cases, fresh seeds, then predefined held-out games |
| H6 | Jev offers a useful quality/cost tradeoff | Same optimizer with another executor, plus direct Python execution where the rule can be implemented |

H1 and H2 are the immediate research priorities. Study one factor at a time before
combining mechanisms. The [evaluation framework](evaluation-framework.md) defines
how to connect edits, behavior, outcomes and costs rather than treating any one
of those as sufficient evidence.

## Current evidence

The [fixed-frame controls](pong-controls-2026-09-18.md) found better aggregate
short-run return for the vertical Jev question, but only 66.85% agreement with its
written 4px rule. The [no-FIRE revision](pong-no-fire-2026-09-18.md) increased mean
confidence and rule agreement while reducing aggregate return from -3 to -5.
The [long trial](pong-match-feasibility-2026-09-18.md) reached 20,000 frames at 7:18,
with no native completion. These are useful control and measurement results.

We have not established a multi-round autonomous teacher optimizer, a repeatable
experience-driven gain, full-match mastery, cross-game transfer, or a cost advantage.
The interactive teacher has seen development results; a strictly train-only study
requires a fresh, isolated teacher context and a recorded packet hash.

## Route to a paper

The [roadmap](research-roadmap.md) stages instrumentation, controlled optimizer
studies, generalization and paper claims. [Related work](related-work.md) includes
GEPA, TextGrad, Reflexion and TypeSafe's question-feature discovery example.
Teacher-authored prompt revision is established prior art. A defensible contribution
must be a measured mechanism, representation/credit result, generalization finding,
or reproducible quality/cost result with appropriate baselines and uncertainty.
