# Freeway round 1 calibration, 2026-09-26

Owner authorization: ten Freeway research rounds, preserving records and videos.
This first round uses no API. Frozen before collecting the following episodes.
Training seeds 410 and 411; ALE defaults mode 0 / difficulty 0; sticky 0.25;
128 plus seeded [0,127] NOOP prefix frames; 9,000 total raw-frame ceiling.
Record each raw frame, observation, action, reward and complete 60-fps video.
Compare random, always-UP, reactive waiting and velocity-based waiting with
16-frame actions on both seeds. Compare always-UP and velocity-based waiting
with 8-frame actions on both seeds as temporal-resolution calibration.
Coordinates/colors adapt OCAtari revision 99c874675df6b76a33a80b57776c123fbcd051af.
Validate screen color support and movement effects before model use; no claim
of exact collision detection. Setup smoke check observed native end at frame 8192.

Use this evidence to freeze the subsequent nine rounds before any live calls.
If waiting rules do not outperform always-UP, retain that negative result and
focus on the narrower execution-versus-score diagnostic; do not claim a useful
strategy-optimization benchmark or silently switch games. This owner request
specifically selected Freeway. Local rule labels never enter model observations.
