# Frozen teacher study protocol v1

Owner approval received 2026-09-19 for the [study plan](teacher-study-plan.md).
This document and its runner are committed before the first live invocation.
The runtime plan records that exact source revision. This protocol fixes the
implementation details left open in the approved proposal; it does not increase
any approved limit.

## Inputs and order

Use `jev-1.13.0`, `pong-vertical-control-v2`, default Pong `Protocol`, all six
actions and the existing probability decoder. Only name/guidance may change;
guidance is at most 2,000 characters. Teacher requests specify `gpt-6-astra`, high.

Rounds use training seeds 60/61, 62/63 and 64/65, respectively. Development uses
66/67 in every round. Final uses 68/69/78/79 after all selections are sealed.
The local evidence inventory found no previously executed study episodes on
these seeds; synthetic unit tests are not experimental evidence.

For each round, collect two A-incumbent training episodes, each capped at 10,000
frames. Then generate and probe A's one proposal, followed by B's one proposal.
Evaluate development in this order on seed 66: A parent, A candidate, B parent,
B candidate. Reverse that order on seed 67. Each evaluation is fresh and capped
at 20,000 frames or native termination. There is no point-based early cutoff.

The gate requires no regression on either development seed and a mean paired
gain of at least +1. Failed/incomplete evaluation cannot promote a candidate.
Teacher-visible prior-edit memory includes proposals, not development scores,
traces or acceptance labels. The selected current question indirectly reveals
some selection history to both arms; report that limitation.

## Packet selection and probes

From each training episode, take 16 evenly spaced decision indices including the
first and last. Add each of the first four point-event decisions and its immediately
preceding decision, deduplicating indices. Preserve state, executed action and
observed subsequent rewards. In the teacher packet, retain next-state objects
instead of repeating its full history. Full transitions remain in the raw logs.

These are representative coverage plus short scoring windows, not estimated
counterfactual credit. A receives the training summaries, selected examples and
its prior proposals. B receives the same game contract/current question and its
own prior proposals, without empirical evidence. Neither receives development or
final outcomes. Packets are at most 200,000 UTF-8 bytes; reject oversized packets
instead of silently resampling. No adaptive selection from development is allowed.

The 32 evenly spaced training inputs are the probe set for both arms. On each
input, query parent and candidate twice; alternate their order by input/repeat
parity. Report parent/candidate action flips and base-2 Jensen-Shannon divergence,
plus parent/parent and candidate/candidate repeat comparisons. These probes are
diagnostic and do not screen candidates out of online evaluation.

## Teacher isolation and recording

Use a fresh noninteractive Codex process inside Bubblewrap. Mount system runtime,
a private temporary credential/runtime directory, the executable and an empty work
directory. Do not mount the host home, repository, prior conversations or artifact
tree. Clear inherited environment variables, disable shell/browser/apps/plugins,
multi-agent and memory features, and disable web search. Check the filesystem
boundary without inference before running a teacher.

Supply only the serialized packet and fixed instructions. Save their hashes,
schema, offline context preview, final output, usage events and invocation status.
Do not publish credentials, private debug logs or internal reasoning. The CLI's
requested model/reasoning settings are recorded; unavailable provider-level model
attestation must remain explicitly unavailable.

Each teacher invocation has a 900-second timeout. There are six planned proposal
invocations, with at most two extra schema/length/reference repairs shared across
the entire study, never quality-based resampling. Repairs preserve the original
hypothesis and retain the invalid proposal. Failed model access or unexpected tool
activity stops the experiment instead of changing teacher/model or context access.

## Budgets, retries and checkpoints

At most 220,000 Jev HTTP attempts: 154,000 nonfinal and 66,000 reserved for final.
Every attempt reserves durable global capacity before transmission. Each episode
also has a local cap of its maximum decisions plus 500 attempts; each 128-query
probe block has a 160-attempt cap. No preflight model calls are required; the first
training request starts the live clock. Local isolation checks consume no model calls.

Retry HTTP 429/500/502/503/504/529 and HTTP transport errors at most twice on the
same unexecuted state, with the existing 0.25/0.5-second backoff. Record every
attempt. Other errors stop dependent execution and preserve partial work. No
automatic episode restart, silent fallback, model substitution or cap extension.

Stop new model requests after 24 hours from the first model invocation. A single
runner holds the study lock. Completed immutable operations can be reused after
restart if source/configuration and artifact identities match. Incomplete episodes
are never restarted by the runner. Seal teacher/nonfinal access before final calls.

## Final evaluation and artifacts

Seal A/B/V2 programs and the environment before test access. Run A, B, V2 on the
first final seed and reverse the order on alternating seeds, at 20,000 frames per
episode. Even identical programs receive separate realizations in this runner;
they remain the same policy, not separate learned methods. Publish per-seed capped
returns and native completion/win denominators, never treating a cap as a win.

Replay/audit each completed episode before dependent selection. Preserve videos,
all raw frames, Jev exchanges, teacher records, probes, gate decisions, failure
prefixes, budget state and final seal. Working output is
`artifacts/pong/teacher-study-v1/`; reviewed publication is
`experiments/pong/teacher-study-v1/`. A study interrupted by a budget or technical
stop is reported as incomplete, with its completed evidence and limits.

Execution after local validation and source freeze:

```bash
uv run --env-file "$HOME/.config/typesafe/credentials.env" \
  python -m jev_atari.study_runner --backend jev \
  --out artifacts/pong/teacher-study-v1 \
  --codex-binary /path/to/pinned/codex-executable \
  --auth-home "$HOME/.codex"
```

The teacher executable version/hash is captured in the runtime plan. Use the
native pinned binary rather than a wrapper that upgrades global tools.
