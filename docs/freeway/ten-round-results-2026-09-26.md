# Freeway ten-round results, 2026-09-26

Completed exactly ten rounds and closed the remaining API capacity. No revision
was promoted: development and final paired gains were both zero. All 42 games
ended natively; timer completion is not mastery.
The [protocol](ten-round-protocol.md) and model runner were frozen at `d11474f`.
Exactly six revisions were authored by the interactive coordinator, with zero
isolated teacher calls and fixed Jev weights. This is not an isolated teacher
experiment or a causal test of feedback benefit.

## Calibration and observation validity

All twelve local calibration episodes reached native termination at raw frame
8,192. At 16-frame action duration:

| Local rule | Seed 410 | Seed 411 | Mean |
| --- | ---: | ---: | ---: |
| Random | 0 | 0 | 0 |
| Always UP | 27 | 22 | 24.5 |
| Reactive wait | 22 | 21 | 21.5 |
| Predictive wait | 27 | 28 | 27.5 |

Eight-frame sensitivity controls scored 27/22 for always-UP and 30/25 for predictive
waiting: the predictive mean remained 27.5, with different seed outcomes. This
supports a bounded 16-frame study; it does not establish optimal action duration.

At 8,204 decision boundaries, all player boxes had color support. Of 90,244 object
checks, 1,930 car checks lacked color; every missing case had RAM x=-3..0 at the
left display boundary. All car boxes with x>0 passed. Nominal hidden edge positions
remain in history for wrap handling. Pixel support does not validate exact collision
geometry, velocity forecasts, or a collision-cause classifier.

## Training revisions

All rows use the same two training seeds and native horizon. The fixed diagnostic
packet has 40 unique observations, eight in each branch/motion group. Fresh baseline
responses accompany every candidate; the baseline was 24/40 in every training round.
The fixed reference is the declared *predictive* heuristic, not an optimal policy.

| Round | Revision | Seed 410 | Seed 411 | Mean | Fixed-reference matches |
| --- | --- | ---: | ---: | ---: | ---: |
| 2 | Generic Jev baseline | 27 | 22 | 24.5 | 24/40 |
| 3 | Explicit entry timing | 27 | 22 | 24.5 | 24/40 |
| 4 | Concrete training examples | 20 | 19 | 19.5 | 27/40 |
| 5 | Swept-interval inequalities | 18 | 18 | 18 | 25/40 |
| 6 | Reactive four-inequality rule | 11 | 14 | 12.5 | 20/40 |
| 7 | Single-lane lookup, reactive | 19 | 19 | 19 | 34/40 |
| 8 | Lane lookup plus prediction | 9 | 11 | 10 | 27/40 |

The highest training-return revision was round 3, tied with the baseline. It was
sealed before development access. No candidate exceeded the baseline training mean.
Round 7's better fixed-state result did not override native-return selection.

### Observed branch behavior

The generic baseline and round 3 selected UP for every training gameplay decision
and every probe. Round 3 increased NOOP probabilities on waiting examples but did
not change the highest-probability selected action. Therefore its training result
is a behaviorally collapsed always-UP policy, not realized traffic prediction.

Round 4 preserved all 24 advance answers and recovered 3/16 predictive waiting
answers. Its first game waited just six times and scored 20 rather than 27. This
shows sensitivity of complete trajectories to a few action changes; it does not
identify those six individual actions as causal mistakes.

Round 6 deliberately changed strategy to reactive waiting, so agreement with the
fixed predictive reference is not agreement with its own written rule. A separately
labeled post-hoc diagnostic on the same packet found:

| Reactive own-rule group | Round 6 | Round 7 |
| --- | ---: | ---: |
| Expected wait | 10/13 | 11/13 |
| Expected advance | 13/27 | 26/27 |
| Total | 23/40 | 37/40 |

Round 7 expresses the same reactive rule as a player-y-to-lane table, then checks
only that lane's car x. This is evidence that this wording made the rule easier to
execute on these reused training states. It supports testing explicit target
selection; it does not prove the model's internal error was incorrect lane binding.
The reactive local rule itself scored below always-UP in calibration, so better
execution of that rule is not sufficient for better game return.

Round 8 restored prediction after the lane lookup. Predictive waiting matches rose
to 8/16, but above-traffic advance matches fell to 3/8; the other 16 advance cases
remained correct. Improved waiting came with a separate branch regression and poor
native return. This resembles Seaquest's branch tradeoffs, now in a three-action game.

## Development evaluation (round 9)

| Seed | Always-UP local | Predictive local | Generic Jev | Sealed round 3 |
| --- | ---: | ---: | ---: | ---: |
| 416 | 27 | 30 | 27 | 27 |
| 417 | 19 | 29 | 19 | 19 |
| Mean | 23 | 29.5 | 23 | 23 |

Paired gains were 0/0, so the frozen development improvement gate failed.
Both model policies chose UP throughout all four games. On the fresh 40-state
packet both matched the predictive rule in 24 cases, missing all 16 waiting
cases. No proposal changed after this access. The final round remains a
confirmation of the same sealed candidate, even after development rejection.

## Final evaluation (round 10)

| Seed | Always-UP local | Predictive local | Generic Jev | Sealed round 3 |
| --- | ---: | ---: | ---: | ---: |
| 418 | 23 | 29 | 23 | 23 |
| 419 | 26 | 29 | 26 | 26 |
| Mean | 24.5 | 29 | 24.5 | 24.5 |

Paired gains were 0/0 and the final improvement gate failed. Both model policies
again chose UP throughout. No revision was promoted. The predictive local rule
outscored always-UP on all four held-out seeds; that is an observed strategy
contrast on these starts, not a model-executed improvement.

Both model versions matched 24/41 fresh final observations. The packet retained
five eight-state groups plus one wait-static-or-unknown/stationary state. Its
six-group macro was 50%, versus 60% on the five-group training/development packets,
even though the policies remained always-UP. This is a composition/weighting
change, not evidence of deterioration or learning. The singleton group is
undercovered; preserve its denominator and avoid population claims. No final
observation hash overlapped training. Final data did not inform any revision.

## Resources and preservation

- 11,711 HTTP attempts, all HTTP 200; no retries or failed calls.
- 11,029 Jev gameplay decisions and 682 matched-state responses.
- 12,032 local-control decisions, zero API calls for those controls.
- 23,302,333 input tokens and 469,878 output tokens.
- Provider-reported cost **US$0.978697986**, excluding coordinator and local compute.
- API wall time 2,773.954 seconds; this is separate from emulator time.
- 344,064 collected raw frames: 336,700 controlled and 7,364 prefix frames.
- 42 complete native episodes and 42 full 60-fps recordings, totaling 5,734.4
  playback seconds (95 minutes 34.4 seconds). Offline replay/test/setup frames
  are excluded from collection totals.
- Requested model `~typesafe/jev-latest`; every response pinned to
  `typesafe/jev-1.13-20260917`. No weight updates, six coordinator revisions,
  zero isolated teacher calls. Unused capacity 4,289 attempts is closed.

[Reviewed evidence and replay instructions](../../experiments/freeway/ten-round-v1/README.md) ·
[All videos](../../experiments/freeway/ten-round-v1/videos.md).
All 42 raw-frame/API/video audits passed. Archive restore produced a byte-identical
full audit; all standalone video hashes matched. The full offline suite passed
196 tests; lint, format and repository link checks passed.
The archive manifest supplies full checksums. Round 1 preceded the source commit;
its decoder hash and later equality to the frozen source are retained. Runtime
and frozen protocol content stayed unchanged during the live study. The only
pre-live existing-test repair isolated a synthetic Seaquest test from completed
local artifacts; it did not alter historical protocols or model execution.

## Interpretation and next research questions

Observed: reducing the action space to three did not eliminate conditional-rule
execution errors. The useful distinction is *which object and condition determine
the action*, in addition to action vocabulary and wording length.

Observed: native return and fixed-state agreement ranked revisions differently.
Keep both metrics, actual state composition and local strategy controls. Do not
present the highest agreement row as the best game policy.

Proposed, not executed: independently test a two-question policy that explicitly
selects the relevant lane before choosing the action, against a budget-matched
single-question policy. Report intermediate lane selection correctness, final
conditional action correctness and native return separately. Keep model-controlled
actions; supplying a precomputed safe action would test a different system.

Limits: two seeds per split, one adaptive search, repeated training packet, no
independent teacher optimizer, no no-feedback arm, no model weight updates, and
no mastery criterion. Full timer completion is not a win or mastery. The local
heuristic is a reference strategy, not an oracle, and DOWN has no expected-label
coverage under either declared waiting rule. No final data may inform new revisions.
