# HLE Id/Identity recurrence — executed probe v1

17 September 2026 · Baseline: accepted R11 · Status: experiment complete; adoption criterion failed.

**The proposed recurrence executes correctly and can refresh changed memories. It does not yet justify becoming the engine's default recall policy.** It offered no new information on repeated cues in the static panel, missed the declared practical improvement threshold, and produced exactly the same results as an ordinary schedule performing the same revisits.

## What was tested

The Fool's Memory manual states that the Id cycle repeats three times over the Ego cycle, with Ego and Super-Ego in parallel. It also explicitly leaves both the traversal and the Id/Identity label relationship unspecified (extracted paragraphs P0107–P0117). The uploaded duplicate manual is byte-identical to the original used by R11.

This probe makes one provisional interpretation: the three Identity cards supply a three-phase Id clock. With zero-based outer position \(e\) and inner position \(i\), a completed frame advances

\[
(e,i)\mapsto(e+1\pmod 9,\ i+1\pmod 3).
\]

Each frame consults its three cues through separate, paid memory queries:

| Frame | Super-Ego card | Ego card | Identity card |
|---:|---:|---:|---|
| 1 | 1 | 10 | Sun 19 |
| 2 | 2 | 11 | Judgement 20 |
| 3 | 3 | 12 | World 21 |
| 4 | 4 | 13 | Sun 19 |
| 5 | 5 | 14 | Judgement 20 |
| 6 | 6 | 15 | World 21 |
| 7 | 7 | 16 | Sun 19 |
| 8 | 8 | 17 | Judgement 20 |
| 9 | 9 | 18 | World 21 |

The next frame returns to the initial phase. This is 27 cue consultations, covering 21 distinct cards. Each Identity card is consulted three times.

This clock is distinct from the spatial fold. Sun stays at folded position 1 even when consulted alongside outer position 4 or 7. All 130 existing cue descriptors remain unchanged. Three scheduling slots do not impose a three-vertex memory graph: a six-vertex linked recall was tested successfully.

The default direction and alignment are experimental choices. All six Identity permutations and all 27 outer/inner start pairs satisfy the same period condition. There are three distinct relative-phase orbits; closure does not select a unique one. The test therefore does not settle the manual's terminology or establish a uniquely correct traversal.

## Execution and controls

All retrieval used real R3 MemoryCommands inside R11 OrganizationWorld, charging one energy and one time unit for each paid recall step. R11's 42 Python runtime files are byte-identical to the accepted build. No engine file or original source document was changed.

The declared panel contained:

- **450 trajectories:** 198 static and 252 with an externally scheduled update.
- **22,050 target evaluations** at recall allowances of 8, 16, 32, 64, and 128 units.
- **4,410 actual physical actions** selected from completed recall results.
- **14 fidelity tests**, including 162 start/order combinations and continuation checks at every prefix of a 54-unit direct-memory traversal.
- **50 selected complete journals** replayed before and after physical actions; 25 selected recall bills independently checked against charged work records.

Static fixtures used six declared seeds, 21 equally weighted targets, and three histories: direct cue bindings; shared scenes with linked fragments; and previously revised ownership with older bindings still accessible. The six recurrence orders were compared with the same order without repeated cues, a flat unique traversal, a shuffled traversal with matching cue multiplicities, one batch query over all unique cues, and an unnamed copy of the recurrence schedule.

Dynamic fixtures changed each of the 21 cue-bound targets separately, after scheduling slot 18 or 36. A real transfer, observation, memory revision, and explicit rebind supplied the update. Every policy faced the same external update slots, including policies that had already finished. These are constructed refresh cases, not a calibrated model of when memories change.

The common decision adapter received only published recall hits and their exact owned memory revisions. It chose the latest available ownership proposition, treated absence/conflict as unknown, and transferred when the recalled owner was self; otherwise it inspected. Evaluation used the actual owner only after that decision. Incomplete recall work and current inbox observations could not supply an answer. The adapter is a supplied, uncharged rule shared by all policies; it is not a newly learned or Model A-routed decision process.

Recall allowances cap paid work. Separate tests exhausted energy and time independently and resumed unfinished work. Setup, update, and action costs were recorded separately from recall. Queries freeze their binding selection when first funded; a later revisit starts a fresh query. Phase advances only after all three queries in a frame complete.

## Static memory results

All policies recovered all 21 latest ownership claims at the 128-unit allowance. All **4,158 static physical actions** were appropriate and completed. Repeated consultations contributed **zero new proposition/version pairs** in these unchanged histories.

| Policy | Direct history: full recall units | Shared history | Revised history | Mean correct recall at 8/16/32/64 units |
|---|---:|---:|---:|---:|
| Canonical recurrence | 54 | 108 | 63 | 48.81% |
| Same order, repeated cues removed | 42 | 84 | 49 | 51.19% |
| Flat unique traversal | 42 | 84 | 49 | 49.60% |
| Shuffled traversal, matched repetitions | 54 | 108 | 63 | 51.85% |
| One batch query, all unique cues | 22 | 43 | 29 | 41.67% |

Percentages count a correct answer over all targets; unknown answers remain in the denominator. They are descriptive results for the declared synthetic panel, not human memory estimates.

The batch query is cheapest for complete retrieval, but it publishes nothing until the whole query completes. Separate queries can therefore provide useful partial answers earlier. This explains its lower average at the selected small allowances; there is no policy that wins every budget and layout.

The predeclared improvement criterion required at least a five-percentage-point gain over the strongest generic control overall, without a lower mean in any layout. The canonical recurrence was **3.04 percentage points below** the strongest generic control and failed this criterion. Its advantage was not rescued by phase closure.

## Changed-memory results

Correct final recall after the scheduled update, at the 128-slot horizon:

| Policy | Changed Super-Ego cue | Changed Ego cue | Changed Identity cue | Total |
|---|---:|---:|---:|---:|
| Canonical recurrence | 9/18 | 9/18 | 6/6 | 24/42 |
| Same order, repeated cues removed | 7/18 | 8/18 | 0/6 | 15/42 |
| Flat unique traversal | 0/18 | 9/18 | 6/6 | 15/42 |
| Shuffled traversal, matched repetitions | 9/18 | 10/18 | 5/6 | 24/42 |
| One batch query | 0/18 | 0/18 | 0/6 | 0/42 |
| Identical unnamed repeat schedule | 9/18 | 9/18 | 6/6 | 24/42 |

Revisiting Identity cues recovered all six scheduled changes there. The same-order unique control had already read those cues and missed the updates. The flat traversal also recovered all six because its first Identity reads occurred later, after the updates. Thus, later access as well as repetition can explain correction in this fixture.

The batch query's frozen early snapshot missed every later change; it was not given a second query. Adding an explicit refresh would be a different policy and was not inserted after observing the outcome.

The canonical recurrence still retained stale answers for **18 of 42** dynamic changes, all outside Identity. Those produced 10 failed transfers and eight completed inspections where transfer was appropriate. Completing the cycle therefore does not certify current knowledge or appropriate action.

Across **60 paired cases**, the canonical recurrence and the identical unnamed schedule had exactly equal engine-state hashes, budgeted answers, and action results. This is a causal boundary of the candidate: its effect is determined by what it rereads and when. No distinct Identity operation is implemented by changing the label. That finding does not disprove a richer Identity mechanism; this candidate supplies no semantic difference with which to test one.

## Acceptance and disposition

| Gate | Result | Evidence |
|---|---|---|
| S1 — 3:1 recurrence and joint closure | Pass | Every tested start/order has joint period 9; the one-lap dwell control fails the required ratio. |
| S2 — preserve cue map and memory structure | Pass | Unchanged catalog and folds; distinct co-folded cues; six-vertex walk succeeds. |
| F1 — paid, resumable, idempotent execution | Pass | No unpaid publication/phase advance; independent energy/time depletion and exact retry checks. |
| F2 — checkpoint fidelity | Pass | Every traversal prefix continues identically; invented rehashed cursor/phase is rejected; 50 full journals replay. |
| F3 — context, revisions, frozen queries | Pass | Context isolation, old binding identity, pending snapshot, and fresh re-read checks. |
| U1 — complete static recall and actions | Pass | All static cases correct at 128; 4,158 appropriate completed actions. |
| U2 — practical static improvement | **Fail** | −3.04 percentage points against the strongest generic control; required gain was +5. |
| U3 — distinguish repeat effects from Identity semantics | Checked; no distinct effect | All 60 matched unnamed schedules are exactly equal. |

**Disposition:** retain this as an experimental scheduling option. R11 remains the accepted engine. The test supports a mechanically valid 3:1 clock and useful refresh through later access. It does not support promoting this recurrence as a general memory improvement or calling the source's Id/Identity question resolved.

A subsequent integration decision would need a precise account of what an Identity phase does to interpretation, selection, or revision beyond scheduling another read. That behavior should have its own controls and be charged through the applicable processing routes. No new production milestone is declared complete here.

## Reproduction and provenance

Run `python3 -m unittest probe.test_recurrence -v`, `python3 -m probe.run`, and `python3 -m probe.audit` from the probe directory. The standard library is sufficient. The executable panel, all per-budget answers and actions, source copies, logs, exact checkpoints, and independent artifact audit are included in the accompanying archive.

The acceptance declaration was hashed before implementation/evaluation:
`b1158d6b9251a44045b2808b7679136e90bef193e5920c9403e7d10e169c045e`.

The final artifact audit identified an incomplete incremental ledger after the first run. The runner was changed to persist and verify one complete final ledger, then the unchanged experimental panel was rerun. Schedules, seeds, histories, budgets, scoring, and acceptance criteria were not adjusted. The final audit checks every planned case and aggregate, so the delivered ledger is the authoritative evidence.

The original Fool's Memory manual SHA-256 is
`8c4ce5231afe02027ca91ad0a507035d3529a441606fc06e9b7104cf28c4ab8f`.
The accepted R11 archive SHA-256 is
`54e832df695d4576441aebede8ddb5fbbf773c8b66401cc3ea9610a5494c7e36`.

Results apply to the declared finite synthetic ownership domain. This probe does not establish psychological validity, autonomous recurrent meaning, or recurrence integration into language and organizational decisions.
