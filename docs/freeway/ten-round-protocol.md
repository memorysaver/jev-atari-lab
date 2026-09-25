# Freeway ten-round protocol, 2026-09-26

Owner requested exactly ten research rounds after the Seaquest lessons. Round 1
was a zero-API calibration under its separate frozen protocol. This continuation
is frozen before the first model request. Complete round 10, then close capacity.

## Environment and observation

ALE/Freeway-v5, mode 0, difficulty 0, sticky actions 0.25; pinned uv.lock.
Left chicken and ten RAM-derived lane boxes; three preceding decision snapshots;
no preferred action, velocity estimate, safe route or diagnostic label in model
state. Coordinates increase right/down. OCAtari revision
99c874675df6b76a33a80b57776c123fbcd051af supplies mapping provenance.

Use 16-frame actions, all three native options, 128+seeded[0,127] NOOP startup,
and 9,000 total raw-frame cap or native end. Calibration's twelve games ended
natively at 8,192 frames. Prefix reward is separate. Round 1's 8-frame sensitivity
check gave the same predictive mean (27.5) as 16 frames, with seed-level variation;
16 frames reduces call cost, not a claim of optimal temporal resolution.

Player color support passed all 8,204 sampled observations. All 1,930 missing car
color checks occur at left-edge RAM x=-3..0; these nominal boxes can be hidden by
the display boundary. Retain such coordinates for wrap history, mark this limit;
all car boxes at x>0 passed. Pixel support is not exact collision validation.
UP movement passed the local deterministic action check. Collision recovery can
continue downward motion after a new request; history is not guaranteed free motion.

## Splits, sequence and budgets

Training 410/411; development 416/417; final 418/419. All descendants share split.

| Round | Work |
| --- | --- |
| 1 | Completed 12 local calibration games, two holds, four controls |
| 2 | Frozen generic baseline: training state probes and two native games |
| 3–8 | One coordinator-authored revision each, based only on prior training feedback; fresh baseline/candidate matched probes and two candidate native games |
| 9 | Seal the best nonbaseline revision by training mean, earlier-round tie; untouched development baseline/candidate games and local controls |
| 10 | Same sealed revision on untouched final seeds, matched probes, local controls; close study and audit/archive |

Each development/final round has four Jev games (two policies x two seeds) and
four local games (always-UP / predictive waiting x two seeds). The nonbaseline
selection is tested even if it failed to beat training baseline; no hidden
selection of the baseline as a successful revision. Development failure does not
permit another candidate or tuning; final remains a confirmation of the same choice.

Exactly six adaptive coordinator proposals, no isolated teacher calls, fixed model
weights. Record each program/hash, rationale and available prior feedback before
its evaluation. No no-feedback teacher arm or independent optimizer repetitions;
this cannot establish a causal feedback/teacher advantage.

Explicit backend OpenRouter Decisions; requested ~typesafe/jev-latest; response
pin typesafe/jev-1.13-20260917. A changed identity stops execution. Global maximum
16,000 HTTP attempts including retries, 24 hours from first call; round limits
1,300 for round 2, 1,400 each for rounds 3–8, 3,000 each for rounds 9–10.
Two retries per request on transport errors or HTTP 429/500/502/503/504/520/529.
Unrecoverable failures stay incomplete, never replaced by a local action.
No extra API calibration call; the first baseline probe is the access check.

## Endpoints and diagnostic packet

Primary: native controlled return, paired by seed. Both held-out gates require
candidate mean gain >=1 crossing and neither seed regressing versus the generic
baseline. Always-UP and predictive local scores contextualize the result, not
model predictions. Passing does not mean beating either local control or mastery.
Mastery target remains unadopted. Two seeds per split do not establish population
reliability. Native completion is timer completion, not a win or mastered game.

Freeze the training packet from all 16-frame calibration trajectories. Deterministic
hash ordering then fixed seeded shuffling selects up to eight unique observations
per (literal rule branch, nearest forward-lane approaching/receding/stationary)
stratum; report actual coverage, never fill absent groups. The nearest forward
lane is a diagnostic context proxy, not necessarily the threatening lane. The
literal predictive label is rule adherence, not optimal action. Its rule never
chooses DOWN; DOWN remains selectable by Jev and is not covered by adherence labels.

Probe each candidate and fresh baseline on identical observations, alternating
order; repeated use can overfit. Held-out packets use fresh local trajectories
with the same sampling rule and report exact training/final overlap checks.
Report per-branch/motion rates and equal-stratum macro; do not infer learning
from changes in aggregate rate across differently composed packets. Probes are
secondary and never override the native score selection/gates. Online actions
visit different states and are not matched-state execution comparisons.

## Preservation

Each complete game has a complete 60-fps recording including prefix, raw-frame
RAM/RGB hashes/rewards/end flags, action/observation transitions and model
exchanges. Keep call attempts, tokens/costs and wall time separate from frames.
Replay every trajectory and reconstruct observations. Audit response pins, action
selection, budgets, program hashes, selection timing, video frames and split use.
Archive under experiments/freeway with SHA-256 manifests, restore and re-audit.
Use Git LFS for recordings/archives. Remote preservation is claimed only after a
fresh download/hash check. Keep negative results and all six rejected/selected edits.
