"""Raw reconstruction from saved worlds/access; never calls a selector/executor."""
import sys,json,gzip,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from hle_unified.compact import unseal
from hle_unified.material import OperationStore
from hle_unified.crux_shell_audit import audit

def verify(base):
    counts={};rows=[]
    for folder in ('admission_panel_final','active_panel_attempt1','development_final'):
        summary=json.loads((base/folder/'summary.json').read_text());assert summary['passed']
        paths=sorted((base/folder).glob('*.json.gz'));counts[folder]=len(paths)
        for p in paths:
            raw=unseal(gzip.decompress(p.read_bytes()).decode(),'hle-full-crux-c5-engine-v1')
            world=OperationStore.restore(raw['world']);a=audit(world.journal(),raw['access']);assert a['passed']
            if folder!='development_final':
                row=a['c5_rows'][0];assert len(a['c5_rows'])==1
                if 'deformed' in p.name:
                    assert row['deformed'] and not row['completed']
                    assert row['foreclosure'] if folder=='admission_panel_final' else row['early_substitution']
                else:assert row['completed'] and not row['deformed']
            rows.append(dict(file=str(p.relative_to(base)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                admissions=a['c5_admissions'],deformed=a['c5_deformed'],completed=a['c5_completed']))
        print('audited',folder,len(paths),flush=True)
    assert counts==dict(admission_panel_final=64,active_panel_attempt1=64,development_final=15)
    result=dict(passed=True,raw_witnesses=len(rows),counts=counts,rows=rows)
    (base/'raw_verification_final.json').write_text(json.dumps(result,indent=2));print('raw verification passed',len(rows),flush=True)
if __name__=='__main__':verify(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'evidence_c5')
