"""Preserve a default-stop checkpoint for independent external reconstruction."""
import sys,gzip,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from tests_c7.fixtures import population
from hle_unified.population_audit import audit_population
from hle_unified.selection_audit import audit
from hle_unified.selection_records import loads
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
p,_=population(17,3,repeat_limit=2);result=p.run(2000)
assert p.stopped==['unchanged_retained_result']*3
cp=p.checkpoint();(out/'default-stop.json.gz').write_bytes(gzip.compress(cp.encode(),mtime=0))
audit(p.engine.world.journal(),p.engine.access.checkpoint())
a=audit_population(p.engine.world.journal(),loads(cp))
(out/'summary.json').write_text(json.dumps(dict(passed=True,result=result,population_audit=a),indent=2))
print(result)
