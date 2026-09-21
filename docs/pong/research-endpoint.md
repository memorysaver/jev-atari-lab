# Pong research endpoint and evidence status

Documented 2026-09-21. This defines the research question and proposes the next
confirmatory study's success and stopping criteria. It does not launch a study,
allocate a new API budget, or change any historical frozen protocol. Numerical
thresholds and sample sizes remain to be frozen before the next study.

## Core question

Can a teacher improve a fixed Jev player's Pong performance by revising its
structured question policy using experience from the environment?

The intervention is the question program. Jev weights/model version, observations,
history, available actions, decoder and environment settings stay fixed. Both
teacher weights and Jev weights remain unchanged. Improvement refers to the
resulting controller's observed game performance, not an increase in the underlying
model's general capability or a demonstration of Q-learning.

For this stage, use one primary outcome: episodic return (points scored minus
points conceded) with a shared, predeclared raw-frame cap and native termination.
A capped episode supports a bounded-horizon performance claim, not a full-match
win claim. If the next study instead targets native-match performance, freeze that
different endpoint before running it; do not choose the more favorable metric later.

## Two evidence milestones

**Milestone 1: teacher-authored policy improvement.** Freeze the selected policy
after training/development selection, then compare it with the frozen v2 baseline
on untouched final-test seeds. Report paired return differences, uncertainty,
all scheduled episodes and API failures. The predeclared success rule must require
a practically meaningful positive effect with enough precision to distinguish it
from run variation. One successful test would support a narrow proof of concept;
repeatable optimization requires independent repetitions of the entire teacher
search, not just more episodes for the same selected question.

**Milestone 2: benefit from experience-driven optimization.** Compare independent
teacher searches with trajectory/outcome feedback against searches without that
feedback, starting from the same baseline. Keep proposal opportunities, selection
procedure, allowed edits and evaluation conditions comparable, and record actual
teacher/Jev token, call and time costs. Freeze how resource differences will be
handled. Evaluate the selected policies on the same untouched final-test schedule.
The feedback arm must improve over baseline and outperform the no-feedback arm
under the predeclared effect and uncertainty criteria. Otherwise a useful revision
may demonstrate prompt search without establishing a benefit from experience.

Repetition counts, seed counts, episode repeats, horizon, minimum meaningful gain,
uncertainty method and decision thresholds are open design parameters. Choose them
using development variance and the available budget, before opening final tests.
Emulator frames and repeated responses on one state are not independent runs.

Pong's teacher-optimizer research stage reaches its positive endpoint at milestone
2 with replicated evidence. Milestone 1 is a useful intermediate result. Neither
requires winning every match or achieving Atari mastery. Mastery is a separate
project objective with its own native-match endpoint and threshold.

## What the current evidence establishes

| Question | Current evidence | Verdict |
| --- | --- | --- |
| Can Jev operate the game through one action Choice question? | Real trajectories, raw requests/responses and replayable frames | Demonstrated for the recorded runs |
| Can a teacher edit the question and alter Jev behavior? | Two isolated teacher proposals and fixed-input action changes | Demonstrated; behavior change is not improvement |
| Have any useful question variants appeared? | Earlier manual/development comparisons favored v2 in short windows | Exploratory evidence; not a held-out teacher learning result |
| Did the isolated experience-informed teacher improve gameplay? | First candidate lost 0:21 twice; mean development gain -11.5 | Negative for that candidate |
| Did the no-feedback candidate establish improvement? | Development gains -3 and +11; mean +4; rejected by its frozen gate | Mixed exploratory outcome; no final test |
| Did explicit motion-reliability wording improve execution? | Agreement with the conservative rule fell from 99/160 to 73/160 | Negative diagnostic result; no gameplay measured |
| Has the selected teacher policy improved on untouched final tests? | Final tests were not run; both arms retained v2 | Not established |
| Does feedback produce a repeatable optimizer advantage? | One incomplete optimization trajectory per arm | Not established |

Sources: [short-window controls](../pong-controls-2026-09-18.md),
[teacher study results](teacher-study-results-2026-09-20.md),
[question diagnostics](question-diagnostics-results-2026-09-20.md), and
[motion probe results](motion-probe-results-2026-09-21.md).

The first teacher study stopped during round two after a failed teacher invocation.
That incomplete execution is not evidence that the general approach cannot work.
The later motion wording was a development-informed manual diagnostic, not a new
isolated teacher round. Literal Python strategy results also cannot substitute for
Jev gameplay. At present neither milestone has been met.

## Next study and finite stopping rule

1. Use development-only diagnostics to screen whether a proposed question executes
   its intended behavior and preserves basic fallback/up/down/hold behavior. Freeze
   screening rules and proposal limits prospectively. Adherence is a diagnostic,
   not the primary success metric or proof that a rule is strategically optimal.
2. Freeze the teacher procedure, baseline, feedback control, splits, candidate
   selection, repetitions, primary outcome and full budget before model calls.
   Reserve enough budget for the final comparison rather than spending it all on
   candidate search. Preserve rejected candidates and failed operations.
3. Run the bounded search on training/development data. Lock each run's selected
   policy before final evaluation. Include unchanged-baseline selections when no
   candidate qualifies; do not report only searches that found a promising edit.
4. Run and report the final comparison once, using the predeclared analysis. Keep
   seeds 66/67 and every inspected diagnostic source in development/training.
   Previously reserved seeds 68/69/78/79 remain unused; they are not automatically
   a sufficiently sized final test. Once test outcomes inform another edit, those
   cases cannot serve as untouched confirmation of that edit.
5. Stop at the frozen round/call/time budget and publish a supported positive,
   negative or inconclusive result. A technical stop remains incomplete. Do not
   extend the same study or move its thresholds until a favorable result appears.

This keeps the next work focused: establish actual policy improvement, then test
whether experience explains a repeatable advantage. More probes, higher action
confidence, a favorable video or a larger archive do not by themselves advance
either milestone.
