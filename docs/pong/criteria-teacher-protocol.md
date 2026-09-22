# Criteria-edit teacher study v1

Frozen before model access, 2026-09-22. The owner requested continued experimentation
toward the [research endpoint](research-endpoint.md). The coordinator selected a
conservative **60,000-attempt stage** while offering a budget preference question.
This is a new study, not a reset of any earlier budget, clock or final seed use.
The earlier negative and incomplete studies remain intact.

## Hypothesis and fixed contracts

Let an isolated teacher edit the six action-criterion descriptions as well as the
question guidance. Putting observation-dependent conditions directly into the
options may improve Jev's control. The mechanism and benefit are unconfirmed.
This expands the old guidance-only edit space; it is not an unchanged continuation.

Use `jev-1.13.0`, exactly one action Choice question, original RAM objects/history,
all six native actions, probability argmax, four-frame hold, sticky probability
0.25 and default reset/mode/difficulty. No observation transformation, computed
answer injection, extra question, action mask, fallback, weight or reward change.
The new `action-choice-program-v2` schema permits guidance <=2,000 characters and
all six `action_criteria` strings of 1..500 characters each; name <=100 characters.
Criteria remain natural language, not Python predicates. Existing v1 serialization,
hashes and requests stay unchanged. Every search starts from v2, hash
`2ef87250f491fcd5a2ba72f29e3f03b6bc66c4ab7315e9e724df76352326633d`.

## Searches and data

Three independent searches each have two rounds in A and B, initially empty memory.
A receives its incumbent's new training traces/outcomes; B receives no empirical
evidence. Both receive the same game contract/edit space and their own previous
proposals. The selected current question indirectly reveals selection history.
The coordinator has prior development exposure and does not author candidates.

| Search | Round-one training | Round-two training | Development |
| --- | --- | --- | --- |
| 1 | 100, 101 | 102, 103 | 106, 107 |
| 2 | 110, 111 | 112, 113 | 116, 117 |
| 3 | 120, 121 | 122, 123 | 126, 127 |

Reserve **148,149,158,159,168,169,178,179** for final evaluation. Check local episode
manifests before launch; no remote-inventory completeness is assumed. Earlier
reserved test seeds remain unused. All new episodes have a **2,000 controlled
raw-frame cap**, or earlier native termination. Primary outcome: capped episodic
return, not native-match mastery. Split assignment still follows seed suffixes.

## Frozen round order

1. Invoke B with current question and proposal-only memory. The first B proposal
   doubles as the counted access preflight before new Jev gameplay.
2. Run A's incumbent on the two training seeds; replay/audit before teacher use.
   Use the existing sampler: 16 evenly spaced decisions per episode plus the first
   four scoring decisions and their immediate predecessors. Preserve actual actions,
   subsequent rewards and next-state objects. These are not counterfactual labels.
3. Invoke A with that training packet, current question and proposal-only memory.
   Neither teacher receives development scores, selection labels or final evidence.
   Save exact proposals and programs before evaluation.
4. Query fresh v2, candidate A and candidate B twice on each of the 80 published
   motion-probe training states; rotate program order by state index plus repeat.
   These inputs are deliberately reused diagnostics, not untouched validation or
   natural gameplay frequencies. All reference labels stay outside model requests.
5. Minimal viability screen: all 160 answers complete; all 16 missing-object answers
   are holding actions (NOOP/FIRE); visible-state answers include at least one upward
   and one downward action. Report every stratum/rule/repeat metric, but do not
   reject a different intended strategy simply for disagreeing with v2's rule.
6. Evaluate fresh v2 and eligible candidates on both development seeds. Rotate
   `[V2,A,B]` by `(search_index + round_index + seed_index) mod 3`, zero-based,
   omitting ineligible arms. V2 is that round/seed's shared fresh comparison.
7. Retain a candidate only if both returns are no worse than fresh v2, mean gain
   is >=+1, and it strictly exceeds the arm's previous best gain (initially zero).
   Ties retain the incumbent. Previous best scores are historical estimates, not
   fresh candidate-versus-incumbent comparisons. This is an engineering selector,
   identical in A/B, not a significance test.
8. Record every proposal, probe, skipped evaluation, gate and cost. Finish both
   rounds even without improvement unless a resource/integrity/access stop applies.

Proposal and selection opportunities match, but actual costs differ: A has training
feedback and longer contexts; failing the viability screen skips only that
candidate's development games. Do not count a shared baseline as multiple samples.

## Teacher isolation and failure handling

Request `gpt-6-astra`, `high`, using the pinned local Codex 0.154.0 binary and
Bubblewrap. Record binary/config hashes, filesystem check, instructions/schema,
packet/context preview, final output, usage events and status. Host home/repository,
prior conversations, tools, browser, apps, plugins and memory are unavailable.
Credentials stay in private temporary runtime storage. The
[official noninteractive documentation](https://learn.chatgpt.com/docs/non-interactive-mode)
describes structured output and JSON events; an ephemeral session alone does not
provide filesystem isolation. Returned provider model attestation is unavailable.

There are **12 planned teacher invocations**, at most **two global schema repairs**
and **two global failed-access retries**: **16 invocations**, 900 seconds each.
Each proposal permits at most one repair and one access retry, at most three
attempts. Repairs fix schema/length/evidence references while retaining the
hypothesis. Access retries require nonzero exit plus `turn.failed`, with no returned
candidate, completed turn or tool activity, and repeat the identical packet.
Timeouts/local setup failures/tools/returned candidates do not qualify. Retain
failed records and private diagnostics; no quality resampling or model substitution.

## Budget and finite stop

| Work | Maximum scheduled Jev queries before retries |
| --- | ---: |
| Training: 3 searches x 2 rounds x 2 episodes x 500 | 6,000 |
| Development: 3 x 2 x 3 policies x 2 seeds x 500 | 18,000 |
| Diagnostics: 3 x 2 x 3 policies x 80 states x 2 repeats | 2,880 |
| Final: at most 7 unique policies x 8 seeds x 500 | 28,000 |
| **Total** | **54,880** |

Hard cap: **60,000 HTTP attempts including retries**, with **29,000 nonfinal** and
**31,000 final**; unused final capacity cannot fund search. Reserve durably before
sending. Probe cap: 520. Training/development episode cap: 500 decisions plus 500
retry attempts, still under the tighter global cap. Final episode cap: 600 attempts.
Eligible Jev transport/429/500/502/503/504/529 failures retry at most twice on the same
unexecuted state, charged to the same allocation.

Stop model access **24 hours after the first teacher/Jev invocation**, or at an
earlier exhausted cap/integrity/access stop. One runner holds the lock. Never
overwrite/restart existing roots, incomplete episodes or probes. No schedule
extension for unsuccessful candidates. Technical stops stay incomplete; finish
offline audits/reporting. Monetary billing is not recorded; call caps are not dollars.

## Final seal and endpoint analysis

After all six search-rounds, seal A1/B1/A2/B2/A3/B3/v2 with model, environment,
horizon, final seeds and source commit. Close teacher/nonfinal access before tests.
Use a separate final admission path; the original study's seal is unchanged.
On each final seed evaluate each distinct selected program hash once, rotating hash
order by seed index. Identical programs explicitly share one fresh trajectory;
they are not independent samples. Include unchanged-baseline selections.

Prespecified primary comparison: **A1 versus v2**, requiring mean paired gain >=+1
and lower 95% percentile-bootstrap bound >0 across eight seeds (20,000 resamples,
RNG seed 20260922). Never substitute the best-looking final A policy. Report all
pairs, uncertainty and limits: this is a small-sample bounded-horizon milestone-one
screen, not mastery or broad population evidence.

For a replicated feedback signal, compare equally weighted A-v2 and A-B over three
paired search IDs and eight shared seeds. Resample search IDs and seed IDs
separately, applying identical draws to compared arms, with 20,000 resamples.
Require both means >=+1, both interval lower bounds >0, and positive mean A-v2 and
A-B in every search. These are signal criteria: **three searches per arm do not
establish a well-powered population feedback advantage**. Confirm a favorable
signal in additional independent searches before declaring milestone two.

Frames/repeated state queries are not independent optimizer runs. This is the first
opened final comparison in this research line. Never feed these final outcomes into
another proposal while calling the same cases untouched. Future studies must retain
this attempt in the evidence history and use new final cases; repeated searching
until one result is favorable is not independent confirmation of the overall claim.

## Evidence

Working root: `artifacts/pong/criteria-teacher-v1/`; reviewed local evidence:
`experiments/pong/criteria-teacher-v1/`. Retain exact packets/proposals, original
HTTP JSON, observations, raw frames, videos, probes, selections, budget, final seal,
costs/results/audits. Archives/videos use LFS. Remote preservation requires a
separate publication and retrieval check. Record teacher entries as
`C<search>-R<round>-<arm>` in the [study log](criteria-teacher-log.md).

Validate locally with mock HTTP, preserve original schema-v1 hashes/audits, freeze
code and this protocol, then launch with explicit `--backend jev`. Future studies'
changes/bounds must precede their data; never rewrite these hypotheses or gates.
