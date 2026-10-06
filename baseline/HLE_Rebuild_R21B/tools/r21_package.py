"""Package the evaluated R21 candidate while retaining its open release status."""
import argparse,hashlib,json,shutil,subprocess,sys,tempfile
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[1]

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def meta(name,path):return {'path':name,'bytes':path.stat().st_size,'sha256':sha(path)}

def write_archive(dest,entries,prefix):
    with ZipFile(dest,'w',compression=ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
        for name,path in sorted(entries):
            info=ZipInfo(prefix+'/'+name,date_time=(2026,9,18,0,0,0));info.compress_type=ZIP_DEFLATED;info.external_attr=0o644<<16
            with path.open('rb') as src,z.open(info,'w',force_zip64=True) as dst:shutil.copyfileobj(src,dst,1024*1024)
    with ZipFile(dest) as z:
        if z.testzip() is not None:raise ValueError('archive CRC failure')
    return {'archive':dest.name,'bytes':dest.stat().st_size,'sha256':sha(dest),'entries':len(entries),'crc_verified':True}

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    decision=json.loads((ROOT/'evidence/r21/release_decision.json').read_text())
    if decision['milestone_complete'] or not decision['panel']['denominator_complete']:
        raise ValueError('this package must record the executed, unsuccessful v1 evaluation')
    if not decision['validation']['passed'] or not decision['replay_passed']:
        raise ValueError('code/replay evidence is incomplete')
    keep=lambda f:f.is_file() and '__pycache__' not in f.parts and f.suffix not in ('.pyc','.pyo','.tmp')
    evidence=[]
    for folder in ('evidence/r21','docs/r21','tests_r21','hle'):
        evidence.extend((str(f.relative_to(ROOT)),f) for f in (ROOT/folder).rglob('*') if keep(f))
    evidence.extend((str(f.relative_to(ROOT)),f) for f in (ROOT/'tools').glob('r21_*.py'))
    for name in ('acceptance_v1.json','Plan_v1.md','source_ledger_v1.json'):
        f=ROOT/'docs/r12'/name;evidence.append((str(f.relative_to(ROOT)),f))
    em=ROOT/'evidence/r21/evidence_manifest.json'
    smoke=ROOT/'evidence/r21/fresh_archive_smoke.json'
    evidence=[pair for pair in evidence if pair[1] not in (em,smoke)]
    files=[f for f in ROOT.rglob('*') if keep(f) and f not in (ROOT/'release_manifest.json',em,smoke)]
    # New population raw traces are in the evidence archive. Preserve all
    # inherited files and all R21 checkpoints/reports in the source archive.
    external=[f for f in files if 'r21' in f.parts and f.name.endswith('.transactions.jsonl.gz')
              and f.parent.name in ('panel','panel_initial')]
    selected=[f for f in files if f not in external]
    m=ROOT/'release_manifest.json'
    m.write_text(json.dumps({'schema':'r21-source-manifest-v1','milestone':'R21','version':'1.11.0rc1',
        'parent_R21_complete':False,'parent_progress':[9,10],'remaining':['R21A','R21B','R21C'],
        'raw_evidence_archives':['HLE_New_Build_Step_R21_Evidence_v1_Part_1.zip','HLE_New_Build_Step_R21_Evidence_v1_Part_2.zip'],
        'files':[meta(str(f.relative_to(ROOT)),f) for f in sorted(selected)],
        'delivered_in_evidence_archive':[meta(str(f.relative_to(ROOT)),f) for f in sorted(external)]},indent=2)+'\n')
    source=write_archive(out/'HolonicLivingEngine_Rebuild_R21_v1.zip',[(str(f.relative_to(ROOT)),f) for f in selected+[m]],'HLE_Rebuild_R21')
    print(json.dumps({'source_built':source}),flush=True)
    with tempfile.TemporaryDirectory(prefix='r21-extracted-',dir=out) as temporary:
        with ZipFile(out/source['archive']) as z:z.extractall(temporary)
        extracted=Path(temporary)/'HLE_Rebuild_R21'
        script='''import gzip,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'tools')
from hle.closure import ClosureWorld
from hle.closure_reference import compare
from hle.world_records import Tick
from r21_workloads import run_episode
from r21_reference import resource_audit
m=json.loads(Path('release_manifest.json').read_text())
for row in m['files']:
    p=Path(row['path'])
    if hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:raise AssertionError(str(p))
with gzip.open('evidence/r20/panel/continued_r19.checkpoint.json.gz','rt') as f:cp=f.read()
w=ClosureWorld.restore(cp)
exact=w.checkpoint()==cp
raw=compare(w)['passed']
length=len(w._journal);w.execute(Tick('r21:extracted-archive-continuation'))
z,meta=run_episode('sli',11,0)
result={'manifest_files_verified':len(m['files']),'original_checkpoint_exact':exact,
        'raw_reference_agreement':raw,'new_event_accepted':len(w._journal)==length+1,
        'zero_budget_deferred':meta['resource_stop'] is not None and not meta['cleared'],
        'zero_budget_unfinished_jobs':resource_audit(z)['unfinished_count']}
result['passed']=all(result[k] for k in ('original_checkpoint_exact','raw_reference_agreement','new_event_accepted','zero_budget_deferred')) and result['zero_budget_unfinished_jobs']==1
print(json.dumps(result))
if not result['passed']:raise SystemExit(1)
'''
        run=subprocess.run([sys.executable,'-c',script],cwd=extracted,capture_output=True,text=True)
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        verification=json.loads(run.stdout);verification['source_archive']=source
        smoke.write_text(json.dumps(verification,indent=2)+'\n')
        print(json.dumps({'fresh_archive_smoke':verification}),flush=True)
    evidence.append(('evidence/r21/fresh_archive_smoke.json',smoke))
    em.write_text(json.dumps({'schema':'r21-evidence-manifest-v1','milestone_complete':False,
        'files':[meta(name,path) for name,path in sorted(evidence)]},indent=2)+'\n')
    parts=[[],[]];sizes=[0,0]
    for name,path in sorted(evidence,key=lambda pair:(-pair[1].stat().st_size,pair[0])):
        index=min(range(2),key=lambda i:sizes[i]);parts[index].append((name,path));sizes[index]+=path.stat().st_size
    ev=[]
    for index,entries in enumerate(parts,1):
        entries.append(('evidence/r21/evidence_manifest.json',em))
        ev.append(write_archive(out/f'HLE_New_Build_Step_R21_Evidence_v1_Part_{index}.zip',entries,'HLE_R21_Evidence'))
    shutil.copyfile(ROOT/'docs/r21/Step_R21_Report.md',out/'HLE_New_Build_Step_R21_Report_v1.md')
    shutil.copyfile(ROOT/'docs/r21/Progress_After_R21.md',out/'HLE_New_Build_Progress_and_Remaining_Steps_After_R21.md')
    (out/'archive_verification.json').write_text(json.dumps({'source':source,'evidence':ev},indent=2)+'\n')
    print(json.dumps({'source':source,'evidence':ev},indent=2))
if __name__=='__main__':main()
