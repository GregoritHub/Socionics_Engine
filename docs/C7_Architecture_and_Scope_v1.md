# C7 release candidate: sustained execution and honest stopping

This candidate adds `hle_unified.population.Population` on top of the unchanged
C6 `SelectionEngine`. It schedules one independently owned demand per actor.
It chooses actors in deterministic round-robin order. It never supplies a
route, semantic result, borrowed skill, external truth, or new resources.

Each turn advances at most one selection, Shell admission, native movement,
or paid reading step by the declared work quantum. Actor locks remain native
locks. A participant's own actual material outcome may be delivered; processing
that delivery is a separately paid future turn. Other hidden world revisions
are not refreshed into participant memory.

Checkpoint schema `hle-c7-population-v2` contains the native C6 checkpoint,
requests, finite episode and work limits, fairness cursor, partial feedback,
counters, scoped repetition signatures, and a turn log. Restoration preserves
future command identities and paid progression. Earlier development-only v1
population snapshots remain raw evidence; they are not v2 restart files.

The default repetition limit is two equal qualifying retained results. Equality
uses actor, context, target, and complete proposition relation/object content.
It only considers successful private binding outputs, not public messages or
actual material events. Both outputs remain in history and both are charged.
`unchanged_retained_result` stops the current supplied demand. It does not prove
truth, general fixed-point closure, new capacity, or exhaustion of future
opportunities. A finite session owns its engine's `c7-turn` command namespace;
resume that session with `Population.restore`, not a second fresh scheduler.

The diagnostic fixture explicitly disables the repetition stop. Its 24 episodes
per actor expose the repeated model/interpretation behavior instead of hiding
it. Initial needs and opportunities are supplied. Replenishment, new goal
formation, autonomous public message delivery, and growing populations are not
implemented by this scheduler.

`population_audit` independently checks raw wallet charges, fairness, episode
counts, native result references, and repetition summaries. It does not import
Population, SelectionEngine, or the participant selector. It complements the
C1-C6 raw semantic, access, authority, material and Shell auditors.

## Release boundary

The 32 canonical route/polarity cells retain their C6 automatic witnesses. The
required second materially different applicable semantic setting for every cell
is still unestablished. Condition maintenance, numeric allocation, and bounded
procedure organization are not interchangeable meanings simply because they
share route endpoints. Renaming stock or changing caps does not close that gate.

This is a release candidate, not a full-Crux completion. No passing aggregate,
long run, or number of repeated outputs overrides an open per-cell requirement.
