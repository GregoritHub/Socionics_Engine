"""Verify FB0.2 against its frozen protocol and the unchanged delivered source."""
import hashlib,json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def read(p):return json.loads((R/p).read_text())
def digest(p):return hashlib.sha256((R/p).read_bytes()).hexdigest()
base='7a772caf6022b8a7fac8bb6a49cdb2db5430b679'
protocol=read('contracts/C7_Final_Protocol_v1.json')
assert [x['section'] for x in protocol['requirements']]==['9.'+str(i) for i in range(1,13)]
for row in protocol['requirements']:
 assert all(row.get(k) for k in ('panel','denominator','seeds','control','auditor','pass_condition'))
assert len(set(protocol['types']))==16
assert protocol['costs']['inactive_history_ratio_max']==[3,1]
assert protocol['costs']['unchanged_native_ratio_max']==[2,1]
assert protocol['population']['seeds']==[17,43,89]
assert protocol['population']['episodes_per_actor']==24 and len(set(protocol['population']['actors']))==2
assert protocol['population']['diagnostic_worlds']==1
plan=(R/'project_sources/HLE_Final_Build_Plan_v1_0.txt').read_text()
assert protocol['workflow_domain_bounds_verbatim'] in plan
old=json.loads(subprocess.check_output(['git','show',base+':contracts/Contract_Manifest.json'],cwd=R))
new=read('contracts/Contract_Manifest.json');assert new['files'][:-1]==old['files']
entry=new['files'][-1];assert entry['path']=='contracts/C7_Final_Protocol_v1.json'
assert digest(entry['path'])==entry['sha256'] and (R/entry['path']).stat().st_size==entry['bytes']
assert {k:v for k,v in new.items() if k!='files'}=={k:v for k,v in old.items() if k!='files'}
m=read('C7_Second_Setting_Delivered_Source_Manifest_v1.json')
differences=[p for p,h in m.items() if digest(p)!=h]
assert differences==['contracts/Contract_Manifest.json'],differences
py=[p for p in m if p.endswith('.py')];assert all(digest(p)==m[p] for p in py)
f=read('C7_Second_Setting_Source_Freeze_v4.json');assert all(digest(p)==h for p,h in f.items())
assert all(digest(p)==h for p,h in read('evidence/FB0.2/pre_gate_freeze.json').items())
register=(R/'docs/FB_Job_Register.md').read_text(); rows=[line for line in register.splitlines() if line.startswith('| ') and line.split('|')[1].strip()[:1].isdigit()]
assert len(rows)==22 and all(not line.split('|')[4].strip() for line in rows)
result=dict(status='probe',passed=True,sections=12,numbered_jobs=22,source_manifest_entries=len(m),unchanged_entries=len(m)-1,changed_metadata_only=differences,inherited_python_files_unchanged=len(py),source_freeze_v4_entries=len(f),protocol_sha256=entry['sha256'],manifest_original_entries_preserved=True,engine_code_changes=0,release_complete=False)
print(json.dumps(result,indent=2))
