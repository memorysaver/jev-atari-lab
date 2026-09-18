# Related work and contribution boundaries

Status: targeted primary-source review, consolidated 2026-09-18. These methods
motivate experiments; their published performance has not been reproduced here.
Our [evaluation framework](evaluation-framework.md) is a project proposal, not a
set of metrics claimed to originate in the papers below.

## GEPA: reflective search over prompt programs

[GEPA, paper v2](https://arxiv.org/pdf/2507.19457v2), Section 3 and Algorithms 1–2,
uses execution feedback to propose prompt changes and maintains candidate programs.
Its method includes minibatch comparisons and selection using performance across
individual evaluation instances. The Pareto mechanism is not simply a frontier
between reward and monetary cost.

The relevant lesson is to evaluate proposed changes through execution, retain
alternatives and account for search effort. GEPA does not supply a universal
numerical measure of a prompt edit's semantic quality or a literal text derivative.
Our action-flip and distribution probes would help inspect how a Jev edit changes
behavior; online return remains a separate endpoint.

The [official adapter interface](https://github.com/gepa-ai/gepa/blob/15ee314f9c7d34ec153b809d401f42f55c4dcd76/src/gepa/core/adapter.py)
was inspected at the linked revision: `evaluate`, `make_reflective_dataset` and
`propose_new_texts` are relevant integration points. We have not integrated or
benchmarked this adapter. A future comparison must record deviations from the
paper and library, evidence access, evaluation instances and total resource use.

## TextGrad: textual feedback and validation

[TextGrad](https://arxiv.org/html/2406.07496v1), Sections 2 and 3.3, frames language
feedback as textual gradients and uses it to revise text variables. Its prompt
optimization example uses validation to decide whether an update improves results.
The feedback is language, not a numerical derivative of Atari return.

For this project, separate the teacher's critique from the measured gate. A fluent
diagnosis is a candidate explanation whose proposed intervention still needs a
behavioral and online outcome test.

## Reflexion and Voyager: experience and memory

[Reflexion](https://arxiv.org/abs/2303.11366) uses linguistic feedback and episodic
memory to improve subsequent attempts without updating the underlying model's
weights. It motivates a memory ablation, including the possibility that accumulated
advice becomes misleading outside the conditions in which it was obtained.

[Voyager](https://arxiv.org/abs/2305.16291v2) studies a Minecraft agent with iterative
feedback and a reusable skill library. Reusing code skills differs from revising
Jev questions, but both raise testable questions about retaining useful experience
and transferring it to new tasks. Neither paper alone establishes our Atari
optimizer's effectiveness.

## RLPrompt: reward-driven discrete prompt optimization

[RLPrompt](https://arxiv.org/abs/2205.12548) optimizes discrete prompts using a
reward-driven learned policy. It is relevant prior art for prompts as optimization
variables. Its parameter-training mechanism differs from our initial fixed-weight
teacher proposing edits to an external question program. Calling both approaches
"reinforcement learning" does not make their update rules equivalent.

## TypeSafe: question-feature discovery

[TypeSafe's autoresearch feature-discovery cookbook](https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery)
describes adding, revising and dropping question-derived features evaluated in a
supervised prediction workflow with CatBoost. It is direct prior art for treating
Jev question definitions as searchable artifacts.

Our proposed distinction is the sequential control setting: actions change future
observations and rewards, creating credit assignment, policy evaluation and
exploration questions. That distinction motivates experiments; it is not by itself
evidence of a novel algorithm or a better optimizer.

## Intended contribution

Seek evidence about **which teacher-optimizer components produce repeatable,
resource-efficient question improvements and under which conditions**. Candidate
contributions include a controlled operator/situation pattern, a useful credit or
representation mechanism, transfer evidence or a reproducible negative finding.

A higher score after one hand-written revision cannot establish such a claim.
The [roadmap](research-roadmap.md) specifies the comparisons and evidence needed
before turning these ideas into paper conclusions.
