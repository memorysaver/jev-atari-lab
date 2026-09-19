# Pong evidence directory

Latest: [teacher-study-v1](teacher-study-v1/README.md) preserves one completed teacher round,
12 replay-verified episodes and the failed second-round teacher call. Neither
candidate was promoted; final tests were not run.

Future reviewed Pong runs belong under `experiments/pong/<study-id>/`. Keep small
JSON indexes readable in Git; archives and videos use Git LFS. Working data belongs
in ignored `artifacts/pong/<study-id>/<round-id>/` until reviewed. These are storage
conventions, not automatic CLI routing.

The human-readable [Pong teacher log](../../docs/pong/teacher-log.md) links proposals
to evidence and decisions. [Pong's evaluation profile](../../docs/pong/evaluation.md)
defines game-specific meanings; each run also needs a frozen protocol.

## Historical evidence stays at its original paths

- [Question history](../question-history.json): value/direct pilot programs and gates.
- [Original pilot archive manifest](../atari-evidence-2026-09-18.manifest.json).
- [No-FIRE proposal](../no-fire-question-proposal.json),
  [results](../pong-no-fire-study-results.json) and
  [manifest](../pong-no-fire-study-2026-09-18.manifest.json).
- [Fixed-frame controls](../pong-controls-v1-results.json) and
  [manifest](../pong-controls-v1-2026-09-18.manifest.json).
- [Local calibration](../pong-match-calibration-v1-results.json) and
  [manifest](../pong-match-calibration-v1-2026-09-18.manifest.json).
- [Long trial](../pong-match-feasibility-v1-results.json) and
  [manifest](../pong-match-feasibility-v1-2026-09-18.manifest.json).

This directory adds a game-level entry point; it does not copy, rename or reinterpret
those archives. See the [existing publishing/replay guide](../README.md) for review,
checksums and restoration. Verify remote LFS retrieval before claiming a new archive
is preserved. Preserve failed work and clearly mark missing historical transcripts.
