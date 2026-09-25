# Atari challenge scope

Our goal is to attempt and work toward mastering every discrete single-agent `ALE/*-v5` game registered by the
locked ale-py installation. On 2026-09-18, ale-py 0.11.2 exposes 104 such games.
The ROM package and website may list a different total; neither defines this experiment's
denominator. Modes, difficulties, continuous actions and multiplayer are separate extensions.

`jev-atari games` generates the inventory from registration. `games --check` boots
each game and executes legal actions without model calls. The checked inventory is
[environment-check-2026-09-18.json](../experiments/environment-check-2026-09-18.json).
All 104 passed eight-frame smoke checks. This only tests startup and stepping.

Define success separately for each game before declaring mastery: not every game
has a final level or a universal completion event. Record mode, difficulty, score
or completion criterion, evaluation budget and replication. Report coverage of
attempts separately from games meeting those criteria.

The second project goal is to discover reusable teacher-optimizer patterns. A game
used to develop an adapter or optimization method is not automatically a held-out
transfer test. See the [research roadmap](research-roadmap.md) for that distinction.

| Capability | Pong | Seaquest | Freeway | Remaining registered games |
| --- | --- | --- | --- | --- |
| Boot/action smoke check | Passed | Passed | Passed | Passed in recorded installation |
| Generic raw-RAM runner | Available | Available | Available | Available |
| Semantic object adapter | RAM and simple RGB rules | Experimental v2 in dedicated studies | Bounded v1 in dedicated study | Not implemented |
| Live Jev experiment | Recorded studies | Policy and execution studies | Ten rounds recorded | Not yet tested |
| Value-based labels | 240-frame first-point outcome | Not implemented | Not implemented | Not implemented |
| Multi-round learning or solved-game claim | Not established | Not established | Not established | Not established |

## Adding a game properly

Create a game directory such as [docs/pong/](pong/README.md), using the shared
[evaluation-profile template](templates/game-evaluation.md) and
[teacher-round template](templates/teacher-round.md). Keep each game's endpoints,
diagnostics and mastery criteria explicit instead of inheriting Pong's metrics.

1. Record environment, ROM hash, legal actions, mode and difficulty.
2. Define observable state, missing values, history and startup/life-loss behavior.
3. Validate action effects; joystick labels alone are not semantic evidence.
4. Run local controls, including a simple domain rule where available.
5. Freeze a direct question and bounded Jev experiment before interpreting outcomes.
6. Define a separate value target; do not reuse Pong's labels blindly.
7. Publish inputs, outputs, teacher changes, all attempts and a replay report.

The raw-RAM runner is an exploration route, not object understanding. It uses ALE
default mode/difficulty, zero startup no-ops, no automatic FIRE, and a raw-frame cap.
The agent must start/resume games through legal actions. Compare matching protocols;
scores across games are not directly comparable.

Source: [ALE environment reference](https://ale.farama.org/environments/).

## Seaquest update, 2026-09-24

[Observation v2](seaquest/observation-v2-results-2026-09-24.md) passed its bounded
pixel-support gate after the original calibration exposed visibility errors. The
[first Jev pilot](seaquest/fixed-question-pilot-results-2026-09-24.md) completed
two 80-point games with DOWN/NOOP behavior; all recordings replayed. This dedicated
pilot does not change the generic raw-RAM CLI or its catalog adapter status.
No isolated Seaquest teacher or learning result is available.

The subsequent [ten-round study](seaquest/ten-round-results-2026-09-24.md) completed
24 episodes, with development mean 80 to 370 and final mean 80 to 290. All ten rounds
and recordings are preserved and the budget is closed. This establishes bounded
question-policy improvement, not Seaquest mastery or repeatable teacher optimization.

The [five-round execution follow-up](seaquest/execution-five-round-results-2026-09-25.md)
then separated literal strategy controls from model execution. Its selected wording
revision failed both final gates; no revision was promoted. Ten new full videos
and all five rounds are retained, with the allocation closed.

## Freeway update, 2026-09-26

[Ten rounds](freeway/ten-round-results-2026-09-26.md) completed with all 42 full
native episodes recorded. No revision improved held-out return. Single-lane
lookup improved a reused training execution probe, but not native return. The
dedicated observer has bounded pixel-support validation with left-edge visibility
limits; generic raw-RAM CLI/catalog behavior is unchanged. No mastery or isolated
teacher-optimizer benefit is established.
