# HLE new build Step R3 report

16 September 2026 · Rebuild release 0.3.0

**R3 is complete. Progress: 3/10 milestones; seven actionable milestones remain. Next: R4 — integrate Crux and Model A with memory and action.** The first integrated demonstrator remains R5. No milestone split was needed.

## What changed

The rebuild now has relational Fool's Memory operating on the same event journal, exact reference index and resource wallets as R2. Cues can share memories, and memories can share cues. Retrieval selects bindings by owner, cue, context and time scope, then optionally follows retained fragment links. Results identify matching propositions and preserve the visited path. No fixed three-vertex recall or card-based memory capacity is imposed.

The catalog preserves 130 distinct cards: 21 numbered Major Arcana, the unlocated Fool, 56 Minor cards and 52 Standard cards. Card identity, rank, nine-location fold and source layer labels remain distinct from associated content. Private contextual labels are independently addressable. The source's card arrangement is retained; the search algorithm, revision behavior and integer prices are declared implementation choices.

Direct cue recall works without an elected navigation policy. Configuring the experimental linked policy changes how far a participant follows stored relationships while leaving the memories and associations intact. This is a controlled navigation setting, not a learned or empirically calibrated psychological competence. The Id/Identity recurrence remains unelected.

Memory revisions and bindings name exact predecessor versions. A revised memory does not silently redirect an old cue or incoming link. Rebinding is an explicit paid operation. Concurrent stale updates fail after their funded processing and preserve the competing current version. An in-progress recall freezes its associations and navigation setting at the first funded step, so later edits cannot change the meaning of its retained work.

The observation-copy helper retains selected delivered content and its provenance. It treats message testimony as tentative; factual accuracy remains separate. Selective participant inputs expose only requested owned memory revisions and the participant's inbox suffix. Acknowledged inbox positions, cursor settings and incomplete recall jobs survive replay.

## Worked result

The 17-event example starts with Bob's original observation that Alice owns the box. Alice transfers it to Bob without informing him. Bob recalls the original memory, chooses an inspection, and receives the changed ownership through that permitted channel. He retains memory revision 2 and explicitly rebinds a cue. A linked scene then recalls the corrected ownership fragment, supporting a successful transfer back to Alice.

The earlier binding and an unrevised alternate cue still resolve memory revision 1. The example saves during partial linked recall and reproduces identical continuation after reload. Bob spends 25 energy and 25 time quanta across the memory work and world actions. These supplied policies demonstrate operational memory use; they do not establish autonomous learning, realized Crux processing or Shell clearance.

## Verification

**107/107 verification cases pass: 37 retained R1 checks, 30 retained R2 checks and 40 new R3 checks, with zero failures, errors or skips.** The first complete test run passed. Final verification runs against an extracted copy of the delivered source. The evidence archive retains the initial tested source, per-test results, final extracted-source results, commands and release hashes.

| Gate | Evidence |
| --- | --- |
| Context and cue reuse | One cue retrieves different memories in different contexts; several cues retrieve one revision without duplicate visits; 721 memories share one cue without a capacity rule. |
| Variable useful recall | Useful paths of 1, 2, 4 and 17 records; branched shared fragments visited once; explicit time, subject and relation filtering; visible visit-limit truncation. |
| Cursor independence | Changing configured navigation changes access without changing stored content, links or bindings. Direct recall remains available with no elected linked policy. |
| Historical fidelity | Old memory and binding versions remain exact; explicit rebinding updates only the active association; pending recall keeps its original bindings, cursor and fragment revisions. |
| Observation and privacy boundaries | Hidden ownership and evaluator activity leave recall and decisions unchanged before inspection. Foreign memory, link, binding and provenance access reject atomically. |
| Revision and action | Observation-driven revision preserves its source and predecessor; tentative testimony and unknown meanings remain distinct from factual truth; recalled correction changes a permitted action and consequence. |
| Resource work | All 16 energy/time pairs from 0–3; deferred and partial recall; unpublished partial writes; competing revisions; idempotent retries; sequential conservation across individual recall charges. |
| Replay and continuation | Every prefix of the 17-event example restores and continues identically. Rehashed binding, cursor and job tampering rejects. Three Python hash seeds produce the same checkpoint digest. |
| Independent comparisons | Complete offline recall agrees across varied graphs, cue orders, limits and rebinding. Independent world folding agrees after all 17 example prefixes. |
| Inactive work | Guarded recall and action cannot iterate the global journal, changed-event log, global record index or unrelated memory/binding heads. One hundred old binding revisions leave one active bucket entry. |
| Source preservation | All 26 inherited reference/core files remain byte-identical, including the nine supplied project sources. Existing R1/R2 tests are retained. New rules distinguish source arrangement from experimental operations. |

## Bounded cost result

Measured on Python 3.12.14, Linux x86-64, an AMD EPYC 9V74 host. Each condition used three repeats of 32 two-unit recalls with one matching binding and one visited record, followed by selective participant input. Initialization is excluded. Values are descriptive measurements, not timing acceptance thresholds or population-scaling guarantees.

| Inactive clock events | Unrelated memories | Recall plus selected input median | Checkpoint bytes | Save / replay median |
| --- | --- | --- | --- | --- |
| 0 | 0 | 278.3 µs | 312,476 | 20.2 / 40.9 ms |
| 0 | 800 | 282.7 µs | 12,163,554 | 1225.5 / 2709.2 ms |
| 2,000 | 0 | 280.4 µs | 1,824,303 | 126.2 / 378.1 ms |
| 2,000 | 800 | 274.0 µs | 13,676,444 | 1513.5 / 3362.8 ms |

Normal access avoids inactive-history traversal. The larger memory fixtures also retain their write/bind events, provenance and work. Typed checkpoints and full replay therefore grow substantially with history. Selected graph width, payload size and immutable frontier/visited bookkeeping still affect processing; large active searches have not received a sustained scaling evaluation. R10 efficiency acceptance remains open.

## What remains open

R3 completes the memory-level cue/retrieval gates. The full A01–A15 integrated panel remains R5. R4 must make Crux and Model A operations change actual content, actions and retained state, with visible type-dependent routing and costs. Shell generation, clearance, identity-return assessment, adaptive populations, recursive organization, richer language and institutions remain their assigned later milestones.

The card-to-Crux correspondence, Id/Identity relationship and recurrence, recursive coherence, sign-specific Shell detectors and biological cost calibration remain open. No universal drain for false belief or mandatory developmental ladder has been added.

The source package is self-contained and includes the preserved papers, runnable R3 code, tests, reproducible evidence commands and full updated roadmap. R2 checkpoints remain readable by the preserved R2 World interface; an automatic R2-to-R3 session migration is outside this release. Participant isolation remains an API boundary for cooperative code.

The former 12A track remains separately paused at parent progress 4/14, with 11 former actionable steps remaining and efficiency acceptance open. Those counts are not rebuild progress.
