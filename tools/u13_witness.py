"""Run the preserved U12 circuit, then archive and inspect its exact history."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'baseline/HLE_Rebuild_R21B'
sys.path[:0]=[str(ROOT),str(BASE)]
sys.dont_write_bytecode=True


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    command=[sys.executable,str(ROOT/'tools/u12_witness.py'),'--out',str(a.out/'u12')]
    with (a.out/'u12.log').open('w') as log:
        r=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    if r.returncode:return r.returncode
    from hle_unified.institutions import InstitutionEngine
    from hle_unified.material import OperationStore
    from hle_unified.archive import write_history, HistoryArchive
    from hle_unified import codec
    cp=(a.out/'u12/complete_institution_history.checkpoint.json').read_text()
    e=InstitutionEngine.restore(cp)
    start=time.perf_counter();archive=write_history(e.world,a.out/'history')
    write_seconds=time.perf_counter()-start
    start=time.perf_counter();last=archive.transaction(len(e.world._journal)-1)
    lookup_seconds=time.perf_counter()-start;selective_reads=archive.segments_read
    start=time.perf_counter();restored=archive.restore(OperationStore)
    restore_seconds=time.perf_counter()-start
    result={'schema':'hle-u13-history-witness-v1',
        'segment_count':len(archive.manifest['segments']),
        'transactions':len(e.world._journal),
        'archive_bytes':sum(f.stat().st_size for f in (a.out/'history').iterdir()),
        'canonical_history_bytes':len(codec.dumps(e.world.journal()).encode()),
        'archive_write_seconds':write_seconds,'single_historical_transaction_seconds':lookup_seconds,
        'single_lookup_segments_read':selective_reads,'full_historical_reconstruction_seconds':restore_seconds,
        'checks':{'exact_single_lookup':last==e.world.journal()[-1],
                  'one_segment_read':selective_reads==1,
                  'exact_complete_reconstruction':restored.checkpoint()==e.world.checkpoint()}}
    reference=ROOT/'contracts/U13_U12_Reference_Witness_Summary.json'
    original=json.loads(reference.read_text())
    current=json.loads((a.out/'u12/summary.json').read_text())
    result['checks']['all_inherited_witness_checks']=current['checks']==original['checks'] and current['passed']
    result['checks']['all_inherited_checkpoints_and_transactions_exact']=all(
        current['artifacts'][k]['checkpoint_sha256']==v['checkpoint_sha256'] and
        current['artifacts'][k]['transactions_sha256']==v['transactions_sha256']
        for k,v in original['artifacts'].items())
    result['reference_scope']='Exact supplied final U12 witness digests; U13 same-feature timing uses fresh reference workers separately.'
    result['passed']=all(result['checks'].values())
    (a.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
