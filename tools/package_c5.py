import json,hashlib,zipfile,shutil,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT.parent.parent/'output';OUT.mkdir(exist_ok=True)
E=ROOT/'evidence_c5'
a=json.loads((E/'tests_final1/summary.json').read_text());b=json.loads((E/'tests_final2/summary.json').read_text());assert b['passed'] and a['source_unchanged']
accepted={x['test_id']:x for x in a['rows'] if x['status']=='passed'};accepted.update({x['test_id']:x for x in b['rows'] if x['status']=='passed'});assert len(accepted)==118
for folder in ('tests_final1','tests_final2'):
 manifest=json.loads((E/folder/'source.json').read_text())
 assert all(hashlib.sha256((ROOT/k).read_bytes()).hexdigest()==v for k,v in manifest.items() if k.startswith('hle_unified/'))
measure=json.loads((E/'measurements_final/summary.json').read_text());raw=json.loads((E/'raw_verification_final.json').read_text());assert measure['passed'] and raw['passed']
execution=dict(version='C5-v1',passed=True,distinct_tests=118,new_c5_methods=19,inherited_methods_rerun=99,
 accepted_tests=sorted(accepted),test_runs=['evidence_c5/tests_final1','evidence_c5/tests_final2'],
 initial_failed_assertions=2,initial_failure_disposition='test assertions corrected; runtime unchanged; 19 C5 tests rerun',
 raw_witnesses=143,admission_pairs=32,active_interruption_pairs=32,development_effect_worlds=15,
 measured_workers=measure['workers'],source_scope='C4 source preserved except shell_records and three audit forwarding signatures',
 audit_amendment='Final raw audit strengthens active-panel validator; exact worlds reaudited with final source',
 full_release_cells_complete=0,next='C6')
(ROOT/'C5_Execution_Manifest_v1.json').write_text(json.dumps(execution,indent=2))
input_zip=ROOT.parent.parent/'upload/HLE_Full_Crux_C4_Source_v1.zip'
with zipfile.ZipFile(input_zip) as z:
 changes=[]
 for info in z.infolist():
  rel=Path(info.filename).relative_to('HLE_Full_Crux_C4_Source_v1')
  if len(rel.parts)==2 and rel.parts[0]=='hle_unified' and rel.suffix=='.py':
   before=hashlib.sha256(z.read(info)).hexdigest();after=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
   if before!=after:changes.append(dict(path=str(rel),before=before,after=after))
assert {x['path'] for x in changes}=={'hle_unified/shell_records.py','hle_unified/autonomy_audit.py','hle_unified/shell_audit.py','hle_unified/development_audit.py'}
(E/'inherited_runtime_changes.json').write_text(json.dumps(changes,indent=2))
rows=measure['rows'];hist=[r for r in rows if r['lane'].startswith('history')];pats=[r for r in rows if r['lane']=='patterns']
report=f'''# HLE Full Crux — C5 completion report

23 September 2026 · Bounded C5 v1

**Decision: C5 is complete within the declared finite Shell application/development contract. Progress: 5/7. C6 and C7 remain open.** All 32 full-release cells still have applicable automatic-selection, distinct-setting and sustained-run requirements.

## What changed, how, and what becomes possible

An explicit Shell-aware request now connects owned patterns and paid development to every canonical Crux route/polarity. It preserves the exact requested input, destination, polarity, target, owner, carrier, bearer and demand. The caller selects the route and application phase; this is not C6 autonomy.

The same generated approval pattern can prevent initiation or interrupt a movement after its first actual paid semantic step. Interruption cancels the remaining work/commit, retains the intermediate and charges, and substitutes the retained personal response. Neither an admission nor a personal wait/attention response counts as completed IT, WE or ITS content. Some crossing recipes have only one semantic step: their interruption occurs after computation but before output retention or material commitment, not before a fictional second step.

After a paid exact-target correction, the native route can complete and its actual result feeds a downstream consumer. The 32-cell ledger records the consumer's decision, prediction, proposal or executed effect. Blocked/interrupted controls have no completed native output to consume. The native C2–C4 semantic and material contracts are unchanged.

## Evidence actually executed

| Evidence | Result |
| --- | --- |
| Prevention-of-initiation panel | 32 deformation/correction pairs, 64 raw worlds |
| Active-interruption panel | 32 deformation/correction pairs, 64 raw worlds |
| Development and other-effect witnesses | 15 raw worlds |
| Independent final raw reconstruction | 143/143 passed; no executor or selector called |
| Current C5 tests | 19 distinct passing methods |
| Inherited U7, U8 and C4 tests rerun | 99 distinct passing methods |
| Combined distinct passing test population | 118 |
| Additional type probe | Theorize admission/completion across all 16 Model A types |
| Cost workers | {measure['workers']} sequential isolated workers; timing and tracing separate |

The 118 passing methods combine two documented runs. The first frozen-source run had 116 passes and two failed **test assertions**: a cancelled job has `binding: None`, and lifetime stock quantity is not remaining stock. The corrected 19-method C5 suite then passed without a runtime change. These are not described as one uninterrupted clean 118-test run. The inherited C4 suite includes its 80 circuit/type cases and 24 continuation configurations; the full historical 554-method C4/U14 population was not freshly rerun.

The first active panel precedes a strengthening of the raw auditor. Its 64 worlds were revalidated by the final auditor with unchanged runtime semantics. Earlier development/export/import failures, source identities and amendments remain in `evidence_c5` and the development log.

## Formation, signs and development

Generated formation remains **approval-only**: two fresh received blame experiences on otherwise applicable action create an additional authorization attribution and persistent unresolved material. Neutral/legitimate-constraint controls distinguish that history from ordinary refusal, danger and lack of opportunity. Obligation, salience, adverse forecast and route exclusion are explicitly injected effect fixtures with real decision/interruption consequences. Their formation is not claimed.

The supplied Shell geometry paper distinguishes prevention of initiation from the four signs that assume active movement. C5 keeps that distinction:

| Observable | Concrete witness and limit |
| --- | --- |
| Premature translation | Paid native intermediate followed by substituted personal response; original destination still unmet. |
| Forced placement | That personal response occupies continuation while a requested IT/WE/ITS obligation remains unmet. This is an attempted placement, never accepted destination completion. |
| New defensive structure | Additional approval attribution is traced to fresh blame, original source material and subsequent demand. |
| Residual fragmentation | The same material recurs after another target's local release or withdrawal of external support. |
| Prevention of initiation | Separate admission-only panel; not relabeled as one of the active signs. |

These are explicit simulation operationalizations, not a universal detector or validation of psychological theory. Application at the first semantic boundary is a bounded engineering policy, not an inferred human mechanism.

The continuing witness retains one material identity through formation, local correction elsewhere, recurrence, independent practice on distinct targets, response reorganization, novel returns with a changed partner and reownership. Afterward, a native Theorize result is used in action. A renewed received threat still blocks movement. A separate supported Share succeeds without acquiring independent capacity and recurs when support is withdrawn.

Correction remains local; supported success is not mastery. Practice uses actual response execution, delivered observation and paid retention. Reownership depends on bounded independent returns and never deletes the original pattern. The response organization does not confer competence in an arbitrary Crux task. There is no separate claim that elapsed wall-clock waiting heals a Shell. Unsupported clearance of forecast, salience or exclusion is rejected.

## Access, failure and continuation

Tests cover route/polarity specificity, paid work, partial admission and partial child restoration, active interruption restoration, cancellation, hidden versus delivered changes, stale evidence subsets, legitimate threat/refusal/unavailability, truncated recall, failed completion claims and source-preserving C4 checkpoint upgrade. C5 does not manufacture consent, public uptake, resources or native competence. Older semantic/access auditors still validate the child operation.

The raw auditor reconstructs native semantics, situated access, cost, pattern formation, scoped correction, practice and reownership, then checks exact admission/child/interruption lineage. It rejects false completion, changed endpoints, forged admission, missing permitted children and altered spending. Actual results are derived from child terminal records, not the admission's label.

## Efficiency

C5 adds three small native modules and extends the admitted encounter-route vocabulary. Three inherited audit modules gain optional accounting-contract forwarding with unchanged defaults. All other inherited native runtime files are byte-identical to C4; the exact change hashes are included. Existing pattern indexes, paid progression and native content operators are reused. No new cache or optimization gain is claimed.

The prospective unchanged-contract median wall-time ratio was **{measure['reference_ratio']:.3f}×** C4, within the declared 2.0× tolerance. The largest/smallest median active-time ratio across 0/100/1,000 shared and unique inactive histories was **{measure['history_ratio']:.3f}×**, within the 3.0× tolerance. Modeled work stayed identical for the matched direct-runtime arms and across the inactive-history panel.

| Workload | Median active time | Modeled active work | Median cold restore | Median audit |
| --- | --- | --- | --- | --- |
'''
for r in rows:
 report+=f"| {r['lane']} / {r['size']} | {r['median_active']*1000:.2f} ms | {r['modeled_work']} | {r['median_restore']:.3f} s | {r['median_audit']:.3f} s |\n"
report+='''
Each measured workload demonstrates one downstream consumer. Therefore its per-demonstrated-consumer active time is the listed active time. New gate work is not claimed free. Setup is excluded from active timing; total-history checkpoint size and raw attempt counts include setup. Allocation peaks and object-resolution counts are in the measurement JSON. Timing sample count is three per direct-runtime arm and two per Shell workload, plus separate traces for the latter.

Pattern count varies separately at 1/4/16. Exact restoration and raw audit are separate, more expensive stages on these workloads; retained history continues to grow. Earlier C2–C4 participant/alternative/depth/dependency measurements are preserved as inherited evidence, not represented as fresh C5 measurements. C5 wraps one chosen movement and introduces no search or new nesting. Wider selection/scaling tests remain C6/C7 work.

## Deliverables and next gate

- Source, with frozen inherited material and C5 implementation/reproduction tools.
- Evidence, including 143 final raw worlds, paired outcomes, development traces, tests, costs, source identities and failures.
- A self-contained HTML inspector, 32-cell progress ledger, this report and specification v7.

**Next: C6 — situated participant selection and transfer**, under the specification's exact gate. Phase and route requests are still supplied. Distinct semantic settings, unrestricted meaning, general cross-owner nesting and sustained full-release behavior are not established by C5.
'''
(ROOT/'docs/HLE_Full_Crux_C5_Report_v1.md').write_text(report)
# Amend the existing specification, preserving historical completion records.
src=ROOT.parent.parent/'upload/HLE_Full_Crux_Build_Specification_v6(1).md';spec=src.read_text()
spec=spec.replace('Version 6 · 23 September 2026','Version 7 · 23 September 2026',1)
start=spec.index('**Status:**');end=spec.index('\n\n',start)
spec=spec[:start]+'''**Status:** C1–C5 are complete under their bounded milestone gates; C6–C7 remain open. C5 supplies 32 admission deformation/correction pairs, 32 active-interruption pairs, 15 development/effect worlds, 143 final raw reconstructions and 118 distinct passing test methods across documented runs. Generated formation remains approval-only. Caller-selected routes and application phases do not close C6 or any full-release cell.'''+spec[end:]
spec=spec.replace('| All 32 cells have the required deformation/control evidence; all supported effects and operationalized signs are covered without blanket clearance | Open |','| All 32 cells have the required deformation/control evidence; all supported effects and operationalized signs are covered without blanket clearance | Complete under bounded C5 gate |')
# Preserve the previous completion direction as explicit history.
spec=spec.replace('**Next: C5 — Shell formation and development across the map.**','**C4 handoff history: C5 — Shell formation and development across the map.**')
spec=spec.replace('The full expressive language, general cross-owner nesting, route-wide Shell extension, autonomous selection and distinct semantic settings remain open.', 'At the C4 handoff, the full expressive language, general cross-owner nesting, route-wide Shell extension, autonomous selection and distinct semantic settings remained open. C5 closes the bounded Shell application gate described below; the other limits remain.')
spec=re.sub(r'\*\*Implementation progress under this specification: 4/7.*?\*\*', '**Implementation progress under this specification: 5/7 milestones complete. C1–C5 passed within their declared domains. Two milestones remain; C6 is next.**',spec)
spec+='''\n\n## C5 completion record — 23 September 2026\n\nThe report, C5_Progress_Ledger_v1.json and C5_Execution_Manifest_v1.json define bounded completion. All 32 cells have both prevention-of-initiation and active-interruption controls with actual native consumers after paid correction. The active witness retains the first paid intermediate and cancels remaining work/commit without claiming the intended destination. When a recipe has only one semantic step, the boundary is before retention or material commitment.\n\nFive supported effect kinds remain distinct from diagnostic signs. Only approval formation is generated from an implemented evidence rule; obligation, salience, forecast and exclusion remain explicit fixtures. The source-material lineage survives local release, recurrence, independent practice, changed-partner/novel-target returns and reownership. No blanket or unsupported clearance is granted. The supplied Shell geometry source's prevention-of-initiation distinction is preserved; prior prevention-only evidence is not relabeled as active translation.\n\nThe release records 118 distinct passing methods across a 118-method run with two failed test assertions and a corrected 19-method C5 run. Runtime was unchanged between those runs. All 143 final raw worlds pass the strengthened auditor. Source amendments and initial failures remain visible. The cost protocol uses 33 isolated workers and retains inherited scaling evidence without claiming it was rerun. No optimization gain is claimed.\n\n**Next: C6.** Participant selection and application phase remain supplied, two distinct applicable semantic settings are not established for every cell, and C7 sustained-release requirements remain open. All 32 full-release cells remain open for their applicable remaining gates.\n'''
(ROOT/'docs/HLE_Full_Crux_Build_Specification_v7.md').write_text(spec)
for name in ('HLE_Full_Crux_C5_Report_v1.md','HLE_Full_Crux_C5_Inspector_v1.html','HLE_Full_Crux_Build_Specification_v7.md'):
 shutil.copy2(ROOT/'docs'/name,OUT/name)
# Exact delivered file manifest, excluding generated bytecode and manifest itself.
files=[p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and p.name!='C5_Source_File_Manifest_v1.json']
manifest={str(p.relative_to(ROOT)):dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in sorted(files)}
(ROOT/'C5_Source_File_Manifest_v1.json').write_text(json.dumps(manifest,indent=2))
with zipfile.ZipFile(OUT/'HLE_Full_Crux_C5_Source_v1.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in [*files,ROOT/'C5_Source_File_Manifest_v1.json']:z.write(p,'HLE_Full_Crux_C5_Source_v1/'+str(p.relative_to(ROOT)))
with zipfile.ZipFile(OUT/'HLE_Full_Crux_C5_Evidence_v1.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(E.rglob('*')):
  if p.is_file():z.write(p,'evidence_c5/'+str(p.relative_to(E)))
 for name in ('C5_Execution_Manifest_v1.json','C5_Progress_Ledger_v1.json','C5_Source_File_Manifest_v1.json'):z.write(ROOT/name,name)
checks={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.iterdir()) if p.name!='HLE_Full_Crux_C5_Delivery_Checksums_v1.json'}
for name in ('HLE_Full_Crux_C5_Source_v1.zip','HLE_Full_Crux_C5_Evidence_v1.zip'):
 with zipfile.ZipFile(OUT/name) as z:assert z.testzip() is None
(OUT/'HLE_Full_Crux_C5_Delivery_Checksums_v1.json').write_text(json.dumps(dict(version='C5-v1',sha256=checks,archive_crc_verified=True),indent=2))
print(json.dumps(dict(output=str(OUT),files={p.name:p.stat().st_size for p in OUT.iterdir()},passed=True)))
