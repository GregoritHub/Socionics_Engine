from pathlib import Path, PurePosixPath
import json,hashlib,zipfile,io,collections
BASE=Path('/workspace/scratch/07b063671898')
REPO=BASE/'Socionics_Engine'
OUT=BASE/'corrective-reassembly'
OUT.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
idx=json.loads((REPO/'evidence/FB6.3/Durable_Components.json').read_text())['archives']
objects=json.loads((REPO/'C7_Final_Ledger_v2.json').read_text())['evidence_objects']
wanted={(x[2],x[3]) for x in objects}
found=collections.defaultdict(list); archives=[]
def extract(z,key,prefix=''):
 for info in z.infolist():
  p=PurePosixPath(info.filename)
  assert not p.is_absolute() and '..' not in p.parts and '\\' not in info.filename
  assert ((info.external_attr>>16)&0o170000)!=0o120000
  if info.is_dir():continue
  data=z.read(info);digest=sha(data);name=info.filename
  if prefix and name.startswith(prefix):name=name[len(prefix):]
  dest=OUT/name;dest.parent.mkdir(parents=True,exist_ok=True)
  if dest.exists():assert dest.read_bytes()==data, ('collision',name)
  else:dest.write_bytes(data)
  if (digest,len(data)) in wanted:found[(digest,len(data))].append({'archive':key,'member':info.filename,'extracted':name})
  if info.filename=='inherited/HLE_Full_Crux_C7_Evidence_v1.zip':
   with zipfile.ZipFile(io.BytesIO(data)) as nested:extract(nested,key+':nested-v1')
for key in ('c2','c7_original','fb6.2'):
 a=next(x for x in idx if x['key']==key);p=next((BASE/'corrective-archives').rglob(a['file_name']))
 assert p.stat().st_size==a['bytes'] and hashlib.file_digest(p.open('rb'),'sha256').hexdigest()==a['sha256']
 archives.append(a)
 with zipfile.ZipFile(p) as z:extract(z,key)
c5=json.loads((REPO/'C6_Inherited_Archive_Index_v1.json').read_text())
p=BASE/'c5-backup-check/HLE/HLE_Full_Crux_C5_Source_v1.zip'
assert hashlib.file_digest(p.open('rb'),'sha256').hexdigest()==c5['sha256']
with zipfile.ZipFile(p) as z:
 for x in c5['excluded_raw_evidence']:
  name='HLE_Full_Crux_C5_Source_v1/'+x['path'];data=z.read(name)
  assert sha(data)==x['sha256'] and len(data)==x['bytes']
  if (x['sha256'],x['bytes']) in wanted:
   dest=OUT/x['path'];dest.parent.mkdir(parents=True,exist_ok=True)
   if dest.exists():assert dest.read_bytes()==data
   else:dest.write_bytes(data)
   found[(x['sha256'],x['bytes'])].append({'archive':'c5-source','member':name,'extracted':x['path']})
recovered=[];missing=[]
for key,name,digest,size in objects:
 matches=found[(digest,size)]
 if not matches:missing.append([key,name,digest,size]);continue
 src=OUT/matches[0]['extracted'];dst=OUT/name;dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists():assert sha(dst.read_bytes())==digest and dst.stat().st_size==size
 else:dst.write_bytes(src.read_bytes())
 recovered.append({'archive_key':key,'ledger_path':name,'sha256':digest,'bytes':size,'recovered_from':matches})
report={'archives_verified':archives,'c5_source_sha256':c5['sha256'],'c5_index_verified':len(c5['excluded_raw_evidence']),'required':len(objects),'verified':len(recovered),'missing':missing,'recovered':recovered}
(BASE/'.corrective-transfer/recovery.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'required':len(objects),'verified':len(recovered),'missing_by_archive':dict(collections.Counter(x[0] for x in missing))}),flush=True)
