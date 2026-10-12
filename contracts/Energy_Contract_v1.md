# Energy Contract v1 — prospective opt-in Phase 7

[source_defined] Authority: Final Build Plan v1.0 §10, Companion Theory §8, and docs/FB7_R5_Authorization.md. This additive experiment does not amend legacy-r4 or any inherited contract. Entry source: 6960145517974f6c69b8ae66b5b56de2c35cbbe1.

## World identity

[source_defined] The default is legacy-r4. Explicit grade-v1 selection occurs only at creation, before any paid command. It is immutable throughout the world. Legacy creation, records, checkpoints and audit output remain byte-compatible, without injecting new legacy metadata. Experimental identity must be committed in initial world evidence and survive every engine/population checkpoint. Unsupported model names and changing or adding the model after initial creation are rejected. Creation may use an additive factory API inherited by engine classes; constructors without an explicit experimental selection remain legacy.

## Prices and work order

[source_defined] A1–A8 time unit prices are [1,2,3,4,4,3,2,1]. Energy unit prices are [1,1,3,3,2,4,4,2], equal to 4 minus the grade supplied by model_g.py. Path choice, support selection and all time calculations stay unchanged. The auditor independently reconstructs prices from type positions without importing the executor or its pricing routine.

[derived] Current jobs execute preparation (`recall_units`), ordered route hops, route seat-content work, and any final material work. Each entered hop is one step. Each route seat-content block is one step with its declared content-size multiplier. A path's starting element is not an entry. The two occurrences of a support/target caused by an actual return path are two entries. Completion is a paid boundary, not an action proposal or a type label.

[probe] At the entry source every route's `content_units` is one dimensionality-priced unit, so its seat content size is 1. Larger content, syntax, recall and traversal workloads are already represented in preparation units. Reclassifying those as seat processing would change the inherited time/work semantics and is not authorized. An explicit integer size at a seat, if present in a future compatible record, must multiply both that seat's time and energy unit price; it must not be inferred from unrelated preparation fields.

[source_defined] All non-Model-A work keeps equal energy/time charging: preparation/recall/syntax traversal, selection comparison and admission work, delivery/reading, and physical execution. `required`, `completed`, `spent`, receipt extents and child-work summaries retain their existing meaning as time/work units; actual energy is reconstructed separately from wallet revisions.

## Exact interrupted payment

[derived] Let each step occupy half-open cumulative-time interval [start,end). For a Model A step, charge all of its integer energy when paid completion moves from start to any value greater than start. Subsequent time units within that same interval cost zero additional energy. Each non-Model-A time unit costs one energy.

[derived] An advance pays the largest sequential prefix within its work limit and available time that can afford each next step admission. It never skips a step. At an unstarted step, sufficient whole-step energy and at least one time unit are mandatory. Once admitted, zero remaining energy does not prevent paying the rest of that already-paid step, provided time remains. No time available means no progress. A positive energy remainder smaller than the next admission price also means no progress. Reservations and all existing ready/commit/cancel rules remain in force.

[derived] Cumulative completed time determines whether each step has already been charged, so no hidden floating debt, new refund or second debit is needed on restore. Zero-progress advances have no wallet revision. Every positive time advance has exactly one wallet revision, which may have zero energy delta within a prepaid step. Cancellation and failed/stale commitment retain all spending and completed intermediates. Fully paid work can commit even when the wallet is empty; commitment itself must not invent an extra price.

## Auditing, scarcity and observations

[source_defined] Legacy raw audits retain their prior checks. Experimental raw audits validate immutable model identity, type-frame prices, whole-step admission, once-only energy, unchanged time, exact wallet deltas, cumulative work and existing semantic/physical evidence. Corrupted charges, types, model identity, completion, refunds and erased wallet revisions must fail ordinary auditing.

[derived] Experimental schedulers may recognize inability to pay the next unit rather than only a zero wallet. This is a resource-stop correction, not an energy-optimized route or selection policy. Existing candidate ordering and affordability comparisons remain as authored; report their effects under scarcity. Ample-resource pairs must remain semantically identical. No replenishment or goal changes.

[source_defined] Conditioning is a derived audit-only view: completed paid hops and completed seat-content blocks count once each by element, never by energy or time quantum. Preparation, material work, unpaid and unfinished blocks do not count. A completed block in a later-cancelled job remains completed use. Counts are reconstructed from raw historical job revisions and never stored in the world or read by execution. Axis load winners, ties, tilts and three-element DCNH formula sums are distinct observations, not subtype assignments.

[open] No psychological calibration, source-register closure, new Model G dynamics, reserve regeneration, optimization gain, or promotion of grade-v1 is claimed.
