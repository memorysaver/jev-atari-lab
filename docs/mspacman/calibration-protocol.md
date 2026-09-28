# Ms. Pac-Man calibration v1, 2026-09-28

Prospective local calibration, authorized by the owner's “go” following the
small-pilot proposal. No API calls in this phase. This is game-specific development.

Use ALE/MsPacman-v5, mode/difficulty 0, frame skip 1, sticky actions 0.25,
training seeds 510 and 511, a 272-frame NOOP prefix, then at most 4,096 controlled
raw frames. Compare random native actions, pellet pursuit, and pellet pursuit
with nearby-ghost avoidance, at eight-frame action holds. Preserve all raw frames,
rewards, actions, observation checks and full 60-fps recordings. Stop at native
termination, unsupported maze change, or the frame cap. No mastery claim.

Exploratory setup found the initial positions unchanged through frame 256 even
with direction input; movement begins later, including under NOOP. The prefix
is startup handling, not an assertion that NOOP remains stationary.

Implement and validate a first-maze observer before live use. RAM coordinates
and RGB colors follow OCAtari; maze geometry is extracted from the initial RGB
image. Distinguish pixel-supported objects, unknown/occluded objects, and static
corridor geometry. The ghost house is excluded from player navigation. Do not
supply computed preferred actions, safe routes or reference labels to Jev.

Calibration gates: deterministic raw-frame replay; full-video frame counts;
player coordinates supported on at least 95% of nonterminal control observations;
all mapped player positions within 3 pixels of the corridor graph on at least
95% of supported control observations; movement effects tested independently at
zero stickiness; retain all discrepancies. Pellet and ghost detection limitations
must be explicitly represented. If these gates fail, preserve results and repair
under a separately named version before spending on Jev.

Compare per-seed native controlled return, life losses and visited positions.
A local strategy spread is evidence about this implementation and starts only.
After calibration, freeze the direct-versus-two-stage pilot's exact programs,
seeds, horizon, HTTP-attempt budget, model/backend pin and stopping rules.
