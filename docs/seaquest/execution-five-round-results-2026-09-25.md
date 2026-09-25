# Five-round Seaquest execution study: no wording revision promoted

Exactly five rounds completed and stopped. The selected wording revision improved
its reused training packet but failed both final gates: movement-branch macro
agreement fell from **68.75% to 60.94%**, and paired game mean return fell from
**300 to 240**. Preserve the negative result; no new wording was promoted.

This comparison uses the prior round-eight **late-diver question** as reference,
not the original DOWN/NOOP baseline or the prior round-three simple winner.
Different seeds and protocols must not be pooled into one improvement curve.

[Frozen protocol](execution-five-round-protocol.md) ·
[Earlier lessons](lessons-2026-09-25.md) ·
[Reviewed evidence](../../experiments/seaquest/execution-five-round-v1/README.md) ·
[Ten full recordings](../../experiments/seaquest/execution-five-round-v1/videos.md)

## What happened in each round

1. **Literal strategy controls:** execute the simple and late-diver rules directly
   on the same training starts as their historical Jev trajectories. Four local
   episodes, zero model calls. This tests the intended strategies rather than
   assuming their instructions describe good play.
2. **Fresh fixed-state baseline:** query both original programs on 96 identical
   training observations. Each question has its own literal target; this is not
   a pure complexity comparison. The late-diver reference matched 40/96 overall,
   with movement macro agreement 14.06%. The simple question matched 71/96 against
   its own rule, but its expected-UP stratum had only one state, so it did not
   meet the primary movement-coverage requirement.
3. **Signed deltas and ordered priorities:** a coordinator-authored same-rule
   revision improved movement macro agreement from its fresh reference's 12.5%
   to 37.5%. DOWNFIRE matches rose from 1/16 to 15/16. It passed the prospective
   training screen despite a permitted 1/16 RIGHTFIRE regression.
4. **Explicit target selection with grounded examples:** a second revision repaired
   UPFIRE from 1/16 to 16/16 but regressed LEFTFIRE and RIGHTFIRE by 3/16 each.
   Its macro rate rose from 14.06% to 28.13%, but those 18.75-point branch losses
   exceeded the 10-point tolerance. It was rejected before final access.
5. **Sealed final comparison:** round three was selected and never changed again.
   New final literal trajectories on seeds 348/349 supplied 68 frozen states;
   both Jev questions were queried on those same states, then played both starts.
   Execution and game-return gates both failed. Stop after this round.

Both proposals changed only guidance and native-action criteria. The intended
late-diver priorities, thresholds, targets and tie breaks were manually reviewed
against the frozen rule. All 18 native actions remained selectable. Natural-language
interpretation is not guaranteed by declaring the intended rule unchanged.
No labels, chosen targets or expected actions were added to the model observation.

## Strategy quality and execution are different measurements

| Training rule / seed | Historical Jev | New literal control | Literal minus historical |
| --- | --- | --- | --- |
| Simple / 320 | 340 | 340 | 0 |
| Simple / 321 | 360 | 300 | -60 |
| Late-diver / 320 | 240 | 360 | +120 |
| Late-diver / 321 | 320 | 340 | +20 |

Literal mean return was 320 for the simple rule and 350 for the late-diver rule;
historical Jev means were 350 and 280 respectively. The ordering reversed.
These are matching starts/horizons, not matching visited states or fresh model
replicates. Deviating from a written rule can sometimes help; perfect agreement
with that rule is not an optimal-play objective. The new literal implementation
also reproduced all prior diagnostic mismatch labels on the 3,200 imported
training observations. See the [historical comparison](../../experiments/seaquest/execution-five-round-v1/historical-comparison.json).

The final games provide a second, fresh comparison under the unchanged start
contract. Each row's prefix and controlled-start observation matched across all
three actors.

| Final seed | Literal late-diver | Original late-diver Jev | Selected wording Jev | Wording gain |
| --- | --- | --- | --- | --- |
| 348 | 380 | 280 | 260 | -20 |
| 349 | 420 | 320 | 220 | -100 |
| Mean | 400 | 300 | 240 | -60 |

The literal controls lost no lives within the cap. Original Jev lost two lives
per seed; the revision lost one and three respectively. All ten new episodes,
including training controls, reached the 800-decision cap. None establishes a
completed game or indefinite survival. The score gaps are observed comparisons;
they do not identify the cause of any individual death.

## Execution gains did not generalize

The execution endpoint weights UPFIRE, DOWNFIRE, LEFTFIRE and RIGHTFIRE agreement
rates equally. Training eligibility required >=8 states in each movement stratum,
macro gain >=5 percentage points, and no movement stratum losing >10 points.
The final packet met the same minimum coverage with counts 16,16,8,12.

| Expected action | Final states | Original matches | Revision matches |
| --- | --- | --- | --- |
| UPFIRE | 16 | 13 | 13 |
| DOWNFIRE | 16 | 15 | 16 |
| LEFTFIRE | 8 | 4 | 3 |
| RIGHTFIRE | 12 | 6 | 3 |
| FIRE, auxiliary | 16 | 13 | 14 |
| NOOP, unavailable in these trajectories | 0 | 0 | 0 |

Overall matches were 51/68 for the original and 49/68 for the revision. Movement
macro gain was **-7.8125 percentage points**, with LEFTFIRE down 12.5 and RIGHTFIRE
down 25 points. Final game mean gain was -60 with both seeds regressing. Neither
gate passed; the combined wording-improvement gate is false.

Original-reference training macro rates stayed near 12.5%-14.06% across three
fresh passes. The final original-reference rate of 68.75% must not be read as
learning: the packet came from different trajectories and contained different
conditional branches. Training UPFIRE states comprised **15 diver-seeking states
and one return state**; final UPFIRE states comprised **three diver-seeking states
and 13 return states**. The original matched every sampled return state and none
of those sampled diver-seeking UP states in either packet. Even balancing by
expected action did not balance the reason for that action.

The [branch-composition record](../../experiments/seaquest/execution-five-round-v1/branch-composition.json)
preserves these counts. Final states had zero observation-hash overlap with the
training packet. Missing NOOP states and smaller turn strata were retained, not
filled with replacement seeds. States are correlated trajectory observations;
these screens are not significance tests or population skill estimates.

## Lessons added by this study

- A poor Jev trajectory does not by itself reject the written strategy: the
  late-diver literal controls scored better on both historical training starts
  and both new final starts. This remains evidence on a small bounded sample.
- A useful wording patch can repair one branch while damaging others. Round
  four's perfect sampled UPFIRE performance did not justify promotion; the
  prospective branch-regression guard caught the tradeoff.
- Training execution gains need held-out checks as well as actual game outcomes.
  Round three passed its training screen but regressed on both final endpoints.
  There is no successful execution-only final result to reinterpret as policy improvement.
- State composition matters within an action label. Future diagnostics should
  distinguish return from diver-seeking ascent, and record target multiplicity,
  relative geometry and conflicting conditions. These are proposed controls,
  not additional experiments performed after the five-round stop.

The two proposals were authored by the interactive coordinator from completed
training rounds. Jev weights were fixed, with zero isolated teacher calls and no
no-feedback arm. This still does not establish a causal teacher-feedback benefit,
repeatable optimization, mastery or transfer. Final results informed this report
only; they did not trigger another proposal or allocation.

## Accounting and reproducibility

- **3,914 HTTP attempts** of 6,000; two HTTP 520 responses recovered within the
  frozen retry rule. The unused 2,086 attempts are closed.
- **3,912 successful responses:** 712 fixed-state probes plus 3,200 gameplay
  decisions. Separately, literal controls made 4,800 local decisions and zero calls.
- **34,560 new collection frames:** 32,000 controlled and 2,560 prefix frames.
  The four imported historical source traces and all offline replays are separate.
- **Ten full 60 fps recordings**, totaling 576 seconds of emulator time. API time
  was 1,075.55 seconds; neither is a substitute for the other.
- **13,643,194 input tokens**, **728,640 output tokens**, and provider-reported
  cost approximately **US$0.573014148**, excluding interactive coordinator usage.

Requested model `~typesafe/jev-latest`, response pin `typesafe/jev-1.13-20260917`;
source was frozen at `776bf0c`. All 190 tests passed before collection, including a
synthetic complete five-round run, budget/retry/stop checks and a full offline audit.
The completed study passed source-state verification, original-exchange decoding,
literal-action checks, raw-frame replay, video counts, selection and gate checks.
The reviewed archive was restored and audited again, with byte-identical audit
and cost records. No credentials, ROMs or emulator snapshots are included.
