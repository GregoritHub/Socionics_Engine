"""Package an honestly held C7 release candidate from executed evidence."""
import sys,json,hashlib,zipfile,html,statistics,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];E=ROOT/'evidence_c7';WORK=ROOT.parents[1];OUT=Path(sys.argv[1]);OUT.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,indent=2))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
reg=read(E/'regressions/summary.json');unit=read(E/'feedback_test/summary.json');fix=read(E/'regression_u11_final/summary.json')
assert unit['passed'] and fix['passed']
methods={r['test_id'] for r in unit['rows'] if r['status']=='passed'}
packages=[]
for p in reg['packages']:
    s=fix if p['package']=='tests_u11' else p['summary']
    assert s and s['passed'] and all(r['status']=='passed' for r in s['rows']),p['package']
    methods.update(x['test_id'] for x in s['rows'] if x['status']=='passed');packages.append(dict(package=p['package'],tests=s['tests'],passed=True,evidence='regression_u11_final/summary.json' if p['package']=='tests_u11' else 'regressions/'+p['package']+'/summary.json'))
assert len(packages)==20
sust=read(E/'sustained_v2/summary.json');amend=read(E/'Source_Scope_Amendment_v1.json');raw=read(E/'sustained_v2/raw_verification.json');cost=read(E/'measurements/summary.json')
assert amend['runtime_and_executed_dependencies_unchanged'] and raw['passed'] and cost['passed']
oldraw=read(WORK/'inherited/evidence_c6/raw_verification_final.json');assert oldraw['passed']
stopraw=read(E/'default_stop/raw_verification.json');assert stopraw['passed']
pc=read(E/'population_costs/accepted_summary.json');assert pc['passed']
# Reverify source scopes, excluding only the explicitly documented, unimported test.
for folder in ('sustained_v2','population_costs'):
    src=read(E/folder/'source.json')
    changed=[k for k,v in src.items() if sha(ROOT/k)!=v]
    assert changed==['tests_c7/test_population.py'],changed
old=read(ROOT/'C6_Progress_Ledger_v1.json');ledger=[]
for row in old:
    row=dict(row);row['c7_release_status']='open';row['full_release_complete']=False
    row['settings_gate']=dict(required=2,established=1,status='open',note='Inherited canonical bounded setting; renamed resources, cap changes and extra repetitions receive no second-setting credit.')
    row['independent_reconstruction']='C6 raw panel and 512 type worlds reverified on current unchanged native runtime'
    row['sustained_scope']='Theorize/Understand numeric content only; no route-wide new semantic domain established'
    row['controls_scope']='C6 choice-withholding raw controls; semantic ablation and access/authority/Shell controls additionally rerun in inherited test suites'
    row['cost_scope']='Matched unchanged native API measured; scheduler stopping modes have different work and are not a speedup comparison'
    row['remaining']=['A second materially different applicable semantic setting and actual downstream use','Integrate that coverage with the final section 9 release ledger']
    ledger.append(row)
write(ROOT/'C7_Progress_Ledger_v1.json',ledger);write(E/'C7_Progress_Ledger_v1.json',ledger)
manifest=dict(milestone='C7',release_complete=False,progress='6/7',remaining_milestones=1,
    decision='Release held: second materially different semantic setting per cell unestablished',
    final_distinct_passing_methods=len(methods),packages=packages,c7_methods=unit['tests'],
    sustained_worlds=6,sustained_episodes_per_actor=24,sustained_native_completions=sum(x['completed_native'] for x in sust['rows']),
    generated_output_reuses=sum(len(x['generated_output_reuses']) for x in sust['rows']),
    sustained_routes=sorted({k for x in sust['rows'] for k in x['recipes']}),
    raw_population_worlds=raw['worlds']+stopraw['worlds'],reverified_c6_worlds=oldraw['worlds'],native_measurement_workers=cost['workers'],population_measurement_workers=len(pc['rows']),
    source_scope_amendment='Source_Scope_Amendment_v1.json',native_runtime_changed_from_C6=False,
    remaining_limits=['32 cells require second semantic setting','sustained panel mostly repeats existing interpretation','supplied initial demands','two-member shared semantic contracts','one population session per engine; exact restore supported'])
write(ROOT/'C7_Execution_Manifest_v1.json',manifest);write(E/'C7_Execution_Manifest_v1.json',manifest)
report=f'''# HLE Full Crux — C7 release-candidate report

23 September 2026

**Decision: hold the full-Crux release. Progress remains 6/7; C7 is not complete.**

The candidate implements sustained participant scheduling, exact continuation,
independent population reconstruction, and an explicit stop for unchanged retained
content. It does not establish a second materially different applicable semantic
setting for every route/polarity cell, as required by specification §9.3. All 32
full-release cells remain open. A complete test matrix cannot substitute for this
missing content evidence.

## What changed, how, and what becomes possible

`Population` now advances independently owned participant demands in fair,
bounded turns. Each participant uses the existing paid C6 comparison, Shell
admission and native execution. Actual material outcomes can return through a
separate paid reading turn. Checkpoints retain the fairness cursor, partial work,
feedback and spending. These changes make a multi-participant continued session
runnable without a scenario supplying a route order.

The diagnostic runs exposed repetition: a participant generated a model and then
repeatedly retained the same interpretation. The default scheduler now stops the
current demand after two equal qualifying scoped retained results. Both outputs,
all paid work and their distinct histories remain available. This is an explicit
stopping policy, not a claim that the interpretation is correct or that all future
development is exhausted. Diagnostic mode disables the stop to make the behavior
visible across the predeclared horizon.

The independent population auditor reconstructs fairness, wallet charges, result
references, episode counts and repetition summaries from committed records. It
does not invoke the scheduler or selector. The inherited independent validators
continue to check semantic postconditions, paid content, access and authority.

## Executed evidence

| Panel | Observed result |
| --- | --- |
| Current C7 test methods | {unit['tests']} passing |
| Distinct passing methods across U2–U14 and C1–C7 | {len(methods)} |
| Sustained diagnostic worlds | 6: seeds 17/43/89 × 2/3 mixed-type actors |
| Horizon | 24 completed episodes per actor; no replenishment |
| Native completed movements | {manifest['sustained_native_completions']} |
| Later native uses of generated outputs | {manifest['generated_output_reuses']} |
| Sustained route coverage | Theorize expenditure and Understand expenditure |
| Independent raw population reconstructions | {raw['worlds']+stopraw['worlds']} (six mid-run, six final diagnostic and one default-stop checkpoint) |
| Reverified inherited C6 raw worlds | {oldraw['worlds']}: {oldraw['valid_worlds']} ordinary and {oldraw['deliberate_ablations']} deliberate choice controls |
| Inherited automatic type matrix | 512 movement/type cases; 32-cell downstream panel remains separate |
| Machine-cost workers | {cost['workers']} native + {len(pc['rows'])} population |

The 345 generated-output uses are mostly repeated use of the same model. They
are **not 345 new capacities**. These populations do not establish route-wide
sustained development, spontaneous goal formation or participant-generated new
semantic domains. The ten C7 tests cover exact interrupted continuation, fairness,
foreign demands, finite horizons, paid material feedback, exhaustion, repeated
content stopping and rejection of fabricated audit summaries.

## Efficiency and stopping

The unchanged native API's median time ratio is {cost['reference_ratio']:.3f}× the
byte-preserved C5 reference (tolerance 2.0×). The largest/smallest active-history
median ratio is {cost['history_ratio']:.3f}× (tolerance 3.0×), with shared and unique
unread histories of 0/100/1,000 records. Matched direct worlds and access are
identical. Alternatives are separately varied at 1/4/16. Setup, active timing,
tracing, cold restoration and audit remain separate measurements. Workers run in
separate processes on a shared host; this is not a dedicated-machine benchmark.

The stopping comparison below intentionally performs different work. It measures
avoided repetition, not a semantics-preserving speedup. Distinct exact scoped
payloads are a diagnostic count; equal payloads do not erase different histories
or establish new competence. Cost per demonstrated new capacity is unassessed.

| Actors | Policy | Native completions | Distinct retained payloads | Modeled work | Median active | Cold restore | Raw audit |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
'''
for mode in ('stop','monitor'):
    for n in (2,3):
        rr=[x for x in pc['rows'] if x['mode']==mode and x['actors']==n and not x['traced']];r=rr[0]
        report+=f"| {n} | {mode} | {r['completed_native']} | {r['distinct_scoped_retained_payloads']} | {r['modeled_work']} | {statistics.median(x['wall_seconds'] for x in rr):.3f} s | {statistics.median(x['restore_seconds'] for x in rr):.3f} s | {statistics.median(x['audit_seconds'] for x in rr):.3f} s |\n"
report+='''
The long-run native work and exact-history retention remain nonconstant. Each
mode/size has two timing workers and one allocation-traced worker. Increasing
owned content still increases candidate collection work within C6's declared
128-content/64-bundle limits; the diagnostic fixture uses 16 bundles per cell.
Earlier composition-depth and dependency measurements remain inherited evidence,
not new measurements by this candidate. No optimization gain is claimed.

## Failures, corrections and execution scope

1. The first population's summary exporter rejected machine-time floats in the
   strict C6 content codec. Summary JSON was corrected; runtime serialization was
   unaffected. The failure log and saved worlds remain included. A later raw-verification summary also needed explicit ObjectRef serialization; that exporter failure and its corrected raw verification are retained.
2. Early population fixtures omitted secondary actors' Shell configuration and
   neutral opportunity evidence. Those worlds completed no native movements.
   Corrected fixtures and explicit per-actor native-completion assertions prevent
   a vacuous horizon from passing. An interrupted attempt remains preserved.
3. Longer corrected runs revealed repetitive interpretation. The v2 stopping
   policy is an intentional new scheduler contract, separately tested and
   measured against monitoring mode. It does not modify native route semantics.
4. One U11 regression process passed all assertions but failed its whole-source
   immutability check while the new population code was being edited. A separate
   final 40-method U11 run passed on unchanged source. Final distinct counts use
   that run rather than calling the earlier process clean.
5. The broad sustained/cost source manifests also included an unimported unit-test
   module that gained a feedback test during execution. Their original source
   guard failures remain visible. The scoped amendment checks that runtime,
   imported fixtures and evaluator are byte-identical; only the unexecuted test
   module differs. Raw saved worlds are independently rechecked, and the final
   unit suite tests the delivered source. This is not presented as one clean,
   uninterrupted whole-tree run.

The standalone inspector is checked for its 32 cells, data, filtering and evidence
expansion in a DOM harness. Local Chromium is unavailable; pixel rendering is not
claimed as verified.

## Remaining C7 work

The current crossing content is largely scalar resource limits, assent and
bounded organization; the self-routes additionally handle condition and procedure
interfaces. A new resource name, changed cap, different type or longer repetition
is insufficient to establish the second semantic setting.

1. Implement and independently validate materially different content contracts
   that support a second applicable setting for every cell. Ground that setting
   in actual material maintenance, shared commitments and teaching/procedure use;
   keep personal assent, authority and practiced ability distinct.
2. Produce changed-output/downstream-use and matched defining-step controls in
   those settings, then integrate them with the existing composition, Shell,
   autonomy, continuation and efficiency evidence in the 32-cell ledger.
3. Run the final sustained and regression assessment on the frozen candidate and
   close C7 only when every applicable §9 gate has passed.

Unrestricted human meaning, universal Shell diagnosis, general cross-owner
nesting and an unrestricted developmental trajectory remain research questions.
They are not silently promoted to release claims or newly added release gates.
'''
name='HLE_Full_Crux_C7_Release_Candidate_Report_v1.md';(OUT/name).write_text(report);(ROOT/'docs'/name).write_text(report)
spec=(WORK/'upload/HLE_Full_Crux_Build_Specification_v8(1).md').read_text().replace('Version 8 ·','Version 9 ·')
a=spec.index('**Status:**');b=spec.index('\n\n',a)
spec=spec[:a]+f"**Status:** C1–C6 remain complete under their bounded gates. C7 has a sustained-execution release candidate, but the full release is held. The candidate adds fair participant scheduling, paid feedback, exact continuation and unchanged-content stopping, with {len(methods)} distinct passing methods. Six diagnostic worlds complete 360 native movements but mostly repeat existing interpretation. All 32 cells still lack established second-setting coverage under §9.3. Progress remains 6/7; one milestone remains."+spec[b:]
spec+='''\n\n## C7 release-candidate assessment — 23 September 2026\n\nC7 is **open**. See HLE_Full_Crux_C7_Release_Candidate_Report_v1.md and the C7 ledger.\nSustained scheduling and reconstruction are implemented; repeated retained output\nis explicitly counted and can stop the current demand. The six diagnostic runs\nexercise Theorize/Understand expenditure, not all routes in a new domain.\n\nNext within C7: implement and evidence a second materially different applicable\nsemantic setting for all 32 cells, with real downstream consumers and causal\ncontrols; integrate the final §9 ledger and freeze/re-evaluate the release.\nNo milestone percentage or number of repeated outputs closes these missing gates.\n'''
(OUT/'HLE_Full_Crux_Build_Specification_v9.md').write_text(spec);(ROOT/'docs/HLE_Full_Crux_Build_Specification_v9.md').write_text(spec)
# Self-contained inspectable release view, without remote dependencies.
data=json.dumps(dict(manifest=manifest,ledger=ledger,sustained=sust['rows']),ensure_ascii=False).replace('<','\\u003c')
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>HLE · C7 release candidate</title><style>
*{box-sizing:border-box}body{margin:0;background:#101920;color:#e7eeef;font:16px/1.6 system-ui,sans-serif}main{max-width:1200px;margin:auto;padding:40px 24px}h1{font-size:40px;line-height:1.15;margin:12px 0}h2{margin-top:32px}.label{color:#84d5cf;letter-spacing:.12em;text-transform:uppercase;font-size:12px}.notice{border-left:4px solid #ffc378;background:#263039;padding:18px}.metrics{display:flex;flex-wrap:wrap;gap:12px;margin:22px 0}.metric{background:#1b2932;padding:14px 22px;flex:1;min-width:180px}.metric strong{display:block;font-size:28px}select,input,button{font:inherit;padding:8px;background:#263741;color:#fff;border:1px solid #617985;border-radius:4px}label{display:inline-block;margin:4px 20px 12px 0}details{border-top:1px solid #3a4b55;padding:12px 0}summary{cursor:pointer;font-weight:650}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#17242d;padding:16px;font:12px/1.5 ui-monospace,monospace;max-height:500px;overflow:auto}.open{float:right;color:#ffc378}table{width:100%;border-collapse:collapse}th,td{text-align:left;border-bottom:1px solid #3a4b55;padding:8px}small{color:#b9c8ce}a{color:#84d5cf}.scroll{overflow:auto}@media(max-width:600px){h1{font-size:30px}.open{float:none;display:block}}</style><main>
<div class="label">HLE / evidence inspector</div><h1>C7 · sustained release candidate</h1><div class="notice"><strong>Release held · 6/7 milestones complete.</strong><br>All 32 cells still need a second materially different applicable semantic setting. Repeated interpretation is visible here; it is not counted as new capacity.</div><div class="metrics" id="metrics"></div>
<h2>What changed</h2><p>Fair participant turns, paid material feedback, exact continuation, independent population audit, and an explicit stop after unchanged retained content. The default stop preserves both paid outputs and their histories.</p><h2>Sustained diagnostic worlds</h2><p>Three seeds × two population sizes; 24 episodes per actor with the repetition stop deliberately disabled. Initial demands are supplied. These worlds exercise Theorize and Understand expenditure.</p><div class="scroll"><table><thead><tr><th>World</th><th>Actors</th><th>Completed</th><th>Output uses</th><th>Failures</th></tr></thead><tbody id="worlds"></tbody></table></div>
<h2>The 32-cell release ledger</h2><label>Route <select id="route"><option value="">All routes</option></select></label><label>Face <select id="face"><option value="">Both polarities</option><option>accumulation</option><option>expenditure</option></select></label><p id="count"></p><div id="cells"></div>
<h2>Evidence boundary</h2><p>Cell details retain C6's exact native, choice and downstream references. Their raw worlds have been reverified. Semantic ablation, access, consent, composition and Shell tests are separate from the choice-withholding controls. Source-scope amendments and initial failed runs remain in the evidence archive.</p><p>Use the report for costs and remaining work. The source package contains runnable evaluators and independent raw verifiers. This file is a standalone inspector; it does not execute the engine.</p></main><script id="data" type="application/json">DATA</script><script>
const d=JSON.parse(document.getElementById('data').textContent);const el=id=>document.getElementById(id);const text=(tag,s)=>{const x=document.createElement(tag);x.textContent=s;return x};
for(const [v,k] of [[d.manifest.final_distinct_passing_methods,'passing methods'],[360,'native completions'],[345,'generated-output reuses'],[0,'fully closed release cells']]){const x=text('div','');x.className='metric';x.append(text('strong',v),text('span',k));el('metrics').append(x)}
for(const r of d.sustained){const tr=document.createElement('tr');for(const v of [r.case,r.actors,r.completed_native,r.generated_output_reuses.length,r.failures.length])tr.append(text('td',v));el('worlds').append(tr)}
for(const n of [...new Set(d.ledger.map(x=>x.name))]){const o=text('option',n);o.value=n;el('route').append(o)}
function render(){el('cells').replaceChildren();const rows=d.ledger.filter(x=>(!el('route').value||x.name===el('route').value)&&(!el('face').value||x.face===el('face').value));el('count').textContent=rows.length+' cells shown · every full-release status remains open';for(const r of rows){const box=document.createElement('details');const s=text('summary',r.name+' · '+r.face);const state=text('span','Open: second setting');state.className='open';s.append(state);box.append(s);box.append(text('p','What changed: '+r.what_changed));box.append(text('p','Afterward: '+JSON.stringify(r.afterward)));box.append(text('p',r.settings_gate.note));box.append(text('pre',JSON.stringify(r,null,2)));el('cells').append(box)}}
el('route').addEventListener('change',render);el('face').addEventListener('change',render);render();
</script></html>'''.replace('DATA',data)
(OUT/'HLE_Full_Crux_C7_Inspector_v1.html').write_text(page)
# Update runnable entry instructions; no external dependencies for runtime.
(ROOT/'README.md').write_text('''# HLE full Crux — C7 release candidate\n\nRelease held. Progress remains 6/7. Read docs/HLE_Full_Crux_C7_Release_Candidate_Report_v1.md and docs/C7_Architecture_and_Scope_v1.md.\n\nPython 3 and standard library suffice. From this root:\n\n```sh\npython tools/test_c6.py new-c7-tests tests_c7\npython tools/regress_c7.py new-regression\npython tools/evaluate_c7.py new-sustained\npython tools/measure_c6.py new-native-costs\npython tools/measure_population_c7.py new-population-costs\n```\n\nExtract the evidence archive here to independently check saved raw worlds:\n\n```sh\npython tools/verify_c7_raw.py evidence_c7/sustained_v2\npython tools/verify_c6_delivery.py evidence_c6\n```\n\nThe default `Population(engine, requests, episodes=24, quantum=32)` stops after two equal qualifying retained results. Pass `repeat_limit=None` explicitly for diagnostic repetition. Resume with `Population.restore(checkpoint)`. One population session owns its engine command namespace; a fresh scheduler on the same engine is not supported. Native C6 APIs and checkpoint format are unchanged.\n\nEarlier failed attempts, broad source-guard failures and scoped amendments remain evidence, not clean passes. All 32 full-release cells retain the second-semantic-setting gate.\n''')
# Save original attached evidence and this turn's re-verification together.
shutil.copy2(WORK/'inherited/evidence_c6/raw_verification_final.json',E/'Inherited_C6_Reverification_v1.json')
write(E/'Input_Artifacts_v1.json',{p.name:sha(p) for p in (WORK/'upload').iterdir() if p.is_file()})
write(ROOT/'C7_Source_File_Manifest_v1.json',{str(p.relative_to(ROOT)):sha(p) for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and 'evidence_c7' not in p.parts and p.name!='C7_Source_File_Manifest_v1.json'})
shutil.copy2(ROOT/'C7_Source_File_Manifest_v1.json',E/'C7_Delivered_Source_Manifest_v1.json')
for filename,base,arcroot in [('HLE_Full_Crux_C7_Source_v1.zip',ROOT,'HLE_Full_Crux_C7_Source_v1')]:
    temporary=OUT/(filename+'.partial')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,6) as z:
        for p in base.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and 'evidence_c7' not in p.parts:z.write(p,str(Path(arcroot)/p.relative_to(base)))
    with zipfile.ZipFile(temporary) as check:assert check.testzip() is None
    temporary.replace(OUT/filename)
temporary=OUT/'HLE_Full_Crux_C7_Evidence_v1.zip.partial'
with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,6) as z:
    for base,prefix in [(E,'evidence_c7'),(WORK/'inherited/evidence_c6','evidence_c6')]:
        for p in base.rglob('*'):
            if p.is_file():z.write(p,str(Path(prefix)/p.relative_to(base)))
with zipfile.ZipFile(temporary) as check:assert check.testzip() is None
temporary.replace(OUT/'HLE_Full_Crux_C7_Evidence_v1.zip')
write(OUT/'HLE_Full_Crux_C7_Delivery_Checksums_v1.json',{p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in OUT.iterdir() if p.is_file() and 'Checksums' not in p.name})
print(json.dumps(manifest,indent=2))
