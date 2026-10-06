# HLE new build Step R2 report

16 September 2026 · Rebuild release 0.2.0

**R2 is complete. Progress: 2/10 milestones; eight actionable milestones remain. Next: R3 — relational Fool’s Memory.** The first integrated demonstrator remains R5. No milestone split was needed.

## What changed

The rebuild now runs a deterministic ownership-transfer world with two actors and two objects. Every accepted command produces an ordered event with exact changes, actual resource work, explicit provenance and permitted observations. Current facts, historical fact timelines, wallets, task progress and record resolution use maintained indexes.

Participants receive their own immutable observations, retained belief records and resources. They cannot obtain Truth or evaluator conclusions through the participant interface. Hidden ownership changes leave matched participant inputs and actions unchanged until a permitted inspection, witness projection or message conveys information. Initial ownership and the logical clock are public in this fixture.

Messages retain their sender, recipient and unverified content. A retained belief has a separate existence record and factual-content check: the demonstration establishes that Bob holds an endorsed account while finding that its ownership claim is false. Unknown meanings, context, identity revisions and future facts remain unassessed. These are pointwise factual checks, not IDEA return or Shell assessments.

Resource transactions preserve full-cost failure, partial work and deferral. Interrupted work resumes from retained progress and charges only the remainder, with preconditions checked again at completion. Command IDs prevent duplicate execution; conflicting retries reject. Prices are explicit experimental integer costs, with no automatic recharge or universal false-belief drain.

A record correction appends a new event linked to the current ownership assertion. It invalidates affected factual checks while retaining prior events, observations and all charges. This is a prospective repair. Arbitrary retroactive rewriting and implicit participant correction are outside this release.

Checkpoints contain typed, versioned JSON. Reload reconstructs the world by executing its commands and comparing every generated transaction against the record. Corrupt, duplicate or semantically inconsistent histories reject.

## Verification

**67/67 verification cases pass: 37 retained R1 cases and 30 new R2 cases, with zero failures, errors or skips.** The first integrated run passed. Final extracted-source results and release hashes are recorded in the evidence package’s `release_acceptance.json` and `verification/packaged_source/`. All verification attempts are retained; no failed test outcome was removed.

| Control | Evidence |
| --- | --- |
| Events and world state agree | Independent state/resource fold and separate ownership oracle across all 216 three-action sequences; each prefix checked. |
| Hidden information stays hidden | Equal participant input under different hidden owners; inspection then conveys the difference through an explicit channel. Own-memory isolation, private-citation rejection and witness projections also pass. |
| Belief existence differs from accuracy | Endorsed ownership account is recorded as held while its content fails factual agreement; historical revisions remain resolvable. |
| Failures and unfinished work remain visible | All 16 energy/time budget pairs from 0–3; paid failure, partial continuation, deferred work, changed preconditions and duplicate requests. |
| Explicit correction | Original event/observations/costs survive; affected check becomes stale; unrelated cached check stays valid; unsupported older-history repair rejects. |
| Replay and continuation | Every prefix of the worked demonstration reloads and continues identically; partial-task reload passes; three Python hash seeds produce the same checkpoint digest. |
| Affected work | Indexed factual checks agree with complete historical comparisons. Guarded runtime execution cannot traverse the global log with 0 or 2,000 inactive events. |
| Source fidelity | All 26 inherited reference/core files checked against R1 remain byte-identical. R2’s 10 operational rules retain implementation-choice status. |

## Bounded cost result

Measured on Python 3.12.14, Linux x86-64, an AMD EPYC 9V74 host. Each condition used five repeats of 64 active inspections, consuming inbox cursors. Values are descriptive measurements on this run, not acceptance thresholds or population-scaling guarantees.

| Inactive events | Action + inbox median | Factual check median | Checkpoint bytes | Save / replay |
| --- | --- | --- | --- | --- |
| 0 | 144.0 µs | 15.9 µs | 372,515 | 15.8 / 43.4 ms |
| 2,000 | 144.1 µs | 16.0 µs | 1,884,561 | 96.2 / 300.7 ms |

No inactive-history traversal occurs in the checked action path. Retained event storage and complete replay still grow with history. Typed JSON favors inspectability over compactness; this does not close sustained efficiency acceptance.

## What remains open

R2 belief records and policies are supplied controls. Relational Fool’s Memory, cue binding/retrieval and navigation competence start at R3. Realized Crux and Model A operations start at R4. The integrated A01–A15 panel, learned correction, IDEA assessment, Shell candidates and clearance remain assigned to R5 and later evaluation.

R2 supplies runtime groundwork for the observation, referent, resource, belief, continuation and incremental checks without counting their future integrated versions as passed. Participant isolation is an API boundary for cooperative policies, not a sandbox for hostile Python code. The caller retains its own inbox cursor; autonomous controller state is not yet implemented.

The source package includes the preserved papers and mathematical core, runnable world, all tests, operational documentation and updated step list. The evidence package includes configurations, full trace/checkpoint, controls, profiles, verification logs, source identification and release integrity checks.

The former 12A track remains separately paused at parent progress 4/14, with 11 former actionable steps remaining and efficiency acceptance open. Those counts are not rebuild progress.
