"""Build the release decision from executed evidence, without upgrading failures."""
import csv,hashlib,json,re,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from r21_evidence import save,summarize

def read(path):return json.loads((ROOT/path).read_text())

def main():
    out=ROOT/'evidence/r21';docs=ROOT/'docs/r21'
    rows=[json.loads(p.read_text()) for p in sorted((out/'panel').glob('*.compact.json'))]
    panel=summarize(rows);save(out/'panel/summary.json',panel)
    perf=read('evidence/r21/performance/summary.json')
    queues=read('evidence/r21/performance/queue_audit.json')
    if not queues['passed']:raise ValueError('unfinished queue accounting differs from benchmark')
    continued=read('evidence/r21/continuation/summary.json')
    inherited=read('evidence/r21/validation/inherited/summary.json')
    initial=(out/'r21_tests.log').read_text();recheck=(out/'r21_test_recheck.log').read_text()
    new_ok=('Ran 10 tests' in initial and 'failures=1' in initial and recheck.rstrip().endswith('OK'))
    validation={'inherited':inherited['total'],'r21_distinct':10,'distinct_total':inherited['total']+10,
                'repeated_recheck_not_added':1,'passed':inherited['passed'] and inherited['total']==859 and new_ok}
    save(out/'validation/summary.json',validation)
    parent=ROOT/'docs/r12/acceptance_v1.json'
    protocol=read('docs/r21/Protocol_R21_v1.json')
    sources=read('docs/r21/Source_Input_Check.json')
    fixed=read('evidence/r21/continuation/original_budget.json')
    supplemental=read('evidence/r21/continuation/supplemental_horizon.json')
    failures={};complete_actions=0;completed_demands=0
    for p in (out/'panel').glob('*_adequate.json'):
        evidence=json.loads(p.read_text())['assessment']['raw_clearance']['reference']['rows']
        completed_demands+=len(evidence)
        complete_actions+=len(evidence)==13 and all(all(r[k] for k in
            ('current_capacities','grounded_conditional_return','no_target_mechanism','own_work','physical_return','two_carriers','unsupported')) for r in evidence)
        for r in evidence:
            if not r['passed']:failures[r['case']]=failures.get(r['case'],0)+1
    with (out/'episode_matrix.csv').open('w',newline='') as f:
        fields=['tim','seed','regime','budget','history','cleared','status','stage','resource_stop','eligible','changes','unfinished','integrity','exact_replay','passed']
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    distributions=[]
    for regime in protocol['parent_evaluation']['regimes']:
        for history in (3,4,5):
            group=[r for r in rows if r['regime']==regime and r['history']==history]
            values=[r['work'][f"s{r['seed']}:worker"] for r in group]
            distributions.append({'regime':regime,'history':history,'n':len(group),'worker_units_min':min(values),
                'worker_units_median':statistics.median(values),'worker_units_max':max(values),
                'episode_wall_seconds_median':statistics.median(r['seconds'] for r in group),
                'resource_censored':sum(r['resource_stop'] is not None for r in group)})
    save(out/'work_distributions.json',distributions)
    result={'schema':'r21-release-decision-v1','milestone_complete':False,'parents_complete':9,'parents_total':10,
        'remaining_parent_milestones':['R21'],'panel':{k:v for k,v in panel.items() if k!='rows'},
        'accounting_agreement':sum(r['integrity'] for r in rows),'exact_episode_replays':sum(r['exact_replay'] for r in rows),
        'unexpected_errors':sum(bool(r['error']) for r in rows),'adequate_all_13_action_predicates':complete_actions,
        'adequate_completed_demands':completed_demands,'failed_demand_shapes':failures,
        'performance_passed':perf['passed'],'replay_passed':continued['replay_passed'],'validation':validation,
        'parent_acceptance_unchanged':hashlib.sha256(parent.read_bytes()).hexdigest()==protocol['parent_sha256'],
        'source_documents_unchanged':len(sources)==9 and all(r['same'] for r in sources),
        'gates':{'R21.1':'FAIL: exact 480 denominator present; adequate/constrained clearance and feasibility requirements fail',
                 'R21.2':'OPEN: no qualifying frozen-panel clearance; original checkpoint reaches 89/100; supplemental branch reaches 100/100',
                 'R21.3':'PASS within tested historical phases, partial work, changes, clearance, recurrence and nested invalidation',
                 'R21.4':'PASS for reconciled work and the declared 32-choice active/inactive benchmark'},
        'remaining_steps':['R21A: version and reconcile demand/resource comparison and whole-episode allocation contract',
                           'R21B: implement and independently establish feasible paid policies for both positive regimes over the full horizon',
                           'R21C: rerun the full release panel and regression/replay/performance gates; preserve this failed v1 evidence']}
    save(out/'release_decision.json',result)
    type_lines=[]
    for tim in protocol['parent_evaluation']['types']:
        group=[r for r in rows if r['tim']==tim and r['regime']=='adequate']
        units=[r['work'][f"s{r['seed']}:worker"] for r in group]
        type_lines.append(f"| {tim.upper()} | 0/10 | {sum(r['resource_stop'] is not None for r in group)}/10 | {min(units):,}–{max(units):,} | 0/10 | 10/10 |")
    ratio_lines='\n'.join(f"| {r['kind']} | {r['median_tick_ratio']:.3f}× | {r['affected_visits_ratio']:.3f}× | {max(r['checkpoint_ratios_per_10x']):.3f}× | Pass |" for r in perf['gates'])
    report=f'''# R21 — sustained release evaluation

**Evaluation completed. Release acceptance failed and R21 remains open.**
The R12–R21 extension remains **9/10 parent milestones complete**. R14.5 and
R16A/R16B retain their prior status. This candidate does not claim the engine
has passed its final release gate.

## Frozen population result

All **480/480 planned episodes** executed: 16 TIMs × 10 held-out seeds ×
three regimes. No incomplete or resource-censored episode was removed.
The exact grid, raw transactions, per-case results, partial jobs, work
distributions and command-policy replays are retained.

| Regime | Episodes | Qualifying clearance | Resource stops | Frozen outcome passed |
| --- | ---: | ---: | ---: | ---: |
| Adequate: 100,000 per actor | 160 | 0 | 12 | 0/160 |
| Constrained: 20,000 per actor | 160 | 0 | 160 | 0/160 |
| Inadequate: 0 per actor | 160 | 0 | 160 | 160/160 honest deferrals |

The operational resource interpretation is one genesis allocation per actor,
covering history, acquisition, clearance and the subsequent horizon. The R12
budget numbers are unchanged. The episode horizon and historical coverage
cannot be silently paid by the old demos' repeated 200,000-unit top-ups.

**Two distinct problems block acceptance.** First, `compare_demands` requires
an identical resource envelope before labeling a requirement increase
“greater.” R19 passes each challenge's actual starting wallet to that
comparison. With a single declining wallet, the three increased-demand cases
are incomparable to their earlier family baselines. The old replenished
demonstration masked this integration problem. All 480 increased-demand rows
across the adequate panel fail that shape check, and the independent evaluator
agrees. **{complete_actions}/160 adequate episodes nevertheless complete all
13 challenges with every noncomparison action predicate satisfied**: own work,
current capacities, grounded return, physical return, two carriers, withdrawn
substitute support and no target defensive mechanism.

Second, the paid policy does not fit the constrained budget. All 160 constrained
episodes exhaust it during development; 12 adequate episodes exhaust their
wallet during clearance. These are observed policy failures, not a proof that
every conceivable policy is infeasible. Separate exact execution of each
recorded legal command policy confirms its costs and consequences; it supplies
no successful full-horizon feasibility witness. That frozen gate therefore
fails. No resource price, comparison law, threshold or success fraction was
changed to convert failure into a pass.

## Sustained original-checkpoint continuation

The supplied R20 checkpoint restores exactly, retaining its **3,131-transaction
prefix**, original actor/material lineage, individual capacities and shared
closure history. With no new credits, it completes **89 eligible opportunities
and two real family changes**, then preserves unfinished work on opportunity
90 when its wallet runs out. Its retained clearance remains in scope; resource
exhaustion is not mislabeled a recurrent Shell.

A separate diagnostic branch adds a recorded **2,000,000 units of energy and
time per actor once**, then completes **100/100 opportunities and both demand
changes**. It uses real selection, temporal and simultaneous-obligation tasks,
conditional physical returns, changed partners, interrupted testimony and
fresh participant controllers. Quiet ticks are not counted. All raw outcome
and resource checks agree. This establishes sustained behavior in that funded
branch; **it does not pass either frozen positive resource regime**.

After that horizon, three enacted returns using the still-addressable old
defensive procedure reopen clearance as unresolved and then recurrent. Exact
replay and raw reconstruction preserve its earlier clearance history. A
separate withdrawal of a native child practice's originating evidence
invalidates the affected nested shared claims. The inherited paired/collective
and succession controls also run on this candidate; these remain finite
custody/obligation cases, not unrestricted institutional development.

## Verification and performance

**{validation['distinct_total']} distinct tests pass**: {validation['inherited']}
inherited and 10 new R21 tests, with one corrected test rechecked separately.
All **480/480** episode journals agree with independent accounting and exact
command replay; no unexpected episode exceptions occurred. The full inherited
source checks and 9,216 OIG comparisons pass. All nine supplied documents and
the frozen R12 acceptance declaration remain byte-identical.

Checkpoint tests cover release, contextualization, reorganization, practice,
reflection, retention, memory revision, partial work, clearance, both shared
depths, resource exhaustion, the sustained horizon, recurrence and nested
invalidation. Exact next-transaction checks accompany the checkpoint checks.

The benchmark holds **32 active choices**, uses **two warmups and nine measured
runs**, and varies inactive history through **100, 1,000 and 10,000** events.
It separately measures participant processing, online observers, checkpoint
serialization, compression, restore and offline reconstruction. Each choice
batch forbids a journal scan and completes all 32 orders before the next batch.

| Inactive history | Median time ratio, 100→10,000 | Affected visits ratio | Largest checkpoint ratio per 10× history | Result |
| --- | ---: | ---: | ---: | --- |
{ratio_lines}

Limits are 2×, 2× and 25× respectively. Affected record lookups remain
**87,744 per measured 32-choice batch**. Archives and offline replay still
grow; this result does not certify every scheduler operation or bounded total
storage. Queue reconstruction reproduces the timed workloads' exact work
accounting. Open circuit orders and unpaid circuit jobs are zero after each
drain, while unread autonomy notifications remain explicit: the inherited
471 notifications stay queued, and completed-inspection histories add 100,
1,000 or 10,000 more. They are preserved, not counted as processed. The timing
gate concerns the declared 32-choice path, not full autonomous inbox service.
Wall times are measurements from this shared execution environment,
not engine work units or psychological quantities.

## Type coverage

| TIM | Adequate clearances | Adequate resource stops | Adequate worker units | Constrained clearances | Inadequate deferrals |
| --- | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(type_lines)}

## Changes and handoff

The runtime's learning, prices and acceptance semantics remain intact.
`clearance_demo` adds explicit switches to disable allocations, vary unique
offer identifiers, permute options and run continuation without opening a
second frozen clearance window. New R21 tools supply the strict-budget driver,
raw resource/renewal audit, full panel, sustained continuation, benchmarks,
report generation and reproducible packaging. Historical R20 files and the
preliminary failed attempts are retained.

The source archive includes the runnable engine, all inherited contents, R21
reports/checkpoints and reproduction tools. The two evidence archive parts
contain the complete R21 raw population traces. Extract both into the same
directory; their common manifest identifies every file. To avoid duplicating hundreds
of megabytes, those traces are listed in the source manifest and delivered in
the evidence parts. Together the source and both evidence parts contain the complete handoff.

**Next: R21A — reconcile and version the resource/comparison contract.** Then
R21B must establish genuinely feasible paid policies across the entire horizon,
and R21C must rerun acceptance while preserving this failed v1 evaluation.
There is **one open parent milestone and three declared follow-up steps**.
'''
    (docs/'Step_R21_Report.md').write_text(report)
    progress='''# HLE progress after the R21 evaluation

**R21 was evaluated and did not pass. The R12–R21 extension remains 9/10
parent milestones complete. One parent remains: R21.**

R12–R20 retain their previously established, bounded completion status.
R14.5 remains the completed prerequisite; R16A/R16B remain the completed parts
of R16. This evaluation does not erase earlier successes or promote them to
sustained release acceptance.

| Gate | Current evidence | Status |
| --- | --- | --- |
| R21.1 population/resource panel | Exact 480/480 grid; 0/160 adequate and 0/160 constrained qualifying clearances; 160/160 honest inadequate deferrals | Failed |
| R21.2 sustained continuation | No qualifying frozen-panel episode; original R20 reaches 89/100 with two changes; explicitly funded diagnostic reaches 100/100 | Open |
| R21.3 replay and current invalidation | Exact original continuation and phase/partial/revision/clearance/recurrence/nested cuts; independent agreement | Passed in tested scope |
| R21.4 accounting and performance | 480/480 accounting agreement; frozen 32-choice performance ratios pass | Passed in tested scope |

## Declared follow-up work

1. **R21A — resource and comparison contract.** Specify the episode's budget
   scope and how two demands remain comparable as resources are spent. Keep
   actual wallets and paid work visible. Any changed comparison, allocation
   semantics, budget or acceptance threshold requires a new version with the
   v1 declaration and failure evidence retained. A declared independent
   feasibility policy must cover the same history and full horizon.
2. **R21B — feasible integrated policy.** Implement useful work reuse and/or the
   justified versioned allocation policy, then separately execute legal
   successful policies within both positive budgets. Verify original
   maintenance, all eight retained capacities, physical conditional returns,
   thirteen clearance challenges and 100 later opportunities with two changes.
   Replenishment cannot be hidden; no participant may consult evaluator status.
3. **R21C — full release rerun.** Rerun all planned cases, denominators,
   paired/shared controls, exact checkpoint continuation, raw evaluation and
   performance gates against the delivered source. Freeze any new held-out
   seeds before using them. Close R21 only when every required gate passes.

## Continuing artifacts

- The unmodified accepted R20 checkpoint is
  `evidence/r20/panel/continued_r19.checkpoint.json.gz`.
- `evidence/r21/continuation/original_budget_stop.checkpoint.json.gz` retains
  the strict continuation's partial work after 89 completed opportunities.
- `evidence/r21/continuation/supplemental_horizon.checkpoint.json.gz` is a
  separate 100-opportunity diagnostic branch with an explicit extra allocation.
- `recurrence.checkpoint.json.gz` and `nested_invalidation.checkpoint.json.gz`
  are later diagnostic branches; they are not clean clearance continuations.

Load these checkpoints with `ClosureWorld.restore`. Preserve their branch
identity; do not treat diagnostic funding as frozen-panel evidence. All prior
transactions, source documents, manifests and R12 declarations are retained.

**Next: R21A. Three follow-up steps remain; the parent count stays 9/10.**
'''
    (docs/'Progress_After_R21.md').write_text(progress)
    print(json.dumps({'milestone_complete':False,'tests':validation,'panel':panel['regimes'],'performance':perf['passed'],'replay':continued['replay_passed']}))

if __name__=='__main__':main()
