# HLE progress after R21B

**R21B is complete. The R12–R21 extension remains 9/10 parent milestones
complete. One parent milestone remains: R21. One follow-up step remains.**

| Step | Result | Status |
| --- | --- | --- |
| R21A — resource and comparison contract | Historical v2 contract and failures preserved | Complete |
| R21B — feasible integrated policy | Paid option reuse, explicit operation extents, frozen v4 allocation; all 60 development cases and separate witnesses meet regime expectations | Complete in declared development scope |
| R21C — full release rerun | Held-out seeds 2001–2010 still unused; full release gates pending | Open — next |

## R21C — next

Use `docs/r21b/Protocol_R21_v4.json`, whose SHA-256 is frozen alongside it.
Start each episode at genesis and enroll the exact v4 contract before any work.
Per-actor whole-episode energy/time budgets are 200,000 adequate, 150,000
constrained, and zero inadequate. This explicitly supersedes the failed v3
100,000 constrained trial and the inherited v2 100,000/20,000 allocation; it
does not establish feasibility under those earlier envelopes. No top-ups,
refunds, stage resets, pooled wallets or omitted histories are permitted.

Execute all 16 TIMs × seeds 2001–2010 × three regimes (480 cases), preserving
all failed, partial, deferred and resource-censored runs in their denominators.
Use `run_candidate(..., evaluation=True)` and a separately invoked
`run_reference_policy(..., evaluation=True)` from `tools/r21b_policy.py`.
Do not substitute replay for an independently constructed policy. Raw audits
must cover paid reuse and causal provenance as well as the full episode.

Preserve three maintaining engagements, original material, conversion and all
eight retained aspects, physical conditional returns, all thirteen challenges,
100 later eligible opportunities and two actual changes. Apply unchanged 100%
positive-regime thresholds. Do not consult evaluator status in participant control.

Rerun all behavioral, paired/shared, recursive closure, checkpoint, independent
accounting and performance gates on final source. R21B's development witnesses
are not held-out release results. Old seeds 1001–1010 remain regression only.
Any further contract, allocation, cost policy or threshold change requires a new
version with all earlier evidence preserved; declare changes before evaluation.

## Continuing artifacts

- `evidence/r21b/development/sli_11_constrained_feasible.checkpoint.json.gz`:
  completed v4 episode, all challenges and 100 later opportunities.
- `evidence/r21b/development/iee_12_constrained_feasible.checkpoint.json.gz`:
  independent second-type continuing branch.
- `evidence/r21b/final_source/summary.json`: all 120 constructions reexecuted
  against final runtime and matched to the retained transaction digests.
- `evidence/r21b/initial/sli11.transactions.jsonl.gz`: retained failed v3 branch.
- Prior R20/v1 and R21A/v2 checkpoints and failed release evidence remain intact.

Restore with `ClosureWorld.restore`. Restoring never upgrades an old contract.
Diagnostic `.no_reuse` / `.legacy_cost` branches cannot count as release evidence.

**Next: R21C. One follow-up step remains; parent progress is 9/10.**
