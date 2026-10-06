"""Create the bounded R21A decision and handoff from measured evidence."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    evidence = ROOT/'evidence/r21a';docs = ROOT/'docs/r21a'
    validation = json.loads((evidence/'validation/summary.json').read_text())
    panel = json.loads((evidence/'development/summary.json').read_text())
    physical = json.loads((evidence/'horizon_physical_audit.json').read_text())
    sources = json.loads((docs/'Source_Input_Check.json').read_text())
    complete = validation['passed'] and panel['contract_checks_passed'] and physical['passed'] and all(r['same'] for r in sources)
    if not complete:raise ValueError('R21A contract checks are incomplete')
    rows = panel['rows'];adequate = [r for r in rows if r['regime']=='adequate']
    increases = sum(r['greater_with_less_headroom'] for r in rows)
    cost_case = json.loads((evidence/'development/iee_12_adequate.json').read_text())
    labels = {'conversion':'History, maintenance and conversion', 'aspects':'Eight-aspect acquisition',
              'clearance':'Support withdrawal and clearance', 'remaining_or_unfinished':'30 later opportunities plus unfinished opportunity 31'}
    costs = '\n'.join(f"| {labels[x['phase_end']]} | {x['charged']['s12:worker']['energy']:,} | {x['charged']['s12:worker']['time']:,} |"
                      for x in cost_case['assessment']['phase_spending'])
    decisions = {'schema': 'r21a-decision-v1', 'R21A_complete': complete, 'R21_complete': False,
        'parent_progress': [9, 10], 'remaining_steps': ['R21B', 'R21C'],
        'validation': validation, 'contract_development_episodes': panel['episodes'],
        'separate_policy_executions': panel['independent_executions'], 'physical_horizon_audit': {
            'executions': physical['executions'], 'completed_windows': physical['windows'], 'passed': physical['passed']},
        'full_horizon_feasibility_established': panel['full_horizon_feasibility_established'],
        'release_rerun_performed': False, 'new_held_out_seeds_used': []}
    (evidence/'decision.json').write_text(json.dumps(decisions, indent=2)+'\n')
    table = '\n'.join(f"| {r['tim'].upper()} | {r['seed']} | {r['history']} | {r['passed_clearance_rows']}/13 | {r['completed_opportunities']}/100 |" for r in adequate)
    report = f'''# R21A — resource and comparison contract

**R21A is complete. Parent R21 remains open; extension progress remains 9/10.
Two declared follow-up steps remain: R21B and R21C.**

The new contract separates a demand's elected requirements from its current
wallet. Under the same episode allocation and otherwise identical scope,
spending no longer erases a valid requirement increase. Actual resources remain
on the demand, in the journal, in each clearance row, and in the independent
audit. No work, price or historical failure is removed.

## Contract changes

- New episodes explicitly enroll in `r21.resource-comparison.v2` immediately
  after genesis. Old checkpoints retain v1 behavior and cannot be retrofitted.
- The existing 100,000 / 20,000 / 0 allocations remain per actor and cover
  history, development, thirteen challenges and the 100-opportunity horizon.
  Top-ups are rejected by the runtime; hidden credits/refunds fail raw audit.
- Comparisons retain the same participant, context, lineage, outcomes,
  movements, constraints, duration, dimensions and allocation scope. Changed
  partners and mixed requirement changes remain incomparable. Less headroom
  is reported separately and never establishes affordability or clearance.
- A declared constructive policy now runs separately from genesis without
  candidate commands or clearance-status decisions. Its scope covers the same
  history and complete planned horizon. Exact command replay is a separate
  reproducibility check, not the feasibility gate.

The normative declaration, hash, detailed explanation and old source snapshots
are in `docs/r21a`. This is a versioned finite operational choice, not a claim
that the source theory proves a universal resource law.

## Measured development evidence

The declared diagnostic panel executed **18/18 episodes and 18/18 independent
constructions**: IEE and SLI, seeds 11/12/13, and all three unchanged budgets.
These seeds give historical lengths five, three and four. Every episode and
separate construction agrees with independent raw comparison and accounting.
All **{increases}/{increases} executed increased-requirement comparisons** retain
their actual lower wallets and correctly report greater requirements.

| TIM | Development seed | Historical exposures | Clearance challenges passed | Later opportunities completed |
| --- | ---: | ---: | ---: | ---: |
{table}

Five of six adequate-budget development cases pass all thirteen clearance
challenges; the sixth exhausts its budget during the last challenge. All six
constrained cases exhaust during development. All six zero-budget cases defer
without acquired capacity. Every partial job remains recorded. None of the
twelve positive-budget construction witnesses completes its full horizon.

**Full-horizon feasibility remains unestablished.** These are observed failures
of the declared current-cost policy, not a proof that no improved policy can
fit. R21B must address paid work reuse and demonstrate genuinely successful
whole-episode policies. Any allocation or policy change must be explicitly
versioned with these results retained.

The IEE/seed-12 worker's exact paid allocation illustrates the remaining cost
problem. The other participants' separate expenditures remain in the raw audit.

| Phase | Energy spent | Time spent |
| --- | ---: | ---: |
{costs}
| Total | 100,000 | 100,000 |

History, maintenance and conversion alone consume more than the constrained
20,000-unit allowance in this existing policy. R21B therefore needs evidence
of reduced paid work across the whole episode.

The same-scenario v1 control still reports all three increased-demand
comparisons as incomparable and fails clearance. No old R21 result is relabeled
as a v2 pass. The 480-case release panel was not rerun for this milestone.

## Validation and preservation

**{validation['total']} distinct tests pass**: 859 inherited through R20,
10 R21 tests and {validation['suites'][-1]['count']} R21A tests. Repeated focused
checks are not added to this count. Checks include scope changes, zero-wallet
eligibility, direct credit rejection, exact v1/v2 checkpoint continuation,
partial-job preservation, evaluator isolation, independent policy construction,
duplicate horizon intervals, forged metadata and a false physical-return label.

A supplementary audit reconstructs actual physical return facts directly from
all **{physical['executions']} retained construction traces**, covering
**{physical['windows']} completed later-opportunity windows** across both
executions. It agrees with every previously recorded outcome. This refinement
checks that a success label cannot replace clean condition, ended loan and
authorized ownership. Its separate log is retained alongside the original
diagnostic records.

That reread also exposed two truncated compressed trace files. Both were
regenerated by executing the declared policy again and matched their original
recorded uncompressed transaction hashes exactly. The truncated bytes,
original metadata and repair record remain in the evidence. New trace writes
now verify compressed readback before atomic publication.

The original R20 checkpoint restores byte-exactly and retains v1 semantics.
The v2 checkpoint preserves the enrolled contract, declining wallets and
unfinished work. All nine supplied source documents, the R12 acceptance
declaration, v1 R21 protocol and inherited evidence remain byte-identical.
Historical raw population traces remain in the two original R21 evidence
archives, with archive hashes and checks recorded in this handoff.

New held-out seeds **2001–2010** are frozen in v2 and have not been executed.
Old evaluation seeds 1001–1010 are regression seeds. The 480-case denominator,
100% positive-regime success thresholds, thirteen challenges, 100 later
opportunities, two changes and performance limits remain unchanged.

The performance gate and full shared/paired population release evaluation are
not renewed by this step. Historical passing results retain their tested
scope; R21C must rerun all release gates on the final delivered source.

## Handoff

- Runtime: `hle/resource_contracts.py` plus explicit enrollment and observers.
- Independent policy: `tools/r21a_policy.py`.
- Whole-episode feasibility checks: `tools/r21a_audit.py`.
- Diagnostics and raw traces: `evidence/r21a/development`.
- Current contract and next steps: `docs/r21a/Resource_and_Comparison_Contract_v2.md`
  and `Progress_After_R21A.md`.

**Next: R21B — feasible integrated policy. Parent progress stays 9/10.**
'''
    (docs/'Step_R21A_Report.md').write_text(report)
    (docs/'Progress_After_R21A.md').write_text('''# HLE progress after R21A

**R21A is complete. The R12–R21 extension remains 9/10 parent milestones
complete. One parent milestone remains: R21. Two follow-up steps remain.**

R12–R20 retain their established bounded status. R14.5 and R16A/R16B retain
their prior status. R21's failed v1 release evaluation is preserved.

| Step | Result | Status |
| --- | --- | --- |
| R21A — resource and comparison contract | Versioned whole-episode allocation; explicit separation of requirements and actual wallets; independent constructive policy and full-horizon audit; compatibility and development controls pass | Complete |
| R21B — feasible integrated policy | Current positive-budget policy still exhausts resources; no full-horizon witness | Open — next |
| R21C — full release rerun | Fresh held-out seeds frozen; no new release-panel evaluation performed | Open |

## R21B — next

Implement useful paid work reuse and/or a justified explicitly versioned
policy. Preserve actual historical exposure, three maintaining engagements,
original material, conversion plus all eight retained aspects, physical
conditional returns, the original and twelve held-out challenges, and all
100 subsequent eligible opportunities with two changes. Independently execute
successful policies in both positive regimes over the same full episode.

Do not silently replenish wallets, reset budgets at stage boundaries, refund
past work, skip histories, weaken thresholds or consult evaluator status in
participant control. The `constrained_feasible` key remains a proposed regime
name until a legal witness establishes feasibility. Current budget exhaustion
does not prove universal infeasibility.

Use the declared development seeds for further work. Any changed contract,
budget/allocation, price, policy or acceptance meaning requires a new version
with v1 and v2 evidence retained. If a change affects the frozen R21C schedule,
declare the new protocol before using it.

## R21C — after feasibility

Execute the complete 16-TIM × 10-seed × 3-regime panel, with every failed,
partial and resource-censored episode retained in denominators. Version 2
reserves seeds 2001–2010; none has been used. The old 1001–1010 panel remains
regression evidence. Rerun all behavioral, paired/shared, checkpoint,
independent-accounting and performance gates against the final source.

Close parent R21 only when every required gate passes. R21A's successful
contract diagnostics do not change release acceptance.

## Continuing artifacts

- `docs/r21a/Protocol_R21_v2.json` and its SHA-256 file: frozen contract.
- `evidence/r21a/development/iee_12_adequate.checkpoint.json.gz`: v2 development
  branch, 13 clearance challenges and 30 later opportunities, then exhaustion.
- `evidence/r21a/development/sli_11_constrained_feasible.checkpoint.json.gz`:
  v2 development branch with unfinished acquisition at exhaustion.
- `evidence/r20/panel/continued_r19.checkpoint.json.gz`: unchanged accepted R20
  checkpoint, with v1 semantics.
- The original R21 strict and supplemental checkpoints retain their separate
  branch identities; diagnostic funding cannot count in either positive regime.

Restore using `ClosureWorld.restore`. A v1 checkpoint remains v1. To test v2,
start a new genesis and journal the episode contract before any work.

**Next: R21B. Two follow-up steps remain; parent progress is 9/10.**
''')
    print(json.dumps(decisions, indent=2))


if __name__ == '__main__':main()
