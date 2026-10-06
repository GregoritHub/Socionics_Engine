"""Package the amended contract without relabeling the failed R21 release."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from r21_package import write_archive, meta, sha


def main():
    parser = argparse.ArgumentParser();parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args();out = args.out.resolve();out.mkdir(parents=True, exist_ok=True)
    decision = json.loads((ROOT/'evidence/r21a/decision.json').read_text())
    if not decision['R21A_complete'] or decision['R21_complete']:
        raise ValueError('package requires complete R21A and open R21')
    inherited = json.loads((ROOT/'docs/r21a/Input_Manifest.json').read_text())['files']
    expected = {'README.md', 'hle/__init__.py', 'hle/clearance.py', 'hle/clearance_demo.py',
                'hle/clearance_records.py', 'hle/clearance_reference.py', 'hle/clearance_runtime.py'}
    changed = [];preserved = 0
    for row in inherited:
        path = ROOT/row['path']
        if not path.is_file():raise ValueError('missing inherited file: '+row['path'])
        if row['path']=='release_manifest.json':
            if sha(ROOT/'docs/r21a/release_manifest.json.before')!=row['sha256']:
                raise ValueError('historical R21 source manifest changed')
            continue
        if sha(path)==row['sha256']:preserved += 1
        else:
            if row['path'] not in expected:raise ValueError('unintended inherited change: '+row['path'])
            before = ROOT/'docs/r21a'/(row['path'].replace('/', '_')+'.before')
            if sha(before)!=row['sha256']:raise ValueError('missing exact historical source snapshot')
            changed.append({'path':row['path'], 'before_sha256':row['sha256'], 'after_sha256':sha(path)})
    (ROOT/'docs/r21a/Source_Changes_R21A.json').write_text(json.dumps({
        'unchanged_inherited_files':preserved, 'changed_with_exact_before_snapshots':changed,
        'release_manifest':'regenerated; exact R21 manifest retained in release_manifest.json.before',
        'deleted_inherited_files':[]}, indent=2)+'\n')
    keep = lambda p: p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo','.tmp')
    manifest = ROOT/'release_manifest.json';em = ROOT/'evidence/r21a/evidence_manifest.json'
    smoke = ROOT/'evidence/r21a/fresh_archive_smoke.json'
    selected = sorted(p for p in ROOT.rglob('*') if keep(p) and p not in (manifest, em, smoke))
    old = json.loads((ROOT/'docs/r21a/release_manifest.json.before').read_text())
    runtime = hashlib.sha256()
    for p in sorted((ROOT/'hle').glob('*.py')):
        runtime.update(p.name.encode());runtime.update(bytes.fromhex(sha(p)))
    manifest.write_text(json.dumps({'schema':'r21a-source-manifest-v1','milestone':'R21A','version':'1.11.0rc2',
        'R21A_complete':True,'R21_complete':False,'parent_progress':[9,10],'remaining':['R21B','R21C'],
        'runtime_sha256':runtime.hexdigest(),'files':[meta(str(p.relative_to(ROOT)),p) for p in selected],
        'unchanged_external_r21_raw_evidence':old['delivered_in_evidence_archive'],
        'external_archive_identity':json.loads((ROOT/'docs/r21a/Inherited_Archive_Identity.json').read_text())},indent=2)+'\n')
    source = write_archive(out/'HolonicLivingEngine_Rebuild_R21A_v1.zip',
                           [(str(p.relative_to(ROOT)),p) for p in selected+[manifest]],'HLE_Rebuild_R21A')
    print(json.dumps({'source':source}),flush=True)
    with tempfile.TemporaryDirectory(prefix='r21a-extracted-',dir=out) as temporary:
        with ZipFile(out/source['archive']) as archive:archive.extractall(temporary)
        root = Path(temporary)/'HLE_Rebuild_R21A'
        script = '''import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'tools')
from r21a_policy import run_reference_policy,protocol
from r21a_audit import audit_episode
from hle.closure import ClosureWorld
from hle.world_records import Credit,Tick
from r21_workloads import run_episode
m=json.loads(Path('release_manifest.json').read_text())
for row in m['files']:
    if hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()!=row['sha256']:raise AssertionError(row['path'])
w,meta=run_reference_policy('iee',12,'inadequate')
checkpoint=w.checkpoint();restored=ClosureWorld.restore(checkpoint)
exact=checkpoint==restored.checkpoint()
rejected=False
try:restored.execute(Credit('forbidden',restored.config.actors[0],1,1,'test'))
except ValueError:rejected=True
for x in (w,restored):x.execute(Tick('archive-next'))
legacy,lm=run_episode('iee',12,0)
result={'manifest_files_verified':len(m['files']),'v2_exact_restore':exact,'v2_next_transaction_exact':w._journal[-1]==restored._journal[-1],
        'direct_credit_rejected':rejected,'honest_zero_budget_deferral':meta['resource_stop'] is not None,
        'v1_remains_unenrolled':legacy.clearance_monitor.resource_contract is None,
        'frozen_v2_verified':protocol()['protocol_id']=='r21.resource-comparison.v2'}
result['passed']=all(v for k,v in result.items() if k!='manifest_files_verified')
print(json.dumps(result))
if not result['passed']:raise SystemExit(1)
'''
        run=subprocess.run([sys.executable,'-c',script],cwd=root,capture_output=True,text=True)
        if run.returncode:raise RuntimeError(run.stdout+run.stderr)
        check=json.loads(run.stdout);check['source_archive']=source
        smoke.write_text(json.dumps(check,indent=2)+'\n');print(json.dumps({'archive_smoke':check}),flush=True)
    evidence=[]
    for folder in ('docs/r21a','evidence/r21a','tests_r21a','hle'):
        evidence.extend((str(p.relative_to(ROOT)),p) for p in (ROOT/folder).rglob('*') if keep(p) and p!=em)
    evidence.extend((str(p.relative_to(ROOT)),p) for p in (ROOT/'tools').glob('r21a_*.py'))
    for path in ('docs/r12/acceptance_v1.json','docs/r21/Protocol_R21_v1.json','docs/r21/Protocol_R21_v1.sha256',
                 'docs/r21/Step_R21_Report.md','docs/r21/Progress_After_R21.md','release_manifest.json'):
        evidence.append((path,ROOT/path))
    em.write_text(json.dumps({'schema':'r21a-evidence-manifest-v1','R21_complete':False,
        'files':[meta(name,p) for name,p in sorted(evidence)]},indent=2)+'\n')
    evidence.append((str(em.relative_to(ROOT)),em))
    packaged=write_archive(out/'HLE_New_Build_Step_R21A_Evidence_v1.zip',evidence,'HLE_R21A_Evidence')
    shutil.copyfile(ROOT/'docs/r21a/Step_R21A_Report.md',out/'HLE_New_Build_Step_R21A_Report_v1.md')
    shutil.copyfile(ROOT/'docs/r21a/Progress_After_R21A.md',out/'HLE_New_Build_Progress_and_Remaining_Steps_After_R21A.md')
    result={'source':source,'evidence':packaged,'fresh_archive_verified':check['passed']}
    (out/'archive_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
