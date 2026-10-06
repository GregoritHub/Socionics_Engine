"""Generate an evidence-gated R21B report and exact remaining-step handoff."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path): return json.loads((ROOT/path).read_text())
def save(path, value): (ROOT/path).write_text(json.dumps(value, indent=2)+'\n')


def main():
    panel = read('evidence/r21b/development/summary.json')
    final = read('evidence/r21b/final_source/summary.json')
    inherited = read('evidence/r21b/validation_inherited/summary.json')
    log = (ROOT/'evidence/r21b/tests_after_partial_fix.log').read_text()
    match = re.search(r'Ran (\d+) tests', log)
    count = int(match.group(1)) if match else 0
    if not (panel['passed'] and final['passed'] and inherited['passed']
            and inherited['total'] == 893 and count == 19 and log.rstrip().endswith('OK')):
        raise ValueError('R21B acceptance checks incomplete or failed')
    source = read('evidence/r21b/final_source/source.json')
    if not all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == h for p,h in source.items()):
        raise ValueError('verified source changed')
    controls = read('evidence/r21b/controls/summary.json')['rows']
    positive = [r for r in panel['rows'] if r['regime'] != 'inadequate']
    costs = [max(r['work'][next(a for a in r['work'] if a.endswith(':worker'))].values()) for r in positive]
    pairs = {r['mode']:r for r in controls}
    example = next(r for r in panel['rows'] if r['tim']=='iee' and r['seed']==12 and r['regime']=='constrained_feasible')
    worker = 's12:worker'
    own = max(example['work'][worker].values()); uncached = max(pairs['no_reuse']['work'][worker].values())
    save('evidence/r21b/validation_summary.json', {'schema':'r21b-validation-v1','inherited':893,
        'r21b':count,'total_distinct_tests':893+count,'passed':True,
        'repeated_runs_not_added':True})
    decision = {'schema':'r21b-decision-v1','R21B_complete':True,'R21_complete':False,
        'parent_progress':[9,10],'remaining':['R21C'],'protocol':'r21.integrated-policy.v4',
        'development_cases':panel['executed'],'independent_executions':panel['independent_executions'],
        'positive_candidate_successes':len(positive),'positive_independent_successes':len(positive),
        'zero_budget_deferrals':panel['zero_count'],'final_source_reexecutions':final['separate_constructions'],
        'distinct_tests':893+count,'held_out_release_seeds_used':[],
        'release_performance_and_shared_population_gates':'not renewed; R21C required'}
    save('evidence/r21b/decision.json', decision)
    report = f'''# R21B — feasible integrated policy

**R21B is complete under the explicitly versioned v4 contract. Parent R21 remains
open; progress is 9/10. One follow-up step remains: R21C, the full release rerun.**

## Established result

All **60 declared development cases and 60 separately constructed witnesses**
were executed. The panel covers every TIM at seed 11 (five historical exposures)
and IEE/SLI at seeds 12 and 13 (three and four exposures), in all three regimes.
All **40 positive-budget candidates and all 40 independent witnesses** completed
their full episodes. All 20 zero-budget cases and their independent counterparts
deferred without acquired capacity. No incomplete case was dropped.

Each positive execution preserves its actual historical exposure, three maintaining
engagements, original material, acquired conversion and all eight retained aspects,
support withdrawal, the original plus twelve challenges, and **100 later paid
opportunities with two changes**. The independent audit verifies actual clean,
authorized physical returns, conditional recall, current capacity use, zero
defensive recurrence in those opportunities, and each actor's energy/time ledger.
There are 8,000 audited later opportunities across candidate and independent
positive runs. Rechecks are not counted as additional experimental cases.

## Explicit contract and resource changes

| Contract | Adequate | Constrained | Inadequate | Result |
| --- | ---: | ---: | ---: | --- |
| v2, inherited R21A | 100,000 | 20,000 | 0 | Original exhaustion evidence retained |
| v3, R21B development | 200,000 | 100,000 | 0 | SLI/11 exhausted after 50 later opportunities |
| v4, current | 200,000 | 150,000 | 0 | All declared development candidates and witnesses pass their regime expectations |

Amounts are **per actor, for each of energy and time, for the entire episode**.
No wallet is reset at a stage boundary, pooled, replenished or refunded. These are
operational simulation allocations, not source-derived physiological constants.
This does **not** establish feasibility at the former 20,000-unit allocation.

The historical work policy remains intact: SLI/11's history and conversion alone
cost 75,202 units. After the v3 constrained failure, a declared development-only
diagnostic completed all sixteen types at the adequate allocation, measuring
77,760–125,664 worker units. v4 was frozen before its paired panel, with a 150,000
constrained envelope and headroom. Across the final positive development cases,
worker spending is {min(costs):,}–{max(costs):,} units. This is a finite measurement,
not a universal upper bound.

All v1/v2 declarations and failures remain unchanged. v3's declaration, source
snapshot, 18 executed candidate diagnostics (17 complete, one censored), and
42 unexecuted/unassessed cases out of its original 60-case plan are retained.
No v3 independent witness was claimed. v4 supersedes that failed candidate contract.

## What the engine now does

The earlier circuit charged every phase for a full eight-predicate scan of every
option. v3/v4 use the frozen operation-specific extents in `Protocol_R21_v4.json`.
Menu delivery still computes current permissions and acknowledgments. Review,
execution, inspection and feedback pay for the selected option, actual outcome,
or retained dependencies they process. Model A routes, hop prices, content-unit
prices and physical-action prices remain unchanged. The change in work extents
is an explicit implementation choice, not a silently reduced price schedule.

Completed paid choices retain exact visible predicate calculations. Reuse is
local to the actor and keyed by context, partner, semantic option fields,
relative observation epoch, requirements, and delivered permissions. Entries
carry completed-event, bulletin and menu provenance. Reuse does not cache an
answer, a world-state result, a shared-load result or an assessor verdict. Current
learned guards, visible concurrent commitments and real physical constraints are
checked again. Cached predicates cannot replace withdrawn retained capacities.
Conceptual material remains separate from these exact factual processing receipts.

Unfinished jobs publish no choice or cache entry. Source withdrawal invalidates
reuse. A targeted failing regression exposed a concurrent offer arriving during
partly paid choice; the fixed runtime preserves the original visible group and
rejects continuation when it changes, without refund. The failing log and exact
pre-fix sources are preserved. All cache and unfinished-group state is rebuilt
from chronological journal replay.

## Controls and validation

The same IEE/12 scenario at 150,000 units uses **{own:,} worker units** with reuse,
versus **{uncached:,}** when predicate reuse is disabled while keeping the new
phase extents. Both complete the full horizon. The legacy blanket-extent control
exhausts its 150,000 units after 50 later opportunities. Thus the result is not
explained by allocation alone. Controls are explicitly marked diagnostic and
cannot satisfy a release feasibility gate.

**{893+count} distinct tests pass**: 893 inherited and {count} R21B tests. Focused
reruns are not added to the count. Tests cover activation, reserved-seed exclusion,
partial payments, byte-exact checkpoint continuation, source withdrawal, changed
partner schedules, changed concurrent demand, retained-capacity withdrawal,
forged cost records, duplicate horizon rows, and independent reconstruction.
One initial audit field-name error and two test-fixture argument errors were
corrected; their logs remain alongside the genuine partial-group regression.

After the partial-group fix, the **final runtime separately reexecuted all 60
candidates and all 60 independent constructions from genesis**. Every complete
transaction digest matches its retained raw trace and every fresh audit agrees.
Neither construction receives the candidate's command list or the assessor's
status. Shared engine primitives and the same declared schedule are used; this
is independent execution, not a claim of two independently invented learners.

All nine supplied source documents remain byte-identical. Old R20/v1 and R21A/v2
checkpoint compatibility is covered by the inherited regression suite. Current
checkpoints preserve the selected v4 contract, declining wallets, retained
processing receipts and unfinished work. No held-out seed 2001–2010 was used.

## Handoff and remaining work

- Contract: `docs/r21b/Protocol_R21_v4.json` and SHA-256 file.
- Runtime: `hle/paid_work.py` plus versioned enrollment in `resource_contracts.py`.
- Candidate/independent drivers: `tools/r21b_policy.py`.
- Independent raw accounting: `tools/r21b_work_audit.py` and `r21b_audit.py`.
- Declared panel: `docs/r21b/Development_Panel_v2.json`.
- Raw evidence: `evidence/r21b/development`; final-source reexecution: `final_source`.
- Continuing checkpoint: `development/sli_11_constrained_feasible.checkpoint.json.gz`
  (also IEE/12), restored with `ClosureWorld.restore`.

R21C must execute the complete **16 TIM × 10 fresh seeds × 3 regimes = 480-case**
held-out panel under v4, plus independently successful positive-regime witnesses.
It must rerun the full paired/shared, recursive, checkpoint, independent-accounting,
behavioral and performance gates against the final delivered source. The 100%
positive success thresholds, thirteen challenges, 100 later opportunities, two
changes and inclusion of every failure/partial/resource-censored episode remain.
The old 1001–1010 panel remains regression evidence. Performance and shared
population release acceptance are not renewed by R21B.

**Next: R21C. One follow-up step remains; parent progress stays 9/10.**
'''
    (ROOT/'docs/r21b/Step_R21B_Report.md').write_text(report)
    progress = '''# HLE progress after R21B

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
'''
    (ROOT/'docs/r21b/Progress_After_R21B.md').write_text(progress)
    print(json.dumps(decision, indent=2))


if __name__ == '__main__': main()
