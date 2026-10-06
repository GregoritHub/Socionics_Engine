"""Supplementary source-binding cases, separate from the main C3 panel."""
import argparse,gzip,hashlib,json,sys,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]; sys.dont_write_bytecode=True
from tests_c3.test_source_transfer import *
from evaluate_u2 import EvidenceResult
from hle_unified import codec

def write(p,x): p.write_text(json.dumps(x,indent=2)+'\n')
def pack(p,s): p.write_bytes(gzip.compress(s.encode(),mtime=0))

def main():
 p=argparse.ArgumentParser(); p.add_argument('--out',type=Path,required=True); a=p.parse_args(); a.out.mkdir(parents=True,exist_ok=False)
 paths=sorted({*ROOT.glob('hle_unified/*.py'),*ROOT.glob('tests_c*/*.py'),Path(__file__),ROOT/'contracts/C3_Source_Transfer_Supplement_v1.json'})
 manifest={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in paths}; write(a.out/'execution_source.json',manifest)
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(SourceTransferTests)
 with (a.out/'tests.log').open('w') as f: result=unittest.TextTestRunner(stream=f,verbosity=2,resultclass=EvidenceResult).run(suite)
 summary=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),rows=result.rows,passed=result.wasSuccessful())
 write(a.out/'summary.json',summary)
 if not summary['passed']: raise SystemExit(1)
 rows=[]
 for name in ('Share','Coordinate','Educate'):
  for face in FACES:
   for control in (False,True):
    e=setup_c3(quantity=1,engine_type=PriorOnly if control else CrossingEngine); out=transfer(e,name,face)
    report=None; rejection=None
    try: report=audit(e.world.journal(),e.access.checkpoint())
    except ValueError as ex:
     if not control: raise
     rejection=str(ex)
    assert bool(rejection)==control
    cp=e.checkpoint(); assert type(e).restore(cp).checkpoint()==cp
    key=name.lower()+'-'+face+('-ablated' if control else '')
    folder=a.out/key; folder.mkdir()
    row=dict(route=name,polarity=face,control=control,before=data(e,out['before'],BOB)['amount'],after=data(e,out['after'],BOB)['amount'],
     own_cap=data(e,out['prior'],BOB)['cap'],main_work=e.job_status(ALICE,'case')['spent'],exact_restore=True,
     checkpoint_sha256=hashlib.sha256(cp.encode()).hexdigest(),refs={k:codec.encode(v) for k,v in out.items()},rejection=rejection)
    write(folder/'result.json',row); pack(folder/'transactions.json.gz',codec.dumps(e.world.journal())); pack(folder/'access.checkpoint.json.gz',e.access.checkpoint()); pack(folder/'engine.checkpoint.json.gz',cp)
    if report: write(folder/'audit.json',report)
    rows.append(row)
 unchanged=all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==v for n,v in manifest.items())
 assert unchanged
 summary.update(source_unchanged=True,type_cases=96,raw_witnesses=12,causal_pairs=6,witnesses=rows); write(a.out/'summary.json',summary)
 print(json.dumps({k:v for k,v in summary.items() if k not in ('rows','witnesses')}),flush=True)

if __name__=='__main__': main()
