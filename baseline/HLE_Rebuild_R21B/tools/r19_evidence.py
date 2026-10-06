"""R19 finite type panel, real R18 continuation, recurrence and replay evidence."""
import argparse,gc,gzip,hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from hle.clearance_demo import *
from hle.clearance_reference import compare
from hle.clearance import ClearanceWorld
from hle.codec import dumps
from hle.individuation_demo import make_offer

def write(path,data):path.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
def digest(text):return hashlib.sha256(text.encode()).hexdigest()
def trace(path,w):
    content=dumps(tuple(w._journal))
    with gzip.open(path,'wt') as g:g.write(content)
    return {'transactions':len(w._journal),'sha256':digest(content),'uncompressed_bytes':len(content)}
def save_case(out,name,w):
    live=w.clearance_report();audit=compare(w)
    meta=trace(out/(name+'.transactions.json.gz'),w)
    write(out/(name+'.json'),{'assessment':live,'independent':audit,'trace':meta})
    return {'name':name,'passed':audit['passed'] and live['status']=='cleared_in_scope',
        'status':live['status'],'cases_passed':sum(r['passed'] for r in live['rows']),
        'paid_work':live['paid_work_in_window'],'baseline_defensive_work':live['baseline_defensive_work'],
        'baseline_signs':live['baseline_signs'],'sensitivity':live['sensitivity'],**meta}

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'evidence/r19/panel')
    p.add_argument('--continuation-only',action='store_true');a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    protocol=json.loads((ROOT/'docs/r19/Protocol_R19_v1.json').read_text());clock=time.monotonic()
    rows=[]
    if not a.continuation_only:
        for tim in protocol['type_order']:
            w=panel(prepared(tim));row=save_case(out,tim,w);rows.append(row);print(json.dumps(row),flush=True)
            del w;gc.collect()
        w=panel(prepared('sli',maintained=5));sensitivity=save_case(out,'sensitivity_five',w)
        del w;gc.collect()
        write(out/'type_summary.json',{'rows':rows,'sensitivity_five':sensitivity,'passed':all(r['passed'] for r in rows) and sensitivity['passed']})
    else:
        prior=json.loads((out/'type_summary.json').read_text());rows=prior['rows'];sensitivity=prior['sensitivity_five']
    path=ROOT/'evidence/r18/panel/continued_r17.checkpoint.json.gz'
    with gzip.open(path,'rt') as g:parent=g.read()
    parent_sha=digest(parent);w=ClearanceWorld.import_r18(parent);del parent;gc.collect()
    start=len(w._journal);prefix=digest(dumps(tuple(w._journal)));historical=w.account_report()
    panel(w);r=save_case(out,'continued_r18',w)
    same_prefix=digest(dumps(tuple(w._journal[:start])))==prefix
    after=w.account_report()
    same_assessments=historical['groups']==after['groups']
    checkpoint=w.checkpoint();cp_sha=digest(checkpoint)
    with gzip.open(out/'continued_r18.checkpoint.json.gz','wt') as g:g.write(checkpoint)
    clear_report=w.clearance_report();del w;gc.collect()
    restored=ClearanceWorld.restore(checkpoint)
    exact=restored.checkpoint()==checkpoint;del checkpoint;gc.collect()
    fresh=make_offer(restored,'r19:fresh-after-restore','si',1,held=True,all_traps=True)
    restored.execute(fresh);finish_order(restored,fresh.key)
    item=restored.clearance_monitor.original_item;borrow(restored,item,restored.config.actors[1]);own_return(restored,item)
    fresh_pass=restored._records[restored._circuit_orders[fresh.key].outcome].success and restored.clearance_report()['status']=='cleared_in_scope'
    continuation={'source_checkpoint_sha256':parent_sha,'source_prefix_transactions':start,'source_prefix_sha256':prefix,
        'prefix_unchanged':same_prefix,'historical_assessments_unchanged':same_assessments,
        'checkpoint_sha256':cp_sha,'exact_restore':exact,'fresh_controller_and_return':fresh_pass,
        'assessment':r,'passed':r['passed'] and same_prefix and same_assessments and exact and fresh_pass}
    write(out/'continuation.json',continuation);print(json.dumps({'continuation':continuation['passed']}),flush=True)
    # Continuing the restored actor makes recurrence a real later event.
    recurrence_rows=[]
    for n in range(5):
        replenish(restored);borrow(restored,item,restored.config.actors[1]);defensive_return(restored,item)
        report=restored.clearance_report();audit=compare(restored)
        recurrence_rows.append({'engagement':n+1,'status':report['status'],'counts':report['recurrence_counts'],
            'independent_agreement':audit['passed'],'history_preserved':any(x['status']=='cleared_in_scope' for x in report['history'])})
    trace(out/'recurrence.transactions.json.gz',restored)
    recurrent_cp=restored.checkpoint()
    with gzip.open(out/'recurrence.checkpoint.json.gz','wt') as g:g.write(recurrent_cp)
    expected=restored.clearance_report();del restored;gc.collect()
    recurrent=ClearanceWorld.restore(recurrent_cp);exact_recurrence=recurrent.checkpoint()==recurrent_cp and recurrent.clearance_report()==expected
    recurrence_result={'rows':recurrence_rows,'checkpoint_exact':exact_recurrence,'assessment':expected,
        'sensitivity':{str(n):all(v>=n for v in expected['recurrence_counts'].values()) for n in (2,3,5)},
        'passed':all(x['independent_agreement'] and x['history_preserved'] for x in recurrence_rows)
            and recurrence_rows[0]['status']=='unresolved' and recurrence_rows[2]['status']=='recurrent' and exact_recurrence}
    write(out/'recurrence.json',recurrence_result)
    summary={'schema':'r19-evidence-v1','types':len(rows),'passing_types':sum(r['passed'] for r in rows),
        'held_out_plus_original':sum(r['cases_passed'] for r in rows),'sensitivity_five':sensitivity,
        'continuation_passed':continuation['passed'],'recurrence_passed':recurrence_result['passed'],
        'passed':len(rows)==16 and all(r['passed'] for r in rows) and sensitivity['passed'] and continuation['passed'] and recurrence_result['passed'],
        'seconds':round(time.monotonic()-clock,6)}
    write(out/'summary.json',summary);print(json.dumps(summary),flush=True)
    return 0 if summary['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
