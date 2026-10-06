# R4 realized Crux processing and Model A

Version 1 · 16 September 2026 · Rules P01–P09

`MetabolicWorld` extends `RelationalWorld`. World actions, relational memory and processing share one transaction journal, record index and pair of energy/time wallets. R1 mathematical modules and all R1–R3 tests remain unchanged. The runtime has no external dependencies.

## Source boundaries

Crux v6 §5 supplies the ordered-pair routes, §9 requires polarity, and §10 supplies accumulation support seats 5/7 and expenditure seats 6/8. These grades remain conditional conventions/imports/derived structural results, as recorded in `rules.json`. The separately preserved Archetypal Shadow paper is not substituted for Crux v6.

The Unified Mathematical Architecture §§2 and 18 supplies position fields and transported cube adjacency; §17 separates fixed TIM from current active IE. Sections 20–21 explicitly leave numerical dynamics proposed. R4 elects a deterministic experimental policy using that structure. Its prices, operator targets, compulsory support visit and tie-breaking are implementation choices. The source does not derive these dynamics, and these checks do not calibrate human information metabolism.

Card coordinates remain separate from Crux endpoints and Model A positions. No club-to-perspective origin restriction is imposed. The source club mapping remains a postulate; all actors initially start at the explicit perspective in their profile. No Id/Identity recurrence, color ladder, Model G chord, automatic reserve replenishment or false-belief drain is added.

## Realized operators

Only the following four movement/face pairs have executable content semantics. The structural core still represents all 32 formal movements; a formal route alone cannot execute an unsupported operation.

| Operator | Route and face | Permitted input | Checkable result |
| --- | --- | --- | --- |
| Theorize | I → ITS, accumulation | Exact completed R3 recall; item and intended recipient | Account identifying a selected ownership proposition, exact evidence, uncertainty and any recalled checking capability. |
| Apply | ITS → IT, expenditure | Exact owned account | Paid inspection and/or transfer, actual receipts and consequences, referenced application record. |
| Embody | IT → I, accumulation | Exact finished application; named memory and expected predecessor | Memory revision containing observed consequences and, when triggered, a reusable checking capability. |
| Understand | ITS → I, accumulation | Exact owned account; named memory and expected predecessor | Tentative personal memory of the account, preserving evidence and any existing capability. |

Theorize uses only proposition indexes selected by recall. It aligns subject, relation and context and selects the latest declared scope start. Contradictory latest-time values yield uncertainty, irrespective of cue order. Truncated recall cannot justify a definite account. Retracted/disputed memories are excluded. Endorsed memories still carry no evaluator truth verdict. The chosen account can be wrong.

The initial supplied action grammar attempts a transfer when the recalled account says the actor owns the object. Otherwise it inspects. An acquired `inspect_before_transfer` capability requires inspection first. After inspection, only an observed self-ownership result permits a transfer. A goal supplies the recipient, never the correct owner or outcome.

Apply preserves R2 world semantics: inspection costs one unit; transfer costs two; each unit debits one energy and one time quantum. A failed transfer reveals failure but does not disclose the hidden owner. Declared witnesses receive the same full or occurrence-only projection as in R2. Inspection and its conditional transfer use distinct transactions, so the transfer cites a previously committed observation. Intervening changes can still cause a paid failure; inspection is not an atomic ownership lock.

Embody copies the latest delivered ownership consequence. If no ownership fact was delivered, the old account remains tentative rather than inventing an unseen correction. A disagreement between prediction and inspection, or a failed transfer, instantiates the supplied generic inspection procedure. Successful intended transfers do not count their intended ownership change as a prediction error. The procedure is independent of the particular object, but has to be present in a recalled memory to affect later action. This is experience-conditioned acquisition within a fixed grammar, not general procedure invention or proof of causality from one example.

Understand supplies an alternate valid movement. It does not acquire new checking procedures, execute physical actions, or turn a tentative interpretation into factual certainty. No global controller forces every demand to take the three-movement circuit.

## Routing and prices

The declared targets are Ti for Theorize, Te for Apply, Si for Embody and Fi for Understand. This assignment is an operational hypothesis, not a source-derived identification of each IE with an algorithm.

For each operation, enumerate the shortest transported-cube paths from the current IE to each eligible support seat, and from that support IE to the target. Among these two-leg candidates choose minimum total hop price, then minimum number of nodes, then lexical IE path, support seat and support offset. A support detour may revisit an IE; that repetition remains in the path and is charged. This is a bounded selector, not a claim of globally optimal cognition.

Entering a node costs `5 - dimensionality(position)` work units: prices 1–4. The starting node is not charged as a hop. Content work costs the target's price multiplied by:

- Theorize: one plus the number of recalled proposition indexes.
- Apply or Understand: one plus the number of cited memories.
- Embody: one plus delivered observation count, cited memory count and a discrepancy indicator.

Each work unit consumes one energy and one time quantum. These are abstract experimental quanta, not measured CPU instructions or biological energy. A deferred call still incurs interpreter overhead despite zero modeled paid progress.

`ProcessingPolicy` provides independent routing and price controls. Disabling typed routing uses the ILE reference frame for every actor while preserving the declared TIM. Disabling positional prices makes every node price one. The fully neutral control removes type effects under otherwise matched inputs. These are harness settings fixed for a session, not participant-selected ways to evade costs.

The invariant path geometry uses a bounded 2,048-entry derived cache keyed only by routing type, starting IE, target, polarity and price mode. It caches no actor identity, memory, conclusion or paid-work state. Cache warmth changes interpreter time, not modeled prices or checkpoint meaning.

The active IE advances only when its hop has been fully funded. Content outputs appear only after all required processing is funded. Sufficiently funded types derive the same account from the same evidence; differences arise in paths, charges, latency and what can finish under a fixed budget. R4 does not insert type-specific answers or change memory content to create apparent differentiation.

## Partial work, retention and history

Every command has a retry ID, persistent task ID and positive work limit. One unfinished movement per actor locks that actor's processing sequence. R2 actions and R3 memory operations may still occur, and other actors remain independent. A resumed movement must preserve its payload. Repeating an identical command returns its existing event without charging twice. A new command against a terminal task rejects. There is no cancellation operator in R4; an unfinished movement resumes when resources and scheduling permit.

Jobs retain their exact route, paid progress, action program counter, partial action payment, observations, discrepancy and processing history. Budget-limited operations publish no speculative account, capability or memory. Completed inspections are real delivered observations even while the following transfer remains unfinished.

A paid failed physical attempt enters IT with its failure available to Embody. A failed stale memory write stays at its previous perspective; it may be retried as a new task naming the actual expected predecessor. Existing historical memories and cue associations do not silently redirect. A profile does not acquire a higher structural dimensionality when it learns a checking procedure.

Every transaction retains a `MovementRecord` with chronological work references for the task, its formal route and face, input addresses, outputs, outcome and retained references. The account/application/capability chain preserves the actual discrepancy even when the final owner returns to the originally predicted owner. Endpoint equality cannot erase the recorded path; IDEA path assessment itself remains R5.

## Isolation, indexes and replay

Pure functions in `processing.py` receive detached owned records. They accept no world or evaluator interface. `_inputs` resolves only selected recalls, memories, accounts, applications and observations. `_enact` is the ownership-world execution boundary; only its permitted result becomes participant evidence. Evaluator checks have no input channel into decisions. Python participant isolation remains an API boundary for cooperative code.

The inherited journal now also contains `MetabolicTransaction`. Extra immutable records have exact revision addresses; latest state/job dictionaries are derived indexes. `processing_changed_since` exposes a suffix identifying changed actors, separate from ownership/held-memory fact changes. Ordinary work does not iterate global history, records, changed-event logs or unrelated memory heads. Retained input size and repeated continuation validation still affect work.

R4 checkpoints persist configuration, explicit profiles, policy and journal. The allowlisted codec also encodes the pre-existing formal movement values. Restore reexecutes commands and compares every transaction, reconstructing inboxes, memories, bindings, pending work, current IE, perspective and affected-state indexes. Rehashing tampered derived data does not make it pass replay. Checksums detect corruption; they are not authentication.

R2 and R3 loaders remain available for their respective schemas. No automatic cross-version session migration is included. R4 checkpoints cannot be opened with the older release's codec. Checkpoint bytes and full replay grow with retained history; R10 sustained efficiency acceptance remains open.

## Reproduce

From the extracted package root, with Python 3.12 or later:

```bash
python -m hle
python -I tools/verify.py --output /tmp/hle-r4-tests
python -I tools/r4_evidence.py --output /tmp/hle-r4-controls
python -I tools/validate_release.py
```

The fixture harness supplies goals, cue selections, interventions and demand order. It does not supply inferred owners, successful outcomes or capability objects. R6 remains responsible for exchanges among independently adapting participants. R5 remains responsible for the full A01–A15 IDEA/error/Shell panel. R4 completion is not a conductivity, identity-return or Shell-clearance verdict.
