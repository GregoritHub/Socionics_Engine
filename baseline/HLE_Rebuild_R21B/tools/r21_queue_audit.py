"""Reconstruct benchmark queue accounting without repeating timing samples."""
import gc,gzip,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from r21_performance import queue_snapshot,fresh,physical,make_offer,do,finish_order,Credit,Tick,ClosureWorld
from r21_reference import resource_audit
from r21_evidence import save

def main():
    out=ROOT/'evidence/r21/performance'
    summary=json.loads((out/'summary.json').read_text())
    with gzip.open(ROOT/'evidence/r20/panel/continued_r19.checkpoint.json.gz','rt') as f:base=ClosureWorld.restore(f.read())
    checks=[]
    for row in summary['rows']:
        w=fresh(base)
        for tx in base._journal[1:]:w.execute(tx.command)
        for a in w.config.actors:w.execute(Credit('benchmark:'+a.key,a,100000000,100000000,'separate performance allocation'))
        actor=w.config.actors[0];item=w.clearance_monitor.original_item
        for i in range(row['inactive_history']):
            if row['kind']=='tick':w.execute(Tick(f'inactive:{i}'))
            else:physical(w,actor,'inspect',(item,))
        before=queue_snapshot(w)
        for batch in range(11):
            keys=[]
            for i in range(32):
                f=make_offer(w,f'profile:{batch}:{i}','si',held=True,all_traps=True)
                w.execute(f);do(w,f.key,f.partner,'menu');keys.append(f.key)
            for key in keys:do(w,key,actor,'choose')
            for key in keys:finish_order(w,key)
        resources=resource_audit(w,allow_credits=True)
        same=resources==row['resources']
        check={'kind':row['kind'],'inactive_history':row['inactive_history'],'exact_work_accounting_reproduced':same,
            'queues_before':before,'queues_after':queue_snapshot(w),'paid_jobs_unfinished':resources['unfinished_count']}
        if not same:raise AssertionError('queue reconstruction differs from timed workload')
        row.update({k:check[k] for k in ('queues_before','queues_after')})
        save(out/f"{row['kind']}_{row['inactive_history']}.json",row)
        checks.append(check);print(json.dumps(check),flush=True);del w;gc.collect()
    summary['queue_accounting_reconstruction']=checks
    save(out/'summary.json',summary);save(out/'queue_audit.json',{'passed':all(c['exact_work_accounting_reproduced'] for c in checks),'rows':checks})
if __name__=='__main__':main()
