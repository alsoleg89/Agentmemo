# Invariant Witness Theory: A Scientific Research Program for Agent Memory

[established] Date: 2026-04-24

[theoretical] Status: theoretical research program, not an engineering specification

[theoretical] Scope: persistent artificial agents reasoning across sessions, users, tasks, and time scales under bounded memory and bounded computation

[theoretical] Constraint note: This document discusses existing systems only as failure cases, baselines, or prior art. It does not propose vector search, sparse lexical search, chunking, re-ranking, extended context, knowledge graphs, summarization pipelines, or any recombination of those as the solution.

[theoretical] Label convention: Every substantive prose claim is marked [established], [theoretical], or [speculative].

[speculative] Core novelty claim: the new idea introduced here is the **cohomological regret charge** of a memory witness: a scalar protection energy assigned not to an item of stored text but to an equivalence class of history constraints whose removal changes future action under some intervention and whose inconsistency appears as non-zero temporal/identity curvature.

## Source Anchors

[established] LoCoMo reports very long-term conversations of about 300 turns and 9K tokens on average, over up to 35 sessions, and finds that long-context and retrieval-style methods improve but remain substantially below human performance on temporal and causal long-range dialogue understanding: https://arxiv.org/abs/2402.17753

[established] LongMemEval evaluates five memory abilities: information extraction, multi-session reasoning, temporal reasoning, knowledge updates, and abstention; it reports a 30% accuracy drop for commercial chat assistants and long-context LLMs across sustained interactions: https://arxiv.org/abs/2410.10813

[established] BEAM creates 100 conversations and 2,000 validated questions up to 10M tokens and reports that even 1M-context LLMs, with and without retrieval augmentation, struggle as dialogue length grows: https://arxiv.org/abs/2510.27246

[established] MemoryArena evaluates multi-session Memory-Agent-Environment loops where earlier actions and feedback must guide later actions, and reports poor performance for agents that do well on existing long-context memory benchmarks: https://arxiv.org/abs/2602.16313

[established] MemGround defines interactive gamified memory tasks with surface state, temporal associative, and reasoning-based memory, and reports that state-of-the-art models and memory agents struggle with sustained dynamic tracking, temporal event association, and reasoning from accumulated evidence: https://arxiv.org/abs/2604.14158

[established] MemGPT proposes virtual context management and hierarchical memory tiers inspired by operating systems: https://arxiv.org/abs/2310.08560

[established] Mem0 proposes extraction, consolidation, and recall of salient conversational information, with a graph-enhanced variant and reported improvements on LoCoMo: https://arxiv.org/abs/2504.19413

[established] A-MEM proposes Zettelkasten-style dynamic indexing, linking, and memory evolution: https://arxiv.org/abs/2502.12110

[established] LightMem proposes sensory, short-term, and long-term stages with offline sleep-time update and reports improvements on LongMemEval and LoCoMo: https://arxiv.org/abs/2510.18866

[established] Zep/Graphiti proposes a temporal knowledge-graph architecture for agent memory and reports gains on DMR and LongMemEval: https://arxiv.org/abs/2501.13956

[established] Friston's free-energy principle frames perception, learning, and action as optimization of a bound on surprise or expected cost: https://www.nature.com/articles/nrn2787

[established] Complementary Learning Systems theory distinguishes rapid episodic learning from slower cortical integration: https://doi.org/10.1037/0033-295X.102.3.419

[established] Clonal selection and immune memory explain adaptive retention of threat-relevant biological responses under resource limits: https://www.nature.com/articles/ni1007-1019

[established] Landauer's principle links irreversible erasure to physical cost, with experimental verification in one-bit memory systems: https://www.nature.com/articles/nature10872

[established] Persistent homology represents stable topological features by equivalence classes such as barcodes: https://repository.upenn.edu/handle/20.500.14332/34758

---

# Phase 0: Ontological Audit

## 0.1 What Is Memory?

[theoretical] Let \(H_t=(O_1,A_1,\ldots,O_t)\) be the physical interaction history of an agent and let \(X_t\) be the complete microstate of the agent at time \(t\). A memory is a physically instantiated macrostate \(M_t=\phi(X_t)\) whose value counterfactually depends on \(H_t\) and whose possession can change future action loss.

[theoretical] The minimal test for memory is not storage but counterfactual dependence:
\[
\exists h,h',q:\ \phi(X_t(h))\ne \phi(X_t(h'))\ \land\ 
\mathcal L(\pi(q,\phi(X_t(h)))) \ne \mathcal L(\pi(q,\phi(X_t(h')))).
\]

[theoretical] A state is any variable sufficient to specify instantaneous dynamics at a chosen scale; a memory is a state variable whose value is evidence about earlier interaction and has positive expected value for future control.

[theoretical] A cached computation is a stored output \(y=f(x)\) where \(x\) is recoverable or recomputable from current resources; a memory is a constraint on histories \(\mathcal H(M_t)=\{h:\phi(X_t(h))=M_t\}\) that cannot generally be recomputed after erasure.

[theoretical] Compression is a map \(c:H_t\to Z_t\) preserving a declared sufficient statistic \(T(H_t)\); forgetting is an irreversible enlargement of compatible histories, \(\mathcal H(M'_t)\supset \mathcal H(M_t)\), that increases minimum possible decision regret for at least one future query distribution.

[established] The data-processing inequality implies that post-processing a memory cannot increase mutual information with the original history, \(I(H_t;h(M_t))\le I(H_t;M_t)\).

[theoretical] Retrieval is selection of a stored representation; reconstruction is inference of a decision-relevant history constraint from stored evidence and a query. The theory below replaces selection-by-closeness with reconstruction-by-counterfactual necessity.

## 0.2 What Is an Agent?

[theoretical] A minimal formal agent is \(\mathcal A=(\mathcal O,\mathcal U,\mathcal M,\eta,\pi)\), where observations \(O_t\in\mathcal O\), actions \(U_t\in\mathcal U\), memory state \(M_t\in\mathcal M\), update \(M_{t+1}=\eta(M_t,O_t,U_t)\), and policy \(U_t\sim\pi(\cdot\mid O_t,M_t)\).

[theoretical] An agent uses memory at \(t\) if there exist \(m,m'\) and an observation \(o\) such that \(\pi(\cdot\mid o,m)\ne\pi(\cdot\mid o,m')\).

[theoretical] A world model predicts state transitions and observations; memory supplies boundary conditions and evidence that condition the world model. In symbols, the model is \(P(S_{t+1},O_{t+1}\mid S_t,U_t,\theta)\), while memory constrains \(P(S_t,\theta\mid H_t)\).

[established] In a fully observed Markov decision process, the present state can be sufficient for optimal action. In a partially observed process, the Bayesian belief state \(b_t=P(S_t\mid H_t)\) is the canonical sufficient statistic.

[theoretical] For long-lived language agents, the minimum rational memory is not the whole transcript but the smallest statistic \(T(H_t)\) such that for all admissible future tasks \(q\), \(\pi^*(q,H_t)=\pi^*(q,T(H_t))\) up to tolerance \(\epsilon\).

## 0.3 What Is Memory Failure?

[theoretical] Memory failure is violation of decision sufficiency:
\[
\exists h,h'\in\mathcal H:\ M(h)=M(h')\ \land\ 
d_\Pi(\pi^*(\cdot\mid h),\pi^*(\cdot\mid h'))>\epsilon .
\]

[theoretical] Equivalently, memory \(M\) fails under task distribution \(P(Q)\) when
\[
\mathbb E_{Q,H}\left[
\mathcal L(\pi(Q,M(H)),H)-\mathcal L(\pi^*(Q,H),H)
\right]>\epsilon .
\]

[theoretical] A wrong answer is only an observable symptom. The formal violation is that \(M\) identifies histories that should remain separated because they imply different safe actions, different truth conditions, or different abstention obligations.

[theoretical] Four primitive failures follow: under-separation, where distinct decision histories collapse; over-separation, where irrelevant distinctions overload the reader; temporal misbinding, where valid time and storage time are conflated; and identity holonomy, where transporting entity state around a loop yields contradiction.

---

# Phase 1: Deep Anomaly Map

## A1. Rare-Critical Fact Survival Under Bounded Memory

[established] Falsifiable observation: in a bounded-memory agent, a low-frequency fact with high action cost if missed, such as a drug allergy, can be less available at read time than repeated low-stakes preferences. This can be tested by inserting one rare high-risk constraint among many repeated low-risk facts and measuring risk-weighted recall after 700 sessions.

[established] LongMemEval's sustained-interaction drop and LoCoMo's temporal/causal deficits establish the general weakness of current long-term memory, but no named benchmark cleanly isolates frequency-low, risk-high survival as a first-class metric.

[theoretical] The missing benchmark is itself an anomaly because current scoring treats facts by answer correctness rather than by expected harm under omission.

[theoretical] RAG-like systems fail because salience is induced by text/query overlap and frequency, not by counterfactual loss.

[theoretical] MemGPT fails because paging decisions provide no conservation law protecting a rare dangerous constraint across long idle intervals.

[theoretical] Mem0 fails in the theoretical limit because salient extraction and optional relational structure do not define a risk-weighted survival invariant.

[theoretical] A-MEM fails because dynamic links reward meaningful connectedness; an isolated rare-critical item may have few links.

[theoretical] LightMem fails because filtering and sleep-time consolidation optimize efficiency and factual QA, not guaranteed survival under future harm.

[theoretical] Zep/Graphiti can represent temporal facts, but representation does not by itself prove bounded-budget protection of rare critical facts.

[theoretical] A full-context long-window LLM fails when the history exceeds context, and may fail before then because attention is a noisy read channel.

[theoretical] Root cause: memory selection is optimized for evidential salience rather than counterfactual regret.

[theoretical] Required science: value of information, rare-event risk, online knapsack with extreme-loss weights, and non-equilibrium allocation.

[theoretical] Rating: civilizationally important.

## A2. Temporal Validity Versus Temporal Storage

[established] Falsifiable observation: agents confuse "when the system learned X" with "when X was true", producing stale or temporally inverted answers.

[established] LongMemEval explicitly evaluates temporal reasoning and knowledge updates, and Zep/Graphiti explicitly motivates temporally aware memory because enterprise knowledge changes over time.

[theoretical] RAG-like systems fail because timestamps attached to text are not equivalent to validity intervals of propositions.

[theoretical] MemGPT fails because memory tiers can preserve old content without a formal valid-time calculus.

[theoretical] Mem0 fails because extracting and updating facts does not guarantee three-time semantics unless validity, transaction, and belief are separated.

[theoretical] A-MEM fails because memory evolution may update note attributes without proving temporal non-contradiction.

[theoretical] LightMem fails because consolidation can summarize a sequence into a stable statement and erase the interval boundary.

[theoretical] Zep/Graphiti is closest, but a temporal graph still requires a read-time semantics for stale belief and contradictory intervals.

[theoretical] A full-context long-window LLM fails because chronological text order does not enforce interval logic.

[theoretical] Root cause: systems store observation time, not truth conditions over time.

[theoretical] Required science: interval temporal logic, bitemporal databases, dynamic epistemic logic, belief revision.

[theoretical] Rating: critical.

## A3. Consolidation As Lossy Compression Under Unknown Future Queries

[established] Falsifiable observation: after idle consolidation, performance improves on common aggregate questions but worsens on rare future questions that depend on details omitted from the consolidation product.

[established] LightMem reports gains from offline sleep-time update, and LongMemEval reports that memory-stage design choices affect downstream QA; neither result proves lossless preservation of unknown future relevance.

[theoretical] RAG-like systems fail because their unit of preservation is externally chosen text, not a sufficient statistic for future decision.

[theoretical] MemGPT fails because moving between memory tiers is not a theorem of sufficiency.

[theoretical] Mem0 fails because extracting salient memories cannot know which omitted details will be future-critical.

[theoretical] A-MEM fails because updating older notes can improve coherence while silently changing evidential boundaries.

[theoretical] LightMem fails most directly because compression and topic grouping are useful but not decision-sufficient in the unknown-query regime.

[theoretical] Zep/Graphiti fails if graph facts are consolidated from language without preserving all future-relevant witnesses.

[theoretical] A full-context long-window LLM avoids consolidation only until capacity is exceeded; then it has no principled compression.

[theoretical] Root cause: no finite lossy compression is universally sufficient for arbitrary future questions.

[established] This impossibility follows from rate-distortion theory unless the future task distribution and distortion function are specified.

[theoretical] Required science: decision-theoretic rate-distortion, minimum description length, sufficient statistics, lossy compression with regret distortion.

[theoretical] Rating: critical.

## A4. Overload Inversion Beyond Read Capacity

[established] Falsifiable observation: adding more memories can reduce answer quality when the read channel becomes saturated or contradictory evidence is over-presented.

[established] BEAM reports that even 1M-token LLMs with and without retrieval augmentation struggle as dialogues lengthen, and MemGround reports failures in sustained dynamic tracking under interactive accumulation.

[theoretical] RAG-like systems fail because candidate volume grows while discriminative capacity at the reader remains bounded.

[theoretical] MemGPT fails because tier movement can become a traffic problem: too many plausible pages compete for a finite working context.

[theoretical] Mem0 fails if extracted memories accumulate faster than the read process can adjudicate validity and relevance.

[theoretical] A-MEM fails if link growth creates activation sprawl rather than stable decision surfaces.

[theoretical] LightMem mitigates overload by staged compression, but compression can produce A3 failures.

[theoretical] Zep/Graphiti mitigates overload by structured traversal, but dense evolving relationships can still saturate decision assembly.

[theoretical] A full-context long-window LLM fails because more tokens can reduce effective use of middle or conflicting evidence.

[theoretical] Root cause: the field assumes monotonicity, \(Q(M\cup x)\ge Q(M)\), while bounded inference creates a phase transition where extra memory increases noise.

[theoretical] Required science: channel capacity, statistical mechanics of constrained inference, phase transitions, load theory.

[theoretical] Rating: critical.

## A5. Entity Identity Under Contradiction And Evolution

[established] Falsifiable observation: an agent can conflate two entities with the same name, split one entity across sessions after pronoun changes, or treat a changed property as a contradiction rather than an update.

[established] MemoryArena shows a gap between recall benchmarks and interdependent agentic use; Zep/Graphiti explicitly centers evolving relationships and historical context.

[theoretical] RAG-like systems fail because identity is an addressing accident, not an invariant.

[theoretical] MemGPT fails because conversational memory can preserve mentions without a formal transport law for entity state.

[theoretical] Mem0 fails when extracted facts require entity resolution beyond local salience.

[theoretical] A-MEM fails when note links make identity plausible but not logically constrained.

[theoretical] LightMem fails when topic grouping merges entities or separates an entity's evolving state across summaries.

[theoretical] Zep/Graphiti is strong on this axis, but a node identifier is still not a full theory of identity under contradiction.

[theoretical] A full-context long-window LLM fails because co-reference across long histories remains a probabilistic act with no persistent identity invariant.

[theoretical] Root cause: identity is represented as a label rather than as an equivalence class of action-preserving transformations.

[theoretical] Required science: groupoids, sheaf semantics, gauge invariance, temporal belief revision.

[theoretical] Rating: critical.

## A6. Write Policy Blindness To Future Task Relevance

[established] Falsifiable observation: an agent fails later because it did not store an observation whose future relevance was latent at write time.

[established] MemoryArena directly evaluates tasks where earlier acquired information must guide later actions, and LongMemEval includes knowledge updates and multi-session reasoning.

[theoretical] RAG-like systems fail because they postpone relevance until query time and therefore may never preserve the right evidence.

[theoretical] MemGPT fails because the agent deciding what to page or store lacks a calibrated model of future regret.

[theoretical] Mem0 fails if its write policy extracts what is currently salient rather than what has high option value.

[theoretical] A-MEM fails when memory evolution reacts to current linkage and cannot price future unseen tasks.

[theoretical] LightMem fails if early filtering discards latent constraints before later consolidation can see them.

[theoretical] Zep/Graphiti fails when construction captures facts but not why they matter for future action.

[theoretical] A full-context long-window LLM fails by deferring all write policy until the context limit arrives, at which point deletion is unprincipled.

[theoretical] Root cause: write policies estimate present informativeness, not future option value.

[theoretical] Required science: Bayesian optimal stopping, value of information, counterfactual regret minimization, exploration under uncertainty.

[theoretical] Rating: critical.

## A7. Cross-Session Causal Dependency

[established] Falsifiable observation: a fact in session 3 constrains an action in session 312 even though no later query shares surface form with the original observation.

[established] LoCoMo reports difficulty with long-range temporal and causal dialogue dynamics, and MemoryArena constructs explicitly interdependent multi-session tasks.

[theoretical] RAG-like systems fail because causal dependency is not a closeness relation.

[theoretical] MemGPT fails because paging a historical note is not equivalent to preserving the structural equation in which it participates.

[theoretical] Mem0 fails when extracted facts are available but their action dependency is not represented.

[theoretical] A-MEM fails when links encode association rather than intervention.

[theoretical] LightMem fails if consolidation preserves "what happened" but not "what later actions are constrained by it".

[theoretical] Zep/Graphiti can encode relations, but causality requires interventions and counterfactuals, not only temporal edges.

[theoretical] A full-context long-window LLM fails because reading a long causal chain remains unbounded theorem proving under noise.

[theoretical] Root cause: memory facts are treated as independent evidential items rather than as boundary conditions in a causal model.

[theoretical] Required science: structural causal models, do-calculus, temporal counterfactuals, proof-carrying state.

[theoretical] Rating: civilizationally important.

## A8. Memory Interference: New Facts Degrading Old Recall

[established] Falsifiable observation: inserting many new facts after an old fact reduces correct recall of the old fact even when the old fact remains stored.

[established] BEAM and LongMemEval both expose degradation with longer histories; MemGround exposes dynamic tracking failures under continuous interaction.

[theoretical] RAG-like systems fail because new candidates compete with old candidates in the same read budget.

[theoretical] MemGPT fails because memory tiers have finite bandwidth and newer events can dominate working context.

[theoretical] Mem0 fails when consolidation or update changes the context in which old facts are surfaced.

[theoretical] A-MEM fails when new links rewrite the neighborhood of old memories.

[theoretical] LightMem fails when later topic summaries absorb or dilute older detail.

[theoretical] Zep/Graphiti fails if graph evolution changes traversal paths or entity summaries in ways that hide older evidence.

[theoretical] A full-context long-window LLM fails because old facts compete for attention with newer tokens and contradictions.

[theoretical] Root cause: memory storage is not error-correcting with respect to read operations.

[theoretical] Required science: error-correcting codes, attractor dynamics, topological order, stability-plasticity theory.

[theoretical] Rating: critical.

---

# Phase 2: Cross-Domain Archaeology

[theoretical] Exactly three mechanisms are excavated because they jointly attack the three hardest anomalies: rare-critical survival, temporal/identity consistency, and unknown-future write policy.

## Mechanism 1: Immune Danger-Gated Clonal Memory

### 2.1 Native Mechanism

[established] In clonal selection, lymphocyte clones bearing receptors that bind antigen proliferate, mutate, and differentiate into effector and memory populations.

[established] The immune system solves a resource-bounded rare-event problem: most molecular patterns are irrelevant, but a rare pathogen can be fatal.

[theoretical] A minimal population model is
\[
\frac{dn_i}{dt}=\alpha\,D(x)\,a_i(x)\,n_i-\delta n_i+\sum_j m_{ji}n_j-\sum_j m_{ij}n_i,
\]
[theoretical] where \(n_i\) is clone abundance, \(a_i(x)\) is binding affinity to antigen \(x\), \(D(x)\) is danger or inflammatory context, \(\delta\) is decay, and \(m_{ij}\) is mutation or differentiation flow.

[established] The mechanism emerged under selection pressure from adversarial, rare, evolving pathogens and a finite metabolic budget.

[established] Known limits include autoimmunity, immunosenescence, original antigenic sin, and pathogen escape.

### 2.2 Structural Analogy

[theoretical] The isomorphism is not "antigen equals text". The isomorphism is between a rare external condition with high expected loss and a memory constraint requiring protected future response.

[theoretical] Mapping:
\[
\text{antigenic determinant}\mapsto \text{observed constraint},\quad
\text{danger signal}\mapsto \text{counterfactual loss},\quad
\text{memory clone}\mapsto \text{protected witness},\quad
\text{affinity maturation}\mapsto \text{test refinement}.
\]

[theoretical] The analogy holds exactly where memory must preserve low-frequency, high-consequence constraints under bounded resources.

[theoretical] The analogy breaks because immune affinity is physical binding, while agent memory needs semantic and causal validity.

[theoretical] What is lost is biochemical parallelism; what can be recovered is a resource law: protection energy should scale with expected loss, not with frequency.

### 2.3 AI Primitive Implied

[speculative] The primitive implied is a **danger-cloned witness**: multiple independent, provenance-bound tests for a constraint whose omission has high expected regret.

[theoretical] It is represented as \(\omega=(c,e,\tau,\rho,\mathcal T)\), where \(c\) is a constraint over histories, \(e\) is evidence, \(\tau\) is temporal validity, \(\rho\) is loss under omission, and \(\mathcal T\) is a set of validation tests.

[theoretical] It interacts with language by using language only to propose candidate constraints and human-readable explanations; the stored object is the constraint plus evidence and tests.

[theoretical] A toy implementation is possible today with typed predicates, interval fields, evidence pointers, and a small library of domain risk rules.

### 2.4 Plausibility

[theoretical] Theoretical soundness: medium-high, because the selection equation maps cleanly to resource allocation under rare high loss.

[theoretical] Empirical testability: high, because rare-critical insertion tests are simple to build.

[theoretical] Architectural feasibility: high, because protected witnesses can be implemented without new hardware.

## Mechanism 2: Sheaf Cohomology And Gauge-Protected Identity

### 2.1 Native Mechanism

[established] In topology, cohomology studies global invariants defined by local consistency conditions.

[established] A cochain complex consists of groups \(C^k\) and coboundary maps \(\delta_k:C^k\to C^{k+1}\) with \(\delta_{k+1}\circ\delta_k=0\).

[established] Cohomology classes are
\[
H^k=\ker \delta_k / \operatorname{im}\delta_{k-1}.
\]

[established] In gauge theory, local descriptions may vary while physical observables remain invariant under a transformation group \(G\).

[established] In topological error correction, information is protected nonlocally; local perturbations do not change the encoded class unless they form an error chain crossing code distance.

[established] Native limits include decoding complexity, finite-size failure, and threshold dependence on noise assumptions.

[theoretical] The selection pressure is robustness: preserve global state under local disturbance.

### 2.2 Structural Analogy

[theoretical] Sessions form local patches \(U_i\) over an interaction manifold; a claim extracted from a patch is a local section \(s_i\).

[theoretical] A memory is globally coherent when local sections agree on overlaps: \(s_i|_{U_i\cap U_j}=g_{ij}s_j|_{U_i\cap U_j}\), where \(g_{ij}\in G\) transports identity and units across contexts.

[theoretical] Contradiction is curvature:
\[
F_{ijk}=g_{ij}g_{jk}g_{ki}\ne I.
\]

[theoretical] A stable memory is not a note but an equivalence class \([s]\) of locally different descriptions that preserve the same action-relevant invariant.

[theoretical] The analogy holds for identity evolution, temporal contradiction, and multi-session dependency.

[theoretical] The analogy breaks because language does not come with a canonical topology; the cover must be induced by sessions, tasks, entities, and times.

[theoretical] What is lost is mathematical purity; what is recovered is an explicit diagnostic for contradiction as curvature rather than as string mismatch.

### 2.3 AI Primitive Implied

[speculative] The primitive implied is a **cohomological witness class**, \([\omega]\), whose identity is its invariant effect across local contexts rather than its textual form.

[theoretical] It is represented by local witnesses, transition maps between mentions, interval restrictions, and a coboundary operator detecting inconsistency.

[theoretical] It interacts with neural language models by receiving candidate local sections from them, but consistency is checked by symbolic temporal and identity transport.

[theoretical] A toy implementation is possible today using interval constraints, mention equivalence classes, and cycle checks over small covers; this is not a knowledge graph proposal because the primitive is the consistency class and its coboundary, not a node-edge store.

### 2.4 Plausibility

[theoretical] Theoretical soundness: medium, because the sheaf formalism is exact but the semantic cover is learned or engineered.

[theoretical] Empirical testability: medium-high, because contradiction/identity loops can be generated and scored.

[theoretical] Architectural feasibility: medium, because local consistency checks are feasible but semantic section construction remains imperfect.

## Mechanism 3: Decision-Theoretic Value Of Information And Active Inference

### 2.1 Native Mechanism

[established] The value of information is the expected improvement in decision utility from observing information before acting.

[theoretical] For information \(I\), actions \(a\), state \(S\), and utility \(U\),
\[
\operatorname{VoI}(I)=
\mathbb E_I\left[\max_a \mathbb E[U(a,S)\mid I]\right]
-\max_a \mathbb E[U(a,S)].
\]

[established] Active inference and the free-energy principle formulate action and perception as reducing expected uncertainty or expected cost under a generative model.

[theoretical] The mechanism solves the problem of what to observe, preserve, or act on when sensing and memory are costly.

[established] Known limits are model misspecification, computational intractability, and dependence on utility specification.

[theoretical] The pressure that produces the mechanism is scarcity: not all observations can be acquired or maintained, so information must be priced by its expected effect on action.

### 2.2 Structural Analogy

[theoretical] The exact correspondence is:
\[
\text{future decision}\mapsto Q,\quad
\text{information item}\mapsto \omega,\quad
\text{utility improvement}\mapsto \text{regret avoided by retaining }\omega.
\]

[theoretical] A fact is important if removing it changes the optimal policy under some plausible future task:
\[
\Delta_Q(\omega)=
\mathcal L(\pi_Q(M\setminus\{\omega\}),H)
-\mathcal L(\pi_Q(M),H).
\]

[theoretical] The analogy holds when memory is used for action; it weakens for purely aesthetic recall unless aesthetic loss is modeled.

[theoretical] What is lost is objective utility; what can be recovered is a conservative upper bound from harm, irreversibility, legal obligation, user preference, and causal centrality.

### 2.3 AI Primitive Implied

[speculative] The primitive implied is a **regret certificate**, a computable claim that a witness must be protected because some action class becomes unsafe, impossible, or lower value without it.

[theoretical] It is represented by a tuple \((\omega,\mathcal A_\omega,\ell_\omega,p_\omega)\), where \(\mathcal A_\omega\) is the set of actions constrained by \(\omega\), \(\ell_\omega\) is loss if omitted, and \(p_\omega\) is belief.

[theoretical] Language models can propose action classes and explanations, but the memory operation is governed by a numerical regret bound.

[theoretical] A toy implementation is possible today by assigning domain-independent risk classes, such as safety, identity, finance, schedule, legal, medical, and preference.

### 2.4 Plausibility

[theoretical] Theoretical soundness: high, because VoI directly formalizes memory under future decision.

[theoretical] Empirical testability: high, because regret-weighted metrics can be measured.

[theoretical] Architectural feasibility: medium-high, because exact VoI is hard but upper-bound risk classes are deployable.

---

# Phase 3: Unified Theory

## 3.1 Name And Postulates

[speculative] The theory is **Invariant Witness Theory** (IWT).

[speculative] IWT states that persistent agent memory is a bounded, evolving set of protected witnesses: constraints on admissible histories with temporal validity, identity transport, uncertainty, provenance, and counterfactual regret charge.

[theoretical] IWT applies when an agent must act under partial observability and its future tasks depend on facts distributed across a long history.

[speculative] Postulate 1: The fundamental unit of memory is a witnessed constraint, not text, not an embedding, not a chunk, not a graph triple.

[speculative] Postulate 2: A memory is preserved in proportion to its cohomological regret charge: expected action loss under removal multiplied by the stability/inconsistency structure of the contexts supporting it.

[speculative] Postulate 3: Temporal and identity consistency are gauge constraints over local observations.

[speculative] Postulate 4: Consolidation is valid only if it preserves all invariants above a regret threshold.

[speculative] Postulate 5: Forgetting is controlled erasure of low-charge degrees of freedom, never creation of new historical information.

[theoretical] If future task relevance cannot be modeled even approximately, Postulate 2 collapses and IWT becomes a descriptive language rather than a predictive theory.

## 3.2 The New Primitive: The Witness

[speculative] A witness \(\omega\) is
\[
\omega=\left(
c_\omega,\ e_\omega,\ \tau_\omega,\ \Gamma_\omega,\ p_\omega,\ 
\rho_\omega,\ \partial\omega,\ \mathcal T_\omega,\ E_\omega
\right).
\]

[theoretical] \(c_\omega:\mathcal H\to\{0,1\}\) is a constraint on admissible histories.

[theoretical] \(e_\omega\) is provenance: pointers to observations sufficient to audit the constraint.

[theoretical] \(\tau_\omega=(\tau^v,\tau^x,\tau^b)\) gives valid time, transaction time, and belief time.

[theoretical] \(\Gamma_\omega\) is identity transport: the maps that say which mentions are the same entity under action-relevant equivalence.

[theoretical] \(p_\omega\in[0,1]\) is current credence.

[theoretical] \(\rho_\omega(Q,A)\) is regret density: expected loss if the witness is absent for task \(Q\) and action class \(A\).

[theoretical] \(\partial\omega\) is the dependency boundary: other witnesses that must be present to interpret \(\omega\).

[theoretical] \(\mathcal T_\omega\) is a finite set of validation tests, including temporal, identity, and contradiction tests.

[theoretical] \(E_\omega\) is protection energy controlling decay and forgetting.

[speculative] The cohomological regret charge is
\[
q(\omega)=
\mathbb E_{Q\sim P_t}\left[\Delta_Q(\omega)\right]
\cdot
\left(1+\lambda\|\delta \omega\|\right)
\cdot
\left(1+\kappa D_\omega\right),
\]
[theoretical] where \(\Delta_Q\) is action regret under removal, \(\delta\omega\) is inconsistency/curvature detected over the cover, and \(D_\omega\) is danger severity.

[theoretical] Witness operations are restriction to a time/entity context, transport across identity maps, composition into a joint constraint, contradiction by non-empty overlap with incompatible truth values, marginalization that removes low-charge detail, and audit by returning provenance.

## 3.3 The Four Operations

### WRITE

[theoretical] Exact write is
\[
M_{t+1}=f(M_t,O_t,C_t)
=\operatorname{Normalize}
\left(M_t\cup\{\omega(O_t): q_t(\omega)>\lambda c(\omega)\}\right),
\]
[theoretical] where \(C_t\) is current context, \(c(\omega)\) is storage cost, and Normalize resolves temporal intervals, identity transport, and duplicate constraints without deleting provenance.

[theoretical] A candidate observation is encoded if it reduces admissible histories in a decision-relevant way:
\[
I_{\rm act}(\omega)=
D_{\rm KL}\left(P(\Pi^*\mid M_t,O_t)\parallel P(\Pi^*\mid M_t)\right),
\]
[theoretical] WRITE includes \(\omega\) if \(I_{\rm act}(\omega)\) or danger severity exceeds threshold.

[theoretical] The write decision does not require knowing exact future queries; it requires a prior over action classes and harms.

[theoretical] In the three-year medical scenario, Session 12 writes a high-charge witness:
\[
\omega_{12}: c=\text{"patient allergic to penicillin-class antibiotics"},\quad
\tau^v=[12,\infty),\quad
D=\text{medical safety}.
\]

[theoretical] Session 89 writes a medium-charge interval witness:
\[
\omega_{89}: \text{"night shifts cause sleep disruption"},\quad
\tau^v=[89,445).
\]

[theoretical] Session 156 writes an action-routing witness:
\[
\omega_{156}: \text{"insurer excludes Clinic A"},\quad
\tau^v=[156,\infty)\ \text{unless updated}.
\]

[theoretical] Session 203 writes a dependency witness:
\[
\omega_{203}: \text{"doctor knew allergy and prescribed cephalosporins instead"},
\quad \partial\omega_{203}=\{\omega_{12}\}.
\]

[theoretical] Session 445 closes the night-shift interval:
\[
\omega_{445}: \text{"night shifts stopped; sleep normalized"},\quad
\tau^v=[445,\infty).
\]

[theoretical] Session 612 writes a record-gap witness:
\[
\omega_{612}: \text{"new doctor lacks old records"},\quad
\partial\omega_{612}=\{\omega_{12},\omega_{203}\}.
\]

[theoretical] The system does not encode pleasantries, duplicate wording, or transient symptoms with no future action effect unless they change uncertainty, validity, identity, or regret charge.

[theoretical] WRITE failure modes include inflated danger labels, missed latent relevance, wrong identity transport, and over-normalization that merges incompatible witnesses.

### READ

[theoretical] Exact read is not nearest-neighbor selection. It is minimal sufficient reconstruction:
\[
S^*(Q,M_T)=
\arg\min_{S\subseteq M_T}
\left[K(S)+\beta |S|\right]
\]
subject to
\[
\sup_{h,h'\in\mathcal H(S,Q)}
d\left(\pi^*_Q(h),\pi^*_Q(h')\right)\le\epsilon .
\]

[theoretical] The replacement for cosine similarity is **counterfactual separability**:
\[
\Delta_Q(\omega)=
d\left(\pi_Q(M_T),\pi_Q(M_T\setminus\{\omega\})\right).
\]

[theoretical] A witness is read when omitting it changes the safe answer, action, abstention, or uncertainty interval.

[theoretical] For Session 698, the query asks for fastest safe treatment, appointment booking, and risk flags. The minimal read set is
\[
S^*=\{\omega_{12},\omega_{156},\omega_{203},\omega_{612}\}
\]
[theoretical] with \(\omega_{445}\) optional and \(\omega_{89}\) excluded because its validity interval has ended.

[theoretical] The reconstructed answer is: flag penicillin-class allergy; note prior clinician chose cephalosporins after acknowledging allergy; avoid assuming the new doctor has that record; book the fastest available non-Clinic-A in-network clinician or urgent care; tell the clinician the allergy before antibiotic selection; propagate uncertainty that insurer status may have changed if no witness after Session 156 confirms it.

[theoretical] Contradictions are resolved at read time by interval overlap, identity transport, credence, and action conservatism. If "not allergic" appears later without provenance, the conflict is not averaged; it becomes a curvature event requiring clarification before unsafe recommendation.

[theoretical] Uncertainty propagates by carrying \(p_\omega\) and interval staleness into the answer:
\[
P(\text{safe action}\mid S^*)=\int P(\text{safe action}\mid x,S^*)\,dP(x\mid S^*).
\]

[theoretical] READ failure modes include exponential subset search, wrong task prior, false independence among witnesses, and overly conservative abstention.

### CONSOLIDATION

[theoretical] Consolidation is an idle-time map
\[
M'_T=h(M_T)=
\arg\min_{M':C(M')\le B}
\mathbb E_{Q\sim P_T}\left[\operatorname{Regret}(Q,M')\right]
+\eta K(M')
\]
subject to preserving all witnesses with charge \(q(\omega)>\theta\) up to equivalence.

[theoretical] Consolidation is triggered by budget pressure, high contradiction curvature, repeated low-charge redundancy, or idle compute availability.

[theoretical] It preserves high-charge witnesses, interval boundaries, identity transport maps, dependency boundaries, and provenance sufficient for audit.

[theoretical] It releases low-charge surface forms, duplicate language, obsolete local detail whose valid interval is closed and whose downstream regret is below threshold.

[established] Consolidation cannot create historical information because \(M'_T=h(M_T)\) and therefore \(I(H_T;M'_T)\le I(H_T;M_T)\).

[theoretical] It can create hypotheses, such as "insurance may be stale", but those must be labeled inferred and cannot be treated as observed witnesses.

[theoretical] In the scenario, consolidation may merge Sessions 89 and 445 into one closed interval witness for sleep disruption, but it may not merge the allergy and cephalosporin-tolerance evidence into "safe to prescribe cephalosporins" because that is a medical action judgment not observed.

[theoretical] CONSOLIDATION failure modes include false invariant discovery, provenance loss, interval boundary loss, and hypothesis-observation confusion.

### FORGETTING

[theoretical] Let \(E_\mu(t)\) be protection energy of witness \(\mu\). Forgetting dynamics are
\[
\frac{dE_\mu}{dt}
=
-\alpha E_\mu
+\beta \widehat{\operatorname{VoI}}_\mu
+\chi D_\mu
+\zeta C_\mu
-\psi R_\mu
-\xi c_\mu ,
\]
[theoretical] where \(D_\mu\) is danger severity, \(C_\mu=\|\delta\mu\|\) is contradiction/curvature requiring preservation, \(R_\mu\) is redundancy, and \(c_\mu\) is resource cost.

[theoretical] A witness is forgotten when \(E_\mu<E_{\rm barrier}\) and no protected dependent witness has \(\mu\in\partial\nu\).

[theoretical] Rare-critical facts are protected because \(D_\mu\) and \(\widehat{\operatorname{VoI}}_\mu\) dominate frequency decay.

[theoretical] The steady-state distribution is a non-equilibrium Gibbs-like allocation:
\[
P(\mu\in M)\propto
\exp\left(\frac{\beta \widehat{\operatorname{VoI}}_\mu+\chi D_\mu+\zeta C_\mu-\xi c_\mu}{T_m}\right),
\]
[theoretical] where \(T_m\) is memory temperature controlling exploration versus rigid retention.

[established] Forgetting is irreversible when the evidence pointer and all redundant witnesses are erased; by data processing and Landauer-style irreversibility, the original observation cannot be recovered from the remaining memory alone.

[theoretical] In the scenario, the allergy witness remains protected indefinitely; the night-shift witness decays to a closed-history fact; duplicate appointment chatter decays rapidly; the insurance exclusion persists with increasing staleness uncertainty.

[theoretical] FORGETTING failure modes include pathological hoarding of high-danger false positives, irreversible erasure under a wrong task prior, and memory freezing when danger labels are overused.

## 3.4 Temporal Semantics

[theoretical] IWT uses three times: valid time \(\tau^v\), when the proposition is true in the modeled world; transaction time \(\tau^x\), when the agent observed or stored it; and belief time \(\tau^b\), when the agent assigns credence.

[theoretical] "X was true from \(T_1\) to \(T_2\)" is represented as
\[
\omega_X: X(e,t)=1\ \forall t\in[T_1,T_2),\quad
\tau^x=t_{\rm observed},\quad
p_{\tau^b}(X)>p_0.
\]

[theoretical] "X is believed true but may be stale" is represented by a survival function
\[
P(X(t)=1\mid \omega_X)=\exp\left(-\int_{\tau^v_0}^{t}\lambda_X(s)\,ds\right)
\]
[theoretical] when no closing witness exists.

[theoretical] A temporal contradiction occurs when two witnesses impose incompatible predicates over overlapping valid intervals after identity transport.

[theoretical] Contradictions are resolved by splitting intervals, lowering credence, asking for new evidence, or choosing the action that minimizes worst-case regret.

## 3.5 Identity Model

[theoretical] A mention \(m_i\) denotes entity \(E\) not by name equality but by membership in an orbit under an action-preserving gauge group \(G\).

[theoretical] Two mentions refer to the same entity when there exists a transport map \(g_{ij}\in G\) such that action-relevant predicates remain invariant under transport:
\[
P(A\mid m_i,\omega)=P(A\mid g_{ij}m_j,\omega)\pm\epsilon .
\]

[theoretical] Entity state evolves by time-indexed belief:
\[
Bel(E,t\mid L)=P(X_E(t)\mid \sigma(\omega_\ell:\ell\in L),\Gamma).
\]

[theoretical] Contradiction is detected by holonomy: if \(g_{12}g_{23}g_{31}\ne I\), then a loop through mentions returns a different entity state than it began with.

[theoretical] In the scenario, "patient", "you", the insured person, and the medical-record subject are the same entity under transport; "old doctor" and "new doctor" are distinct entities even though both instantiate the role doctor.

## 3.6 Boundary Conditions

[established] No finite memory can guarantee rational action for arbitrary future questions over an unbounded history.

[theoretical] IWT requires a future task prior, a harm model, temporal extraction good enough to form witnesses, and auditable provenance.

[theoretical] IWT cannot solve semantic extraction from observations by itself, cannot prove medical truth beyond evidence, cannot recover erased evidence, and cannot remove the need for uncertainty.

[theoretical] IWT reduces to existing approaches as special cases: if all witnesses have equal charge and no temporal/identity constraints, it becomes flat storage; if read uses only textual closeness, it becomes retrieval; if witnesses are forced into entity-relation tuples, it becomes a temporal graph; if all history is read, it becomes full-context reasoning.

---

# Phase 4: Mathematical Architecture

## 4.1 Memory State Space

[theoretical] The bounded memory state space is
\[
\mathcal M_B=
\left\{
M=(W,\Gamma,\mathcal I,\mathcal P,E):
W\subset\Omega,\ \sum_{\omega\in W} c(\omega)\le B
\right\},
\]
[theoretical] where \(W\) is a finite set of witnesses, \(\Gamma\) identity transport, \(\mathcal I\) interval algebra, \(\mathcal P\) provenance, and \(E\) protection energies.

[theoretical] The natural topology is induced by a decision-regret pseudometric:
\[
d_{\Pi}(M,N)=
\sup_{Q\in\mathcal Q}
w(Q)\,
D_{\rm TV}\left(\pi_Q^M,\pi_Q^N\right).
\]

[theoretical] Distance means two memories are far apart if they induce different actions, abstentions, or uncertainty under important future tasks.

[theoretical] A second topology is the consistency topology, where neighborhoods preserve the set of high-charge cohomology classes and have bounded curvature \(\|\delta M\|\).

## 4.2 Dynamics

[theoretical] Let \(P(M,t)\) be the probability distribution over memory states. A birth-death-consolidation master equation is
\[
\frac{\partial P(M,t)}{\partial t}
=
\sum_{\omega}
\left[
w^+_\omega(M-\omega)P(M-\omega,t)-w^+_\omega(M)P(M,t)
\right]
\]
\[
+
\sum_{\omega}
\left[
w^-_\omega(M+\omega)P(M+\omega,t)-w^-_\omega(M)P(M,t)
\right]
+
\sum_{N}
\left[
k(N\to M)P(N,t)-k(M\to N)P(M,t)
\right].
\]

[theoretical] \(w^+_\omega\) is write rate, \(w^-_\omega\) is forgetting rate, and \(k\) is consolidation transition rate.

[theoretical] A fixed point satisfies zero net flux for high-charge witness classes and bounded total cost.

[theoretical] Attractors are minimal sufficient witness sets: removing any high-charge witness increases expected regret, adding any low-charge witness increases cost without reducing regret.

[theoretical] Limit cycles appear when a witness alternates between stale and refreshed, such as insurance status periodically reconfirmed.

[theoretical] Pathological divergence occurs when write rate exceeds forgetting capacity, curvature grows without reconciliation, or danger labels saturate all memory energy.

## 4.3 Information-Theoretic Constraints

[theoretical] The minimum description length of useful memory at tolerance \(\epsilon\) is
\[
L^*(\epsilon)=
\min_{M:\ \mathbb E_Q[\operatorname{Regret}(Q,M)]\le\epsilon}
K(M).
\]

[theoretical] The fundamental tradeoff is decision rate-distortion:
\[
R(D)=
\min_{P(M\mid H):\ \mathbb E[d_{\rm act}(H,M)]\le D}
I(H;M),
\]
[theoretical] where \(d_{\rm act}\) is regret distortion rather than reconstruction distortion.

[theoretical] If there are \(N\) equally likely critical hidden facts and memory contains \(B\) bits, then a Fano-style lower bound gives
\[
P_e\ge 1-\frac{B+\log 2}{\log N}.
\]

[theoretical] If facts have unequal loss \(L_i\), optimal retention is not by probability \(p_i\) alone but by \(p_iL_i\) and by dependency boundaries; this is why rare-critical facts can dominate frequent low-loss facts.

## 4.4 Computational Complexity

[theoretical] Exact WRITE is intractable in general because computing future VoI over policies contains POMDP planning as a subproblem.

[theoretical] Exact READ is NP-hard because minimal sufficient support contains set cover: choose the smallest witnesses covering all constraints needed by a query.

[theoretical] Exact CONSOLIDATION is NP-hard because it contains budgeted compression with decision distortion and dependency preservation.

[theoretical] Exact FORGETTING is tractable only if witness charges are independent; with dependencies it becomes budgeted closure selection.

[theoretical] Under monotone submodular regret reduction, greedy selection gives a \((1-1/e)\) approximation for bounded read/write support.

[theoretical] Practical complexity for a typed Level 2 system is \(O(nk)\) for read scoring over \(n\) candidate witnesses and \(k\) action constraints, \(O(r\log r)\) for forgetting over \(r\) witnesses by energy, and \(O(n^2)\) worst-case for small-cover consistency checks.

## 4.5 Approximation Hierarchy

[theoretical] Level 0 is the exact optimum: Bayes-optimal POMDP memory with exact VoI, exact cohomology over semantic covers, and exact rate-distortion consolidation. It is intractable.

[theoretical] Level 1 is a tractable approximation: typed witnesses, interval logic, identity groupoids over mentions, structural causal dependency boundaries, and greedy submodular selection.

[theoretical] Level 2 is deployable today: language proposes candidate witnesses; deterministic validators assign temporal fields, identity links, risk classes, dependency boundaries, and evidence pointers; read solves a constrained support problem; forgetting uses protection energy.

[theoretical] Level 3 is a heuristic baseline: extracted facts with timestamps, manual risk tags, interval closure, dependency pointers, and audit trails. Existing systems become degenerate Level 3 cases when they preserve evidence but lack cohomological regret charge.

---

# Phase 5: Five Falsifiable Hypotheses

## H1: Write Policy

HYPOTHESIS: [speculative] A write policy based on estimated regret charge will retain rare-critical facts at equal memory budget better than salience-based write policies.

MECHANISM: [theoretical] Rare-critical facts have low frequency but high \(D_\mu\) and \(\widehat{\operatorname{VoI}}_\mu\). Protection energy prevents them from being filtered or overwritten. Salience-based systems will underweight them because local textual prominence is low.

PREDICTION: [theoretical] In a 700-session benchmark with one critical constraint per 100 sessions, IWT Level 2 will achieve at least 95% risk-weighted recall at 10% storage budget, with at least 20 percentage-point gain over the best baseline.

BASELINE: [theoretical] Full context where feasible, MemGPT, Mem0, A-MEM, LightMem, Zep/Graphiti, and a no-memory agent.

BENCHMARK: [theoretical] A rare-critical extension of LongMemEval and the new benchmark in Phase 6.2.

FALSIFICATION: [theoretical] If salience-based baselines match IWT within 5 percentage points at equal budget and equal extraction quality across three random seeds, H1 fails.

CONFIDENCE: [theoretical] Medium-high, because the causal mechanism is direct but risk extraction may be noisy.

## H2: Read Policy

HYPOTHESIS: [speculative] Read by counterfactual separability will outperform text-proximity read on action questions with distractors.

MECHANISM: [theoretical] The read set is chosen by whether omission changes the action, not by whether text resembles the query. Distractors can resemble the query without changing the safe action. Critical constraints can be lexically remote but action-determining.

PREDICTION: [theoretical] On action-coupled tasks, IWT will reduce unsafe or contraindicated recommendations by at least 30% relative to the best baseline at the same evidence budget.

BASELINE: [theoretical] Mem0, A-MEM, LightMem, Zep/Graphiti, MemGPT, and full-context LLM.

BENCHMARK: [theoretical] MemoryArena safety/planning variants and the Phase 6.2 benchmark.

FALSIFICATION: [theoretical] If text-proximity systems achieve the same unsafe-action rate with no extra context or domain templates, H2 fails.

CONFIDENCE: [theoretical] Medium, because exact counterfactual separability is expensive and approximations may collapse to rules.

## H3: Forgetting

HYPOTHESIS: [speculative] Energy-based forgetting will show a non-monotonic advantage: lower memory volume with higher risk-weighted correctness than keep-all or recency decay.

MECHANISM: [theoretical] The system releases low-charge details and preserves high-charge constraints. This reduces overload inversion while protecting rare-critical witnesses. Keep-all overloads the read channel; recency decay erases old but important constraints.

PREDICTION: [theoretical] At 5%, 10%, and 20% memory budgets, IWT will dominate recency and keep-all on the Pareto frontier of risk-weighted accuracy versus read cost.

BASELINE: [theoretical] Recency-only, frequency-only, keep-all where feasible, MemGPT, LightMem, and Mem0.

BENCHMARK: [theoretical] BEAM-scale synthetic histories plus rare-critical labels.

FALSIFICATION: [theoretical] If keep-all or recency-only is Pareto-superior at all tested budgets, H3 fails.

CONFIDENCE: [theoretical] Medium, because overload is established but the exact frontier depends on reader behavior.

## H4: Temporal Reasoning

HYPOTHESIS: [speculative] Tri-temporal witnesses will reduce temporal contradiction errors more than timestamped facts.

MECHANISM: [theoretical] Valid time, transaction time, and belief time answer different questions. Timestamped facts collapse them, producing stale or inverted conclusions. Interval closure and staleness hazards make uncertainty explicit.

PREDICTION: [theoretical] On temporal update questions, IWT will reduce wrong-current-state answers by at least 25% relative to timestamp-only baselines.

BASELINE: [theoretical] Long-context LLM, Mem0, LightMem, A-MEM, Zep/Graphiti, and a timestamped extracted-fact store.

BENCHMARK: [established] LongMemEval temporal reasoning and knowledge update tasks; [theoretical] augmented LoCoMo update tasks.

FALSIFICATION: [theoretical] If timestamped facts with no valid/belief separation match within 5 percentage points, H4 fails.

CONFIDENCE: [theoretical] High, because temporal database theory directly predicts the failure of single-time representations.

## H5: Causal Dependency

HYPOTHESIS: [speculative] Dependency-boundary witnesses will improve cross-session action success where early observations constrain late actions.

MECHANISM: [theoretical] A boundary \(\partial\omega\) preserves the conditions needed to interpret a later witness. Read reconstructs a causal support set rather than isolated facts. Omitting a boundary witness changes the action under intervention.

PREDICTION: [theoretical] On interdependent multi-session tasks, IWT will increase task success by at least 15 percentage points and reduce missing-precondition failures by at least 30%.

BASELINE: [theoretical] MemoryArena published baselines plus MemGPT, Mem0, A-MEM, LightMem, Zep/Graphiti.

BENCHMARK: [established] MemoryArena; [theoretical] Phase 6.2 causal-chain split.

FALSIFICATION: [theoretical] If adding dependency boundaries does not improve over identical witnesses without boundaries, H5 fails.

CONFIDENCE: [theoretical] Medium, because causal extraction is hard but the evaluation is clean.

---

# Phase 6: Experimental Program

## 6.1 Benchmark Gap Analysis

[established] LoCoMo tests long-term conversation QA, event summarization, and multimodal dialogue generation over multi-session dialogue.

[theoretical] LoCoMo can test temporal reasoning and cross-session recall, but its blind spot is risk-weighted action loss. A clean modification would add hidden high-regret constraints and score unsafe actions, not just answer overlap.

[established] LongMemEval tests extraction, multi-session reasoning, temporal reasoning, updates, and abstention over 500 curated questions.

[theoretical] LongMemEval can test write/read/temporal hypotheses, but its blind spot is bounded-memory survival under action harm. A clean modification would enforce a storage budget and use regret-weighted grading.

[established] BEAM scales coherent conversations to 10M tokens and includes validated questions over a range of memory abilities.

[theoretical] BEAM can test overload inversion and forgetting, but its blind spot is the distinction between high-frequency relevance and low-frequency high-risk constraints. A clean modification would add rare-critical causal witnesses with delayed action queries.

[established] MemoryArena tests memory acquisition and later use in interdependent multi-session agentic tasks.

[theoretical] MemoryArena can test causal dependency and write blindness, but its blind spot is formal temporal validity and risk-weighted sufficiency. A clean modification would log all ground-truth causal preconditions and score missing-precondition regret.

[established] MemGround tests interactive dynamic state, temporal association, and reasoning from accumulated evidence.

[theoretical] MemGround can test dynamic tracking and temporal association, but its blind spot is provenance-preserving witness sufficiency. A clean modification would require the agent to output the minimal witness set supporting each action.

## 6.2 New Benchmark: Counterfactual Continuity Benchmark

[speculative] The new benchmark is **Counterfactual Continuity Benchmark** (CCB).

[theoretical] CCB contains 1,000 synthetic-but-human-edited agent histories, each 200 to 1,000 sessions, across medical logistics, finance, project management, family care, travel, and legal-administrative domains.

[theoretical] Each history contains low-frequency high-regret witnesses, stale facts, identity shifts, contradictions, and delayed causal dependencies.

[theoretical] The task is not to answer from memory alone but to choose a safe action, state uncertainty, and output a minimal support set of witnesses.

[theoretical] Ground truth is established by a hidden event calculus and structural causal simulator, with human review for natural-language plausibility.

[theoretical] The isolated failure mode is collapse of decision-distinct histories into the same memory state.

[theoretical] Existing systems cannot solve CCB by construction unless they approximate witness reasoning, because the score penalizes unsupported action, stale validity, missing dependency boundary, and unsafe omission, not only answer text.

[theoretical] Estimated build cost is 8 weeks for a prototype of 200 histories, 4 annotators, one simulator engineer, and one evaluation engineer; full 1,000-history release is 4 to 6 months.

## 6.3 Three Core Experiments

### Experiment 1: Rare-Critical Survival

[theoretical] Baselines are full-context LLM where feasible, MemGPT, Mem0, A-MEM, LightMem, Zep/Graphiti, and recency-only memory.

[theoretical] Experimental system is IWT Level 2 with danger-cloned witnesses and energy forgetting.

[theoretical] Dataset is CCB-Rare plus LongMemEval modified with high-regret hidden constraints.

[theoretical] Primary metric is risk-weighted action accuracy:
\[
\operatorname{RWAA}=\frac{\sum_i L_i\mathbf 1[\text{safe correct}_i]}{\sum_i L_i}.
\]

[theoretical] Ablations are no danger term, no VoI term, no dependency boundary, no temporal intervals, and uniform forgetting.

[theoretical] Expected effect size is 20 to 35 percentage points on RWAA at 10% budget.

[theoretical] Failure modes are over-retention, false danger labels, and domain-rule leakage; detect them by calibration curves and out-of-domain histories.

[theoretical] Internal validity threats are annotation bias and hidden templates; external validity threat is synthetic domain structure.

[theoretical] Compute budget is modest: below 5,000 LLM calls for extraction plus local deterministic evaluation for prototype scale.

### Experiment 2: Temporal-Identity Consistency

[theoretical] Baselines are timestamped fact store, full-context LLM, Mem0, A-MEM, LightMem, Zep/Graphiti, and MemGPT.

[theoretical] Experimental system is IWT Level 2 with tri-temporal witnesses and gauge transport.

[theoretical] Dataset is LongMemEval temporal/update questions, LoCoMo temporal questions, and CCB-Identity loops.

[theoretical] Primary metric is interval-correct belief:
\[
\operatorname{ICB}=\mathbf 1[
\hat X(e,t)\text{ matches truth and uncertainty is calibrated}
].
\]

[theoretical] Ablations are no valid time, no belief time, no identity transport, no curvature check, and no staleness hazard.

[theoretical] Expected effect size is 15 to 25 percentage points on current-state and contradiction questions.

[theoretical] Failure modes are spurious splits, spurious merges, and excessive abstention; detect them by entity-pair precision/recall and abstention calibration.

[theoretical] Internal validity threat is evaluator leakage of interval syntax; external validity threat is real-world ambiguity beyond benchmark labels.

[theoretical] Compute budget is below 10,000 LLM calls plus interval solver execution.

### Experiment 3: Cross-Session Causal Dependency

[theoretical] Baselines are MemoryArena default agents, full-context LLM where feasible, MemGPT, Mem0, A-MEM, LightMem, and Zep/Graphiti.

[theoretical] Experimental system is IWT Level 2 with dependency-boundary witnesses and read by counterfactual separability.

[theoretical] Dataset is MemoryArena plus CCB-Causal, where early constraints become late action preconditions.

[theoretical] Primary metric is task success under hidden causal precondition:
\[
\operatorname{CPS}=\frac{1}{N}\sum_i
\mathbf 1[\text{action succeeds and all required preconditions are cited}].
\]

[theoretical] Ablations are no boundary pointers, no read separability, no evidence audit, no risk weighting, and no temporal closure.

[theoretical] Expected effect size is 15 to 30 percentage points on CPS.

[theoretical] Failure modes are memorizing benchmark templates, citing irrelevant witnesses, and missing latent causal links; detect them with held-out domains and causal graph perturbations.

[theoretical] Internal validity threat is scoring too close to the IWT representation; external validity threat is real agent environments with unmodeled effects.

[theoretical] Compute budget is 20,000 to 50,000 LLM calls for full baseline comparison.

## 6.4 Landmark Result

[speculative] The landmark result is a capacity-scaling curve: at fixed 10% memory budget and 700-session histories, IWT maintains at least 90% risk-weighted action accuracy while all baselines fall below 65%, and the gap widens rather than shrinks as history length increases.

[theoretical] The phenomenon would be a phase transition: existing systems show overload inversion after a critical history length, while IWT shows stable high-charge witness conservation.

[theoretical] The single headline number is \(\Delta_{\rm RWAA}\ge 25\) percentage points at 10% budget with calibrated uncertainty and audited support sets.

---

# Phase 7: Hostile Tribunal

## Scientist B: 7.1 The Kill Shot

[theoretical] The single fragile assumption is that future task relevance can be approximated well enough to assign regret charge at write time.

[theoretical] If this assumption is false, \(q(\omega)\) becomes arbitrary. Then IWT either stores everything, collapsing to full-context or archival hoarding, or stores salient extracted facts, collapsing to existing memory systems.

[theoretical] The collapse is exact: if \(q(\omega)=\text{constant}\), forgetting becomes cost/recency allocation; if \(q(\omega)\) is estimated by textual salience, write becomes extraction; if read uses observed query overlap because \(\Delta_Q\) is unavailable, read becomes retrieval.

## Scientist A Response

[theoretical] Concede the assumption is the central risk.

[speculative] Revise the theory: IWT is not a universal memory theory for arbitrary future tasks; it is a theory for agents with learnable or declared action niches.

[theoretical] The first empirical target must therefore be domains where regret priors are explicit: medical logistics, finance, scheduling, legal compliance, safety, and user commitments.

## Scientist B: 7.2 Prior Art Attack

[established] Immune clonal selection has inspired artificial immune systems, anomaly detection, negative selection algorithms, and danger-theory-inspired classifiers.

[established] Topological and sheaf methods have been proposed in machine learning, sensor fusion, distributed consistency, and topological data analysis.

[established] Value of information has long been used in decision theory, active sensing, Bayesian experimental design, reinforcement learning, and memory management.

[theoretical] Therefore none of the three mechanisms is novel in isolation.

## Scientist A Response

[theoretical] Concede component novelty is absent.

[speculative] The novelty claim narrows to the primitive: a memory witness whose retention energy is the product of regret under intervention and cohomological inconsistency over temporal/identity covers.

[theoretical] The paper must state that the contribution is synthesis into a falsifiable memory unit and operations, not discovery of immune selection, sheaves, or VoI.

## Scientist B: 7.3 Empirical Attack

[established] LongMemEval shows that memory design optimizations can greatly improve recall and downstream QA without IWT.

[established] Mem0 reports outperforming several baselines on LoCoMo and large latency/token reductions.

[established] LightMem reports up to 7.7% and 29.3% QA accuracy improvements on LongMemEval and LoCoMo, plus major token/API reductions.

[established] Zep reports temporal-memory gains and latency reduction on LongMemEval.

[theoretical] These results weaken the claim that existing methods are scientifically bankrupt.

## Scientist A Response

[theoretical] Concede that current systems produce real engineering gains.

[theoretical] The revised claim is asymptotic and diagnostic: existing systems lack formal conservation of decision-relevant rare-critical witnesses under bounded memory, even if they improve average QA.

[theoretical] IWT must beat them on CCB and risk-weighted capacity curves, not merely assert superiority.

## Scientist B: 7.4 Complexity Attack

[theoretical] Exact IWT contains POMDP planning, set cover, budgeted compression, and semantic consistency; it is computationally intractable.

[theoretical] The Level 2 approximation may reduce to a temporal fact table with risk scores and dependency pointers.

[theoretical] If so, the formal machinery is decorative.

## Scientist A Response

[theoretical] Concede exact IWT is intractable.

[theoretical] Reject that this makes the theory decorative: statistical mechanics and Bayesian decision theory also define intractable optima but yield useful order parameters and approximations.

[speculative] The decisive order parameter is cohomological regret charge; if experiments show that charge predicts survival necessity and overload resistance better than frequency, recency, or salience, the theory earns its machinery.

## Scientist B: 7.5 Benchmark Attack

[theoretical] CCB can be gamed by extracting all explicit risk templates, storing them in a domain-specific table, and applying hand-coded rules.

[theoretical] A strong existing system plus domain prompts could mimic witness behavior without implementing IWT.

## Scientist A Response

[theoretical] Concede the first version can be gamed.

[theoretical] Revise CCB to include held-out domains, adversarial paraphrases, hidden causal generators, counterfactual interventions, and scoring of minimal support sets under perturbed histories.

[theoretical] A system that passes by implementing explicit risk constraints, temporal validity, identity transport, and dependency boundaries has in practice implemented the Level 3 approximation, which is acceptable for the minimal publishable unit.

---

# Phase 8: Research Roadmap

## 8.1 Minimal Publishable Unit

[theoretical] The smallest publishable experiment is a 500-line Python Level 3 witness engine.

[theoretical] It implements witnesses with fields \(c,e,\tau,p,\rho,\partial,E\), interval closure, dependency-aware read, and energy forgetting.

[theoretical] It evaluates on a synthetic 700-session rare-critical benchmark with fixed budget and compares against recency, frequency, keep-all, and extracted-fact baselines.

[theoretical] A positive result suitable for a workshop is a risk-weighted accuracy gain above 20 percentage points at equal memory budget, with ablations showing the danger term and temporal interval term matter.

## 8.2 Twelve-Month Program

[theoretical] Months 1-2 deliver formal definitions, synthetic generator, and benchmark selection. Risk: the formalism is too broad. Fallback: restrict to rare-critical and temporal validity.

[theoretical] Months 3-4 deliver the Level 3 prototype under 500 lines plus deterministic tests. Risk: extraction noise dominates. Fallback: use oracle witnesses first, then add extraction later.

[theoretical] Months 5-6 deliver baseline experiments on LongMemEval and LoCoMo variants. Risk: no gain on public benchmarks. Fallback: report benchmark blind spot and focus on risk-weighted synthetic tasks.

[theoretical] Months 7-8 deliver CCB prototype with 200 histories and human review. Risk: benchmark can be gamed. Fallback: add counterfactual perturbation scoring and held-out domains.

[theoretical] Months 9-10 deliver full experimental program with three experiments and ablations. Risk: Level 2 approximation collapses to rules. Fallback: publish the collapse as a negative result showing which theoretical components are unnecessary.

[theoretical] Months 11-12 deliver paper, rebuttal pack, artifacts, and replication scripts. Risk: reviewers see it as over-theory. Fallback: submit a narrower empirical paper on risk-weighted memory conservation.

## 8.3 Five-Year Vision

[speculative] If IWT works, agent memory research shifts from "what should be found?" to "what constraints must never be collapsed?".

[speculative] The field gains memory systems that can maintain safety facts, commitments, identity continuity, temporal validity, and causal dependencies across years without unbounded context growth.

[speculative] Solved classes include personal medical-logistics assistants, long-running project agents, compliance-aware enterprise assistants, multi-user household agents, and multi-agent handoff systems where rare facts matter more than frequent themes.

[speculative] Existing lookup architectures become implementation details for low-charge facts, not the foundation of agent memory.

## 8.4 Dead-End Protocol

[theoretical] If the core hypothesis is falsified by Month 6, the salvageable contribution is a formal benchmark showing that rare-critical memory cannot be evaluated by average QA alone.

[theoretical] Surviving sub-hypotheses are tri-temporal representation, risk-weighted scoring, and dependency-boundary evaluation.

[theoretical] The fastest pivot is to publish CCB plus a negative result: simple risk-tagged interval witnesses explain most gains, while cohomological machinery is unnecessary at current benchmark scale.

[theoretical] That pivot preserves the generator, metrics, baselines, extraction code, and formal impossibility framing.

---

# Final Theoretical Commitments

[theoretical] We know finite memory cannot preserve arbitrary history for arbitrary future tasks.

[theoretical] We do not know whether cohomological regret charge can be estimated robustly from natural language interactions.

[theoretical] It is not unknowable; it is measurable by whether charge predicts which memories must survive to avoid future regret.

[speculative] The bet is that correct artificial memory is not a larger store and not a better lookup method. It is a physics of preserved constraints: the agent must conserve those distinctions in its past whose erasure would change its future obligations.
