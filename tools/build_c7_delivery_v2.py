"""Build the second-setting report/ledger/inspector from completed evidence.

Usage: python tools/build_c7_delivery_v2.py OUTPUT_DIRECTORY PRIOR_EVIDENCE_ZIP
Extract current evidence_c7_settings under the source root before rebuilding.
"""
import json,sys,hashlib,zipfile,statistics,re,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence_c7_settings'
def read(path):return json.loads(path.read_text())
def write(path,value):path.write_text(json.dumps(value,indent=2))

def build(out,prior):
    out.mkdir(parents=True,exist_ok=True)
    unit=read(E/'unit_delivery/summary.json');matrix=read(E/'matrix_delivery/summary.json')
    raw=read(E/'matrix_delivery/independent_raw_verification.json');reg=read(E/'regression_delivery/summary.json')
    costs=read(E/'cost_delivery/summary.json');native=read(E/'native_cost_delivery/summary.json')
    assert all(x['passed'] for x in (unit,matrix,raw,reg,costs,native))
    frozen=read(ROOT/'C7_Second_Setting_Source_Freeze_v4.json')
    assert all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in frozen.items())
    for directory in ('unit_delivery','matrix_delivery','regression_delivery','cost_delivery','native_cost_delivery'):
        executed=read(E/directory/'source.json')
        assert all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in executed.items()), directory+' source differs'
    verified={r['file']:r['sha256'] for r in raw['rows']}
    for row in read(E/'matrix_delivery/matrix.json')+read(E/'matrix_delivery/controls.json'):
        assert verified[row['raw']['file']]==row['raw']['sha256'], 'raw record does not match evaluated witness'

    inherited=sum(row['summary']['tests'] for row in reg['packages']);total=inherited+unit['tests']
    panel=read(E/'matrix_delivery/matrix.json');controls=read(E/'matrix_delivery/controls.json')
    old=read(ROOT/'C7_Progress_Ledger_v1.json');ledger=[]
    contracts={}
    for line in (ROOT/'docs/C7_Second_Setting_Contract_v1.md').read_text().splitlines():
        if line.startswith('| ') and not line.startswith('| Route'):
            cells=[x.strip() for x in line.strip('|').split('|')]
            if len(cells)==4:contracts[cells[0]]=cells[1:]
    for previous in old:
        name,face=previous['name'],previous['face'];w=next(x for x in panel if (x['type'],x['route'],x['face'])==('iee',name,face))
        c=next(x for x in controls if (x['route'],x['face'])==(name,face));case=contracts[name][face=='expenditure']
        ledger.append(dict(name=name,face=face,settings_gate=dict(required=2,established=2,status='passed',
            first='Inherited canonical condition/resource-cap/static-interface setting',second='Timed maintenance, role commitments, teaching and equipment handover'),
            what_changed=case,how_changed=dict(recipe='workflow-'+name.lower()+'-'+face+'-v1',source_inputs=w['source_inputs'],
                main_operation=w['main_operation'],output=w['output'],modeled_main_work=w['spent'],
                mechanism='Actor-paid native Fold steps, exact retained intermediate content, native material laws and reciprocal receiver work'),
            afterward=dict(consumer=w['consumer'],kind=contracts[name][2],next_task=w['after']['next_task'],next_action=w['after']['next_action'],
                question_completed=w['after']['completed'],question_clock=w['after']['clock'],owner_use=w['owner_use']),
            control=dict(spent=c['spent'],changed_downstream=c['changed_downstream'],matched_main_cost=True,
                fixed_downstream_question=True,next_task=c['after']['next_task'],owner_use=c['owner_use'],ordinary_audit_rejected=True,raw=c['raw']),
            second_setting_raw=w['raw'],type_cases=len([x for x in panel if (x['route'],x['face'])==(name,face)]),
            independent_raw_reconstruction=True,interruption_boundaries=3,full_release_complete=False,
            inherited=dict(what_changed=previous['what_changed'],how_changed=previous['how_changed'],afterward=previous['afterward'],
                automatic_selection=previous['automatic_selection'],evidence_scope='Canonical setting; retained as inherited evidence'),
            remaining=['Final joint section 9 assessment, including sustained execution and applicability of inherited selection/Shell evidence to new content']))
    write(ROOT/'C7_Second_Setting_Ledger_v1.json',ledger)
    write(E/'C7_Second_Setting_Ledger_v1.json',ledger)
    measured=[]
    for count in (2,4,8):
        samples=[x for x in costs['rows'] if x['tasks']==count and x['history']==0 and not x['shared'] and not x['traced']]
        measured.append(f"| {count} | {statistics.median(x['active_seconds'] for x in samples):.4f} s | {statistics.median(x['restore_seconds'] for x in samples):.3f} s | {statistics.median(x['audit_seconds'] for x in samples):.3f} s | {samples[0]['actor_work']} |")
    hist=max(x['largest_smallest_ratio'] for x in costs['history_panel'].values())
    report=f'''# HLE Full Crux — C7 second-setting implementation

23 September 2026 · Release-candidate update v2

**Second-setting coverage is complete for all 32 cells under the declared finite contract. Full C7 release remains held; milestone progress remains 6/7.**

The new setting uses timed maintenance runbooks, assigned responsibilities, reciprocal commitments, learner answers and real equipment handover. It adds executable content responsibilities beyond scalar caps or renamed resources. The inherited canonical setting remains intact.

## What changed, how, and what becomes possible

`WorkflowEngine` extends the native engine with versioned `WorkflowRequest` recipes for all sixteen routes and both polarities. Task contents include primitive actions, predecessor tasks, earliest/latest slots and the responsible actor. Reconciliation exposes incompatible windows, missing dependencies and cycles. Actual maintenance events carry paid-read occurrence times. Models remain hypotheses, and hypothetical task completion cannot bypass actual physical work.

The implementation uses the existing object store, Fool's Memory retention, Model A routes, paid intermediate handoffs, access receipts, material laws and finite wallets. Shared outputs consume exact offers and receiver-computed answers. Draft rules require exact votes; assent, understanding and practiced skill remain separate. Two members cannot promise a nonmember's work. Repeated readings of one event cannot become multiple practices.

Every cell's generated output is actually consumed. The ordinary cases select a meaningful next task in a fixed later question; removing the defining transformation removes that result at the same main-movement spending. The two Act cases additionally restore or transfer custody so the recipient's later paid tool use succeeds; it fails in the matched control. Native maintenance/readiness operations and representation-dependent predictions are reported separately from claims of new competence.

The second self-route settings are explicit: Contemplate compares time/resource intentions; Commune revises procedural commitments; Integrate reconciles temporal and role constraints; Act restores loan custody or transfers ownership. These differ from the original condition, scalar-cap and static-interface cases. See the 32-row ledger and `docs/C7_Second_Setting_Contract_v1.md` for the exact faces and their consumers.

## Executed evidence on frozen corrected source

| Gate | Result |
| --- | --- |
| Second-setting route/polarity cells | 32/32 |
| New setting across all sixteen types | {matrix['matrix_worlds']}/{matrix['matrix_worlds']} native cases |
| Matched defining-step controls | {matrix['semantic_controls']}/32; equal main work and fixed downstream question |
| Separate saved-world reconstruction | {raw['ordinary_worlds']} ordinary passes; {raw['deliberate_controls']} deliberate controls rejected as expected |
| Exact interruption/continuation | 96 configurations: three boundaries × 32 cells |
| New boundary/semantic test methods | {unit['tests']}/{unit['tests']} |
| Inherited U2–U14/C1–C7 methods | {inherited}/{inherited} |
| Total distinct passing methods | {total} |
| Isolated measurement workers | {costs['workers']} workflow + {native['workers']} unchanged-native |

The independent workflow auditor reconstructs access, scope, task constraints, semantic steps, authority, public outputs and prices from committed objects and access receipts. It does not invoke the participant selector or workflow executor. Inherited independent checks verify native physical effects and charges. The separate verifier parses saved world/access snapshots without replaying participant commands. The final test, matrix, regression and measurement panels retain their executed-file hashes and pass their source-unchanged checks; packaging also verifies the complete frozen execution manifest.

The tests also cover invalid scope, missing receiver reading, dissent, withheld observations, stale membership, unaccepted drafts, wrong/duplicate votes, unavailable resources, cancellation, one-attempt allowances, forged outputs/timestamps/prices, label independence and native composition. Generated rule → teaching → governed Apply and generated models → Integrate → Apply have concrete witnesses. Coverage requests, starting intentions, resources and opportunities are supplied fixtures; this is not a claim of spontaneous institutions or general learning.

## Measured costs

The workflow inactive-history panel varies shared/unique unread histories at 0/100/1,000 records while holding active work fixed. Its largest within-panel median ratio is **{hist:.3f}×**, below the inherited 3.0× tolerance. Each configuration has two timing workers and one separately traced worker. The additional task-count panel stays within the declared eight-task bound.

| Tasks | Median active work | Cold restoration | Raw audit | Modeled work |
| ---: | ---: | ---: | ---: | ---: |
{chr(10).join(measured)}

Active timing above covers four paid movements. The modeled total includes those four movements and one separately timed downstream query; setup, checkpoint, restoration and audit are separate in the evidence. These are isolated processes on a shared host. Exact unique history still costs storage and restoration time. No optimization gain, constant-time total execution or cost-per-new-capacity claim is made.

The unchanged native API remains materially and access-equivalent to the byte-preserved C5 reference. Its median ratio is **{native['reference_ratio']:.3f}×** (2.0× tolerance), and its inactive-history ratio is **{native['history_ratio']:.3f}×** (3.0× tolerance).

## Failures and corrections retained

The first smoke attempt found noncontiguous memory-link keys; retention was corrected. The initial 16-method suite had a fixture that repeated care without renewed wear and a runtime check that treated a rule's voting authority as an individual owner. Both failures and their fixes remain recorded. Review then demonstrated duplicate-event inflation and nonmember task authorization; explicit input/authority checks and regression tests were added. Earlier candidate panels overlapped those review corrections and are not counted as clean frozen runs. A final grounding review then changed maintenance readiness and personal responses to depend on the observed wear and condition; a dedicated held-out outcome check changes the later choice from care to use after actual maintenance. A further review found that reusing reconciled content could erase an inherited action conflict; execution and the independent oracle now preserve that conflict through nesting and teaching. The new regression verifies that it cannot authorize physical action. The final delivery directories use the corrected freeze-v4 source. Earlier interrupted panels remain preserved; they are not counted as completed evaluations. A later duplicate measurement launch stopped before execution because its output directory already existed; the preserved completed measurements were accepted only after every executed-file hash matched the delivered source. No failed or source-changed attempt is relabeled a pass.

The standalone inspector has structural/data/filter verification. Pixel rendering is not claimed as verified.

## Remaining C7 work and limits

This closes the second-setting content-coverage gate (§9.3); it does not itself release C7. The new workflow domain has at most eight tasks, eight inputs, two participants, unit-duration serial scheduling and 0–1,000 local slots. Native care/inspection/transfer/return remain the finite physical vocabulary. Reading or agreeing to a runbook grants no practiced ability. Old C6 checkpoints continue to use `SelectionEngine`; workflow checkpoints use their own exact-restoration schema.

**Next within C7:** integrate the completed setting ledger into the final joint §9 assessment and sustained evaluation. Automatic participant choice, Shell application and population scheduling for the new workflow content require explicit assessment; inherited canonical evidence is not silently promoted to that broader claim. The original six sustained populations remain historical evidence and were not rerun as new-domain populations here. General cross-owner nesting, unrestricted meaning and unrestricted development remain outside the present claims.

## Reproduce

From the source root, Python 3 and the standard library suffice:

```sh
python tools/test_c6.py new-workflow-tests tests_c7_workflow
python tools/evaluate_c7_settings.py new-setting-matrix
python tools/verify_c7_settings.py new-setting-matrix
python tools/regress_c7_parallel.py new-regression
python tools/measure_c7_settings.py new-workflow-costs
python tools/measure_c6.py new-native-costs
```

Extract the new evidence archive beside the source to inspect its saved checkpoints. `inherited/HLE_Full_Crux_C7_Evidence_v1.zip` preserves the supplied prior evidence unchanged.
'''
    report_name='HLE_Full_Crux_C7_Release_Candidate_Report_v2.md'
    (out/report_name).write_text(report);(ROOT/'docs'/report_name).write_text(report)
    spec=(ROOT/'docs/HLE_Full_Crux_Build_Specification_v9.md').read_text()
    spec=spec.replace('Version 9','Version 10',1)
    status='**Status:** C1–C6 remain complete under their bounded gates. Second-setting coverage is now evidenced for all 32 cells: 512 new movement/type cases, 32 matched semantic controls, independent raw reconstruction and 96 interruption configurations. The corrected source passes '+str(total)+' distinct test methods. Section 9.3 is closed within the declared timed-workflow domain. C7 remains open for the final integrated section 9 and sustained assessment. Progress remains 6/7; one milestone remains.'
    spec=re.sub(r'\*\*Status:\*\*[^\n]*',lambda m:status,spec,count=1)
    spec=spec.replace('## C7 release-candidate assessment — 23 September 2026','## C7 first release-candidate assessment — historical, 23 September 2026')
    spec+='\n\n## C7 second-setting implementation — 23 September 2026\n\n'+status+'\n\nSee '+report_name+', C7_Second_Setting_Ledger_v1.json, docs/C7_Second_Setting_Contract_v1.md and contracts/C7_Second_Setting_Protocol_v1.json. The original setting evidence remains inherited and separate. New recipe versions implement timed maintenance/procedure constraints, actual resource handover, reciprocal commitments and receiver-owned questions; they do not alter the formal route map. All 32 ledger rows have two applicable settings with downstream and equal-main-cost defining-step controls. New-world raw audits and unchanged-native regressions passed on the frozen corrected source.\n\nThe first candidate records above are history, not the current setting gate. Full-release cell status remains open pending the joint assessment and sustained evaluation, including explicit applicability of automatic selection and Shell evidence to workflow content. No new milestone or theoretical claim is introduced.\n'
    spec_name='HLE_Full_Crux_Build_Specification_v10.md';(out/spec_name).write_text(spec);(ROOT/'docs'/spec_name).write_text(spec)
    manifest=dict(progress='6/7',release_complete=False,setting_cells=32,settings=2,matrix_worlds=matrix['matrix_worlds'],controls=32,
        continuations=96,passing_methods=total,new_methods=unit['tests'],workflow_workers=costs['workers'],native_workers=native['workers'])
    write(ROOT/'C7_Second_Setting_Execution_Manifest_v1.json',manifest);write(E/'C7_Second_Setting_Execution_Manifest_v1.json',manifest)
    inspector='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>HLE · Second-setting coverage</title><style>
*{box-sizing:border-box}body{margin:0;background:#101920;color:#e7eeef;font:16px/1.6 system-ui,sans-serif}main{max-width:1200px;margin:auto;padding:40px 24px}h1{font-size:40px;line-height:1.15;margin:12px 0}h2{margin-top:32px}.label{color:#84d5cf;letter-spacing:.12em;text-transform:uppercase;font-size:12px}.notice{border-left:4px solid #ffc378;background:#263039;padding:18px}.metrics{display:flex;flex-wrap:wrap;gap:12px;margin:22px 0}.metric{background:#1b2932;padding:14px 22px;flex:1;min-width:180px}.metric strong{display:block;font-size:28px}select{font:inherit;padding:8px;background:#263741;color:#fff;border:1px solid #617985;border-radius:4px}label{display:inline-block;margin:4px 20px 12px 0}details{border-top:1px solid #3a4b55;padding:12px 0}summary{cursor:pointer;font-weight:650}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#17242d;padding:16px;font:12px/1.5 ui-monospace,monospace;max-height:500px;overflow:auto}.state{float:right;color:#84d5cf}small{color:#b9c8ce}@media(max-width:600px){h1{font-size:30px}.state{float:none;display:block}}
</style><main><div class="label">HLE / evidence inspector</div><h1>Second-setting coverage · 32/32</h1><div class="notice"><strong>Content coverage complete · full C7 release held · 6/7 milestones.</strong><br>Every route and polarity now has a materially different second setting. Final integrated and sustained assessment remains open.</div><div class="metrics" id="metrics"></div>
<h2>What changed</h2><p>Timed maintenance runbooks now carry task order, time windows, assigned roles, explicit commitments and learner answers. Equipment handover changes actual custody. Shared understanding, assent and practiced ability remain separate.</p>
<h2>The 32-cell ledger</h2><label>Route <select id="route"><option value="">All routes</option></select></label><label>Face <select id="face"><option value="">Both polarities</option><option>accumulation</option><option>expenditure</option></select></label><p id="count"></p><div id="cells"></div>
<h2>Scope of evidence</h2><p>Every new case has an actual downstream consumer. Defining-step controls preserve main movement spending and the later question. The raw auditor independently reconstructs accessible content, semantics, authority and charges. The source contains the engine, tests, measurement workers and separate saved-world verifier.</p><p>Initial intentions, resources, memberships and opportunities are supplied. Limits: eight tasks, eight inputs, two participants and unit-duration serial scheduling. Native workflow cases do not establish spontaneous institutions or unrestricted development.</p><p>The earlier six diagnostic populations (360 movements and 345 mostly repetitive uses) remain inherited evidence. They are not new-domain sustained runs. Canonical automatic-selection and Shell evidence is retained separately in each cell.</p><p><small>Raw filenames and hashes below identify records in the evidence archive. This standalone inspector displays evidence; it does not run the engine.</small></p></main><script id="data" type="application/json">'''+json.dumps(dict(manifest=manifest,ledger=ledger),separators=(',',':')).replace('</','<'+chr(92)+'/')+'''</script><script>
const d=JSON.parse(document.getElementById('data').textContent);const el=id=>document.getElementById(id);const text=(tag,s)=>{const x=document.createElement(tag);x.textContent=s;return x};
for(const [v,k] of [[d.manifest.matrix_worlds,'new movement/type cases'],[32,'matched semantic controls'],[96,'exact continuations'],[d.manifest.passing_methods,'passing methods']]){const x=text('div','');x.className='metric';x.append(text('strong',v),text('span',k));el('metrics').append(x)}
for(const n of [...new Set(d.ledger.map(x=>x.name))]){const o=text('option',n);o.value=n;el('route').append(o)}
function render(){el('cells').replaceChildren();const rows=d.ledger.filter(x=>(!el('route').value||x.name===el('route').value)&&(!el('face').value||x.face===el('face').value));el('count').textContent=rows.length+' cells shown · second setting passed · full release pending';for(const r of rows){const box=document.createElement('details');const s=text('summary',r.name+' · '+r.face);const state=text('span','2 settings · '+r.type_cases+' types');state.className='state';s.append(state);box.append(s,text('p','What changed: '+r.what_changed),text('p','How: '+r.how_changed.mechanism+' · '+r.how_changed.modeled_main_work+' modeled work units.'),text('p','Afterward: '+r.afterward.kind+' → '+r.afterward.next_task+(r.afterward.owner_use?' · recipient use '+r.afterward.owner_use:'')),text('p','Control: '+r.control.spent+' main work units; next task '+r.control.next_task+'; normal semantic audit rejected the withheld transformation.'),text('pre',JSON.stringify(r,null,2)));el('cells').append(box)}}
el('route').addEventListener('change',render);el('face').addEventListener('change',render);render();
</script></html>'''
    html_name='HLE_Full_Crux_C7_Inspector_v2.html';(out/html_name).write_text(inspector)
    subprocess.run(['node',str(ROOT/'tools/verify_c7_second_inspector.cjs'),str(out/html_name),str(E/'inspector_delivery')],check=True)
    (ROOT/'README.md').write_text('# HLE Full Crux — C7 second-setting update\n\nSecond-setting content coverage: **32/32 cells**. Full release remains held, progress **6/7**.\n\nRead `docs/'+report_name+'` and `docs/C7_Second_Setting_Contract_v1.md`. Python 3 and standard library suffice.\n\n```sh\npython tools/test_c6.py new-workflow-tests tests_c7_workflow\npython tools/evaluate_c7_settings.py new-setting-matrix\npython tools/verify_c7_settings.py new-setting-matrix\npython tools/regress_c7_parallel.py new-regression\npython tools/measure_c7_settings.py new-workflow-costs\npython tools/measure_c6.py new-native-costs\n```\n\n`WorkflowEngine` and `WorkflowRequest` add the timed workflow domain; existing `SelectionEngine` APIs remain available. Restore each checkpoint with its corresponding engine. New-domain automatic selection, Shell integration and sustained assessment are not claimed complete. The protocol, four source freezes, independent audit, raw worlds and all earlier failed/source-changed attempts are preserved.\n')
    # Final source includes documentation and the reproducible packaging script;
    # execution guards separately identify exactly the frozen executed modules.
    source_manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*') if p.is_file() and p.name!='C7_Second_Setting_Delivered_Source_Manifest_v1.json' and not any(v.startswith('evidence_') or v=='__pycache__' for v in p.relative_to(ROOT).parts) and p.suffix not in ('.pyc','.zip')}
    write(ROOT/'C7_Second_Setting_Delivered_Source_Manifest_v1.json',source_manifest)
    source_zip=out/'HLE_Full_Crux_C7_Source_v2.zip'
    with zipfile.ZipFile(source_zip,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(ROOT.rglob('*')):
            if p.is_file() and not any(v.startswith('evidence_') or v=='__pycache__' for v in p.relative_to(ROOT).parts) and p.suffix not in ('.pyc','.zip'):
                z.write(p,'HLE_Full_Crux_C7_Source_v2/'+str(p.relative_to(ROOT)))
    shutil.copy2(out/html_name,E/html_name);shutil.copy2(out/report_name,E/report_name)
    shutil.copy2(ROOT/'C7_Second_Setting_Source_Freeze_v1.json',E/'C7_Second_Setting_Source_Freeze_v1.json')
    shutil.copy2(ROOT/'C7_Second_Setting_Source_Freeze_v2.json',E/'C7_Second_Setting_Source_Freeze_v2.json')
    shutil.copy2(ROOT/'C7_Second_Setting_Source_Freeze_v3.json',E/'C7_Second_Setting_Source_Freeze_v3.json')
    shutil.copy2(ROOT/'C7_Second_Setting_Source_Freeze_v4.json',E/'C7_Second_Setting_Source_Freeze_v4.json')
    shutil.copy2(ROOT/'C7_Second_Setting_Delivered_Source_Manifest_v1.json',E/'C7_Second_Setting_Delivered_Source_Manifest_v1.json')
    evidence_zip=out/'HLE_Full_Crux_C7_Evidence_v2.zip'
    with zipfile.ZipFile(evidence_zip,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(E.rglob('*')):
            if p.is_file():z.write(p,'evidence_c7_settings/'+str(p.relative_to(E)))
        z.write(prior,'inherited/HLE_Full_Crux_C7_Evidence_v1.zip',compress_type=zipfile.ZIP_STORED)
    files=[source_zip,evidence_zip,out/report_name,out/html_name,out/spec_name]
    write(out/'HLE_Full_Crux_C7_Delivery_Checksums_v2.json',dict(files=[dict(file=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]))
    print(json.dumps(dict(passing_methods=total,files=[dict(file=p.name,bytes=p.stat().st_size) for p in files]),indent=2))
if __name__=='__main__':build(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
