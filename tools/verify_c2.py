"""Reconstruct the delivered C2 decision without a participant selector."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
sys.dont_write_bytecode=True
from hle_unified import codec
from hle_unified.self_audit import audit


def read(p):return json.loads(p.read_text())
def raw(p):return gzip.decompress(p.read_bytes()).decode()
def check_manifest(manifest,base):
    for name,digest in manifest.items():
        assert hashlib.sha256((base/name).read_bytes()).hexdigest()==digest,name


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
    accepted_ids=set()
    for stage,count in (('final_tests',499),('final_review_tests',4)):
        summary=read(e/stage/'summary.json')
        assert summary['passed'] and summary['source_unchanged'] and summary['tests']==count
        assert not (summary['failures'] or summary['errors'] or summary['skipped'])
        assert all(r['status']=='passed' for r in summary['rows'])
        accepted_ids.update(r['test_id'] for r in summary['rows'])
        manifest=read(e/stage/'execution_source.json')
        # Export utilities are tested by their separate witness/measurement runs.
        check_manifest({k:v for k,v in manifest.items() if k.startswith(('hle_unified/','tests_'))},ROOT)
    assert len(accepted_ids)==503
    check_manifest(read(e/'witnesses/execution_source.json'),ROOT)
    ledger=read(e/'witnesses/summary.json');assert ledger['passed'] and ledger['cells']==8 and len(ledger['rows'])==16
    pairs={}; reconstructed=0
    for result_path in sorted((e/'witnesses').glob('*/result.json')):
        result=read(result_path);directory=result_path.parent
        txs=codec.loads(raw(directory/'transactions.json.gz'));access=raw(directory/'access.checkpoint.json.gz')
        rejected=False
        try: report=audit(txs,access)
        except ValueError:
            rejected=True
        assert rejected==result['control'],directory.name
        if not rejected: assert report['c2_self_completed']==1
        cp=raw(directory/'engine.checkpoint.json.gz')
        assert hashlib.sha256(cp.encode()).hexdigest()==result['checkpoint_sha256']
        pairs.setdefault((result['route'],result['polarity']),{})[result['control']]=result
        reconstructed+=1
    assert len(pairs)==8 and reconstructed==16
    for pair in pairs.values():
        assert pair[False]['movement_spending']==pair[True]['movement_spending']
        assert pair[False]['consequence']!=pair[True]['consequence']
    measurement=read(e/'measurements/summary.json');assert measurement['passed'] and measurement['source_unchanged']
    check_manifest(read(e/'measurements/execution_source.json'),ROOT)
    samples=[read(f) for f in sorted((e/'measurements').glob('*.stdout.json'))]
    assert len(samples)==46 and all(x['exact_restore'] and x['audit_passed'] for x in samples)
    assert sum(s['mode']=='time' for s in samples)==37
    panel=[s for s in samples if s['lane']=='panel']
    assert len(panel)==24
    keys=('movement_attempts','movement_completions','self_completions','semantic_steps','modeled_total_work','modeled_active_work','outcomes')
    assert len({json.dumps([s[k] for k in keys],sort_keys=True) for s in panel})==1
    traced=[s for s in panel if s['mode']=='trace']
    assert len({(s['memory']['resolve_calls'],s['memory']['unique_refs_sum']) for s in traced})==1
    import statistics
    reference=statistics.median(s['active_wall_seconds'] for s in samples if s['lane']=='reference')
    current=statistics.median(s['active_wall_seconds'] for s in samples if s['lane']=='c2')
    assert current/reference<=1.5
    # Recheck the inherited immutable files, rather than trusting a pass label.
    inherited=read(e/'inherited_identity.json')
    keep={k:v for k,v in inherited.items() if k.startswith('baseline/') or k.startswith('hle_unified/') and not k.startswith('hle_unified/crux_')}
    check_manifest(keep,ROOT)
    source_manifest=ROOT/'C2_Source_File_Manifest_v1.json'
    if source_manifest.exists():check_manifest(read(source_manifest),ROOT)
    evidence_manifest=e/'C2_Evidence_File_Manifest_v1.json'
    if evidence_manifest.exists():check_manifest(read(evidence_manifest),e)
    print(json.dumps(dict(passed=True,distinct_tests=len(accepted_ids),raw_witnesses=reconstructed,
                          causal_pairs=len(pairs),measurement_workers=len(samples),inherited_files=len(keep),c1_ratio=current/reference)),flush=True)

if __name__=='__main__': main()
