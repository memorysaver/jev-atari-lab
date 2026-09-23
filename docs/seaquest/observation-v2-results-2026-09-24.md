# Seaquest observation v2 validation

The prospective gate **passed**, with zero model calls. Frozen source `680f303`;
[protocol](observation-v2-protocol.md). Random and sweep controls on training seeds
302/303 produced four trajectories, **12,460 collection frames / 3,118 decisions**.
A separate 12,460-frame recorded-action replay matched all observations, original
RAM/RGB hashes, rewards, lives and end flags. The original v1 evidence is unchanged.

| Screen check | Supported / checked | Result |
| --- | ---: | --- |
| Oxygen width | 3,118 / 3,118 | Gate passed |
| Active player box | 2,748 / 2,748 | Gate passed |
| Diver box | 2,453 / 2,453 | Gate passed |
| Shark box | 4,567 / 4,586 | Gate passed; 19 disagreements retained |
| Player missile box | 1,055 / 1,068 | Gate passed; 13 disagreements retained |
| Enemy submarine box | 638 / 642 | Additional coverage; 4 disagreements retained |
| Enemy missile box | 348 / 348 | Additional coverage |

The revised contract suppresses object positions in 370 animation/end states,
rather than presenting stale positions as active objects. Unit tests additionally
verify clearing history across missing animation states, life loss and native end.
This removes the measured active-player visibility discrepancy on these traces.

Color support is presence within a proposed box, not exact shape, recall, identity
tracking or complete rescue semantics. Remaining mismatches are preserved; no box
coordinates or gate thresholds were adjusted after these results. The two sweep
runs have identical aggregate scores/counts; correlated/repeated observations must
not be treated as independent evidence of policy quality.

Returns were 120/80 for random and 120/120 for sweep; all four ended natively.
These are training calibration outcomes, not learned-policy improvements.
The [fixed-question pilot](fixed-question-pilot-protocol.md) is separately frozen
before any paid access and retains the observation limitations.

[Reviewed evidence](../../experiments/seaquest/observation-check-v2/README.md)
contains a checksummed local archive and independent restored replay verifications.
The restoration audit adds a separate 12,460 emulator frames and zero API calls.
