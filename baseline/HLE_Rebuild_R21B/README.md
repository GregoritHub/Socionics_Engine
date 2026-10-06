# HLE R21B — feasible integrated policy

R21B adds paid reuse of exact owned option predicates and explicit per-operation
work extents. The frozen v4 whole-episode allocations are 200,000 adequate,
150,000 constrained and zero inadequate, per actor and per energy/time unit.
Historical budgets and failures remain available under their original versions.

**Parent progress is 9/10. Next: R21C — full release rerun.** Development
feasibility is established in the declared panel; held-out release acceptance,
shared/population release and performance remain open.

Read `docs/r21b/Step_R21B_Report.md`, `Progress_After_R21B.md`,
`Implementation_and_Validation_Notes.md` and the frozen `Protocol_R21_v4.json`.
The report distinguishes the original failed budgets, the v3 development failure,
and the current v4 operational envelope. No stage resets or credits are allowed.

Python 3.12 or later, standard library only. For one full development episode:

```bash
python -c "import sys; sys.path.insert(0, 'tools'); from r21b_policy import run_candidate; from r21b_audit import audit_episode; w,m=run_candidate('sli',11,'constrained_feasible'); a=audit_episode(w,m); print(a['successful_full_horizon'], a['sustained']['eligible'])"
```

For tests and full development reproduction (use a fresh evidence directory):

```bash
python -m unittest discover -s tests_r21b -t . -v
python tools/r21a_validate.py --out evidence/r21b/reproduction_inherited
python tools/r21b_evidence.py --out evidence/r21b/reproduction --workers 2
```

The 60-case development command runs both a candidate and a separately
constructed witness for each case. Success includes honest deferral in the
zero-budget cases. It never uses release seeds 2001–2010; those remain reserved
for R21C. Diagnostic `.no_reuse` and `.legacy_cost` contracts cannot count as
release witnesses. Restoring a checkpoint preserves its exact contract version.

The engine archive includes all inherited files, current code, reports, summaries
and continuing checkpoints. New raw transaction streams are in the two R21B
evidence parts; their paths and hashes appear in `release_manifest.json`.
Extract both evidence parts into the same location. Their file tree can be
copied over the engine root for raw-trace audit scripts. The older R21 raw
population archives remain identified in the inherited archive manifest.

Historical handoffs follow.

---

# HLE R21A — resource and comparison contract

R21A adds an explicit, journaled v2 contract for new episodes. One genesis
allocation covers each actor's complete history, learning, clearance and later
horizon. Requirement ordering is separate from the actual declining wallet;
actual balances and all paid work remain visible. Existing v1 checkpoints,
comparison behavior and failed R21 evidence retain their original meaning.

**Parent progress remains 9/10. R21B and R21C remain.** This build establishes
the contract, not a successful full-budget release policy. The development
panel's independently executed policies still exhaust their budgets.

Read `docs/r21a/Step_R21A_Report.md`, `Progress_After_R21A.md`,
`Resource_and_Comparison_Contract_v2.md` and the frozen `Protocol_R21_v2.json`.
Reproduce with standard Python 3.12 or later:

```bash
python tools/r21a_validate.py
python tools/r21a_evidence.py --out evidence/r21a/reproduction
python -m unittest discover -s tests_r21a -t . -v
```

The evidence command returns success for correct contract behavior even when
the separately reported full-horizon feasibility gate fails. It preserves all
unfinished work and resource stops. Use a fresh output directory for reruns.
Fresh release seeds 2001–2010 are reserved for R21C; R21A uses development
seeds only. The source is runnable without the historical R21 population raw
traces; those remain in the two unchanged R21 evidence archives identified in
`docs/r21a/Inherited_Archive_Identity.json`.

Historical handoffs follow.

---

# HLE R21 — sustained release evaluation (acceptance open)

R21 now includes the frozen 480-episode evaluator, strict budget enforcement,
independent raw-journal accounting, exact replay, long continuation, and active /
inactive-history benchmarks. **This is an evaluated candidate, not an accepted
R21 release.** Read `docs/r21/Step_R21_Report.md` and
`docs/r21/Progress_After_R21.md` for measured results and remaining work.

Run with Python 3.12 and the standard library:

```bash
python tools/r21_evidence.py --workers 4
python tools/r21_continuation.py
python tools/r21_performance.py
python tools/r20_validate.py --out evidence/r21/validation/inherited
python -m unittest discover -s tests_r21 -t . -v
```

A failed behavioral gate makes the panel command exit with status 1. Its rows,
raw transactions, unfinished jobs and denominator remain in `evidence/r21`.
Use a fresh `--out` directory to rerun the panel instead of reusing completed
case files. The original R20 checkpoint remains at
`evidence/r20/panel/continued_r19.checkpoint.json.gz` and loads through
`hle.closure.ClosureWorld.restore`. R21 retains that wire format.

The supplemental continuation has an explicitly logged additional allocation;
it is diagnostic evidence and does not pass the frozen resource regimes.

The R20 package documentation follows as the historical handoff.

---

# Holonic Living Engine — R20

R20 establishes two successive recursive/shared closures within a declared finite consent-and-obligation grammar. R12–R21 progress is **9/10**. One parent milestone remains: **R21 — sustained release evaluation**.

Run a complete small demonstration with standard Python:

```bash
python -m hle.closure_demo
```

Reproduce validation and evidence:

```bash
python tools/r20_validate.py
python tools/r20_evidence.py
```

No network or third-party Python dependency is required. Full validation/evidence takes several minutes.

**859 distinct tests pass: 825 inherited and 34 R20.** All sixteen R20 type cases and the original cleared R19 checkpoint continuation pass. The independent raw-journal audit agrees. See `evidence/r20/validation/summary.json` for the full run and the six focused repeated checks after final refinements; repeats are not added to the count.

- `docs/r20/Step_R20_Report.md`: results, controls and scope.
- `docs/r20/Progress_After_R20.md`: R21 handoff and remaining release gates.
- `docs/r20/Integration_R20.md`: source decisions, finite search, shared authority and observer separation.
- `docs/r20/Protocol_R20_v1.json` and `Operational_Details_R20_v1.json`: acceptance interpretation.
- `hle/closure.py`: continuing runtime, shared obligations, exact checkpoint and indexed invalidation.
- `hle/closure_policy.py`: finite protocol search with explicit effects and minimal extension selection.
- `hle/closure_reference.py`: independent reconstruction from raw transactions.
- `evidence/r20/panel/continued_r19.checkpoint.json.gz`: final checkpoint; restore with `ClosureWorld.restore`.

The continuing actor preserves its original material and all nine native capacities. Its shared routine survives founder departure through new consent, reduced unnecessary checking and actual successor performance. Shared competence is distinct from each member’s individual competence. Current invalidation never erases historical evidence.

The complete prior source documents, reports and evidence remain included. The seven-program search and finite constructor grammar do not establish unrestricted development. R21’s 480-case panel, sustained horizons and efficiency gates remain open.
