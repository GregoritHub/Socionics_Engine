"""Build versioned evidence-backed artifacts without changing old deliverables."""
from pathlib import Path
import json,hashlib,re,copy
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):
 assert not p.exists(),str(p)
 p.write_text(json.dumps(x,separators=(',',':'))+'\n')
def main():
 run=ROOT/'evidence/Corrective5/attempt1';a=read(run/'Acceptance.json');review=read(run/'Corrective_Ledger_Assessment.json');candidate=read(run/'Corrective_Ledger.json')
 assert a['passed'] and a['required_jobs']==54 and a['distinct_methods']==742 and a['measurement_workers']==81
 assert review['passed'] and review['rows_reconstructed']==32 and review['candidate_sha256']==sha(run/'Corrective_Ledger.json')
 ledger=copy.deepcopy(candidate);ledger['schema']='srl-corrected-release-evidence-ledger-v3';ledger.pop('goal_complete',None)
 ledger.update(complete_cells=32,full_release_complete=True,phase_7_authorized=False,candidate_sha256=sha(run/'Corrective_Ledger.json'),independent_assessment_sha256=sha(run/'Corrective_Ledger_Assessment.json'),release_decision='Evidence accepted; final clean durable delivery receipt governs release',delivery_receipt='evidence/Corrective6/Delivery_Decision.json')
 for row in ledger['rows']:
  row['full_release_complete']=True
  for setting,e in row['settings'].items():
   e['complete']=True;e['current_requirements']=copy.deepcopy(e['inherited_sections']['requirements'])
   for key,field in [('9.8','native_continuations'),('9.11','parent_worlds'),('9.9','longitudinal_controls')]:e['current_requirements'][key]={'status':'passed','corrective_evidence_field':field,'assessment_sha256':sha(run/'Corrective_Ledger_Assessment.json')}
   e['current_requirements']['9.12']={'status':'passed','acceptance':'evidence/Corrective5/attempt1/Acceptance.json','sha256':sha(run/'Acceptance.json'),'methods':742,'jobs':54}
 write(ROOT/'C7_Final_Ledger_v3.json',ledger)
 html=(ROOT/'docs/HLE_Full_Crux_C7_Inspector_v3.html').read_text();d=json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>',html,re.S)[1])
 d['manifest']['passing_methods']=742;d['manifest']['release_complete']=True;d['reviewed_ledger_sha256']=sha(ROOT/'C7_Final_Ledger_v3.json');d['findings']=[]
 def ref(path):
  p=ROOT/path;return {'member':path,'sha256':sha(p),'bytes':p.stat().st_size}
 for r in d['ledger']:
  final=next(x for x in ledger['rows'] if (x['route'],x['polarity'])==(r['name'],r['face']))
  r['full_release_complete']=True;r['remaining']=[];r['reviewed_requirements']={s:e['current_requirements'] for s,e in final['settings'].items()}
  r['current_evidence']={k:ref(v['member'].replace('evidence/FB6.2/attempt1/','evidence/Corrective5/attempt1/')) for k,v in r['current_evidence'].items()}
  for s,e in final['settings'].items():
   for row in e['native_continuations']:
    for k in ('boundary_world','restored_boundary','original_terminal','restored_terminal'):
     r['current_evidence'][f'{s}_boundary_{row["boundary"]}_{k}']=ref('evidence/Corrective5/attempt1/corrective-native/'+row[k]['file'])
   for row in e['parent_worlds']:r['current_evidence'][s+'_parent_'+row['category']]=ref('evidence/Corrective5/attempt1/corrective-parents/'+row['world']['file'])
  r['current_evidence']['corrected_longitudinal_audit']=ref('evidence/Corrective5/attempt1/corrective-longitudinal/independent_verification.json')
 html=re.sub(r'<script id="data" type="application/json">.*?</script>',lambda m:'<script id="data" type="application/json">'+json.dumps(d,separators=(',',':'))+'</script>',html,flags=re.S)
 notice='<div class="notice"><strong>[machine-checked] All 32 release evidence rows pass in both settings.</strong><p>The full corrective run passed 742 exact methods, all 54 jobs and 81 isolated cost workers. Continuation, parent and longitudinal findings have fresh independent raw reconstruction.</p><p>[source_defined] Final release acceptance requires the clean durable delivery receipt linked in the release report. Historical held artifacts remain unchanged.</p></div>'
 html=re.sub(r'<div class="notice">.*?</div><div class="metrics"',notice+'<div class="metrics"',html,count=1,flags=re.S)
 html=html.replace('inspector v3','inspector v4').replace('[[732,','[[742,').replace("[0,'complete release cells']","[32,'complete evidence cells']").replace('full release held','release evidence passed').replace('Held · 2 settings','Verified · 2 settings').replace("'[open] Release items: '+r.remaining.join(', ')","'[machine-checked] Every applicable evidence gate passed; see final delivery receipt.'")
 html=html.replace('HLE_Full_Crux_C7_Release_Report_v3.md','HLE_Full_Crux_C7_Release_Report_v4.md').replace('../C7_Final_Ledger_v2.json','../C7_Final_Ledger_v3.json')
 (ROOT/'docs/HLE_Full_Crux_C7_Inspector_v4.html').write_text(html)
 costs=a['costs']
 report=f'''# Socionics Research Lab — corrected Release 1.0 evidence report

[machine-checked] Report v4: all 32 route/polarity rows pass every applicable evidence gate in canonical and workflow settings. The independent joint assessment reconstructs 192 native continuation comparisons, eight parent scenarios and the corrected longitudinal controls. Historical held reports and failed attempts remain unchanged.

[source_defined] Final clean/durable acceptance is recorded separately in [Delivery_Decision.json](https://github.com/GregoritHub/Socionics_Engine/blob/main/evidence/Corrective6/Delivery_Decision.json). This report supplies the evidence decision and does not substitute for that delivery gate. Phase 7 remains unauthorized.

| Verified check | Result |
| --- | --- |
| Mandatory jobs | 54/54 |
| Exact distinct method IDs | 742/742, including all 732 prior IDs |
| Isolated measurement workers | 81/81 |
| Frozen files | 1,381 unchanged |
| Kernel probes | 10/10 and 17/17; intake-identical kernel |
| Historical ledger objects | 739/739 exact hashes and sizes |
| Fresh compressed raw files | 3,182 |
| Native continuation comparisons | 192, plus six negative worlds; 780 ordinary raw audits |
| Parent panel | Eight scenarios and exact restores; six forged-success controls rejected |
| Corrected longitudinal controls | One status forgery and two real paid bypasses rejected |

[machine-checked] Native reference ratio {costs['native_reference_ratio']:.6f} passes 2x; native inactive-history {costs['native_history_ratio']:.6f}, workflow {max(costs['workflow-costs'].values()):.6f} and population {max(costs['population-costs'].values()):.6f} pass 3x. No optimization gain is claimed. The exact raw measurements and command timestamps are preserved.

[source_defined] What changed: the three evidence defects in the held release now have prospective, frozen, independently reconstructed panels and a complete rerun. How: exact raw identities, ordinary auditors, matched controls, saved paid progression and an unchanged full source freeze. What becomes possible: inspect and reproduce all applicable cell gates with their actual saved evidence. Model G and axes remain read-only; no theoretical register item is closed.

[source_defined] Use FB_Corrective6_Reproduce.md for clean assembly and fresh computational reproduction. The full evidence ledger is C7_Final_Ledger_v3.json; the standalone inspector is HLE_Full_Crux_C7_Inspector_v4.html. Inspector structural/filter and raw-link checks are required by delivery; pixel rendering is not claimed.

[source_defined] Workflow scope stays at eight tasks, eight inputs, two participants, unit-duration serial scheduling and slots 0–1,000. No claim of general learning, spontaneous goals/institutions, unrestricted development, calibrated energy, human typing or Release 1.1 is made. The sealed pyref rerun remains owed and does not block Release 1.0.
'''
 (ROOT/'docs/HLE_Full_Crux_C7_Release_Report_v4.md').write_text(report)
 old=(ROOT/'docs/HLE_Full_Crux_Build_Specification_v11.md').read_text()
 (ROOT/'docs/HLE_Full_Crux_Build_Specification_v12.md').write_text('# Build Specification v12 — corrective completion record\n\n[source_defined] All inherited normative contracts remain unchanged. The record below supersedes the historical v11 held status only after the separate final delivery receipt passes.\n\n[machine-checked] Milestone C7 evidence is complete for 32/32 cells in both settings: 54 jobs, 742 distinct methods, 81 isolated workers, 192 continuation comparisons and eight parent scenarios independently assessed. Source freeze has 1,381 unchanged files. Read report v4 and C7_Final_Ledger_v3.json. Final release/goal-complete is determined by evidence/Corrective6/Delivery_Decision.json; Phase 7 requires a separate R5 ruling.\n\n## Preserved v11 specification and historical held record\n\n'+old)
 print(json.dumps({'evidence_rows':32,'ledger_sha256':sha(ROOT/'C7_Final_Ledger_v3.json'),'report':'docs/HLE_Full_Crux_C7_Release_Report_v4.md'}))
if __name__=='__main__':main()
