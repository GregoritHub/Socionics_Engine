from pathlib import Path,PurePosixPath
import json,hashlib,zipfile,tarfile,shutil
B=Path('/workspace/scratch/07b063671898');R=B/'Socionics_Engine';O=B/'corrective-reassembly'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
idx=json.loads((R/'evidence/FB6.3/Durable_Components.json').read_text())['archives']
report=[]
def save(name,data,root):
 p=PurePosixPath(name);assert not p.is_absolute() and '..' not in p.parts and '\\' not in name
 d=root/name;d.parent.mkdir(parents=True,exist_ok=True)
 if d.exists():assert d.read_bytes()==data,('collision',str(d))
 else:d.write_bytes(data)
for a in idx:
 p=next((B/'corrective-archives').rglob(a['file_name']));assert sha(p)==a['sha256'] and p.stat().st_size==a['bytes']
 if a['key'] not in ('c2','c7_original','fb6.2'):
  suffix=a['extract_to'].removeprefix('evidence/historical').lstrip('/')
  with zipfile.ZipFile(p) as z:
   for i in z.infolist():
    assert ((i.external_attr>>16)&0o170000)!=0o120000
    if not i.is_dir():save(i.filename,z.read(i),O/suffix)
 report.append({'key':a['key'],'sha256':a['sha256'],'bytes':a['bytes'],'verified':True})
for num in (1,2,3):
 a=json.loads((R/f'evidence/Corrective{num}/Raw_Evidence_Index.json').read_text())['archive'];p=next((B/'corrective-archives').rglob(a['file_name']))
 assert sha(p)==a['sha256'] and p.stat().st_size==a['bytes']
 if p.suffix=='.zip':
  with zipfile.ZipFile(p) as z:
   for i in z.infolist():
    assert ((i.external_attr>>16)&0o170000)!=0o120000
    if not i.is_dir():save(i.filename,z.read(i),O)
 else:
  with tarfile.open(p) as t:
   for i in t:
    assert i.isfile(),i.name
    save(i.name,t.extractfile(i).read(),O)
 report.append({'key':f'corrective{num}','sha256':a['sha256'],'bytes':a['bytes'],'verified':True})
dep='evidence/FB5.6/attempt4/matrix/iee-04-same-target-recurrence.json.gz'
save(dep,(O/dep).read_bytes(),R)
checks={}
for name in ('evidence/FB6.2/Raw_SHA256.json','evidence/Corrective1/Raw_SHA256.json','evidence/Corrective2/Raw_SHA256.json','evidence/Corrective3/Raw_SHA256.json'):
 m=json.loads((O/name).read_text());assert isinstance(m,dict)
 for path,digest in m.items():assert sha(O/path)==digest,path
 checks[name]=len(m)
(B/'.corrective-transfer/support-results.json').write_text(json.dumps({'archives':report,'raw_manifests':checks},indent=2)+'\n')
print(json.dumps({'archives_verified':len(report),'raw_manifests':checks}))
