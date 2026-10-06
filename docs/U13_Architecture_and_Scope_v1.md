# U13 architecture and scope

U13 changes physical representation and execution overhead. Its policies, operation grammar, Model A work prices, rights, histories and claimed psychological scope remain those of U12.

## Authority

Every new mechanism here is an engineering choice under the supplied U13 roadmap and the foundation's exact-reconstruction and cost-separation requirements. The theoretical papers supply no processor-performance target. `Efficiency_Acceptance_v1.json` retains its U1 numerical targets and failure rule without amendment. `U13_Protocol_v1.json` freezes the additional same-feature workloads before tuning.

## Physical changes

1. Compile each immutable record's existing type predicate once. Every construction still checks every field and invokes its existing local consistency checks. Strict bool/int distinctions remain mandatory.
2. Give the structural pool local integer addresses. A typed structural hash selects a bucket, then full typed equality verifies reuse. Collisions do not grant equivalence. The public wire table still uses the same deterministic insertion order; hash randomization cannot alter serialized history.
3. Keep the original version differences and add reconstruction anchors every 32 revisions. Anchors contain references to existing tokens and introduce no wire records. Normal historical lookup walks at most 32 rows. The original untrusted restore input is still replayed and checked.
4. Validate referenced identities against the pending batch and existing identity index, avoiding a copy of every inactive identity on each write.
5. Use exact typed index keys for participant particulars, avoiding serialization and hashing on every lookup. Participant snapshots, permitted content and invalidation remain unchanged.
6. Provide an explicit `install_legacy_optimizations()` adapter. It installs the same compiled type checks and shares equal immutable values after validated R21B restoration. A temporary per-restore table is released afterwards. Every field, referent, actor, revision, resource and ledger remains present. Mutable state is not pooled across worlds.
7. Cache actor-specific availability, current capacities and signatures only during one synchronous circuit command. A commit disables the cache across every publication layer; completion, nesting and exceptions clear it. Returned mutable mappings are fresh copies. No cached result survives into a later command or crosses actor ownership. Decisions and material actions still execute, with identical paid work.
8. Provide lossless chronological history segments. Each has an independent checksum and gzip member; the ordered manifest also binds the complete stream. Reading one transaction touches one segment. Full reconstruction validates the original transactions through their store contract. These archives are for offline audit and do not remove live work or become participant observations.

Importing the native `hle_unified` package installs the compiled shape validator for the shared Record base. Legacy-only applications opt into the legacy restore adapter explicitly. All 98 frozen legacy runtime modules remain unchanged on disk. No external dependency, database, pickle or executable deserializer is introduced.

## Preserved boundaries

The existing dependency cache, actor-local receipt requirement, paid acquisition and event-driven command dispatch continue to govern action. Cache invalidation is an internal effect. A hidden revision may rebuild a view but must not alter its bytes. No new scheduler drops queues or merges unfinished jobs. All costs in the benchmark's participant ledgers are simulated units; timings, Python allocations and archived bytes are machine measurements.

No lossy summary or bounded total-memory claim is made. Unique history still consumes storage. Existing raw and compressed checkpoint formats are retained exactly. Compression improvements are not the basis for the performance claim; the intended gains are active execution and retained allocation.

## Measurement domains

The common panel uses the original six 32-choice workloads and two v4 checkpoints. Separate native workers run the complete U12 engine with inactive objects whose structures are shared, unique, or linked to eight recent objects. They hold each paid active batch at eight reads while increasing inactive history from 100 to 1,000 to 10,000 records. A supplemental prospective protocol measures complete institutional negotiation episodes in the tool and pump contexts: public delays, disputes, independently corrected participants, rejected unilateral amendment, collective revision and real work. These episode timings include initialization and exclude offline audit and serialization. They supplement the primary participant-only timings. A complete U12 institutional witness separately checks succession, newcomer teaching and dissolution.

Native queues, actor views, wallets, transactions and canonical checkpoints must match the unchanged U12 reference. All reference and candidate performance workers are sequential and isolated; profiling and validation are separate. After the first candidate failed the common active-time target, the final panel reused that run's first completed reference sample set for the six unchanged common cases. Source, fixtures, worker, contracts, Python and platform were verified; no reference samples were chosen by timing. Every candidate and all other reference cases were measured afresh. The default reproduction command measures both sides afresh. Memory tracing excludes checkpoint text and follows equal warm imports. All samples and unsuccessful development runs are retained.

A segmented archive is a historical store projection, not an entire live engine checkpoint. Its byte count is reported against the same canonical transaction history; full-engine checkpoint bytes are reported separately. Selective archival inspection and full reconstruction have separate timings.

## Limits

These measurements concern the declared Python workshop and inherited circuit workloads on the recorded machine. They establish no general latency guarantee, unlimited community size, natural-language fluency, unbounded developmental complexity, or human psychological validity. U14 held-out combinations and sustained release acceptance remain open. The older R21C release contract is separate.
