"""Assemble bounded C6 delivery from executed summaries, retaining failures."""
import sys,json,hashlib,html,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];E=ROOT/'evidence_c6';OUT=Path(sys.argv[1]);OUT.mkdir(parents=True,exist_ok=True)
def read(name):return json.loads((E/name).read_text())
def write(path,value):path.write_text(json.dumps(value,indent=2))
unit=read('tests_attempt2/summary.json');reg=read('regression_continuation/summary.json');panel=read('panel_final/summary.json');types=read('types_final/summary.json');transfer=read('transfer_final/summary.json');measure=read('measurements_final/summary.json');raw=read('raw_verification_final.json')
assert all(x['passed'] for x in (unit,reg,panel,types,transfer,measure,raw))
assert panel['cases']==32 and types['cases']==512 and transfer['worlds']==7
methods={x['test_id'] for result in (unit,reg) for x in result['rows'] if x['status']=='passed'}
manifest=dict(milestone='C6',bounded_complete=True,progress='6/7',remaining=['C7'],automatic_cells=32,movement_type_cases=512,matched_choice_controls=32,
    transfer_history_capacity_worlds=7,valid_raw_worlds=raw['valid_worlds'],deliberate_ablation_worlds=raw['deliberate_ablations'],
    final_test_methods=len(methods),c6_methods=unit['tests'],inherited_methods=reg['tests'],performance_workers=measure['workers'],
    tests='Clean final C6 suite plus completed isolated-package regression continuation; initial failed and interrupted evaluations retained.',
    full_release_complete=False)
write(ROOT/'C6_Execution_Manifest_v1.json',manifest);write(E/'C6_Execution_Manifest_v1.json',manifest)
ledger=[]
for row in panel['rows']:
    ledger.append(dict(name=row['name'],face=row['face'],automatic_selection=True,canonical_cell_complete_for_C6=True,full_release_complete=False,
        what_changed='An owned outcome demand and accessible content selected a native movement; its real result was consumed.',
        how_changed=dict(selection=row['decision'],native_child=row['child'],native_work=row['child_work'],evidence='evidence_c6/panel_final/'+row['raw']['file']),
        afterward=row['later'],control=row['control'],type_cases=16,remaining=['two distinct applicable semantic settings per cell','C7 sustained release gates']))
write(ROOT/'C6_Progress_Ledger_v1.json',ledger);write(E/'C6_Progress_Ledger_v1.json',ledger)
report=f'''# HLE Full Crux — C6 completion report

23 September 2026 · Bounded situated selection v1

**Decision: C6 is complete within the declared finite selection and transfer contract. Progress: 6/7. One milestone remains: C7 — sustained full-Crux release.** All 32 full-release cells remain open for their applicable distinct-setting and sustained-release requirements.

## What changed, how, and what becomes possible

Participants now choose among all 32 canonical movement/polarity cells from paid owned demands, received information, retained meanings, acquired use, their Model A processing costs and available work resources. The request supplies no route or recipe. Candidate inputs are constructed from accessible content; there is no prescribed route sequence.

Paid comparison records every cell, its applicability reason, score, input revisions and deferred search. The chosen operation then passes the existing Shell admission and native semantic/material contracts. Selection, admission and completed destination are separate events. The original native APIs remain available.

Every automatic cell witness completes a native operation and feeds an actual later consumer. In 32 matched controls, withholding the winner after the same paid comparison leaves the candidate records and comparison charges intact but launches no native child. Total spending differs because that later work never occurs. The ordinary choice audit correctly rejects those deliberate interventions; native accounting passes.

The more specific history and development witnesses establish why changed content matters:

- With the same personal-information demand, a retained model selects Understand. After an actual local stock observation is received and processed, Embody wins the comparison and changes the later allocation decision.
- Successful practice and paid acquisition on one tool make automatic Act accumulation available on another. Before acquisition, the selector defers repair. A different context does not inherit that competence.
- An old model is contextually qualified only when local intention and actual local observation are available. Local limits of 1 and 4 yield corresponding retained limits and later choices. Without local observation, the selector creates a local hypothesis and makes no transfer claim. The adapter remains Integrate accumulation, not an additional route.

## Executed evidence

| Evidence | Result |
| --- | --- |
| Automatic main-cell witnesses with downstream use | 32/32 |
| Matched paid choice-withholding controls | 32; expected ordinary choice-audit rejection |
| Automatic movement/type cases | 512/512 across all 16 Model A frames |
| Saved transfer, history and capacity worlds | 7 |
| Independent ordinary raw-world reconstructions | {raw['valid_worlds']}/{raw['valid_worlds']} |
| Deliberate intervention reconstructions | {raw['deliberate_ablations']}; native accounting passes, choice contract rejects |
| Final C6 test methods | {unit['tests']} |
| Inherited test methods in completed package continuations | {reg['tests']} |
| Distinct passing methods on final runtime | {len(methods)} |
| Isolated cost workers | {measure['workers']} |

The inherited packages rerun are U4–U8 and C1–C5. The complete U2–U14 historical population was not rerun. The 512 type cases establish automatic native completion; the separate 32-cell panel supplies actual later consumers. Different type frames change paid processing costs; type labels manufacture no knowledge or ability.

The first C6 test run had one failed responsiveness expectation and two fixture errors. The support coefficient changed from 5 to 20 under the retained review amendment. The fixtures were corrected; an artificial lock-release test was replaced with a lawful pending-delivery test, and exhaustion now replays the same setup from a smaller initial wallet. The final 19-method C6 run passed on unchanged source.

The initial combined inherited run was interrupted after its visible log stopped advancing at a U5 recall test. The cause was not established; that test passed alone. The same requested package population then completed in separate processes. Earlier failed/stalled logs, source fingerprints and the execution amendment remain included; this is not described as one uninterrupted clean combined run.

## Access, interruption and reconstruction

Hidden material changes do not alter pre-delivery content or route ranking. A pending delivery is not paid processed evidence. Foreign demands, fabricated fields, altered scores and false selected cells are rejected. Search limits disclose deferred alternatives. Cancellation and genuine wallet exhaustion retain charges without launching a child. Twelve selection/admission/native interruption configurations across four representative contracts restore to exactly the same subsequent state and spending. A C5 checkpoint upgrades by exact replay.

Automatic selection does not bypass Shells: the generated-pattern witness cancels the chosen native movement after its first actual paid semantic step. Teaching and contextual qualification do not grant practiced competence or authority. C5's contextual adapter mapping uses the existing Integrate accumulation gate.

The raw auditor imports neither the participant selector nor selection executor. It reconstructs accessible inputs from committed access receipts, separately enumerates candidate joins, recomputes scores and links the maximum to the paid launch. Native content, material law, consent and Shell behavior retain their separate validators. Shared recipe definitions and Model A geometry are the common specification.

## Efficiency

No optimization gain is claimed. The unchanged direct-native API median ratio is **{measure['reference_ratio']:.3f}×** the byte-preserved C5 runtime, within the prospective 2.0× tolerance. Across 0/100/1,000 shared and unique unread inactive histories, the largest/smallest active median ratio is **{measure['history_ratio']:.3f}×**, within 3.0×. Matched modeled work is unchanged in those panels.

| Workload | Size | Median active | Modeled active work | Cold restore | Raw audit |
| --- | ---: | ---: | ---: | ---: | ---: |
'''
for r in measure['rows']:report+=f"| {r['lane']} | {r['size']} | {1000*r['median_active']:.2f} ms | {r['modeled_work']} | {r['median_restore']:.3f} s | {r['median_audit']:.3f} s |\n"
report+='''
Each workload demonstrates one downstream consumer. Setup is excluded from active timing. The direct comparison has three timing samples per arm; each selection/history/alternative workload has two timing samples and a separate allocation trace. Cold restoration, checkpoint size and raw audit are measured separately. The JSON includes CPU time, allocation peaks and resolution counts.

Candidate count varies separately at 1/4/16 supplied intentions. Search is capped at 128 local contents, 128 foreign models and 64 bundles per cell, including a separately identified contextual adapter. Collection still traverses current participant bindings; these measurements establish no constant-time bound for growing owned memory. Exact history, cold restoration and audit have real costs. Earlier participant/composition-depth measurements remain inherited evidence rather than newly repeated measurements.

## Scope and next gate

The policy and its numeric priorities are explicit engineering constructions. Initial owned needs and opportunities are supplied; spontaneous goal formation and sustained automatic population management are not established. The scheduler advances one bounded request through comparison, admission and native work. The language remains the inherited finite condition/resource contracts, and shared contracts still use two participants.

All 32 cells now have automatic witnesses. Two materially distinct semantic settings for **every** cell remain unproved. Unrestricted meaning, general cross-owner nesting, universal Shell diagnosis and an unrestricted developmental trajectory are also not claims of this milestone.

**Next: C7 — sustained full-Crux release.** Complete the release ledger with prolonged mixed-type runs, distinct applicable settings for every cell, reconstruction and regression gates, failure reporting and matched efficiency evidence.
'''
reportname='HLE_Full_Crux_C6_Report_v1.md';(OUT/reportname).write_text(report);(ROOT/'docs'/reportname).write_text(report)
spec=(ROOT/'docs/HLE_Full_Crux_Build_Specification_v7.md').read_text()
spec=spec.replace('Version 7 ·','Version 8 ·')
a=spec.index('**Status:**');b=spec.index('\n\n',a)
spec=spec[:a]+f"**Status:** C1–C6 are complete under their bounded milestone gates; C7 remains open. C6 supplies 32 automatic native/downstream witnesses, 32 matched choice controls, 512 movement/type cases, seven transfer/history/capacity worlds and {len(methods)} distinct final-runtime passing methods. Initial failures and interrupted regression execution remain explicit. All full-release cells retain their applicable distinct-setting and sustained-run gates."+spec[b:]
spec=spec.replace('| Every cell has an automatic witness; distinct histories and changed contexts produce explainable differences without scripted route ordering | Open |','| Every cell has an automatic witness; distinct histories and changed contexts produce explainable differences without scripted route ordering | Complete under bounded C6 gate |')
spec=spec.replace('**Implementation progress under this specification: 5/7 milestones complete. C1–C5 passed within their declared domains. Two milestones remain; C6 is next.**','**Implementation progress under this specification: 6/7 milestones complete. C1–C6 passed within their declared domains. One milestone remains: C7.**')
spec=spec.replace('**Next: C6.** Participant selection','**C5 handoff history:** Participant selection')
spec+='''\n\n## C6 completion record — 23 September 2026\n\nC6 adds paid participant selection from owned outcome demands, received evidence, acquired use and Model A processing estimates. All 32 cells have automatic completed native witnesses and actual later consumers. The 512 movement/type cases cover all sixteen frames. Thirty-two matched choice-withholding controls retain comparison spending but lack a native child; they intentionally fail the ordinary choice contract. Seven saved worlds demonstrate new-information responsiveness, practiced repair on a held-out target and contextual qualification from actual local evidence.\n\nThe finite scheduler accepts no route or recipe in its selection request. An explicit contextual adapter competes as an implementation of Integrate accumulation under the existing Shell gate. Comparison, admission and realized destination remain separate. The independent auditor reconstructs paid access and candidate joins without calling the participant selector; native validators check resulting semantics and effects.\n\nSee HLE_Full_Crux_C6_Report_v1.md, C6_Protocol_v1.json, C6_Review_Amendment_v1.json, the progress ledger and execution manifest for exact counts, failed/stalled evaluations, successful continuations and cost measurements. No speedup is claimed. Initial needs remain supplied; shared contracts remain bounded to two members. Every cell's two distinct semantic settings and the sustained full-release obligations remain open.\n\n**Next: C7 — sustained full-Crux release. One milestone remains.**\n'''
(OUT/'HLE_Full_Crux_Build_Specification_v8.md').write_text(spec);(ROOT/'docs/HLE_Full_Crux_Build_Specification_v8.md').write_text(spec)
# The inspector embeds its exact ledger so it works without network access.
cards=''.join(f'<div class="card"><b>{n}</b><span>{html.escape(label)}</span></div>' for n,label in [('6 / 7','bounded milestones'),('32','automatic movement cells'),('512','movement/type cases'),('7','transfer and development worlds')])
rows=[]
for item in ledger:
    later=item['afterward'];effect=(later.get('action','event')+' · '+str(later.get('amount',later.get('outcome',''))))
    detail=html.escape(json.dumps(item,indent=2));evidence=item['how_changed']['evidence']
    rows.append(f'''<details class="cell" data-search="{item['name'].lower()} {item['face']}"><summary><strong>{item['name']}</strong><span>{item['face']}</span><em>automatic + later use</em></summary><div class="answers"><section><h3>What changed?</h3><p>The participant chose this movement from its accessible content and owned demand. The native operation completed.</p></section><section><h3>How?</h3><p>Paid comparison, the Shell gate and the native semantic handoffs. Comparison: <b>{item['how_changed']['selection']['spent']}</b> units; native child: <b>{item['how_changed']['native_work']}</b> units. Other work is separately charged.</p></section><section><h3>What became possible?</h3><p>The actual result supplied a later consumer: <b>{html.escape(effect)}</b>. The matched control retained comparison work and launched no child.</p></section></div><p><a href="{evidence}">Raw witness after extracting the evidence archive</a> · All 16 type frames completed this cell.</p><details class="raw"><summary>Exact evidence and references</summary><pre>{detail}</pre></details></details>''')
perf=''.join(f"<tr><td>{r['lane']}</td><td>{r['size']}</td><td>{1000*r['median_active']:.2f}</td><td>{r['modeled_work']}</td><td>{r['median_restore']:.3f}</td><td>{r['median_audit']:.3f}</td></tr>" for r in measure['rows'])
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>HLE · C6 situated selection and transfer</title><style>
*{box-sizing:border-box}body{margin:0;background:#101820;color:#e8f0f3;font:16px/1.6 system-ui,sans-serif}main{max-width:1160px;margin:auto;padding:48px 24px}h1{font-size:clamp(32px,5vw,54px);line-height:1.1;max-width:850px}.eyebrow{color:#87dbce;letter-spacing:.14em;font-size:13px;text-transform:uppercase}p{color:#bdced6;max-width:930px}h2{margin-top:40px}a{color:#8ae1d6}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:32px 0}.card{background:#1b2b37;padding:20px;border:1px solid #344c5a;border-radius:12px}.card b{display:block;font-size:34px;color:#a3e7d8}.card span{font-size:13px}.limit{border-left:3px solid #e1b772;padding:10px 20px;background:#1b2630}details.cell{margin:12px 0;padding:16px 20px;background:#192833;border:1px solid #354b59;border-radius:10px}summary{cursor:pointer;display:flex;gap:20px;align-items:center}summary strong{min-width:160px}summary span{color:#aec6d1}summary em{margin-left:auto;color:#9bdccb;font-size:12px;font-style:normal}.answers{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}.answers h3{font-size:15px;color:#a3e7d8}.answers p{font-size:14px}details.raw{padding:12px;background:#101820;border-radius:8px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}input{width:100%;background:#101820;color:white;border:1px solid #567080;padding:15px;font:inherit;border-radius:8px}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-size:14px}td,th{text-align:left;padding:10px;border-bottom:1px solid #354b59}.stories{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}.stories section{background:#192833;border-radius:10px;padding:18px}.stories h3{margin-top:0}.muted{font-size:13px;color:#99b0be}@media(max-width:720px){.cards,.stories,.answers{grid-template-columns:1fr 1fr}.stories section:last-child,.answers section:last-child{grid-column:1/-1}summary{flex-wrap:wrap;gap:7px}summary em{margin-left:0}}@media(max-width:440px){.cards,.stories,.answers{grid-template-columns:1fr}main{padding:30px 16px}}
</style><main><div class="eyebrow">HLE · Full Crux · C6</div><h1>Situated choice.<br>Consequential transfer.</h1><p>Follow a participant's owned demand through paid comparison, an actual movement and a later use. The selector receives accessible content and outcome priorities; it receives no route sequence.</p>'''+cards+'''<p class="limit"><b>C6 is complete within its bounded contract.</b> C7 remains open. Initial demands are supplied, the language is finite, shared contracts use two members, and two distinct semantic settings for every cell are still required.</p><h2>Changes that change the next choice</h2><div class="stories"><section><h3>Received information</h3><p>A retained model supports Understand. A new paid local observation makes Embody win under the same personal-information demand and changes later use.</p></section><section><h3>Acquired capacity</h3><p>Successful practice and paid acquisition on one tool enable automatic repair of another. A different context does not inherit that skill.</p></section><section><h3>Contextual transfer</h3><p>A prior model is qualified by actual local evidence. Limits of 1 and 4 change the later choice. Without observation, no transfer is claimed.</p></section></div><h2>The 32 automatic cells</h2><p>Each main row includes a completed native movement, actual downstream use, a matched choice-withholding control and 16 completed type cases. The ordinary choice auditor rejects the deliberate controls, while their native accounting passes.</p><label for="filter">Find a route or polarity</label><input id="filter" placeholder="For example: Embody or accumulation"><p id="count" class="muted">32 cells shown</p>'''+''.join(rows)+f'''<h2>Validation and measured cost</h2><p>{len(methods)} distinct passing methods on the final runtime; {raw['valid_worlds']} ordinary raw worlds reconstructed and {raw['deliberate_ablations']} deliberate controls correctly rejected by the choice contract. The first failed C6 run and the interrupted combined regression log remain in the evidence.</p><p>Unchanged native median: {measure['reference_ratio']:.3f}× C5. Inactive-history median spread: {measure['history_ratio']:.3f}×. No speedup is claimed. Timing and allocation tracing ran separately.</p><div class="scroll"><table><thead><tr><th>Workload</th><th>Size</th><th>Active ms</th><th>Modeled work</th><th>Restore s</th><th>Audit s</th></tr></thead><tbody>{perf}</tbody></table></div><p class="muted">Standalone inspector. Raw links work when evidence_c6 is extracted beside this HTML file. Exact source identities, changed costs, amendments and failures accompany the release. Next: C7 — sustained full-Crux release.</p></main>'''+'''<script>const input=document.getElementById('filter');input.addEventListener('input',()=>{const q=input.value.toLowerCase().trim();let n=0;document.querySelectorAll('.cell').forEach(e=>{e.hidden=!e.dataset.search.includes(q);if(!e.hidden)n++});document.getElementById('count').textContent=n+' cells shown';});</script></html>'''
(OUT/'HLE_Full_Crux_C6_Inspector_v1.html').write_text(page)
if '--preview-only' in sys.argv:sys.exit(0)
# Runtime/tests are self-contained. Avoid recursively copying old raw evidence.
notes='''# C6 package notes

The source includes the current runtime, all inherited runtime modules, test and reproduction sources, current protocols, reference papers and a byte-preserved C5 comparison runtime. Current C6 raw evidence is delivered separately; extract its evidence_c6 directory beside this source's modules.

Historical raw evidence directories are not recursively duplicated in this source ZIP. They remain in the supplied HLE_Full_Crux_C5_Source_v1.zip (Library identity libfile_afc1720942108191b62b67651de88b6e). C6_Inherited_Archive_Index_v1.json lists the omitted paths and exact hashes, and identifies that unchanged input archive. No source module or current C6 evidence is omitted on that basis. Some historical packaging/verification commands require their original evidence archive.
'''
(ROOT/'C6_Package_Notes_v1.md').write_text(notes)
readme='''# HLE full Crux — C6

C6 adds paid situated participant choice and contextual transfer. Progress: 6/7; C7 remains open. Read docs/C6_Architecture_and_Scope_v1.md and the C6 report for exact claims and limits.

The runtime, native tests and evidence reconstruction use Python 3 and its standard library. Optional browser inspection uses Node/Playwright with Chromium. From this directory:

```sh
python tools/test_c6.py new-c6-test-run tests_c6
python tools/evaluate_c6.py panel new-c6-panel
python tools/evaluate_c6.py types new-c6-type-panel
python tools/evaluate_c6.py transfer new-c6-transfer-panel
python tools/measure_c6.py new-c6-measurements
```

For raw evidence reconstruction, extract the delivered evidence_c6 folder here and run:

```sh
python tools/verify_c6_delivery.py evidence_c6
```

Use `SelectionEngine.from_c5(checkpoint)` for exact C5 replay upgrade. Construct an actor-owned paid demand, then call `participate(cid, SelectionRequest(...))` repeatedly to advance comparison, Shell admission and native work. The request has no recipe field. Native direct requests remain compatible.

The initial failed tests, review amendment, interrupted regression log and completed continuation are retained in the evidence. See C6_Package_Notes_v1.md for the historical evidence index and packaging boundary.
'''
(ROOT/'README.md').write_text(readme)
input_archive=Path('/workspace/scratch/862559953c7d/upload/HLE_Full_Crux_C5_Source_v1.zip')
excluded=[];included=[]
for p in sorted(ROOT.rglob('*')):
    if not p.is_file():continue
    rel=p.relative_to(ROOT)
    if '__pycache__' in rel.parts or p.suffix=='.pyc' or any(x.startswith('.') for x in rel.parts):continue
    if any(x=='evidence' or x.startswith('evidence_') for x in rel.parts):
        if rel.parts[0]!='evidence_c6':excluded.append(dict(path=str(rel),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
        continue
    if rel.name in ('C6_Source_File_Manifest_v1.json','C6_Inherited_Archive_Index_v1.json'):continue
    included.append(p)
write(ROOT/'C6_Inherited_Archive_Index_v1.json',dict(archive=input_archive.name,sha256=hashlib.sha256(input_archive.read_bytes()).hexdigest(),library_file_id='libfile_afc1720942108191b62b67651de88b6e',excluded_raw_evidence=excluded))
included.append(ROOT/'C6_Inherited_Archive_Index_v1.json')
source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in included}
write(ROOT/'C6_Source_File_Manifest_v1.json',source_hashes);included.append(ROOT/'C6_Source_File_Manifest_v1.json')
write(E/'C6_Delivered_Source_Manifest_v1.json',source_hashes)
with zipfile.ZipFile(OUT/'HLE_Full_Crux_C6_Source_v1.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in included:z.write(p,Path('HLE_Full_Crux_C6_Source_v1')/p.relative_to(ROOT))
with zipfile.ZipFile(OUT/'HLE_Full_Crux_C6_Evidence_v1.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(E.rglob('*')):
        if p.is_file():z.write(p,Path('evidence_c6')/p.relative_to(E),compress_type=zipfile.ZIP_STORED if p.suffix=='.gz' else zipfile.ZIP_DEFLATED)
checksums={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(OUT.iterdir()) if p.is_file() and 'Checksums' not in p.name}
write(OUT/'HLE_Full_Crux_C6_Delivery_Checksums_v1.json',checksums)
print(json.dumps(dict(manifest=manifest,files={p.name:p.stat().st_size for p in OUT.iterdir()}),indent=2))
