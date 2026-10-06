"""R17 frozen finite panel, controlled resources and independently read outcomes."""
import argparse
from dataclasses import replace
import hashlib,json,time
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from hle.conversion_demo import case,renew
from hle.conversion import ConversionWorld
from hle.conversion_records import ConversionPolicy,ConversionTransaction
from hle.conversion_reference import evaluate
from hle.reconciliation_records import AccountTransaction
from hle.compensation_demo import run,introduce
from hle.concept_demo import fund_command
from hle.world_records import Tick
from hle.codec import loads,dumps
from tests_r17.support import fresh,prefix,first,command,failed_trial

def write(out,name,data):
    (out/name).write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')

def matched_resources(w,budget):
    config=replace(w.config,wallets=tuple(replace(b,
        energy=b.energy-w._wallets[b.actor].energy+budget,
        time=b.time-w._wallets[b.actor].time+budget) for b in w.config.wallets))
    v=fresh(w,config)
    for tx in w._journal[1:]:v.execute(tx.command)
    assert all((b.energy,b.time)==(budget,budget) for b in v._wallets.values())
    return v

def panel(out,resume=False):
    out.mkdir(parents=True,exist_ok=True);reports={};worlds={};setups={};timings={};wallets={}
    variants=[('converted',ConversionPolicy()),('no_access',ConversionPolicy(material_access=False)),
              ('no_practice',ConversionPolicy(practice=False)),('no_retention',ConversionPolicy(retention=False))]
    for name,policy in variants:
        at=time.perf_counter();w,s=case(conversion_policy=policy,stop_after_acquisition=True)
        w=matched_resources(w,20000);wallets[name]={a.key:[b.energy,b.time] for a,b in w._wallets.items()}
        work_before=evaluate(w)['work_units'];renew(w,s);r=evaluate(w)
        r['renewal_work_units']=r['work_units']-work_before;r['setup']=s
        later=set(s['renewed_items']+s['held_out_items'])
        r['renewal_choices']=[x for x in r['choices'] if x['item'] in later]
        r['renewal_returns']=[x for x in r['returns'] if x['item'] in later]
        r['shell_report']=w.shell_report()
        reports[name]=r
        if name=='converted': worlds[name]=w
        setups[name]=s
        if resume:
            assert json.loads((out/(name+'.json')).read_text())==r, 'saved trajectory differs from fresh reconstruction'
        write(out,name+'.json',r)
        timings[name]=round(time.perf_counter()-at,6)
        print(json.dumps({'case':name,'passed':r['passed'],'capacity':r['current_capacity'],'renewal_work':r['renewal_work_units']}),flush=True)
    main=worlds['converted'];setup=setups['converted'];checks={}
    no_peer_substitution=not any(type(tx) is AccountTransaction and tx.command.actor==main.config.actors[0]
        for tx in main._journal[setup['start']:])
    if resume:
        cached=json.loads((out/'complete_replay.json').read_text())
        with (out/'converted.checkpoint.json').open('rb') as source:
            digest=hashlib.file_digest(source,'sha256').hexdigest()
        assert digest==cached['sha256'] and cached['exact'], 'previously completed replay evidence changed'
        exact=cached['exact']
    else:
        cp=main.checkpoint();(out/'converted.checkpoint.json').write_text(cp)
        restored=ConversionWorld.restore(cp)
        exact=restored.checkpoint()==cp and evaluate(restored)==evaluate(main) and restored.shell_report()==main.shell_report()
        write(out,'complete_replay.json',{'exact':exact,'bytes':len(cp.encode()),'sha256':hashlib.sha256(cp.encode()).hexdigest()})
        del restored,cp
    # Full worlds are unnecessary for the remaining witnesses. Retaining four
    # complete histories during nested typed-JSON replay needlessly raises peak
    # evaluator memory; participant state and charges are unchanged.
    del main,worlds,w
    small,small_setup=case(history=1,maintained=1);seen=set();boundaries=[];partial=[]
    for i,tx in enumerate(small._journal):
        if type(tx) is not ConversionTransaction or tx.job.operation in seen:continue
        seen.add(tx.job.operation);v=prefix(small,i+1);text=v.checkpoint();r=ConversionWorld.restore(text)
        equal=r.checkpoint()==text;continuation=True
        if i+1<len(small._journal):r.execute(small._journal[i+1].command);continuation=r._journal[-1]==small._journal[i+1]
        boundaries.append({'operation':tx.job.operation,'events':i+1,'checkpoint':equal,'next_event':continuation})
        if tx.job.operation in ('release','context','reorganize','try','reflect','retain','recall'):
            v=prefix(small,i);cmd=replace(tx.command,work_limit=1);v.execute(cmd)
            no_output=not any(getattr(v._journal[-1],x) for x in ('study','candidate','capacity','use','treatment','concept'))
            r=ConversionWorld.restore(v.checkpoint());next_cmd=replace(cmd,command_id='partial:'+tx.job.operation)
            v.execute(next_cmd);r.execute(next_cmd)
            partial.append({'operation':tx.job.operation,'no_early_output':no_output,'next_event':v._journal[-1]==r._journal[-1]})
        print('continued '+tx.job.operation,flush=True)
        del v,r,text
    write(out,'continuation.json',{'boundaries':boundaries,'partial':partial})
    failed,event=failed_trial(small);open_report=evaluate(failed);run(failed);failed_report=evaluate(failed)
    # Continue the same material through the other required practice branch.
    introduce(failed,3);run(failed)
    revised=evaluate(failed);introduce(failed,4);run(failed);reused=evaluate(failed)
    text=failed.checkpoint();again=ConversionWorld.restore(text)
    failed_exact=again.checkpoint()==text
    write(out,'failed_practice.json',{'initial':open_report,'retry':failed_report,'retained':revised,'renewed':reused,
        'exact_replay':failed_exact,
        'learned_checks':[tx.event.ref.key for tx in failed._journal if tx.event.action=='r14.inspect' and tx.command.command_id.startswith('r17:')]})
    del failed,again,text
    dynamic=[]
    for op in ('restrict','withdraw'):
        w=prefix(small,small_setup['acquired']);fund_command(w,command(w,op,work_limit=256));introduce(w,4);run(w);r=evaluate(w)
        dynamic.append({'control':op,'passed':r['passed'],'last_choice':r['choices'][-1],'current_capacity':r['current_capacity'],'material_preserved':r['material_preserved']})
    write(out,'post_acquisition_controls.json',dynamic)
    inactive=[];i=first(small,'reorganize')
    for n in (0,100,1000):
        w=prefix(small,i)
        for k in range(n):w.execute(Tick('inactive:'+str(k)))
        class IndexedOnly(list):
            def __iter__(self):raise AssertionError('active conversion scanned history')
        w._journal=IndexedOnly(w._journal);w.execute(small._journal[i].command)
        inactive.append({'ticks':n,'required':w._journal[-1].job.plan.required,'charged':sum(x.completed_units for x in w._journal[-1].works)})
    write(out,'inactive.json',inactive)
    del w,small
    old=(ROOT/'evidence/r16b/panel/maintained.checkpoint.json').read_text()
    imported=ConversionWorld.import_r16(old)
    migration={'journal_exact':loads(imported.checkpoint()).base==loads(old),
               'positive_history':imported.shell_report()['groups'],'events':len(imported._journal)}
    write(out,'r16_import.json',migration);write(out,'matched_resources.json',wallets)
    full=reports['converted'];ops=full['operations'];controls=[reports[x] for x in ('no_access','no_practice','no_retention')]
    checks['R17.1']=(any(x.get('preserved') for x in ops) and any(x.get('contrasting_conditions') for x in ops)
        and any(x.get('unfinished') for x in ops) and any(x.get('covered')==[False] for x in ops)
        and any(x.get('reowned') for x in ops) and full['current_capacity'])
    checks['R17.2']=(len(full['recalls'])==4 and all(x['mode']=='direct' and x['retained_use'] for x in full['renewal_choices'] if not x['required'])
        and len([x for x in full['renewal_choices'] if not x['required']])==3
        and all(not r['current_capacity'] and not r['recalls'] and all(x['mode']=='confirm' for x in r['renewal_choices']) for r in controls)
        and not reports['no_access']['practice'] and not reports['no_practice']['practice']
        and len(reports['no_retention']['practice'])==2)
    checks['no_peer_account_substitution']=no_peer_substitution
    checks['independent_and_accounting']=all(r['passed'] and r['material_preserved'] for r in reports.values())
    checks['real_required_terms']=all(x['mode']=='confirm' for r in reports.values() for x in r['renewal_choices'] if x['required'])
    checks['physical_returns']=all(len(r['renewal_returns'])==4 and all(x['correct'] for x in r['renewal_returns']) for r in reports.values())
    checks['matched_current_resources']=all(v==wallets['converted'] for v in wallets.values())
    checks['honest_scheduling']=all(not q['horizon_exhausted'] and not q['resource_censored'] for s in setups.values() for q in s['scheduling'])
    checks['historical_signs_preserved']=all(
        full['shell_report']['groups'][0]['signs'][k]['positive']>=3 and setup['historical_report']['groups'][0]['signs'][k]['positive']==3
        for k in setup['historical_report']['groups'][0]['signs'])
    checks['failed_reorganization_and_revision']=(open_report['passed'] and not open_report['current_capacity']
        and not open_report['practice'][-1]['success'] and failed_report['passed']
        and any(x['success'] for x in failed_report['practice']) and revised['current_capacity']
        and reused['passed'] and reused['choices'][-1]['retained_use'] and failed_exact)
    checks['post_acquisition_dependence']=all(x['passed'] and x['last_choice']['mode']=='confirm' and x['material_preserved'] for x in dynamic)
    checks['exact_replay']=exact and all(x['checkpoint'] and x['next_event'] for x in boundaries) and all(x['no_early_output'] and x['next_event'] for x in partial)
    checks['r16_import']=migration['journal_exact']
    checks['inactive']=len({x['required'] for x in inactive})==1 and len({x['charged'] for x in inactive})==1
    checks['frozen_parent']=hashlib.sha256((ROOT/'docs/r12/acceptance_v1.json').read_bytes()).hexdigest()=='91c7ca3b79cfa5b455268ff0bb497defdce33e91d808e42f14c0c01f16291c1b'
    summary={'schema':'r17-panel-v1','gates':checks,'passed':all(checks.values()),
        'renewal_work_units':{n:r['renewal_work_units'] for n,r in reports.items()},
        'parent_R17_complete':all(checks.values()),'completed_parents':6 if all(checks.values()) else 5,
        'remaining_parents':4 if all(checks.values()) else 5,'clearance':'unassessed; R19 remains open'}
    write(out,'summary.json',summary);write(out,'timings.json',timings);print(json.dumps(summary),flush=True)
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'evidence/r17/panel')
    p.add_argument('--resume',action='store_true',help='reuse an unchanged completed full checkpoint replay after reconstructing all four trajectories exactly')
    a=p.parse_args()
    raise SystemExit(0 if panel(a.out.resolve(),a.resume)['passed'] else 1)
