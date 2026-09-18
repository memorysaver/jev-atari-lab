# Game evaluation profile template

Create `docs/<game>/evaluation.md` and a game README/teacher log when introducing
a new game. Use [Pong](../pong/evaluation.md) as a worked profile, not as a universal
Atari scoring rule. This template is not a runnable experiment configuration.

## Identity and environment

- Profile ID/version; environment, ROM hash, mode/difficulty and pinned dependencies.
- Observation contract, history, available information and missing-value behavior.
- Native legal actions and verified effects; startup and life-loss handling.
- Action repeat, sticky actions, reset randomization, termination and truncation.

## Game-specific outcomes

- Native reward semantics and return aggregation.
- Meaning of success/completion; handling games without a final level.
- Primary endpoint for policy evaluation; any secondary outcomes such as level
  progress or lives, with definitions and observable sources.
- Failure/censoring rules and all denominators; full versus capped episodes.
- Mastery criterion: unadopted, or an explicit target and evidence requirement.

## Diagnostics and value targets

- Useful situation categories and their extraction rules; proxy limitations.
- Confidence/adherence metrics kept separate from observed reward.
- If using a critic: horizon, continuation, discount time unit and labels.
- Same-input probe contract versus online evaluation on visited states.

## Comparison and research use

- Local/model controls, matched information and resources, paired repetitions.
- Teacher-visible training data, selector feedback and untouched final evaluation.
- Independent uncertainty units; no treating correlated frames as separate trials.
- Common teacher log and resource ledger, linked to a frozen per-study protocol.
- In-game development versus held-out-game transfer designation.
- Cross-game normalization, if any, with reference scores and compatible protocols;
  retain raw per-game results and never compare arbitrary raw score scales directly.
