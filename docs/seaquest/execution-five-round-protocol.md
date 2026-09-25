# Five-round Seaquest strategy and execution study

Prospective, 2026-09-25. The owner requested five more rounds along the direction
in [the recorded lessons](lessons-2026-09-25.md). This is a new, separately bounded
allocation. The earlier ten-round study remains closed. Freeze source and this
protocol before collection. Stop after round five; no extra candidate or seed.

## Question and limits of inference

Separate the quality of a written strategy from Jev's execution of that strategy.
Use the prior round-three simple policy and round-eight late-diver policy as fixed
references. Only the latter may receive wording revisions; preserve its exact
priority order, thresholds, target selection, tie breaks and intended actions.
The interactive coordinator authors two proposals from training evidence; zero
isolated teacher calls. This does not estimate a causal teacher-feedback benefit.

Literal local controls implement the written rules, not optimal play. They are
explicitly labeled zero-model-call controls and never substitute for Jev during
model-controlled episodes. Observation v2, the action decoder, all eighteen native
choices, reward, model and emulator settings remain unchanged. Guidance <=2,000
characters and each native-action criterion <=500. Manually review each proposal
against the frozen literal rule before calls; a declaration alone is not proof
that the model interprets it equivalently.

## Exactly five rounds

1. Run both literal references on training seeds **320/321**, four full recorded
   episodes. Compare them descriptively with the corresponding historical Jev
   trajectories under identical starts/horizons. Historical model responses are
   not fresh replicates. This diagnoses strategy versus execution, not wording.
2. Freshly query both original questions on the same frozen training-state packet.
   Each policy is scored against its own literal target. Because targets can
   differ, this is not a controlled estimate of complexity effects.
3. Author one same-rule late-diver wording proposal using completed training
   rounds. Evaluate it and a fresh original late-diver reference on that same
   packet, alternating role order across states. Preserve all original exchanges.
4. Author one further same-rule proposal using prior training results, including
   failures. Again compare with a freshly evaluated original reference on the same
   packet. Do not change the packet or retune earlier proposals.
5. Seal the eligible revision with highest candidate movement macro agreement;
   earlier round breaks ties. If neither passes, retain the unchanged reference.
   Only after sealing, run the literal late-diver reference on fresh final seeds
   **348/349**, two videos, and form a final-state packet by the same sampling rule.
   Query original and sealed candidate on that packet, then run both Jev programs
   on each final seed, four more videos. Even a rejected/no-change candidate gets
   this diagnostic; identical programs must not be promoted from response noise.
   Close all unused capacity after this round regardless of outcome.

This yields ten new full episode videos: six literal-control and four Jev episodes.
Probes do not step an emulator; they retain exact observations/history, source
transition references and responses, not invented gameplay videos. No proposal
uses final-state observations, responses or game outcomes. No additional edits
follow final access.

## Packet construction and endpoints

Before new model calls, copy and hash the four original training source traces
(prior rounds 3/8, seeds 320/321). Select unique complete observations, including
history, by observation digest. Stratify by the late-diver literal action among
NOOP, FIRE, UPFIRE, DOWNFIRE, LEFTFIRE and RIGHTFIRE. Shuffle each hash-sorted
stratum with random.Random(250925 + stratum_index), take up to 16, and shuffle the
combined packet with random.Random(250926). The frozen training packet has at most
96 states. Use the same procedure on the two final literal trajectories after
sealing. Preserve missing/undersized strata instead of inventing or replacing
states. Labels, strata and desired actions are never included in model state.

Primary execution endpoint: mean of the four movement-action agreement rates,
with each expected-action stratum weighted equally. A training revision is eligible
only if all four movement strata have >=8 states, its macro gain over that round's
fresh original reference is >=0.05, and no movement stratum loses more than 0.10.
Report overall agreement, every denominator, branch errors and original-reference
variation across rounds. These small stratified probes are engineering screens,
not natural occupancy estimates, significance tests or optimal-action labels.

Apply the same gate to final matched-state execution. Separately, final controlled
native-return improvement requires mean paired gain >=20 with neither seed
regressing. Claim bounded same-rule wording improvement only for a distinct
candidate passing both final execution and gameplay gates. If no revision qualifies,
run the no-change diagnostic but set the improvement claim false. Interpret literal
versus Jev trajectories with their differing visited states and capped endings.

## Environment, budget and provenance

Reuse the previous pinned environment: mode 0/difficulty 0, sticky 0.25, raw
frameskip one, four-frame action hold. Every episode includes 32 NOOP holds followed
by 32 random.Random(seed).randrange(18) holds, then <=800 actor decisions/3,200
controlled frames or native termination. Record prefix and controlled rewards
separately. A prefix ending before control stops the study; no favorable resampling.
Store RAM/RGB hashes, observations, native rewards/lives/end flags and full 60 fps MP4s.

OpenRouter Decisions requests `~typesafe/jev-latest`, responses pinned to
`typesafe/jev-1.13-20260917`. No model drift, action mask, derived target injected
into observations, or confidence fallback is allowed. Maximum **6,000 attempts**,
including retries: round limits **0, 400, 400, 400, 4,800**. At most 3,968 successful
requests if both packets have 96 states and all four Jev games reach their caps.
The first request starts a **24-hour** deadline; reserve/fsync each attempt before
sending. Based on previous rates, expected reported cost is around US$0.60, not a
billing guarantee or monetary hard cap.

At most two same-request retries for transport or HTTP 429/500/502/503/504/520/529.
Exhaustion, model drift or malformed responses stop incomplete, preserving all
attempts and recordings. Never silently restart an episode or reset the budget.
The original ten-round source/records are immutable.

## Verification and closure

Require a clean committed source, synthetic transport/selection/budget tests,
full local suite and lint checks before collection. Verify source observations,
original requests/responses and probability decoding, all local literal actions,
raw-frame replays, video frame counts, selected program, final start equality and
gates. Archive all original evidence with checksums and known-secret scanning;
restore and re-audit. Count imported historical records separately from new calls,
local decisions and emulator replay work. Preserve negative results and publish a
five-round report with proposal provenance. Existing publication authorization
covers the research branch; verify remote retrieval before claiming preservation.
