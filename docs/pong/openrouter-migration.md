# OpenRouter Jev migration: access and bounded playback pilot

Prepared 2026-09-23 after the owner requested switching to OpenRouter because
the direct TypeSafe endpoint still returned HTTP 402 on one separately authorized
access check. The [criteria study](criteria-teacher-results-2026-09-23.md) remains
closed and incomplete. A provider change does not resume that frozen experiment.

## Observed access check

One call to `https://openrouter.ai/api/alpha/decisions` with the owner's requested
`~typesafe/jev-latest` alias succeeded with HTTP 200. The response identified
`typesafe/jev-1.13-20260917`, provider `TypeSafe`, and returned a valid six-action
Choice answer on a published training observation. The unchanged v2 program,
original observation and existing probability decoder were used. This was one
request, with no retries, gameplay or final-test access.

Reported use: 1,620 input tokens, 69 output tokens, and `usage.cost` 0.00006804.
The original response is retained in
`artifacts/pong/openrouter-access-check-20260923T143856692484Z/`.
This establishes successful access at that time, not numerical equivalence to
the direct endpoint or a policy improvement.

[OpenRouter's Decisions documentation and examples](https://openrouter.ai/blog/insights/what-is-jev/)
describe this typed-decision endpoint. The [latest alias](https://openrouter.ai/~typesafe/jev-latest)
can change its target, so playback must explicitly require the observed response
model identity. A mismatch aborts before any action from that response is executed.

## Prospective playback pilot

Freeze source and this schedule before playback calls:

- Backend `openrouter`, endpoint `/api/alpha/decisions`.
- Requested model `~typesafe/jev-latest`; required response model
  `typesafe/jev-1.13-20260917` on every call.
- Unchanged `examples/vertical-policy-program.json`, all six actions, original
  observations/history, existing probability-argmax action selection.
- One training seed **150**, checked unused in recorded local live episodes.
- Default Pong protocol: four-frame action hold and sticky probability 0.25.
- **100 decisions / 400 controlled raw frames**, or earlier native termination.
- **100 HTTP attempts maximum, zero retries**, separate from the completed access
  check and every historical experiment. Stop on an error or identity mismatch.
- Record every original request/response, usage including reported cost, chosen
  action, reward, raw frame and video. Record transport, alias and required model
  in the episode manifest. Replay offline and verify original requests/responses.

Working root: `artifacts/pong/openrouter-player-pilot-v1/`. Never overwrite it.
This is transport/playback validation with a short training trajectory, not a
teacher search, paired performance comparison, native-match win or final test.
Do not pool the result with direct-provider performance evidence. Future teacher
studies need a distinct frozen protocol and baseline measurements on this transport.

## Playback command

Read `OPENROUTER_API_KEY` from an existing protected environment file; do not copy
credentials into this repository or place them in command arguments. After the
pilot plan is written, the corresponding command is:

```bash
uv run --env-file /path/to/existing/credentials.env jev-atari play \
  --policy jev-action --backend openrouter \
  --model '~typesafe/jev-latest' \
  --expected-response-model typesafe/jev-1.13-20260917 \
  --program examples/vertical-policy-program.json \
  --seed 150 --decisions 100 --max-api-calls 100 --video \
  --out artifacts/pong/openrouter-player-pilot-v1/episode
```

The explicit OpenRouter transport currently supports the Pong `play` action
policy. Historical teacher-study runners retain their original direct endpoint.
Missing OpenRouter credentials do not fall back to the TypeSafe key or another
model. The client also preserves ordinary direct-provider CLI defaults.

## Observed playback result

The pilot completed **100/100 HTTP 200 responses**, with zero retries and the
required `typesafe/jev-1.13-20260917` identity on every response. Provider was
`TypeSafe` throughout. The episode ran 400 controlled frames plus 16 reset frames
in 31.74 wall seconds. Actions were 71 NOOP, 16 UP and 13 DOWN. The capped score
was 0:0; no native match completed and no performance comparison was attempted.

OpenRouter reported 166,686 input tokens, 6,871 output tokens and total
`usage.cost` **US$0.007000812** for playback. Including the separate one-call access
check, migration testing used **101 requests and US$0.007068852** in reported costs.
These are API-reported costs, not an independently reconciled invoice.

Original observations and questions matched the recorded program on every call;
all returned probabilities, selected actions, provider/model identities and usage
fields were checked. An offline replay verified the complete trajectory without
model access. The full unit suite passed **150 tests** using mocked model calls.

**Setup deviation:** Source and this prospective schedule were committed before
playback at `7f195a0823c0be8b3a8e1b9d59634fd1849df3e3`. An additional JSON plan writer
then used system Python instead of the project environment and failed to import
the package; the following CLI command nevertheless launched. The episode manifest
and bounded client still recorded/enforced the declared model pin, 100-attempt cap
and zero retries before calls. The supplementary plan JSON was written afterward
with this timing explicitly disclosed. It must not be represented as a pre-call
JSON record. No outcome-dependent setting or schedule changed.

[Reviewed local evidence and video](../../experiments/pong/openrouter-player-pilot-v1/README.md)
preserve the access check, every request/response, full trajectory, audit and setup
deviation. The result establishes a working replacement transport. It does not
prove weight equivalence to the direct endpoint or satisfy either research milestone.
