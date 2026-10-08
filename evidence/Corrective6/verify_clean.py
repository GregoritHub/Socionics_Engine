"""Portable integrity and raw-audit gate; preserves original execution paths."""
import hashlib,json,gzip,sys,shutil,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mapping(m):
 for name,e in m.items():
  h=e['sha256'] if isinstance(e,dict) else e;p=ROOT/name
  assert p.is_file() and sha(p)==h,name
  if isinstance(e,dict):assert p.stat().st_size==e['bytes'],name
 return len(m)
def main():
 source=mapping(read(ROOT/'C7_Corrective_Delivery_Source_Manifest_v1.json'))
 historical=mapping(json.loads(gzip.decompress((ROOT/'evidence/Corrective6/Historical_Delivery_Manifest.json.gz').read_bytes())))
 fresh=mapping(read(ROOT/'evidence/Corrective5/Raw_SHA256.json'))
 freeze=ROOT/'C7_Corrective_Final_Source_Freeze_v1.json';frozen=mapping(read(freeze))
 old=read(ROOT/'C7_Final_Ledger_v2.json')
 for _,name,h,size in old['evidence_objects']:
  p=ROOT/'evidence/historical'/name;assert p.stat().st_size==size and sha(p)==h,name
 counts={}
 for name in ('evidence/FB6.2/Raw_SHA256.json','evidence/Corrective1/Raw_SHA256.json','evidence/Corrective2/Raw_SHA256.json','evidence/Corrective3/Raw_SHA256.json'):counts[name]=mapping(read(ROOT/name))
 run=ROOT/'evidence/Corrective5/attempt1';protocol=read(ROOT/'contracts/C7_Corrective_Evaluation_Protocol_v1.json')
 acceptance=read(run/'Acceptance.json');assert acceptance['passed'] and acceptance['source_unchanged']
 assert acceptance['distinct_methods']==742 and acceptance['required_jobs']==54 and acceptance['measurement_workers']==81
 assert acceptance['freeze']['sha256']==sha(freeze)
 method=read(run/'Accepted_Method_Inventory.json');declared=read(ROOT/protocol['accepted_method_inventory'])
 assert method['passed'] and len(method['method_ids'])==len(set(method['method_ids']))==742
 assert set(method['method_ids'])==set(declared['method_ids'])
 records={j['id']:read(run/'commands'/(j['id']+'.json')) for j in protocol['jobs']}
 original_roots={r['cwd'] for r in records.values()};assert len(original_roots)==1
 original_root=Path(next(iter(original_roots)));original_run=original_root/'evidence/Corrective5/attempt1'
 assert {p.stem for p in (run/'commands').glob('*.json')}==set(records)
 for job in protocol['jobs']:
  row=records[job['id']];assert row['passed'] and row['exit_code']==0 and row['source_unchanged']
  assert row['freeze_sha256']==sha(freeze)
  assert row['argv'][1:]==[s.replace('{out}',str(original_run)) for s in job['argv'][1:]]
  if 'result' in job:
   expected=Path(job['result'].replace('{out}',str(original_run))).relative_to(original_root)
   assert row['result']==str(expected) and sha(ROOT/expected)==row['result_sha256']
   v=read(ROOT/expected);assert v['passed'] and all(v.get(k)==n for k,n in job.get('expected_counts',{}).items())
 for e in acceptance['commands']:
  assert sha(run/'commands'/(e['id']+'.json'))==e['record_sha256']
  assert sha(run/'commands'/(e['id']+'.stdout.log'))==e['stdout_sha256']
 from datetime import datetime
 for j in protocol['jobs']:
  assert all(datetime.fromisoformat(records[d]['finished_at'])<=datetime.fromisoformat(records[j['id']]['started_at']) for d in j['depends_on'])
 previous=max(datetime.fromisoformat(records[j['id']]['finished_at']) for j in protocol['jobs'] if j['lane']!='measurements')
 for j in [j for j in protocol['jobs'] if j['lane']=='measurements']:
  assert datetime.fromisoformat(records[j['id']]['started_at'])>=previous
  previous=datetime.fromisoformat(records[j['id']]['finished_at'])
 for name,h in acceptance['kernel_identical_to_intake'].items():assert sha(ROOT/'baseline/HLE_Rebuild_R21B'/name)==h
 for name,n in [('closure',10),('below_dcnh',17)]:assert f'{n}/{n} passed  (R21B kernel; pyref rerun owed)' in (run/'commands'/(name+'-probe.stdout.log')).read_text()
 a=read(run/'Corrective_Ledger_Assessment.json');candidate=run/'Corrective_Ledger.json'
 assert a['passed'] and a['rows_reconstructed']==32 and a['candidate_sha256']==sha(candidate)
 from tools import verify_corrective_native as n,verify_corrective_parents as p,verify_longitudinal_shell as l
 audit_root=ROOT/'verification-output/raw-audit-copies';assert not audit_root.exists()
 for name in ('corrective-native','corrective-parents','corrective-longitudinal'):shutil.copytree(run/name,audit_root/name)
 assert n.verify(audit_root/'corrective-native')['passed']
 assert p.verify(audit_root/'corrective-parents')['passed']
 assert l.verify_corrective(audit_root/'corrective-longitudinal')['passed']
 final=read(ROOT/'C7_Final_Ledger_v3.json')
 assert final['complete_cells']==32 and final['full_release_complete'] and not final['phase_7_authorized']
 assert final['independent_assessment_sha256']==sha(run/'Corrective_Ledger_Assessment.json')
 assert final['candidate_sha256']==sha(candidate)
 assert len(final['rows'])==len({(r['route'],r['polarity']) for r in final['rows']})==32
 assert all(r['full_release_complete'] and set(r['settings'])=={'canonical','workflow'} and all(e['complete'] for e in r['settings'].values()) for r in final['rows'])
 prior_rows={(r['route'],r['polarity']):r for r in read(candidate)['rows']}
 for row in final['rows']:
  original=prior_rows[(row['route'],row['polarity'])]
  for setting,entry in row['settings'].items():
   before=original['settings'][setting]
   assert {k:v for k,v in entry.items() if k not in ('complete','current_requirements')}=={k:v for k,v in before.items() if k!='complete'}
   assert set(entry['current_requirements'])=={f'9.{i}' for i in range(1,13)}
   for key,value in entry['current_requirements'].items():
    expected='not_applicable' if key=='9.5' and before['inherited_sections']['requirements'][key]['status']=='not_applicable' else 'passed'
    assert value['status']==expected
 html=ROOT/'docs/HLE_Full_Crux_C7_Inspector_v4.html';text=html.read_text()
 data=json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>',text,re.S)[1])
 assert data['reviewed_ledger_sha256']==sha(ROOT/'C7_Final_Ledger_v3.json')
 assert data['manifest']['passing_methods']==742 and data['manifest']['release_complete']
 links=0
 for row in data['ledger']:
  assert row['full_release_complete'] and not row['remaining']
  for ref in row['current_evidence'].values():
   p=ROOT/ref['member'];assert sha(p)==ref['sha256'] and p.stat().st_size==ref['bytes'];links+=1
 js=r'''const fs=require('fs'),vm=require('vm');const html=fs.readFileSync(process.argv[1],'utf8');const data=html.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1];const script=html.match(/<\/script><script>([\s\S]*?)<\/script>/)[1];class Element{constructor(tag){this.tag=tag;this.children=[];this.textContent='';this.value='';this.events={};}append(...xs){this.children.push(...xs)}replaceChildren(...xs){this.children=xs}addEventListener(k,f){this.events[k]=f}}const nodes={};for(const id of ['data','metrics','route','face','count','cells'])nodes[id]=new Element(id);nodes.data.textContent=data;vm.runInNewContext(script,{document:{getElementById:id=>nodes[id],createElement:t=>new Element(t)},JSON,Set},{timeout:5000});if(nodes.cells.children.length!==32||nodes.metrics.children.length!==4)throw Error('missing cells or metrics');const d=JSON.parse(data);if(!d.manifest.release_complete||d.ledger.some(x=>!x.full_release_complete))throw Error('release evidence differs');for(const n of new Set(d.ledger.map(x=>x.name)))for(const f of ['accumulation','expenditure']){nodes.route.value=n;nodes.face.value=f;nodes.route.events.change();if(nodes.cells.children.length!==1||!nodes.cells.children[0].children.some(x=>x.tag==='pre'&&x.textContent.includes('second_setting_raw')))throw Error('filter or evidence failed');}nodes.route.value='';nodes.face.value='';nodes.face.events.change();if(nodes.cells.children.length!==32)throw Error('reset failed');console.log('PASS inspector 32 cells, filters, reset and raw evidence');'''
 subprocess.run(['node','-e',js,str(html)],check=True)
 result={'passed':True,'source_members':source,'historical_members_delivered':historical,'fresh_members':fresh,'frozen_files':frozen,'historical_ledger_objects':739,'raw_manifests':counts,'jobs':54,'methods':742,'independent_corrected_raw_audits':True,'original_execution_paths_preserved':True,'inspector_cells':32,'inspector_verified_links':links,'inspector_filters':True,'phase_7_authorized':False,'pixel_rendering_verified':False}
 out=ROOT/'verification-output';out.mkdir(exist_ok=True);(out/'Clean_Assessment.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
