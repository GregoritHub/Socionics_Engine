"""Reproducible 48-case R18 panel. The R21 480-case release is not run here."""
import argparse,gc,gzip,hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from hle.individuation_demo import case,make_offer,run_order,do,acquire_aspects,command,CircuitController
from hle.individuation_reference import evaluate
from hle.individuation import IndividuationWorld
from hle.individuation_records import CircuitTransaction,CircuitCommand,ASPECTS,WorkPartner
from hle.world_records import Credit,Tick
from hle.model_a import element_at
from hle.codec import encode,dumps,loads

def write(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def sha(text):return hashlib.sha256(text.encode()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'evidence/r18/panel');p.add_argument('--parent-checkpoint',type=Path);p.add_argument('--continuation-only',action='store_true')
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    protocol=json.loads((ROOT/'docs/r18/Protocol_R18_v1.json').read_text());rows=[];modes={};start=time.monotonic()
    if a.continuation_only:
        summary=json.loads((out/'summary.json').read_text());rows=summary['rows']
        if len(rows)!=48 or not all(r['passed'] for r in rows) or not all(summary['controlled_content'].values()):
            raise ValueError('a completed matching 48-case panel is required')
        summary['passed']=True
    else:
        for tim in protocol['type_order']:
            content=[]
            for mode in protocol['support_modes']:
                clock=time.monotonic();w,setup=case(tim,mode)
                report=evaluate(w);report['setup']=setup
                report['seconds']=round(time.monotonic()-clock,6)
                raw=[encode(t) for t in w._journal if type(t) is CircuitTransaction]
                payload=json.dumps(raw,sort_keys=True,separators=(',',':'))
                report['r18_trace_sha256']=sha(payload)
                with gzip.open(out/(tim+'_'+mode+'.transactions.json.gz'),'wt') as g:g.write(payload)
                write(out/(tim+'_'+mode+'.json'),report)
                content.append(report['correction_content'])
                row={'tim':tim,'mode':mode,'passed':report['integrity_passed'] and all(report['gates'].values()),
                    'work':report['paid_work'],'shared_output':report['shared_output'],'seconds':report['seconds']}
                rows.append(row);print(json.dumps(row),flush=True)
                del w,report,raw,payload;gc.collect()
            modes[tim]=content[0]==content[1]==content[2]
        summary={'schema':'r18-panel-v1','cases':len(rows),'passed_cases':sum(r['passed'] for r in rows),
            'all_types':len({r['tim'] for r in rows}),'controlled_content':modes,'R18.4':all(modes.values()),'rows':rows,
            'passed':len(rows)==48 and all(r['passed'] for r in rows) and all(modes.values()),'seconds':round(time.monotonic()-start,6)}
        write(out/'summary.json',summary)
    if a.parent_checkpoint:
        text=a.parent_checkpoint.read_text();parent_hash=sha(text)
        # Import verifies the supplied parent before extending it.
        parent=loads(text)
        partners=tuple(WorkPartner(actor,max_load=5) for actor in parent.base.base.base.base.config.actors)
        del parent;gc.collect()
        w=IndividuationWorld.import_r17(text,partners=partners);del text;gc.collect()
        initial_count=len(w._journal);old_shell=w.shell_report()
        inherited=[dumps(tx) for tx in w._journal]
        prefix_hash=sha(''.join(inherited));del inherited
        for actor,wallet in tuple(w._wallets.items()):
            w.execute(Credit('r18:match:'+actor.key,actor,200000-wallet.energy,200000-wallet.time,'R18 matched comparison allocation'))
        acquire_aspects(w);do(w,'',w.config.actors[2],'support',flag=False)
        for n in (0,1):run_order(w,make_offer(w,'held:'+str(n),element_at(w.profiles[0].tim,1),n,held=True,all_traps=True))
        report=evaluate(w)
        prefix_after=sha(''.join(dumps(tx) for tx in w._journal[:initial_count]))
        historical=w.shell_report()
        checkpoint=w.checkpoint();cp_hash=sha(checkpoint);cp_bytes=len(checkpoint.encode())
        with gzip.open(out/'continued_r17.checkpoint.json.gz','wt') as g:g.write(checkpoint)
        write(out/'continued_r17.json',report)
        del w;gc.collect()
        restored=IndividuationWorld.restore(checkpoint)
        exact=restored.checkpoint()==checkpoint
        # Fresh ordinary work after restore exercises retained use again.
        o=run_order(restored,make_offer(restored,'restored:renewal','si',1,held=True,all_traps=True))
        success=restored._records[o.outcome].success and o.credited and len(o.uses)==8
        result={'source_checkpoint_sha256':parent_hash,'prefix_transactions':initial_count,'prefix_unchanged':prefix_hash==prefix_after,
            'historical_assessments_unchanged':{k:v for k,v in old_shell.items() if k!='events_consumed'}=={k:v for k,v in historical.items() if k!='events_consumed'},
            'events_consumed_before':old_shell['events_consumed'],'events_consumed_after':historical['events_consumed'],'report_passed':report['integrity_passed'] and all(report['gates'].values()),
            'checkpoint_sha256':cp_hash,'checkpoint_bytes':cp_bytes,'checkpoint_exact':exact,'fresh_controller_after_restore':success}
        result['passed']=all(result[k] for k in ('prefix_unchanged','historical_assessments_unchanged','report_passed','checkpoint_exact','fresh_controller_after_restore'))
        write(out/'r17_continuation.json',result);print(json.dumps(result),flush=True)
        summary['r17_continuation']=result['passed'];summary['passed'] &= result['passed'];write(out/'summary.json',summary)
    print(json.dumps({'passed':summary['passed'],'cases':len(rows)}),flush=True)
    return 0 if summary['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
