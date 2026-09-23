# Prospective continuation of the ten-round Seaquest study

2026-09-24, after the original study stopped on HTTP 520 during round 4 seed 321,
with 76 model decisions executed in that episode. Rounds 1..3 and the first episode
of round 4 are complete. The owner's instruction remains to autonomously complete
ten research rounds, preserve records/videos, then stop.

The [original frozen protocol](ten-round-protocol.md) did not retry HTTP 520 and
correctly stopped incomplete. Preserve that original tree and its failed request
in a checksummed archive; do not relabel it complete. This document prospectively
authorizes a separate continuation lineage, **not a retrospective protocol rewrite**.
No claim that all ten rounds followed one uninterrupted original transport contract.

## Exact recovery and limits

- Require the original full API/frame/video audit and a checksum-verified archive.
- Create `artifacts/seaquest/ten-round-v1-continuation` as a copy with explicit parent
  plan/report/budget/archive hashes. Never mutate the stopped predecessor root.
- In the new tree preserve imported request/transition bytes, original episode
  manifest, incomplete summary and partial MP4. Record a separate continuation
  manifest with source revision, transport, prefix byte counts and SHA-256 hashes.
- Reset seed 321 and replay all 560 recorded raw frames, checking every RAM byte,
  RGB hash, reward, life/end flag, observation and pixel check before live access.
  Do not reissue any completed model decision. Resume at the exact unexecuted input
  following model decision 76, with the **unchanged round 4 program**.
- Regenerate the original video prefix from verified replay and append the new
  frames to a complete MP4. Keep the original partial MP4 separately. Replay adds
  560 emulator frames and zero model calls; it does not add controlled decisions.
- Carry forward the existing **4,632 attempts**, original start time and per-round
  counts. Keep the original **24,000-attempt**, per-round and 24-hour limits. No
  extra episode, fresh seed, question change or extra proposal is allocated.
- For continuation calls only, add HTTP **520** to the existing transient set.
  Keep at most two identical-request retries, all charged before transmission.
  Other fatal-response policies, model pin, decoder and observation contract stay
  unchanged. Original Pong/pilot transports retain their old status sets.
- Round 4 remains one research round with a documented technical interruption.
  Its final result is a composite of original and resumed segments, not a fresh
  independent run. Original failed calls remain in cumulative accounting.
- After completing round 4, execute rounds 5..10 under the same prospective
  proposal, selection and held-out data rules. Stop after round 10 regardless of
  outcome. If another failure exhausts this recovery contract, preserve it as
  incomplete; do not silently restart a whole episode.

## Verification before execution

Mock tests must demonstrate: the original transport still stops on HTTP 520;
the new transport retries it within the durable budget; resumed requests start at
the original failed observation; prior requests are not repeated; original files
are unchanged; the combined trajectory replays; and a modified recorded RAM byte
prevents live access. Run the full local suite and lint/format checks, then commit
the implementation and this continuation protocol before resuming.
