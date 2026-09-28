# Ms. Pac-Man evaluation profile v1

Environment: ALE/MsPacman-v5, default mode/difficulty 0, pinned dependencies from
`uv.lock`, discrete nine-action set, frame skip 1 and sticky probability 0.25.
The per-episode manifest records the ROM SHA-256 and installed library versions.
No ROMs or emulator snapshots are published.

Observation v1 combines RAM player/ghost positions, RGB visibility, visible
regular pellets and a first-maze static corridor graph. Coordinates use screen
pixels, x rightward and y downward. Every policy receives the same geometry and
observations. Cardinal exits describe geometry, not recommended actions. The
graph excludes the ghost house and includes the two side-tunnel pairs. All nine
native actions remain available; a diagonal is native joystick input, not a
promise of diagonal movement. Model choice is executed without a safety override.

Limitations: regular-pellet detection may miss occluded pellets. Blue ghost color
is an appearance observation, not a verified remaining vulnerability timer.
Ghost identities are RAM slots; unsupported appearances are marked unknown.
Fruit and power-pellet state are omitted in v1. Only the first maze is supported;
maze changes stop collection explicitly. Two prior object frames are supplied.

Primary outcome: native reward during the controlled raw-frame horizon. Prefix
reward, life losses, end reason, decisions, observations and execution diagnostics
are separate. Videos include prefix and every stepped frame at 60 fps, excluding
API wall time. Native termination and frame-cap completion are distinct. No
mastery criterion or value-learning target has been adopted.

Initial training/calibration seeds: 510/511. New held-out starts will be sealed in
a live protocol after calibration. No final-test data may inform proposals. This
is game development, not untouched cross-game transfer. Local controls and
rule-agreement labels are declared heuristics, not optimal-play ground truth.
