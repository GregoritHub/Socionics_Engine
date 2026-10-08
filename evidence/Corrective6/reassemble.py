"""Reassemble exact immutable historical containers; never executes the engine."""
import argparse,hashlib,json,zipfile,tarfile,io
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[2]
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(root,name,data):
 q=PurePosixPath(name)
 assert not q.is_absolute() and '..' not in q.parts and '\\' not in name,name
 p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():assert p.read_bytes()==data,('collision',str(p))
 else:p.write_bytes(data)
def unzip(z,root):
 for i in z.infolist():
  assert ((i.external_attr>>16)&0o170000)!=0o120000,i.filename
  if not i.is_dir():write(root,i.filename,z.read(i))
def main(archives,target):
 assert not target.exists(),'Clean target must not already exist'
 target.mkdir(parents=True);history=target/'evidence/historical';history.mkdir(parents=True)
 verified=[]
 specs=json.loads((ROOT/'evidence/FB6.3/Durable_Components.json').read_text())['archives']
 for a in specs:
  matches=list(archives.rglob(a['file_name']));assert len(matches)==1,a['file_name']
  p=matches[0];assert p.stat().st_size==a['bytes'] and digest(p)==a['sha256'],a['key']
  suffix=a['extract_to'].removeprefix('evidence/historical').lstrip('/')
  with zipfile.ZipFile(p) as z:
   assert z.testzip() is None
   if a['key']=='fb6.2':unzip(z,target);unzip(z,history)
   else:unzip(z,history/suffix)
   if a['key']=='c7_original':
    with zipfile.ZipFile(io.BytesIO(z.read('inherited/HLE_Full_Crux_C7_Evidence_v1.zip'))) as n:
     assert n.testzip() is None;unzip(n,history)
  verified.append(a)
 for num in (1,2,3):
  a=json.loads((ROOT/f'evidence/Corrective{num}/Raw_Evidence_Index.json').read_text())['archive']
  matches=list(archives.rglob(a['file_name']));assert len(matches)==1
  p=matches[0];assert p.stat().st_size==a['bytes'] and digest(p)==a['sha256']
  if p.suffix=='.zip':
   with zipfile.ZipFile(p) as z:
    assert z.testzip() is None;unzip(z,target);unzip(z,history)
  else:
   with tarfile.open(p) as t:
    for i in t:
     assert i.isfile(),i.name
     data=t.extractfile(i).read();write(target,i.name,data);write(history,i.name,data)
  verified.append(dict(a,key=f'corrective{num}'))
 objects=json.loads((ROOT/'C7_Final_Ledger_v2.json').read_text())['evidence_objects']
 for _,name,h,size in objects:assert digest(history/name)==h and (history/name).stat().st_size==size,name
 counts={}
 for name in ('evidence/FB6.2/Raw_SHA256.json','evidence/Corrective1/Raw_SHA256.json','evidence/Corrective2/Raw_SHA256.json','evidence/Corrective3/Raw_SHA256.json'):
  m=json.loads((target/name).read_text())
  for path,e in m.items():
   h=e['sha256'] if isinstance(e,dict) else e
   assert digest(target/path)==h,path
   if isinstance(e,dict):assert (target/path).stat().st_size==e['bytes']
  counts[name]=len(m)
 dep='evidence/FB5.6/attempt4/matrix/iee-04-same-target-recurrence.json.gz'
 write(target,dep,(history/dep).read_bytes())
 manifest={str(p.relative_to(target)):{'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(target.rglob('*')) if p.is_file()}
 out=target/'evidence/Corrective6';out.mkdir(parents=True,exist_ok=True)
 (out/'Historical_Delivery_Manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 result={'passed':True,'archives_verified':verified,'historical_members':len(objects),'raw_manifests':counts,'delivered_members':len(manifest),'source_instruction':'Clean reassembly of all immutable indexed components; no reconstructed history or overwritten evidence.'}
 (out/'Historical_Reassembly_Assessment.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k!='archives_verified'}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('archives',type=Path);p.add_argument('target',type=Path);a=p.parse_args();main(a.archives.resolve(),a.target.resolve())
