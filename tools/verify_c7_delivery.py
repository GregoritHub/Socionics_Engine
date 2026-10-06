import sys,json,hashlib,zipfile,re
from pathlib import Path
root=Path(sys.argv[1]);out=Path(sys.argv[2]);prior=Path(sys.argv[3]);e=root/'evidence_c7_settings'
def read(p):return json.loads(p.read_text())
def sha(raw):return hashlib.sha256(raw).hexdigest()
for name in ('unit_delivery','matrix_delivery','regression_delivery','cost_delivery','native_cost_delivery'):
 d=read(e/name/'summary.json');assert d['passed'] and d['source_unchanged'],name
raw=read(e/'matrix_delivery/independent_raw_verification.json');assert raw['passed'] and raw['ordinary_worlds']==512 and raw['deliberate_controls']==32
ids=[r['test_id'] for r in read(e/'unit_delivery/summary.json')['rows']]
for package in read(e/'regression_delivery/summary.json')['packages']:
 assert package['summary']['passed'];ids += [r['test_id'] for r in package['summary']['rows']]
assert len(ids)==len(set(ids))==625
frozen=read(root/'C7_Second_Setting_Source_Freeze_v4.json')
assert all(sha((root/k).read_bytes())==v for k,v in frozen.items())
ledger=read(root/'C7_Second_Setting_Ledger_v1.json')
assert len(ledger)==32 and len({(x['name'],x['face']) for x in ledger})==32
assert all(x['settings_gate']['established']==2 and x['type_cases']==16 and not x['full_release_complete'] for x in ledger)
html=(out/'HLE_Full_Crux_C7_Inspector_v2.html').read_text()
data=json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>',html,re.S)[1])
assert data['ledger']==ledger and data['manifest']['passing_methods']==625
assert read(e/'inspector_delivery/summary.json')['passed']
with zipfile.ZipFile(out/'HLE_Full_Crux_C7_Source_v2.zip') as z:
 assert z.testzip() is None
 prefix='HLE_Full_Crux_C7_Source_v2/'
 source=read(root/'C7_Second_Setting_Delivered_Source_Manifest_v1.json')
 for name,digest in source.items():assert sha(z.read(prefix+name))==digest,name
 assert len(z.namelist())==len(source)+1
 for n in ['HLE_Full_Crux_C7_Release_Candidate_Report_v2.md','HLE_Full_Crux_Build_Specification_v10.md']:
  assert z.read(prefix+'docs/'+n)==(out/n).read_bytes()
with zipfile.ZipFile(out/'HLE_Full_Crux_C7_Evidence_v2.zip') as z:
 assert z.testzip() is None
 assert sha(z.read('inherited/HLE_Full_Crux_C7_Evidence_v1.zip'))==sha(prior.read_bytes())
 for row in raw['rows']:
  assert sha(z.read('evidence_c7_settings/matrix_delivery/'+row['file']))==row['sha256'],row['file']
 for row in ledger:
  for proof in [row['second_setting_raw'],row['control']['raw']]:
   blob=z.read('evidence_c7_settings/matrix_delivery/'+proof['file'])
   assert sha(blob)==proof['sha256'] and len(blob)==proof['bytes']
checks=read(out/'HLE_Full_Crux_C7_Delivery_Checksums_v2.json')
for x in checks['files']:
 p=out/x['file'];assert p.stat().st_size==x['bytes'] and sha(p.read_bytes())==x['sha256']
summary=dict(passed=True,distinct_methods=625,cells=32,types=16,raw_worlds=544,source_files=len(source)+1,source_freeze_files=len(frozen),archive_crc=True,source_and_evidence_hashes=True,inherited_evidence_unchanged=True,inspector_ledger_matches=True)
print(json.dumps(summary,indent=2))
if '--record' in sys.argv:
 p=e/'delivery_validation';p.mkdir(exist_ok=True);(p/'summary.json').write_text(json.dumps(summary,indent=2))
