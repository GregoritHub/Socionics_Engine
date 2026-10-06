"""Original R19 continuation and finite R20 type evidence, with raw replay audit."""
import argparse,gc,gzip,hashlib,json,sys,time,platform
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from hle.closure_demo import *
from hle.closure_reference import compare
from hle.closure import ClosureWorld
from hle.codec import dumps
from hle.model_a import TYPES

def digest(value):return hashlib.sha256(value.encode()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def compressed(path,value):
    with gzip.open(path,'wt') as f:f.write(value)

def case(out,name,w):
    start=len(w._journal);prefix=digest(dumps(tuple(w._journal)));historical=w.account_report()['groups']
    before={a.key:(x.energy,x.time) for a,x in w._wallets.items()}
    began=time.monotonic();w,f,s,result=run(w);audit=compare(w)
    prefix_ok=digest(dumps(tuple(w._journal[:start])))==prefix
    history_ok=w.account_report()['groups']==historical
    work={a.key:before[a.key][0]-w._wallets[a].energy for a in w.config.actors}
    result.update(name=name,seconds=time.monotonic()-began,source_prefix_transactions=start,source_prefix_sha256=prefix,
        prefix_unchanged=prefix_ok,historical_assessments_unchanged=history_ok,independent=audit,work_units=work,
        allocation={r.key:n for r,n in w._closure_production.items()},
        passed=result['first_depth']==1 and result['second_depth']==2 and result['native_clearance']=='cleared_in_scope' and audit['passed'] and prefix_ok and history_ok)
    trace=dumps(tuple(w._journal));compressed(out/(name+'.transactions.json.gz'),trace)
    result['trace']={'sha256':digest(trace),'bytes':len(trace)}
    save(out/(name+'.json'),result)
    print(json.dumps({'case':name,'passed':result['passed'],'events':len(w._journal),'seconds':round(result['seconds'],3)}),flush=True)
    return w,f,s,result

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'evidence/r20/panel');p.add_argument('--continuation-only',action='store_true');a=p.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    source=ROOT/'evidence/r19/panel/continued_r18.checkpoint.json.gz'
    with gzip.open(source,'rt') as f:parent=f.read()
    parent_digest=digest(parent);clock=time.monotonic();w=ClosureWorld.import_r19(parent);del parent;gc.collect()
    w,first,second,continued=case(out,'continued_r19',w)
    cp=w.checkpoint();compressed(out/'continued_r19.checkpoint.json.gz',cp)
    cp_meta={'sha256':digest(cp),'bytes':len(cp),'source_checkpoint_sha256':parent_digest}
    before=w.closure_report();del w;gc.collect()
    restored=ClosureWorld.restore(cp);exact=restored.checkpoint()==cp and restored.closure_report()==before
    del cp;gc.collect()
    # Retained original individual capacity remains usable after the shared
    # succession window, without pretending that successors acquired it.
    sig=restored._signature(restored.config.actors[0])
    offer=make_offer(restored,'r20:fresh-native-after-restore','si',held=True,all_traps=True)
    order=run_order(restored,offer);borrow(restored,first['item'],restored.config.actors[1]);event=own_return(restored,first['item'])
    lower_usable=restored._records[order.outcome].success and event.outcome==WorkStatus.COMPLETED and restored._signature(restored.config.actors[0])==sig
    continuation={'exact_restore':exact,'lower_usable_after_succession_and_restore':lower_usable,**cp_meta,'passed':exact and lower_usable and continued['passed']}
    save(out/'continuation.json',continuation);del restored;gc.collect()
    rows=[]
    if not a.continuation_only:
        for tim in sorted(TYPES):
            w=clone(panel(prepared(tim)));w,f,s,r=case(out,tim,w)
            rows.append({k:r[k] for k in ('name','passed','first_depth','second_depth','work_units','seconds')})
            del w;gc.collect()
    summary={'schema':'r20-evidence-v1','continued_original':continuation,'type_cases':rows,
        'passed':continuation['passed'] and all(r['passed'] for r in rows),'seconds':time.monotonic()-clock,
        'python':sys.version,'platform':platform.platform(),'scope':'finite shared custody and inherited obligations; R21 release/efficiency gates remain open'}
    save(out/'summary.json',summary);print(json.dumps(summary),flush=True)
    return 0 if summary['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
