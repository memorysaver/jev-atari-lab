# Atari challenge scope

Our goal is to attempt every discrete single-agent `ALE/*-v5` game registered by the
locked ale-py installation. On 2026-09-18, ale-py 0.11.2 exposes 104 such games.
The ROM package and website may list a different total; neither defines this experiment's
denominator. Modes, difficulties, continuous actions and multiplayer are separate extensions.

`jev-atari games` generates the inventory from registration. `games --check` boots
each game and executes legal actions without model calls. The checked inventory is
[environment-check-2026-09-18.json](../experiments/environment-check-2026-09-18.json).
All 104 passed eight-frame smoke checks. This only tests startup and stepping.

| Capability | Pong | Other registered games |
| --- | --- | --- |
| Boot/action smoke check | Passed | Passed in recorded installation |
| Generic raw-RAM runner | Available | Available |
| Semantic object adapter | RAM and simple RGB rules | Not implemented |
| Live Jev experiment | Recorded pilot | Not yet tested |
| Value-based labels | 240-frame first-point outcome | Not implemented |
| Multi-round learning or solved-game claim | Not established | Not established |

## Adding a game properly

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
