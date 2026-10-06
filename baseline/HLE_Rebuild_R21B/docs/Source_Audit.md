# R1 source and dependency decisions

The supplied 5.2.1 archive contains 188 files, including 83 Python modules and 30 Erlang modules. `tools/audit_sources.py` inventories and hashes every file, parses every Python module, records local import edges including implicit package initializers, and lists lexical Erlang remote-module calls. Four dynamic import sites are recorded separately. The audit is static; it does not claim to resolve arbitrary dynamic imports or execute the Erlang implementation.

The runtime is a new Python standard-library package. No legacy module is imported or copied wholesale. The original archive remains unchanged under `reference/originals`.

## Selected mathematical operations

| Old location | R1 decision | Governing evidence |
| --- | --- | --- |
| `pyref/core.py`, GF(2) helpers | Rewrite exact operations with strict shape/bit checks and immutable affine values. | UMA Parts I–III; ordinary finite algebra. |
| `pyref/core.py`, Model A/IE data and frames | Preserve the 16 named ego pairs; generate complete stacks from the source frame equation. Keep the original full stack table as a verification fixture. | UMA §§2–6; old table is an explicit input; UMA §18 also supplies IEE's full stack. |
| `pyref/core.py`, routing | Rewrite transported cube adjacency, distances and all shortest paths. | UMA §18 and corrected §24 return example. |
| `pyref/core.py`, relation and estafette operations | Rewrite structural action and static finite group. | UMA §§9–10. No clock policy follows from the static permutation. |
| `metabolism/exchange.py`, landing calculation | Rewrite only the element-preserving seat transfer through the inverse frame relation. | Frame definition, exact comparison on all 2,048 source-seat-receiver cases. |
| `crux/perspectives.py` | Rewrite the pair groupoid, displacement, formal movement and conventional route table. | Unified Shell Geometry §§2–3 and Crux v6 §§3–9. |

No conventional names are assigned to the full relation group in R1. The structural transformation and direction are explicit; source-silent relation-name elections from the old runtime are deferred. Model G reindexing, directed chords, DCNH dynamics and OIG machinery are not needed for this milestone and are not automatically activated.

## Imports that would have brought unwanted rules back

| Requested old module | Python modules in conservative import closure | Consequence |
| --- | ---: | --- |
| `pyref.core` | 2 | The mathematical monolith also contains extra tables; extraction still needs function-level selection. |
| `crux.perspectives` | 10 | Importing the route module executes `crux/__init__.py`, pulling in typemap and algebra packages. |
| `metabolism.exchange` | 21 | Package initialization pulls in clock, energy, handler, tick and old holon machinery. |
| `fools_memory.schema` | 5 | Initializer also exposes encoding, retrieval and store rules. |
| `holon_tower.altitude` | 22 | Developmental selection brings demand, detector and shell dependencies. |

The evidence includes the full closure lists and a disposition for every Python module. R1 runtime imports are restricted to explicit new modules and the Python standard library, and a fresh interpreter test loads only a copied runtime directory with no legacy or reference tree.

## Rejected or deferred assumptions

| Old implementation | Evidence of the issue | R1 handling |
| --- | --- | --- |
| Exactly three memory vertices | `fools_memory/schema.py` requires keys A, B, C and three distinct values. | No vertex-count restriction. The boundary accepts content and links of variable lengths. |
| Universal replay | `fools_memory/retrieve.py` fixes A → apex → B → C → A. | No replay order is implemented. Retrieval policy belongs to R3. |
| Rank from edge count | `fools_memory/encode.py` assigns `rank = edge_count`. | Rank is cue metadata, independent of relational content. |
| Super-Ego-only storage | `fools_memory/schema.py` rejects other storage phases. | Memory identity is separate from card/layer metadata. No storage phase is mandated. |
| Undifferentiated courts | Old `COURTS` maps Queen to 13 and King to 14 for all suits. The revised manual distinguishes Minor and Standard decks. | Cue descriptors retain deck, suit, rank and fold separately; the full card catalog is R3. |
| Club mapping claimed as derived | `algebra/perspective.py` calls its IE-bit map derived; Crux v6 §8.2 explicitly says the club/perspective correspondence is a postulate. | Preserve the postulate's grade; do not elect the mapping in the core. |
| Typemap dwelling scores treated as cost | `crux/typemap.py` sums dimensionalities to 7/6/4/3. | No numeric runtime cost follows from these sums. Cost policies remain R4 work. |
| Generated development inferred from existing tower rules | `holon_tower/altitude.py` defines organization extension and sealing rules. | Leave composition and selection to an explicit R7 hypothesis. |
| Eight-element aspect sets used as complete content | `algebra/content.py` represents aspects plus opaque foreign keys. | Use reference-bearing propositions, context and provenance at the boundary. Semantic content processing remains later work. |

The audited archive does **not** establish that it enforces a literal 720-record cap, nor is its generated-altitude module simply a fixed color ladder. R1 does not make those claims. It excludes both an inferred capacity restriction and any automatic adoption of the existing developmental law. The 721-binding fixture checks the new boundary's compatibility; it is not an unlimited-memory performance claim.

## Source grades and missing handoff material

The foundation refers to `Source_Decisions.md`, `Source_Manifest.json` and older baseline logs that were not included in this turn's supplied files. This release creates fresh manifests and decisions from the bytes actually available. It does not treat the quoted old 80/80, 106/106 or 116/117 results as new verification and does not report them as rerun.

The full Crux route-name table was absent from the attached papers. The earlier `The_Crux_v6_Readable_Examined_Edition (1)(1).docx` was recovered as an additional governing reference and preserved unchanged, with its hash in the manifest. It confirms every route name and clarifies the original claim grades. Its presence does not activate all other Crux hypotheses.

The disorder, archetypal-shadow and dense-consciousness papers are retained and indexed. Their psychological or clinical interpretations are not executable R1 rules. This milestone does not validate those interpretations.

## Review finding retained in evidence

The first 37-case run passed. A subsequent review added the case where all declared work is performed but the operation fails at the end. The first contract rejected that record because it conflated full work extent with a completed outcome. The counterexample failed, was preserved, and was repaired: `FAILED` now allows any actual performed extent, including the full extent; `PARTIAL` requires started but unfinished work. Resource conservation and actual charges remain required. The full 37-case suite passed after the repair.
