"""Raw 32-cell C5 causal panel; each pair is saved before verification."""
import sys,json,gzip,time,hashlib,traceback
from dataclasses import asdict,is_dataclass
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from tests_c5.fixtures import *
from hle_unified.crux_shell_audit import audit
from hle_unified import codec

def dump(value): return json.dumps(value,default=lambda v:asdict(v) if is_dataclass(v) else str(v),indent=2)

def run(out,phase="admission"):
    out.mkdir(parents=True,exist_ok=False)
    manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for pattern in ('hle_unified/*.py','tests_c5/*.py','tools/*c5*.py','contracts/C5*') for p in ROOT.glob(pattern)}
    (out/'source.json').write_text(json.dumps(manifest,indent=2))
    rows=[]
    for name in NAMES:
        for face in FACES:
            key=name+'-'+face;start=time.perf_counter()
            try:
                d,c,row=panel_case(name,face,phase=phase)
                for label,e in (('deformed',d),('corrected',c)):
                    (out/(key+'-'+label+'.json.gz')).write_bytes(gzip.compress(e.checkpoint().encode(),mtime=0))
                    a=audit(e.world.journal(),e.access.checkpoint())
                    row[label+'_audit']={k:v for k,v in a.items() if k not in ('c5_rows',)}
                assert not row['deformed']['admitted'] and row['control']['child'] is not None
                assert c.job_status(ALICE,'case')['status']=='succeeded'
                assert row['deformed_audit']['c5_completed']==0 and row['corrected_audit']['c5_completed']==1
                row['elapsed_seconds']=time.perf_counter()-start
                rows.append(row)
                (out/(key+'.json')).write_text(dump(row))
                print('PASS',key,round(row['elapsed_seconds'],2),flush=True)
            except Exception:
                (out/(key+'-failure.txt')).write_text(traceback.format_exc());raise
    (out/'summary.json').write_text(dump(dict(passed=True,pairs=len(rows),rows=rows)))
if __name__=='__main__': run(Path(sys.argv[1]),sys.argv[2] if len(sys.argv)>2 else 'admission')
