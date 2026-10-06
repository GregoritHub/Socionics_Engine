"""Reconstruct the C3 delivery decision from source and raw evidence."""
import argparse,gzip,hashlib,json,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
sys.dont_write_bytecode=True
from hle_unified import codec
from hle_unified.crossing_audit import audit
from hle_unified.crossing_records import PATHS,FACES

def read(p): return json.loads(p.read_text())
def raw(p): return gzip.decompress(p.read_bytes()).decode()
def check(manifest,base=ROOT):
    for name,digest in manifest.items():
        assert hashlib.sha256((base/name).read_bytes()).hexdigest()==digest,name

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--evidence',type=Path,required=True); args=parser.parse_args(); e=args.evidence
    initial=read(e/'run_1/summary.json'); final=read(e/'final_tests/summary.json')
    assert initial['source_unchanged']
    inherited=[r for r in initial['rows'] if not r['test_id'].startswith('tests_c3.')]
    assert len(inherited)==503 and all(r['status']=='passed' for r in inherited)
    original=read(e/'run_1/execution_source.json')
    check({k:v for k,v in original.items() if k.startswith('hle_unified/') and not k.startswith('hle_unified/crossing_') or k.startswith('tests_') and not k.startswith('tests_c3/')})
    assert final['passed'] and final['source_unchanged'] and not (final['failures'] or final['errors'] or final['skipped'])
    assert all(r['status']=='passed' for r in final['rows'])
    check({k:v for k,v in read(e/'final_tests/execution_source.json').items() if k.startswith(('hle_unified/','tests_','contracts/'))})
    accepted={r['test_id'] for r in (*inherited,*final['rows'])}
    check(read(e/'witnesses/execution_source.json'))
    summary=read(e/'witnesses/summary.json'); assert summary['passed'] and summary['cells']==24 and len(summary['rows'])==48
    pairs={}
    for result_file in sorted((e/'witnesses').glob('*/result.json')):
        result=read(result_file); folder=result_file.parent
        txs=codec.loads(raw(folder/'transactions.json.gz')); access=raw(folder/'access.checkpoint.json.gz')
        rejected=False
        try: report=audit(txs,access)
        except ValueError: rejected=True
        assert rejected==result['control'],folder.name
        if not rejected: assert any(r['main'] and r['route']==result['route'] and r['polarity']==result['polarity'] for r in report['c3_results'])
        assert hashlib.sha256(raw(folder/'engine.checkpoint.json.gz').encode()).hexdigest()==result['checkpoint_sha256']
        # Reconstruct the reported later answer from the committed output.
        ref=codec.decode(result['refs']['downstream']); versions={v.ref:v for tx in txs for v in tx.versions}
        from hle_unified.crossing_audit import payload
        assert payload(versions[ref])['amount']==result['consequence']
        pairs.setdefault((result['route'],result['polarity']),{})[result['control']]=result
    assert set(pairs)=={(n,f) for n in PATHS for f in FACES}
    for pair in pairs.values():
        assert pair[False]['movement_spending']==pair[True]['movement_spending']
        assert pair[False]['consequence']!=pair[True]['consequence']
    measurement=read(e/'measurements/summary.json'); assert measurement['passed'] and measurement['source_unchanged']
    check(read(e/'measurements/execution_source.json'))
    samples=[read(p) for p in (e/'measurements').glob('*.stdout.json')]
    assert len(samples)==30 and sum(s['mode']=='time' for s in samples)==24
    assert all(s['exact_restore'] and s['audit_passed'] for s in samples)
    keys=('movement_attempts','movement_completions','semantic_steps','modeled_total_work','modeled_active_work','outcomes')
    invariant=lambda s:json.dumps([s[k] for k in keys],sort_keys=True)
    panel=[s for s in samples if s['lane']=='panel']; assert len(panel)==18 and len({invariant(s) for s in panel})==1
    traces=[s for s in panel if s['mode']=='trace']; assert len(traces)==6
    assert len({(s['memory']['resolve_calls'],s['memory']['unique_refs_sum']) for s in traces})==1
    reference=[s for s in samples if s['lane']=='reference']; adapted=[s for s in samples if s['lane']=='adapted']
    assert len(reference)==len(adapted)==3 and {invariant(s) for s in reference}=={invariant(s) for s in adapted}
    ratio=statistics.median(s['active_wall_seconds'] for s in adapted)/statistics.median(s['active_wall_seconds'] for s in reference)
    assert ratio<=1.5
    medians=[statistics.median(s['active_wall_seconds'] for s in panel if s['shape']==shape and s['inactive']==count and s['mode']=='time') for shape in ('shared','unique') for count in (0,100,1000)]
    assert max(medians)/min(medians)<=1.75
    inherited_manifest=read(ROOT/'reference/C2_Inherited_File_Manifest.json')
    unchanged={k:v for k,v in inherited_manifest.items() if k.startswith('baseline/') or k.startswith('hle_unified/') and k not in ('hle_unified/crux_execution.py','hle_unified/self_audit.py')}
    check(unchanged)
    for filename,base in (('C3_Source_File_Manifest_v1.json',ROOT),('C3_Evidence_File_Manifest_v1.json',e)):
        if (base/filename).exists(): check(read(base/filename),base)
    result=dict(passed=True,distinct_tests=len(accepted),inherited_tests=len(inherited),final_c3_tests=final['tests'],
        initial_full_run_passed=initial['passed'],initial_errors=initial['errors'],causal_pairs=len(pairs),raw_witnesses=48,
        measurement_workers=len(samples),inherited_unchanged_files=len(unchanged),c2_ratio=ratio)
    print(json.dumps(result),flush=True)

if __name__=='__main__': main()
