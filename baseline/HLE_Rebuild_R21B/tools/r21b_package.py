"""Package R21B with exact inherited preservation and two raw evidence parts."""
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
from r21_package import write_archive, meta, sha


def save(path, value): path.write_text(json.dumps(value, indent=2)+'\n')


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(); out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    decision = json.loads((ROOT/'evidence/r21b/decision.json').read_text())
    if not decision['R21B_complete'] or decision['R21_complete']: raise ValueError('wrong acceptance state')
    before = json.loads((ROOT/'docs/r21b/Input_Manifest.json').read_text())['files']
    allowed = {'README.md','hle/__init__.py','hle/resource_contracts.py','hle/clearance.py',
               'hle/clearance_runtime.py','hle/clearance_reference.py','hle/individuation.py','release_manifest.json'}
    changes = []; kept = 0
    for row in before:
        p = ROOT/row['path']
        if not p.is_file(): raise ValueError('missing inherited file: '+row['path'])
        if row['path'] == 'release_manifest.json':
            original = ROOT/'docs/r21b/release_manifest.json.before'
            if sha(original) != row['sha256']: raise ValueError('historical source manifest changed')
            continue
        if sha(p) == row['sha256']: kept += 1; continue
        snapshot = ROOT/'docs/r21b'/(row['path'].replace('/','_')+'.before')
        if row['path'] not in allowed or not snapshot.is_file() or sha(snapshot) != row['sha256']:
            raise ValueError('unpreserved inherited change: '+row['path'])
        changes.append(dict(path=row['path'], before_sha256=row['sha256'], after_sha256=sha(p)))
    save(ROOT/'docs/r21b/Source_Changes_R21B.json', {'preserved_inherited_files':kept,
        'changed_with_exact_before_snapshots':changes,'deleted_inherited_files':[],
        'release_manifest':'regenerated separately; exact inherited manifest preserved in release_manifest.json.before'})
    manifest = ROOT/'release_manifest.json'
    em = ROOT/'evidence/r21b/evidence_manifest.json'
    smoke = ROOT/'evidence/r21b/fresh_archive_smoke.json'
    excluded = {manifest, em, smoke}
    keep = lambda p: p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo','.tmp')
    files = sorted(p for p in ROOT.rglob('*') if keep(p) and p not in excluded)
    # Raw new traces travel in the evidence parts; every inherited file stays
    # in source, including historical evidence and previous source snapshots.
    external = [p for p in files if 'r21b' in p.parts and 'evidence' in p.parts
                and p.name.endswith('.transactions.jsonl.gz')]
    selected = [p for p in files if p not in external]
    inherited = json.loads((ROOT/'docs/r21b/release_manifest.json.before').read_text())
    digest = hashlib.sha256()
    for p in sorted((ROOT/'hle').glob('*.py')):
        digest.update(p.name.encode()); digest.update(bytes.fromhex(sha(p)))
    save(manifest, {'schema':'r21b-source-manifest-v1','milestone':'R21B','version':'1.11.0rc3',
        'R21B_complete':True,'R21_complete':False,'parent_progress':[9,10],'remaining':['R21C'],
        'runtime_sha256':digest.hexdigest(),
        'files':[meta(str(p.relative_to(ROOT)),p) for p in selected],
        'delivered_in_r21b_evidence_parts':[meta(str(p.relative_to(ROOT)),p) for p in external],
        'external_r21_archive_identity':inherited.get('external_archive_identity'),
        'unchanged_external_r21_raw_evidence':inherited.get('unchanged_external_r21_raw_evidence')})
    source = write_archive(out/'HolonicLivingEngine_Rebuild_R21B_v1.zip',
                           [(str(p.relative_to(ROOT)),p) for p in selected+[manifest]], 'HLE_Rebuild_R21B')
    print(json.dumps({'source':source}), flush=True)
    with tempfile.TemporaryDirectory(prefix='r21b-extracted-', dir=out) as temporary:
        with ZipFile(out/source['archive']) as z: z.extractall(temporary)
        root = Path(temporary)/'HLE_Rebuild_R21B'
        program = '''import gzip,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'tools')
from hle.closure import ClosureWorld
from hle.world_records import Tick
from r21b_policy import run_candidate,protocol
from r21b_work_audit import audit_paid_work
from r21_workloads import trace_digest
m=json.loads(Path('release_manifest.json').read_text())
for row in m['files']:
    if hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()!=row['sha256']:raise AssertionError(row['path'])
path=Path('evidence/r21b/development/iee_12_constrained_feasible.checkpoint.json.gz')
with gzip.open(path,'rt') as f:text=f.read()
w=ClosureWorld.restore(text)
exact=w.checkpoint()==text
raw=audit_paid_work(w)['passed']
expected=json.loads(Path('evidence/r21b/development/iee_12_constrained_feasible.json').read_text())['traces']['candidate']['sha256']
matched=trace_digest(w)==expected
contract=w._journal[1].command.protocol_id
n=len(w._journal);w.execute(Tick('r21b:fresh-archive-continuation'))
z,meta=run_candidate('sli',11,'inadequate')
result={'manifest_files_verified':len(m['files']),'checkpoint_exact':exact,
 'paid_work_audit':raw,'transaction_digest_matches':matched,'contract':contract,
 'new_event_accepted':len(w._journal)==n+1,'zero_budget_deferred':meta['resource_stop'] is not None,
 'frozen_protocol':protocol()['protocol_id']}
result['passed']=all(result[k] for k in ('checkpoint_exact','paid_work_audit','transaction_digest_matches','new_event_accepted','zero_budget_deferred')) and contract=='r21.integrated-policy.v4'
print(json.dumps(result))
if not result['passed']:raise SystemExit(1)
'''
        checked = subprocess.run([sys.executable,'-c',program], cwd=root, capture_output=True, text=True)
        if checked.returncode: raise RuntimeError(checked.stdout+checked.stderr)
        check = json.loads(checked.stdout); check['source_archive'] = source; save(smoke, check)
        print(json.dumps({'fresh_archive_smoke':check}), flush=True)
    evidence = []
    for folder in ('docs/r21b','evidence/r21b','tests_r21b','hle','docs/r21a','evidence/r21a','tests_r21a'):
        evidence.extend((str(p.relative_to(ROOT)),p) for p in (ROOT/folder).rglob('*') if keep(p) and p != em)
    evidence.extend((str(p.relative_to(ROOT)),p) for p in (ROOT/'tools').glob('r21*.py'))
    for name in ('docs/r12/acceptance_v1.json','docs/r21/Protocol_R21_v1.json','docs/r21/Protocol_R21_v1.sha256',
                 'docs/r21/Step_R21_Report.md','docs/r21/Progress_After_R21.md','release_manifest.json'):
        evidence.append((name, ROOT/name))
    if len({n for n,_ in evidence}) != len(evidence): raise ValueError('duplicate evidence path')
    save(em, {'schema':'r21b-evidence-manifest-v1','R21_complete':False,
        'files':[meta(n,p) for n,p in sorted(evidence)]})
    parts=[[],[]]; sizes=[0,0]
    for entry in sorted(evidence,key=lambda x:(-x[1].stat().st_size,x[0])):
        index=min(range(2),key=lambda i:sizes[i]); parts[index].append(entry); sizes[index]+=entry[1].stat().st_size
    archives=[]
    for n, entries in enumerate(parts,1):
        entries.append((str(em.relative_to(ROOT)),em))
        archives.append(write_archive(out/f'HLE_New_Build_Step_R21B_Evidence_v1_Part_{n}.zip',entries,'HLE_R21B_Evidence'))
        print(json.dumps({'evidence':archives[-1]}), flush=True)
    shutil.copyfile(ROOT/'docs/r21b/Step_R21B_Report.md',out/'HLE_New_Build_Step_R21B_Report_v1.md')
    shutil.copyfile(ROOT/'docs/r21b/Progress_After_R21B.md',out/'HLE_New_Build_Progress_and_Remaining_Steps_After_R21B.md')
    result={'source':source,'evidence':archives,'fresh_archive_verified':check['passed']}
    save(out/'archive_verification.json',result)
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__': main()
