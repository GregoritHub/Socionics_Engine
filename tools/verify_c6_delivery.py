"""Reconstruct saved world/access evidence without restoring an engine."""
import sys,json,gzip,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from hle_unified.compact import unseal
from hle_unified.material import OperationStore
from hle_unified.selection_audit import audit,extent
from hle_unified.crux_shell_audit import audit as native_audit

def verify(base):
    rows=[]
    for folder in ('panel_final','types_final','transfer_final'):
        assert json.loads((base/folder/'summary.json').read_text())['passed']
        for p in sorted((base/folder).glob('*.json.gz')):
            raw=unseal(gzip.decompress(p.read_bytes()).decode(),'hle-full-crux-c6-engine-v1');world=OperationStore.restore(raw['world'])
            if p.stem.endswith('-control.json'):
                a=native_audit(world.journal(),raw['access'],extent_check=extent,extended_flags=('c6',));assert a['passed']
                try:audit(world.journal(),raw['access'])
                except ValueError as exc:
                    assert 'not the accountable best' in str(exc);status='expected_choice_ablation_rejection'
                else:raise AssertionError('control unexpectedly passed')
            else:a=audit(world.journal(),raw['access']);assert a['passed'];status='passed'
            rows.append(dict(file=str(p.relative_to(base)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),status=status))
        print('verified',folder,flush=True)
    result=dict(passed=True,worlds=len(rows),valid_worlds=sum(x['status']=='passed' for x in rows),deliberate_ablations=sum(x['status']!='passed' for x in rows),rows=rows)
    (base/'raw_verification_final.json').write_text(json.dumps(result,indent=2));print('PASS',len(rows),flush=True)
if __name__=='__main__':verify(Path(sys.argv[1]))
