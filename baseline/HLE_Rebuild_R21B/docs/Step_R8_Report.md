# HLE new build Step R8 report

17 September 2026 · Rebuild release 0.8.0

**R8 is complete within its declared finite symbolic language. Progress: 8/10 milestones complete; two actionable milestones remain. Next: R9 — participant-generated organization.** No milestone split was needed.

## What changed

`LanguageWorld` extends `ComposedWorld`, retaining the same world, journal, memories, recursive compositions and Socion processing. It adds paid acquisition, production and interpretation, immutable local lexicon revisions, receiver expectations and exact action linkage.

A participant accesses its own retained organization using R7's paid contextual unfold. The language operation abstracts the selected ownership relations into argument slots, preserving shared entities across relations. A concept may contain several relations recovered from a nested composition. The token is supplied; the pattern is calculated from retained content. Exact memory/composition access and the prior lexical revision remain recorded.

For example, an ownership relation learned from Alice's box can become a two-argument predicate. Alice can instantiate that predicate for Bob's tool, which was absent from her learning example. Several calls can be conjoined and combined with an ordered sequence of actions. Repeated-entity patterns retain shared argument slots rather than treating each edge as unrelated.

Definitions and messages travel through ordinary directed R2 messages. A receiver must complete R6 Model A reception before learning or interpreting them. Definition acquisition requires a matching abstraction of the receiver's own paid retained access. Merely receiving a definition does not install it. Private memory and composition addresses are not included in the transmitted semantic payload.

## Consequential meaning and repair

The main demonstration has **20 journal transactions**:

1. Alice retains an observation about her box and acquires a relation pattern.
2. Bob independently retains evidence about his tool.
3. Alice transmits the definition and a conditional explanation proposing inspection followed by transfer of Bob's tool.
4. Before acquisition, Bob records `repair` and has no actionable plan.
5. Bob checks the transmitted definition against his own retained structure and acquires a local lexical revision.
6. Reinterpreting the original message now produces an accepted plan. Bob actually inspects the tool and transfers it to Alice.

The original failed interpretation remains in the journal. The explanation is a supported conditional rationale for a proposed action; it is **not** a discovered causal law or an English-language explanation.

Tests also revise a one-relation meaning into a two-relation meaning. An unmatched receiver rejects the new definition without changing its old lexicon. After acquiring the matching structure, it can explicitly accept the replacement. Old calls retain their semantic fingerprints and cannot silently acquire a different meaning. Same-meaning revisions remain semantically compatible, while their local revision identities and provenance remain distinct.

Opaque label substitutions preserve behavior. Argument substitutions change behavior: a supported condition permits action, contradictory evidence refuses it, missing evidence yields `unknown`, and conflicting ownership claims yield `ambiguous`. Changed retained constituents yield `stale` until the participant explicitly revises and accesses them. None of these statuses grants action merely because a familiar phrase was received.

Requests and explanations both produce real receiver action plans when supported. Commitments instead create receiver expectations about the speaker. A speaker can enact its own commitment only after actual successful transmission and a separate paid check against its own retained evidence. Its linked physical actions must complete before its execution status becomes `fulfilled`. Failure remains `failed`; partial work remains pending.

**Receiver expectation is not private fulfillment knowledge.** Speaker completion is not automatically delivered to the receiver. This release does not implement acknowledgment negotiation, deadlines, sanctions or contracts. Those are not silently credited as R9 organization.

## Verification

**294/294 tests pass: all 258 unchanged inherited tests and 36 R8 tests, with no final failures, errors or skips.** A separate panel passes **32 request/explanation cases** across all 16 receiver types, using LSE as sender. This is not a 256-pair population evaluation.

| Gate | Evidence |
| --- | --- |
| L01 — acquired representation | Owned access, nested compositions, multi-relation abstraction, shared argument slots, private-source rejection and exact revisions. |
| L02 — exchange and repair | Ordinary channel delivery, required paid reception, failed acquisition, independent matching evidence, explicit replacement, historical meaning preservation and unavailable-channel control. |
| L03 — useful composition | Held-out object; alternate world context; new call/action combinations; label permutation; actual inspection and transfer; explicit physical charges. |
| L04 — commitments | Receiver expectations, unsent-commitment rejection, separate speaker intention, actual fulfillment and failed action. |
| L05 — interpretation controls | False, unknown, conflicting, stale and invalid conditions; foreign-context rejection; policy refusal; hidden-world-change control; independent bounded journal guard oracle. |
| L06 — continuation | Every demo prefix; partial semantic and physical work; independent energy/time limits; competing revisions; duplicate/changed commands; action tampering; rehashed semantic checkpoint tampering. |
| L07 — preservation/release | Inherited tests and references preserved, runnable demo, three hash seeds, exact checkpoint replay and fresh source extraction verification. |

The hidden-state control changes world ownership without updating the retained access. Interpretation stays the same; subsequent physical execution differs. This demonstrates that interpretation is not receiving a hidden ownership oracle. Correct interpretation of an inaccurate retained account can still lead to a failed action.

The independent guard oracle reconstructs the local lexicon and accessed facts from journal records for the bounded argument-control panel. It does not independently implement every R8 operation and is not presented as full semantic equivalence verification.

The first R8 unit run retained one test error: a malformed-message test selected the sender's receipt rather than Bob's delivered observation. The fixture was corrected to select the receiving observation by owner and message source. A later context-boundary test initially read the context from a job-result field that is unused by R3 context creation; it was corrected to use the committed context record and supply the explicit observation provenance required by R3 retention. Release review also added rejection of non-world-context access and a failed-commitment execution test. No inherited test was weakened. All construction logs are retained in the evidence archive.

## Costs and descriptive profile

Acquisition costs one unit plus pattern count plus selected retained content count. Production costs one plus call count, argument count and action count. Interpretation/intention costs one plus that speech-production extent plus retained content count. Each unit charges both energy and time. R2 transmission, R6 routed reception, R7 access and physical actions charge separately. Partial language jobs retain payment and their original proposed result; changed proposals fail rather than silently inheriting earlier payment.

The default inspection/transfer sequence costs three additional physical units after interpretation. Validation, immutable-record construction and index maintenance remain uncharged simulated overhead, as in the earlier stages. Runtime overhead still exists and is measured separately.

A descriptive profile holds one known one-call/one-action production constant, excludes one warm-up, and measures six cycles:

| Inactive ticks | Units per production | Median active time, ms | Checkpoint bytes | Save / replay, ms |
| --- | --- | --- | --- | --- |
| 0 | 5 | 0.163 | 98,625 | 4.2 / 12.0 |
| 2,000 | 5 | 0.228 | 1,609,403 | 82.7 / 284.5 |

These are development-run measurements on the recorded Linux/Python environment. Fresh-extraction evidence contains its own rerun. This small production-only profile does not measure sustained dialogue, growing lexicons or large compositions. **R10 efficiency acceptance remains open.** Checkpoint size and replay cost grow with history; retained messages, expectations, output indexes and action records can also grow.

## Scope, preservation and next step

The grammar supplies ownership predicates, conjunction, concrete argument substitution, ordered inspect/transfer actions and three speech modes. Acquisition learns patterns from retained structures; it does not invent arbitrary predicate or action classes. Names, composition assembly, dialogue goals and demonstration orchestration are supplied. There is no automatic conversation planner, autonomous naming, unrestricted natural language or proof of general compositional closure. The language operations use explicit semantic-work prices; Model A participates through inherited routed reception, not a new empirical model of language production.

All inherited runtime modules remain unchanged except codec registration and entry-point/version metadata. All inherited tests and the entire reference tree are unchanged. New records share the same journal. Earlier checkpoint loaders remain available; automatic live migration from R7 is not provided.

R9 should use the acquired meanings and executable plans as parts from which participants construct, evaluate and revise shared procedures. It must add genuine participant rule generation, agreement, recurring consequences, transmission/succession and dispute/dissolution evidence. The R8 expectation record alone does not satisfy that gate.

**Next: R9 — participant-generated organization. Then R10 — sustained evaluation and release. Two actionable milestones remain.** General recursive coherence, Shell emergence/clearance, the Id/Identity cycle and empirical calibration remain unestablished. The former 12A track stays separately paused at parent progress 4/14, with 11 former actionable steps and efficiency acceptance open.
