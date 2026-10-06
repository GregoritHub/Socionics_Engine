"""Reconstruct the C4 decision from raw artifacts and recorded populations."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
sys.dont_write_bytecode=True
from hle_unified.crux_composition_audit import audit
from hle_unified.crossing_audit import payload
from hle_unified.material import attrs
from hle_unified import codec


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();root=a.evidence
    tests=json.loads((root/'tests_final/summary.json').read_text())
    assert tests['passed'] and tests['source_unchanged'] and not any(tests[k] for k in ('failures','errors','skipped'))
    assert tests['tests']==len(tests['rows'])==len({r['test_id'] for r in tests['rows']})
    assert all(r['status']=='passed' for r in tests['rows'])
    for folder in ('tests_final','witnesses','measurements'):
        manifest=json.loads((root/folder/'execution_source.json').read_text())
        for name,digest in manifest.items(): assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,(folder,name)
    rows=[]
    for folder in sorted((root/'witnesses').iterdir()):
        if not folder.is_dir():continue
        row=json.loads((folder/'result.json').read_text())
        txs=codec.loads(gzip.decompress((folder/'transactions.json.gz').read_bytes()).decode())
        access=gzip.decompress((folder/'access.checkpoint.json.gz').read_bytes()).decode()
        cp=gzip.decompress((folder/'engine.checkpoint.json.gz').read_bytes())
        assert hashlib.sha256(cp).hexdigest()==row['checkpoint_sha256']
        rejected=False
        try: report=audit(txs,access)
        except ValueError:
            if not row['control']:raise
            rejected=True
        assert rejected==row['control'] and row['raw_audit_passed']!=row['control']
        versions={v.ref:v for tx in txs for v in tx.versions}
        decision=codec.decode(row['refs']['decision'])
        assert payload(versions[decision])['amount']==row['outcome']
        jobs=[attrs(v) for tx in txs for v in tx.versions if v.ref.identity.namespace=='u4.operation' and attrs(v).get('key')=='case']
        assert jobs[-1]['spent']==row['focus_spent']
        if not row['control']:
            saved=json.loads((folder/'audit.json').read_text());assert saved==report
            assert report['c4_independent_content_check']
        rows.append(row)
    pairs={}
    for row in rows:
        if row['failed_child']:continue
        pairs.setdefault(row['name'],{})[row['control']]=row
    assert len(pairs)==7 and len(rows)==15
    for name,pair in pairs.items():
        assert pair[False]['focus_spent']==pair[True]['focus_spent'] and pair[False]['outcome']!=pair[True]['outcome'],name
    assert any(r['failed_child'] and r['parent_complete'] is False and r['outcome']==0 for r in rows)
    m=json.loads((root/'measurements/summary.json').read_text())
    samples=[json.loads(p.read_text()) for p in sorted((root/'measurements').glob('*.stdout.json'))]
    assert m['passed'] and m['source_unchanged'] and len(samples)==m['workers']==36
    assert sum(s['mode']=='trace' for s in samples)==m['trace_workers']==6
    assert all(s['exact_restore'] and s['audit_passed'] for s in samples)
    assert m['c3_ratio']<=1.5 and m['history_ratio']<=1.75
    inv=lambda s:json.dumps([s[k] for k in ('attempts','completions','semantic_steps','modeled_total_work','modeled_active_work','outcomes')])
    assert len({inv(s) for s in samples if s['lane']=='panel'})==1
    assert len({(s['memory']['resolve_calls'],s['memory']['unique_refs_sum']) for s in samples if s['mode']=='trace'})==1
    assert len({inv(s) for s in samples if s['lane'] in ('reference','adapted')})==1
    preservation=json.loads((root/'inherited_preservation.json').read_text());assert preservation['passed']
    for name,sha in preservation['preserved_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
    for name,values in preservation['changed'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==values['after'],name
    result=dict(passed=True,distinct_tests=tests['tests'],raw_witnesses=len(rows),causal_pairs=len(pairs),
        measured_workers=len(samples),preserved_files=preservation['preserved_count'],
        decision='C4 complete under its bounded composition and nested-evidence contract; full-release cells remain open')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
