"""Build delivery prose and ledger from accepted C4 evidence; no runtime changes."""
import copy,json,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence_c4'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')


def main():
    tests=read(E/'tests_final/summary.json');w=read(E/'witnesses/summary.json');m=read(E/'measurements/summary.json')
    assert all(d['passed'] and d['source_unchanged'] for d in (tests,w,m))
    assert tests['tests']==554 and w['causal_pairs']==7 and m['workers']==36
    preservation=read(E/'inherited_preservation.json')
    inherited_runtime=sum(n.startswith('hle_unified/') and n.endswith('.py') for n in preservation['preserved_sha256'])
    frozen=sum(n.startswith('baseline/') for n in preservation['preserved_sha256'])
    healthy=[r for r in w['rows'] if not r['control'] and not r['failed_child']]
    cases=[]
    for good in healthy:
        bad=next(r for r in w['rows'] if r['name']==good['name'] and r['control'])
        cases.append(f"| {good['name']} | {good['outcome']} / {bad['outcome']} | {good['focus_spent']} |")
    panel=[r for r in m['rows'] if r['lane']=='panel']
    ref=next(r for r in m['rows'] if r['lane']=='reference');adapt=next(r for r in m['rows'] if r['lane']=='adapted')
    tab=[]
    for r in panel:
        tab.append(f"| {r['shape'].title()} | {r['inactive']:,} | {1000*r['median_active_wall_seconds']:.1f} | {r['median_restore_seconds']:.2f} | {r['median_audit_seconds']:.2f} | {r['memory']['peak_bytes']/1048576:.2f} | {r['checkpoint_bytes']/1048576:.2f} |")
    growth=[]
    for r in m['rows']:
        if r['lane'] in ('depth','dependencies'):
            growth.append(f"| {'Nested review depth' if r['lane']=='depth' else 'Direct child operations'} | {r['size']} | {1000*r['median_active_wall_seconds']:.1f} | {r['modeled_active_work']} | {r['median_restore_seconds']:.2f} |")
    q=panel[0]
    per_effect=[1000*r['median_active_wall_seconds']/5 for r in panel]
    per_attempt=[1000*r['median_active_wall_seconds']/r['attempts'] for r in panel]
    per_complete=[1000*r['median_active_wall_seconds']/r['completions'] for r in panel]
    report=f'''# HLE full Crux — C4 report v1

23 September 2026 · **C4 complete under its bounded acceptance gate · 4/7 milestones complete.**

The five required connected families now consume generated intermediate outputs. Explicit context transfer qualifies a model with local evidence, and paid parent review makes completion accountable to exact child results. Seven matched semantic controls change the later result at equal focus-operation spending. **Three milestones remain. Next: C5 — Shell formation and development across the map.**

This is a finite composition and nested-evidence contract in the consumable workshop. It does not close any of the 32 full-release cells. Route-wide Shell development, automatic selection, materially distinct settings and sustained mixed runs remain open under C5–C7. General nesting across independently owned child holons is also outside this contract.

## What changed, how, and what becomes possible

| Family | What changed | How it changed | Demonstrated later use |
| --- | --- | --- | --- |
| Theorize → Apply → Embody | An owned limit becomes a model, an actual four-unit use, and a retained limit of two. | Apply consumes the exact generated model. Embody consumes the paid-read observation of the actual event. | A changed demand selects two. Altering the model changes the material history and later selection to five. Returning to I restores neither stock nor spending. |
| Share → Commune → Identify | A previously shared cap of two becomes a renewed cap of one, with unequal positions retained. | A new offer names the exact shared prior. A separately paid reply feeds Commune, whose generated output feeds personal Identify. | Later choice uses one; preserving the earlier limit in the semantic control produces two. |
| Coordinate → Mobilize | Actual observed supply becomes a shared participation limit and two units of real consumption. | Mobilize consumes the exact Coordinate output under current uptake and authority. | Later work observes four remaining; the altered shared limit leaves five. |
| Institutionalize → Educate | An exact ratified rule becomes jointly understood by a receiver with its own larger limit. | Paid votes refer to the same draft. Its generated rule is offered, answered and taught within the original group. | The learner proposes two on a changed demand; altering the rule changes its answer to one. Teaching grants no practiced skill. |
| Organize → Integrate → Apply | Observed limits of six and two become one conjunctive system retaining both sources. | Separate generated Organize models enter paid Integrate. Apply consumes the combined constraint. | Consumption leaves four units; removing the tighter constraint leaves two. |
| Parent review and release | A model becomes eligible for use only when its declared child obligations are complete. | Paid receipt reads and exact child outputs support a parent record with distinct-operation spending. | A released model selects three; a matched blocked-parent intervention selects zero. A genuine cancelled-child case also permits zero and passes audit. |
| Context transfer | A source model with cap five becomes a qualified model with cap one in a different context. | Transfer consumes the owned source, local owned intention and a real local stock observation, retaining the source context. | A changed demand selects one; removing the local qualification selects four. Authority is not copied across contexts. |

The values below are selected/proposed amounts or observed remaining stock, **healthy / semantic control**. They are consequences of each case, not a common scale of development.

| Case | Later amount | Matched focus work units |
| --- | ---: | ---: |
{chr(10).join(cases)}

Each pair has the same initial world, content, resources, participants, recipe and focus spending. The evaluator intervenes only at the final defining semantic step of the designated focus operation. Downstream work can differ because the content differs. These interventions deliberately violate the semantic contract; the independent raw auditor rejects all seven. The extra cancelled-child witness is a valid blocked outcome, not an ablation.

## Implementation and parent accountability

Four new `crux_composition_` modules provide immutable requests, pure content transformations, paid runtime integration and independent reconstruction. Eight recipes cover a renewed Commune offer, both Commune faces, both Integrate faces, context transfer, parent review and release. All retain the fixed Crux route names and paid F/F or N/N return paths. No new formal edge is introduced.

The first semantic step creates scoped intermediate work; the second consumes that exact intermediate. C4 outputs enter the inherited generated-output indexes so C3 consumers can use them under their own schema, scope, access and authority checks. A numeric allocation model is not silently cast into the distinct C2 maintenance-interface schema. Existing C2 and U9 mechanisms retain their contracts.

A parent names exact terminal child-operation revisions, their accessible outputs and any claimed handoff links. It pays to read actor, context, status, spending and result fields. A link needs compatible endpoints **and** the exact upstream output among the downstream sources. Independent siblings may be reviewed without being called a connected circuit. Endpoint equality cannot substitute another history.

The current parent certifies **one actor's own child operations in a common context and target**. Other participants contribute through paid addressed exchanges, votes and transitive consent dependencies. A review operation can succeed while its declared parent outcome remains blocked. Required cancelled, materially failed or declined children block that outcome. Current stance, group and source revisions remain necessary for completion and later release.

Each parent retains direct children and a union of exact descendant-operation references. Shared descendants in a diamond appear once in cited spending. A parent pays for its own review without charging its children again. `cited_spending` covers declared descendants; it is not the total cost of all setup, supporting reads and exchanges. Wallet and raw-transaction totals account for that wider work separately.

Release accepts an exact owned model child of a current complete parent. A parent summary is not itself an executable model and grants no competence. Higher-level review can certify a lower parent; the depth benchmark still releases the first parent's direct model. Increasing depth therefore measures evidence review, not newly demonstrated capacity at every level.

Only addressed C4 public messages can be disclosed. Private generated content cannot be imported as authored input. A C4 Commune expenditure attempt consumes its exact actor/offer/reply exchange at start. Cancellation, later failure and checkpoint restoration preserve that consumption; another commitment requires a new exchange.

Limits are eight inputs, eight direct children, four nested levels, 64 distinct cited operations, two social members and demands of 1–1000. Within this limit, ancestor evidence and its paid review grow with cited work. There is no arbitrary-depth or constant-total-storage claim.

## Validation and retained failures

| Gate | Recorded result |
| --- | --- |
| Regression population | **554 distinct passing methods**: 531 inherited C1–C3/U2–U14 methods and 23 C4 methods; zero failures, errors or skips in the accepted combined population. |
| Execution form | An interrupted frozen-source run plus explicitly recorded continuations, **not one uninterrupted process**. Source hashes match before and after continuation. The original log-only prefix lacks retained individual timing; continued methods retain timings. No aggregate run duration is claimed. |
| Type coverage | Five families × sixteen initiating Model A types = **80 circuit/type cases**. Every circuit consumes generated outputs and reviews exact child evidence. This is not full composition coverage of all 32 cells in every setting. |
| Causal reconstruction | **Seven pairs / fourteen raw witnesses**, plus one independently audited cancelled-child witness. All fifteen restore exactly using the appropriate healthy or intervention engine. |
| Interrupted progression | **Eight recipes × three boundaries = 24 configurations**: one paid unit, first semantic result and ready before commit. Continued checkpoints match exactly. |
| Failure and invalidation | Every-recipe cancellation, exhaustion, child cancellation, real material failure, changed membership, actual stance withdrawal and stale successful-parent reuse. Performed work and historical effects remain. |
| Meaning and authority | Wrong schema/scope, unread or foreign child, fabricated output, disconnected handoff, equal-endpoint substitution, unsupported coupling, borrowed competence, repeated renewal and attempted cross-context authority. |
| Accounting and depth | Shared-descendant diamond, exact operation charges, depths one/two/four and rejection beyond the declared bound. Mixed polarities, source differences, conflicts and provenance remain addressable. |
| Independent audit | Reconstructs C4 postconditions, paid thresholds, input handoffs, child claims, public audiences, current dependencies and distinct spending from raw records. It imports no C4 executor, transformer or selector. Raw mutations are rejected; display labels alone do not change meaning. |
| Preservation | All **{frozen:,}** frozen baseline files and **{inherited_runtime} of {inherited_runtime+2}** inherited native runtime files remain byte-identical. Only the two declared runtime hooks and the root README change among inherited source files. Historical legacy-suite results are inherited evidence, not newly rerun claims. |

Early smoke attempts exposed a collision with the existing U9 module names and a missing `primitive="bind"` constructor field. The original U9 files were restored byte for byte; new names use the `crux_composition_` prefix. Both failed probes remain retained. The initial 22-method C4 evaluation had two fixture assertion failures: the inherited schema retained `binding=None`, while the assertions expected an absent field. Corrected assertions passed separately; the failed run remains failed.

A later review probe found that the same renewal exchange could mint another commitment under a new operation key. The runtime and independently implemented auditor now consume that exchange at attempt start, including cancellation and replay. The twenty-third C4 test covers completed/cancelled reuse and restoration. The review amendment changes no performance tolerance. Earlier witness exports remain under `witnesses_initial`; accepted witnesses were re-exported from the final guarded source.

An earlier full regression launch produced no usable completion summary and is retained as `tests_interrupted`. The subsequent run lost its transport, and a later continuation was interrupted by the user. The resume tool retained explicit per-method passes and reran only methods lacking a recorded result. The final population is identified as combined execution. Detailed failures and source identities remain in the development record and evidence.

## Measured cost

The prospective protocol retained the original **1.5× unchanged-contract** and **1.75× fixed-history** tolerances. No failed timing sample was discarded or tolerance relaxed. All **36 sequential isolated workers** are retained: 30 timing workers and six separate traced workers. Source identities remain unchanged during measurements.

The original C3 executor layers and the C4 wrapper run the same five-route C3 panel in three fresh workers each. Median active time was **{ref['median_active_wall_seconds']*1000:.1f} ms** for C3 and **{adapt['median_active_wall_seconds']*1000:.1f} ms** for C4: a ratio of **{m['c3_ratio']:.3f}**, within the 1.5× limit. Outcomes and modeled work match. This is a regression check, not a speedup claim.

The new fixed panel runs five independent connected families, including content retention, actual exchanges, child receipt reads, parent review and later consumers. Initial engine construction is excluded. Checkpoint creation, restore and audit are separate. Each worker starts a fresh Python process; restore constructs fresh engines inside that worker, not an operating-system cold start. Peaks are the largest independent case; other panel costs sum the cases.

| Inactive history | Records per case | Active median (ms) | Restore (s) | Audit (s) | Largest incremental peak (MiB) | Raw checkpoints (MiB) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(tab)}

Every fixed panel has **{q['attempts']} counted C3/C4 attempts, {q['completions']} completions and {q['semantic_steps']} paid semantic steps**, with **{q['modeled_active_work']} modeled active work units** and **{q['modeled_total_work']} including setup**. Inherited native supporting operations are included in spending but outside this C3/C4 attempt count. All five demonstrated outcomes remain `[2, 1, 4, 2, 4]` across sizes and shapes.

Traced access stays at **{q['memory']['resolve_calls']:,} store resolutions** and **{q['memory']['unique_refs_sum']:,} distinct references summed across cases**. The maximum/minimum active median ratio is **{m['history_ratio']:.3f}**, within 1.75×. Exact history and replay cost still grow.

Including support and downstream work, the panel costs **{min(per_effect):.1f}–{max(per_effect):.1f} ms per demonstrated family consequence**, **{min(per_attempt):.1f}–{max(per_attempt):.1f} ms per counted attempt**, and **{min(per_complete):.1f}–{max(per_complete):.1f} ms per counted completion**. These are workload-normalized costs, not universal prices for a route. Full CPU, checkpoint, compressed-byte, allocation and individual-case measurements remain in the raw worker rows.

| Separately varied dimension | Size | Active median (ms) | Modeled active work | Restore (s) |
| --- | ---: | ---: | ---: | ---: |
{chr(10).join(growth)}

Depth varies with two initial child models. Direct child count varies at depth one. Both retain the same downstream selection of three. Larger populations and alternative-search scaling are unassessed. Full replay is a substantial cost beyond active execution; exact checkpoint storage and audit add further cost. C4 introduces no history deletion or compaction. Future optimization should preserve the exact continuation, access, authority and constituent evidence measured here.

## Delivery and next step

The source README gives reproduction commands. `tools/verify_c4_delivery.py` reconstructs acceptance from recorded tests, evaluated source identities, fifteen raw witnesses, thirty-six workers and inherited preservation. The evidence package retains initial failures, the review amendment and accepted results separately. The self-contained inspector displays the three-question view, exact child content, references, paired consequences and measurement rows.

The 32-cell ledger records the exact route/polarity appearances in the five principal circuits, rather than granting every cell blanket composition credit. It preserves inherited C2/C3 evidence and leaves all full-release cells open. The context change uses the same consumable-workshop semantics; it is not a second materially distinct setting.

**Next: C5 — Shell formation and development across the map.** Extend route-aware deformation, supported formation, scoped correction, recurrence and reownership evidence across all 32 cells. C6 then addresses situated selection and transfer; C7 closes the sustained full-release gate only when its complete evidence ledger is satisfied.
'''
    (ROOT/'docs/HLE_Full_Crux_C4_Report_v1.md').write_text(report)
    spec=(ROOT/'docs/HLE_Full_Crux_Build_Specification_v5.md').read_text()
    spec=spec.replace('Version 5 · 22 September 2026','Version 6 · 23 September 2026')
    old=next(line for line in spec.splitlines() if line.startswith('**Status:**'))
    new='**Status:** C1–C4 are complete under their bounded milestone gates; C5–C7 remain open. C4 connects the five required families through generated outputs, explicit contextual qualification and paid parent review of exact child evidence. This does not close the full-release requirements for any of the 32 cells.'
    spec=spec.replace(old,new+'\n\nThe C4 release records 554 distinct passing methods across an interrupted frozen-source run and explicit continuations, 80 circuit/type cases, seven causal pairs plus a lawful cancelled-child witness, 24 interrupted continuation configurations, and 36 isolated measurement workers. Its source identities, initial failures and renewal-review amendment remain explicit. Bounded parents certify one actor’s child operations; general cross-owner nesting remains open.')
    spec=spec.replace('nested outcomes agree with constituent evidence | Open |','nested outcomes agree with constituent evidence | Complete under bounded C4 gate |')
    spec=spec.replace('## 11. C1, C2 and C3 completion, and the next build','## 11. C1–C4 completion, and the next build')
    old=next(line for line in spec.splitlines() if line.startswith('C1 supplies a minimal scoped condition language'))
    spec=spec.replace(old,'C1 supplies a minimal scoped condition language and the common executor. C2 supplies eight bounded self-route contracts; C3 supplies all 24 crossing contracts in a finite consumable-workshop setting. C4 now connects generated outputs across all five required families and makes a bounded parent outcome accountable to exact compatible child results, current authority and distinct-operation spending. Context transfer requires actual local evidence; parent summaries and teaching confer no practiced competence. Failure, withdrawal, mixed polarities and historical material consequences remain visible.\n\nThe full expressive language, general cross-owner nesting, route-wide Shell extension, autonomous selection and distinct semantic settings remain open. **Next: C5 — Shell formation and development across the map.** Supply route-aware deformation/control evidence for all 32 cells, distinguish supported effect kinds from operationalized diagnostic signs, and preserve scoped correction, practice, recurrence and reownership evidence. C4 completion is not automatic credit for those gates.')
    amendment='''### Version 6 implementation update

- HLE_Full_Crux_C4_Report_v1.md and C4 source/evidence: five generated connected families, contextual qualification and the bounded parent/child contract; 554 distinct passing methods across recorded stages, seven causal pairs plus one lawful blocked witness, and 24 interrupted recipe configurations.
- C4_Protocol_v1.json and measurements/summary.json: 36 isolated workers, unchanged original-C3 comparison, shared/unique inactive-history panels, and separate depth/child-count growth. Original performance tolerances remain unchanged; no speedup or bounded-total-history claim.
- C4_Review_Amendment_v1.json: one attempt per exact renewed offer/reply exchange, including cancellation and restoration. Initial smoke failures, fixture assertion failures, interrupted evaluations and earlier witness exports remain retained.
- C4_Progress_Ledger_v1.json records exact circuit/polarity evidence and limitations. All 32 full-release cells remain open for applicable C5–C7 and distinct-setting requirements. Current parents certify one actor's own children; this does not prove general cross-level equivalence.
- Formal route names, polarity definitions and theoretical authority are unchanged. New composition algorithms and paid parent review are declared engineering constructions.

'''
    spec=spec.replace('### Version 5 implementation update',amendment+'### Version 5 implementation update')
    old=next(line for line in spec.splitlines() if line.startswith('**Implementation progress'))
    spec=spec.replace(old,'**Implementation progress under this specification: 4/7 milestones complete. C1–C4 passed within their declared domains. Three milestones remain; C5 — Shell formation and development across the map — is next.**')
    (ROOT/'docs/HLE_Full_Crux_Build_Specification_v6.md').write_text(spec)
    ledger=copy.deepcopy(read(ROOT/'C3_Progress_Ledger_v1.json'))
    ledger.update(milestones_complete=4,milestones_total=7,next='C5',full_release_cells_complete=0,
        c4_gate='Complete under bounded composition/nested-evidence contract; no blanket cell completion',
        c4_scope='One consumable-workshop language; one actor owns child operations; paid public social contributions; no general cross-owner nesting',
        c4_counts=dict(tests=554,circuit_type_cases=80,causal_pairs=7,raw_witnesses=15,continuation_configurations=24,measurement_workers=36))
    for cell in ledger['cells']:
        appearances=[]
        for i,row in enumerate(healthy[:5],1):
            if any(c['route']==cell['route'] and c['polarity']==cell['polarity'] for c in row['children']):
                appearances.append(dict(family=row['name'],evidence=f'evidence_c4/witnesses/{i:02d}-healthy/result.json',
                    control=f'evidence_c4/witnesses/{i:02d}-control/result.json'))
        cell['inherited_evidence']=cell.pop('evidence')
        cell['inherited_evidence_location']='C3_Progress_Ledger_v1.json and its evidence_c3 or historical C2 evidence'
        cell['c4_connected_family_appearances']=appearances
        cell['nested_accountability']='Exercised as an exact child in the bounded C4 family panel' if appearances else 'This route/polarity is not a principal child in the C4 family panel; full-release coverage remains open'
        cell['c4_measured_costs']='evidence_c4/measurements/summary.json; family-level workload, not per-cell price' if appearances else 'No new per-cell C4 measurement'
        cell['full_release_complete']=False
        cell['remaining_requirements']=['C5 Shell evidence','C6 automatic selection and distinct-setting transfer','C7 complete sustained-release assessment']
    write(ROOT/'C4_Progress_Ledger_v1.json',ledger);write(E/'C4_Progress_Ledger_v1.json',ledger)
    html=ROOT/'docs/HLE_Full_Crux_C4_Inspector_v1.html'
    subprocess.run([sys.executable,str(ROOT/'tools/build_c4_inspector.py'),'--out',str(html)],check=True)
    content=html.read_text().replace('Passing methods in the final regression run','Passing methods across recorded regression stages')
    content=content.replace('<div class="controls">','<p class="muted">Regression evidence combines an interrupted frozen-source run with recorded continuations. The three answers below describe the healthy transformation; the selected branch supplies its child records and audit result.</p><div class="controls">',1)
    html.write_text(content)
    print(json.dumps(dict(report=True,specification_version=6,ledger_cells=len(ledger['cells']),inspector=True)))

if __name__=='__main__':main()
