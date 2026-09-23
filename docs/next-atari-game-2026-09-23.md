# Next Atari game after Pong: recommend Seaquest

Recommendation, 2026-09-23; no non-Pong live model experiment is launched here.
The owner requested roughly three more Pong rounds and a next game that better
exposes capability differences. Interpret capability as the quality of Jev-executed
question policies and the teacher's ability to improve them from experience.
A model-versus-model claim would require separately varying the executor.

## What Pong has taught us

The [criteria study](pong/criteria-teacher-results-2026-09-23.md) rejected all six
fully development-evaluated proposals; two more were incomplete. No final tests ran.
The [compact-wording probe](pong/wording-probe-results-2026-09-22.md) also regressed.
A [literal relative-motion control](pong/relative-motion-controls-results-2026-09-23.md)
improved mean capped training return by 1.5 over tracking, with two regressions.
These separate seeds/implementations do not prove a Jev execution deficit, but they
motivate distinguishing strategy quality from action-rule execution.

The observed feedback gap is that a rejected proposal did not generate the next
teacher's training experience. The new [three-round closure study](pong/candidate-feedback-openrouter-protocol.md)
addresses this while keeping the no-trajectory-feedback control. Its results are
not available yet. More complex prose is not an established route to better play.

## Why Seaquest

Seaquest combines submarine movement and shooting with diver collection, enemy
avoidance and a declining oxygen supply requiring surfacing. It exposes 18 native
actions. These are documented game mechanics, not our measurements.
[Official ALE Seaquest documentation](https://ale.farama.org/environments/seaquest/).

My inference is that it offers a more informative next test than another pure
paddle-tracking task: priorities can conflict in observable ways. A teacher might
learn when to abandon a nearby reward opportunity to surface, when to rescue, or
when to evade. Such edits can be linked to measurable event sequences, while native
score remains the primary outcome. This is a hypothesis about experimental value;
we have not measured a policy-quality spread or teacher gain in Seaquest.

| Candidate | Useful contrast | Reason for ranking |
| --- | --- | --- |
| **Seaquest — first choice** | Immediate shooting versus rescue/survival priorities | Several interpretable decisions with score and resource consequences; more action/observation work required |
| **Ms. Pac-Man — second** | Local pellet pursuit versus safe route choice | Attractive for planning; maze connectivity and pellet-map encoding add substantial representation work |
| **Breakout — lower-cost bridge** | Ball tracking versus useful rebound/brick strategy | Reuses paddle/ball expertise, but risks reproducing Pong's precision-control bottleneck |
| **Freeway — narrow diagnostic** | Constant forward motion versus traffic-sensitive timing | Small action space is useful for execution checks; less breadth for testing a teacher optimizer |

Ms. Pac-Man requires collecting pellets while avoiding ghosts and exposes nine
native actions. My estimate of representation work is a project assessment.
[Official ALE Ms. Pac-Man documentation](https://ale.farama.org/environments/ms_pacman/).
Breakout uses a paddle to return the ball and remove bricks, with four actions;
Freeway crosses traffic with three actions. Their ranking is an inference from
these mechanics and our current implementation, not a benchmark comparison.
[Breakout](https://ale.farama.org/environments/breakout/) ·
[Freeway](https://ale.farama.org/environments/freeway/).

## Make differences interpretable before paying for a large study

The repository currently has a validated semantic adapter for Pong only. Other
games have a generic raw-RAM runner and boot/action smoke checks. Passing 128
uninterpreted RAM bytes to Jev would entangle decoding with decision quality.
See [coverage and adapter requirements](games.md). Seaquest is therefore a next
implementation target, not a ready-to-launch teacher benchmark.

1. Validate a versioned observation adapter for submarine/diver/enemy/projectile
   objects, motion history, oxygen and carried-diver count. Verify semantic fields
   against emulator frames and legal-action effects; mark missing/uncertain fields.
   Supply observations and game rules consistently, without computed preferred
   actions, shortest safe routes, or coordinator-authored decision labels.
2. On training seeds, calibrate the horizon to include oxygen depletion, a chance
   to rescue/surface, and life loss. Do not blindly inherit Pong's 2,000-frame cap:
   it may exclude the behavior being tested. Freeze frame hold, reset rules and
   final horizon before comparisons. Choose an API cap from this calibration.
3. Establish transparent local controls: random actions, a simple shooting rule,
   and a declared oxygen-aware rule. These locate floor/ceiling and failure modes;
   they do not count as teacher discoveries. Keep equal observations and native
   actions, no hidden safety controller. Defer a large teacher run if all feasible
   policies hit the same floor or ceiling.
4. Compare a fixed starting Jev policy with teacher search without trajectories
   and teacher search with its own candidate training experience. Equalize proposal
   opportunities and selector access; report actual calls/tokens/context volumes.
   Independently replicate searches if claiming an optimizer advantage. Testing
   executor capability additionally requires a separate fixed-program comparison.
5. Keep native capped score primary. Report oxygen-related life losses, successful
   surfacing/rescue cycles, divers returned, survival and collision events as
   diagnostics only after their detectors are validated. A policy that shoots for
   points can otherwise look improved while never learning the rescue/resource loop.
   Do not retrofit diagnostic rewards or pick a favorable metric after results.

This gives the teacher meaningful failure evidence and the evaluator observable
behavioral tests. It does not guarantee separation: validate that assumption in a
small pilot before committing to another long search. Selecting Seaquest after Pong
makes it a new development task; it is not automatically an untouched cross-game
transfer test or proof of mastering Atari.
