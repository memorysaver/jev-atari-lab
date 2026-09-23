# Seaquest initial calibration protocol

Frozen before the bounded calibration suite on 2026-09-24; local unit/startup checks
already used training seed 300. This is instrumentation development, not an untouched
performance test. Owner authorized moving to Seaquest after closing Pong.

Entry point: `scripts/seaquest_calibration.py`; [profile](evaluation.md).
**Zero teacher/Jev calls.** No paid backend is constructed or credential loaded.

- Training seeds 300 and 301; controls NOOP, FIRE, random and scripted sweep.
- Eight trajectories, each capped at 8,000 controlled raw frames or native end;
  maximum 64,000 collection frames. Sticky 0.25, action hold four, no automatic
  FIRE or reset no-ops. Record initial state and all 18 native action names.
- Replay each trajectory using recorded actions and matching seed/protocol, never
  resample its policy. Compare every raw-frame RAM array, RGB hash, reward, lives,
  termination/truncation, semantic observation and screen-check result. Report
  replay frames separately; at most 64,000 additional frames.
- Separate action-effect checks: all 18 native actions on matched seed-300 resets,
  sticky zero, 128 NOOP frames, 40 DOWN frames, then 16 frames of the tested action.
  Total 3,312 additional frames. Record before/after observations and player delta.
  These are effect probes, not independent episodes in policy-return statistics.
- Preserve original JSONL and summaries, four videos (seed 300, one per control),
  source revision, extractor/upstream versions, ROM hash and dependency versions.
- Check oxygen-bar width against RGB grey pixels, player-color presence inside
  proposed boxes, observed object classes, oxygen ranges and carried-diver bytes.
  Retain disagreements and unvisited states. Do not quietly modify the decoder
  during this suite or claim full semantic validation from two visual checks.
- Every root is new and immutable. Write plan before trajectories; failures remain
  incomplete. A replay mismatch stops the suite for investigation.

This phase decides what observation validation is still needed and whether a short
pilot could distinguish behaviors. It does not select a successful learned policy,
freeze a model benchmark horizon, or establish Seaquest mastery.
