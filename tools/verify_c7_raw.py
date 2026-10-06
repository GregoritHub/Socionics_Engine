"""Raw-world verification; never calls a participant executor or selector."""
import sys,gzip,json,hashlib
from dataclasses import asdict,is_dataclass
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from hle_unified.selection_records import loads
from hle_unified.compact import unseal
from hle_unified.material import OperationStore
from hle_unified.selection_audit import audit
from hle_unified.population_audit import audit_population

def verify(folder):
    rows=[]
    for path in sorted(folder.glob('*.json.gz')):
        outer=loads(gzip.decompress(path.read_bytes()).decode())
        raw=unseal(outer['engine'],'hle-full-crux-c6-engine-v1')
        world=OperationStore.restore(raw['world']);result=audit(world.journal(),raw['access'])
        assert result['passed']
        schedule=audit_population(world.journal(),outer)
        rows.append(dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),audit=result,population=schedule))
    assert rows
    (folder/'raw_verification.json').write_text(json.dumps(dict(passed=True,worlds=len(rows),rows=rows),indent=2,default=lambda x:asdict(x) if is_dataclass(x) else str(x)))
    print('raw worlds verified',len(rows),flush=True)
if __name__=='__main__':verify(Path(sys.argv[1]))
