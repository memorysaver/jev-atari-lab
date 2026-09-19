# Research roadmap and paper plan

Status: proposed studies, introduced 2026-09-18, updated 2026-09-20. The bounded
teacher loop is implemented; its [first live attempt](pong/teacher-study-results-2026-09-20.md)
stopped in round two. This roadmap does not authorize an unbounded API run. Each paid study needs a frozen protocol with explicit call/resource caps.

## Stage 0: Establish the environment and evidence chain

Existing building blocks include the pinned game inventory, Pong observations,
direct and value-based question programs, imported teacher proposals, limited
selection gates, API exchange logs, replay and reviewed LFS archives.

The [research index](README.md) links completed experiments. Current evidence is
fixed-policy evaluation, manual revisions and one isolated A/B teacher round. It does not establish
autonomous multi-round learning. Native-match completion and reliable win rates
also remain open. Preserve these runs as historical controls, not fresh held-out data.

## Stage 1: Build instruments for measuring an edit

Implement the [evaluation framework](evaluation-framework.md)'s repeated fixed-input
probe harness and the [optimizer](teacher-optimizer.md)'s round records. Initially
keep one Choice question, six legal actions and edits restricted to guidance.

Acceptance evidence: a recorded parent/candidate pair can be traced from teacher
input through exact diff, repeated action/distribution probes, per-seed online
outcomes, resource ledger and selection decision. Invalid proposals and failed
evaluations must remain inspectable. A local or mocked harness check validates
plumbing; only real executor calls establish Jev behavior.

Choose evaluation horizons from training calibration and the desired endpoint.
The 2,000-frame results and unfinished 20,000-frame trial show why duration cannot
be treated as a neutral implementation detail.

## Stage 2: Run the smallest isolated teacher loop

Propose three rounds with one candidate per round as an integration pilot. Use a
fresh teacher context containing only the declared training packet, current question
and allowed memory. The interactive assistant has already seen development results;
its existing conversation cannot establish train-only proposal generation.

Before execution, freeze the teacher and Jev versions, initial question, editing
limits, seeds and split membership, frame caps, API budgets, repeat counts and
selection rule. Keep development selection separate from teacher-visible traces.
Record whether each gate accepted, rejected or could not resolve the proposal.

Pilot success means the complete loop and evidence chain work. Reward improvement
would be exploratory evidence; no improvement is also a useful result. Do not
reuse a historical pilot's promotion threshold as an unexplained default.

## Stage 3: Compare optimizers and discover patterns

Prioritize experience versus no-experience feedback, then isolate one optimizer
component at a time. Include the frozen starting policy and a relevant GEPA-style
baseline with the same Jev interface, evidence access and resource accounting.
Distinguish a faithful reproduction from a deliberately modified adapter.

Repeat complete optimization runs with independent training/evaluation draws under
the split rules. Predeclare the main endpoint and a practical effect size; use
training/pilot variability to plan replication. Archive all proposals and costs,
including rejected edits and infrastructure failures.

Use exploratory runs to define operator/situation categories. Test those patterns
on fresh runs before treating them as reusable optimizer knowledge. A candidate
pool's best development score is not an unbiased estimate of final performance.

## Stage 4: Test representation and credit assignment

The original value-based direction remains a separate study. Compare trajectory
feedback with controlled branch outcomes, specifying continuation policy, horizon,
discount time unit and stochastic replication. Test prediction quality and action
selection quality separately. Charge teacher, Jev and environment branching costs.

Then test structured critics, richer question programs, retrieval or learned
aggregation against the simplest working representation. A TD experiment also
requires stable targets, target-version handling and appropriate terminal/truncation
semantics. Text updates alone do not establish Bellman consistency or convergence.

## Stage 5: Expand across Atari and test transfer

Work toward mastery of all 104 games in the [pinned scope](games.md). Many games
do not have one universal "completion" event. Define per-game success criteria,
mode/difficulty and evaluation protocol before declaring mastery. Track boot,
observation validation, live attempt, optimizer study and mastery separately.

Add games with distinct control demands and validated observation/action contracts.
Compare reuse of an optimizer or modification memory against starting without that
knowledge. Hold out games for transfer tests and record any game-specific knowledge
in adapters, teacher instructions or starting questions. Environment coverage and
scientific transfer are different denominators.

Normalize cross-game summaries only with explicit reference scores and protocols;
also publish raw per-game outcomes and uncertainty. A pretrained RAM/object-based
agent is not directly comparable to a pixel-based agent trained from scratch under
a different budget. The all-games challenge can continue beyond the first paper.

## Evidence required for paper claims

| Possible claim | Minimum supporting evidence |
| --- | --- |
| Experience improves question optimization | Matched feedback ablation across independent optimization runs |
| A particular optimizer mechanism helps | Controlled component comparison, uncertainty and full resource accounting |
| An optimization pattern is reusable | Prespecified pattern replicated on fresh situations/seeds; held-out games for transfer |
| Structured/value questions improve control | Matched representation study plus online outcomes, not prediction scores alone |
| Jev provides an efficiency advantage | Quality/resource comparison with alternative executor and relevant local controls |
| A game is mastered | Predeclared game-specific criterion met under its complete evaluation protocol |
| A result is reproducible | Versioned questions/teacher packets, raw exchanges, all attempts, environment provenance and verified replay |

These are evidence requirements, not completed results. Negative or conditional
findings can support a useful paper when the study identifies what fails and under
which conditions. Do not claim novelty merely for teacher-written prompt revisions;
position any contribution against [related work](related-work.md).

## Proposed paper structure

1. Research questions and the distinction between executor, question and optimizer.
2. System, observation contracts and versioned question representations.
3. Teacher optimizer components and experience/credit interfaces.
4. Experimental protocols, controls, budgets and uncertainty methods.
5. Learning curves and operator/situation patterns, including negative results.
6. Generalization, resource tradeoffs and limits of the evidence.
7. Reproduction package and Atari coverage appendix.

Every result table should link to an immutable experiment revision. The paper's
scope should follow the evidence actually collected, rather than require all
Atari games to be solved or every proposed mechanism to succeed.
