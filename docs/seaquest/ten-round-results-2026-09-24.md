# Seaquest: ten rounds completed and closed

The owner-authorized ten-round study completed 24 bounded episodes and stopped.
The training-selected round-three question passed both prospective held-out gates:
development mean return **80 to 370** (+290), final mean **80 to 290** (+210),
with neither seed regressing in either split. This establishes bounded score
improvement over the collapsed baseline under this start/horizon contract. It does
not establish game mastery, statistical significance or a causal benefit of teacher feedback.

[Frozen protocol](ten-round-protocol.md) · [Prospective continuation](ten-round-continuation-protocol.md) ·
[Reviewed evidence](../../experiments/seaquest/ten-round-v1-continuation/README.md) ·
[All 24 full recordings](../../experiments/seaquest/ten-round-v1-continuation/videos.md)

## Contract and proposal provenance

Jev weights stayed fixed. The interactive coordinator authored seven question
revisions using completed training records, with hypotheses, exact programs,
evidence references and risks recorded before evaluation. There were **zero
isolated teacher calls**, no no-feedback proposal arm, and no independent optimizer
replications. Later revisions also used source-reported game mechanics; this is
not a clean estimate of feedback benefit. All 18 native actions remained selectable.
Only guidance and action criteria changed; observation v2, decoder and reward did not.

OpenRouter requested `~typesafe/jev-latest`; every successful response was pinned
to `typesafe/jev-1.13-20260917`. Seaquest mode 0/difficulty 0 used sticky probability
0.25 and four raw frames per action. Each episode recorded 128 NOOP startup frames,
128 seeded random-action frames, then at most 800 model decisions/3,200 controlled
frames or native termination. Primary return excludes the prefix; all observed
prefix rewards happened to be zero. Native termination and capped survival are different outcomes.

Training seeds were 320/321, development 326/327, and final 328/329. The best mean
training return among rounds 2..8 selected the candidate, with the earlier round
winning ties. The program was sealed before development and remained unchanged for
both held-out rounds. Each gate required mean paired gain >=20 and no seed regression.
Two seeds per split support only this engineering gate, not a population estimate.

All six seed-specific controlled-start hashes differed. Repeated training starts
were identical within each seed, and each held-out baseline/candidate pair had
byte-identical 64-decision prefixes and controlled-start observations. Seed 320
began control during an animation inherited from the prefix; a subsequent life
loss must not be attributed solely to the first model actions. Different seeds
alone were not used as proof of different observed states.

## All ten rounds

Training scores below are native controlled returns on seeds 320/321. Every
completed proposal remains in the evidence, including regressions.

| Round | Question change | Seed 320 | Seed 321 | Mean | Disposition |
| --- | --- | --- | --- | --- | --- |
| 1 | Original DOWN/NOOP-collapsed baseline | 60 | 80 | 70 | Baseline |
| 2 | Explicit depth band, firing and oxygen return | 140 | 240 | 190 | Not selected |
| 3 | Face the nearest same-lane enemy | 340 | 360 | 350 | Selected before development |
| 4 | Seek one diver whenever empty and a diver is visible | 140 | 180 | 160 | Not selected; exact-state transport continuation |
| 5 | Same intended rule, explicit facing polarity/example | 260 | 260 | 260 | Not selected |
| 6 | Shallower hunting band: y=62..76 instead of 86..100 | 300 | 380 | 340 | Not selected |
| 7 | Round-three rule, later oxygen return: 8 instead of 20 | 300 | 340 | 320 | Not selected |
| 8 | Seek one diver only while empty and oxygen <=32 | 240 | 320 | 280 | Not selected |

| Round / split | Seed | Baseline | Sealed candidate | Paired gain |
| --- | --- | --- | --- | --- |
| 9 / development | 326 | 80 | 360 | +280 |
| 9 / development | 327 | 80 | 380 | +300 |
| 10 / final | 328 | 80 | 280 | +200 |
| 10 / final | 329 | 80 | 300 | +220 |

Both development and final gates passed. All four held-out baseline games ended
natively; all four candidate games reached the 800-decision cap. Final candidates
lost two lives each. Across the whole study, nine episodes ended natively and 15
reached the cap. Scores, life losses and ending reasons are all retained in the
[episode results](../../experiments/seaquest/ten-round-v1-continuation/final-metrics.json).
The selected program hash is
`12176a58c289536d74822a4719feed19af1f6e0523f9766a2ec41adc46b9cea5`.

## Findings and unresolved mechanisms

1. Explicit firing/depth criteria resolved the baseline's observed DOWN/NOOP
   collapse. Adding a same-lane facing rule produced the highest training mean;
   its sealed version also improved all four held-out comparisons. This is an
   observed policy comparison, not proof that any single wording clause caused the gain.
2. More elaborate resource management did not win. Always seeking a diver
   regressed, explicit facing wording partially recovered, and delayed seeking
   still scored below the simpler round-three controller. These revisions changed
   visited states as well as language; their score differences do not isolate a
   general reasoning-complexity effect.
3. High aggregate instruction agreement hid movement errors. The post-hoc literal
   checker matched 1,490/1,600 round-three decisions (93.1%), but only 129/175
   opportunities (73.7%) whose intended action was neither FIRE nor NOOP. The
   corresponding movement/turning figures were 119/740 (16.1%) for round four,
   196/573 (34.2%) for round five and 113/675 (16.7%) for round eight. These are
   training visited-state diagnostics, not matched probes or optimal-action labels.
   [Full disagreements](../../experiments/seaquest/ten-round-v1-continuation/literal-rule-check-final.json),
   [checker source](../../experiments/seaquest/ten-round-v1-continuation/literal-rule-check-final-method.txt),
   and [branch denominators](../../experiments/seaquest/ten-round-v1-continuation/literal-branch-diagnostic.json)
   preserve this distinction.
4. Recorded loaded ascents sometimes reached the surface and replenished oxygen
   without immediate life loss. Empty low-oxygen ascents also preceded animation
   and life loss. The [original manual](https://atariage.com/manual_html_page.php?SoftwareLabelID=424),
   linked from [ALE's Seaquest reference](https://ale.farama.org/environments/seaquest/),
   reports that empty surfacing loses a submarine and partial unloading consumes a
   diver. Source-reported mechanics informed rounds four onward; our observation
   adapter does not independently classify death causes or rescue success.
5. A later return threshold can move failure outside the measurement window.
   Round-seven seed 321 lost no lives before the cap, but ended empty with oxygen
   25. Round-three seed 320 ended during an animation. These are censored endings,
   not evidence of indefinitely sustainable play. The maximum recorded carried
   count was only two across all 24 episodes; a full six-diver rescue was not demonstrated.

A useful subsequent study would separate policy quality from rule execution using
matched training-state probes and literal-controller comparisons, with a new
budget and independent seeds. No such additional study was executed here; all
unused capacity was closed after round ten.

## Transport interruption, cost and preservation

The original root stopped on HTTP 520 in round four, seed 321, after 76 model
decisions in that episode. Its failure ledger, partial video and original closure
remain in the [interrupted archive](../../experiments/seaquest/ten-round-v1-interrupted/README.md).
A separately frozen continuation replayed all 560 recorded raw frames before
resuming the unchanged question at the unexecuted observation. It preserved all
imported bytes and the partial MP4, inherited the original 4,632 attempts and
24-hour clock, and added 520 to the continuation-only transient retry set. It did
not restart the game, repeat completed model requests or expand the budget.
The ten-round result is a documented composite, not an uninterrupted original run.

- **16,848 HTTP attempts** of 24,000; the unused 7,152 are closed.
- **16,778 executed model decisions** and 70 failed attempts: 63 HTTP 529,
  five HTTP 520 and two HTTP 503, including the original stop.
- **67,085 controlled frames + 6,144 prefix frames = 73,229 collection frames**.
  Offline replays are additional emulator work with zero model calls.
- **53,225,526 input tokens**, **3,121,844 output tokens**, and provider-reported
  cost **US$2.235472092**. This excludes interactive coordinator usage and is not
  an independently reconciled billing total.
- Recorded API time was 13,940.06 seconds; the 24 full 60 fps videos total
  1,220.48 seconds (20 minutes 20.48 seconds). Video time is emulator time, not API wall time.

Every original request/response, decoding result, raw-frame RAM/RGB hash, reward,
life/end flag, observation, pixel check and video frame count passed the full
audit. The selected program, gate arithmetic and matched starting prefixes were
also checked independently of the runner. The final local archive was restored
and audited again, with identical verification and cost records. It contains 327
files with SHA-256
`7f1b2b11fbdb5069a6b6ddf344921c47e6214aef12e8be4e1f88d1e992d3b196`.
All 24 full videos and the predecessor partial video are retained. There are no
ROMs, emulator snapshots or credentials in the reviewed archive. This is verified
local Git LFS preservation; no remote retrieval or publication is claimed.
