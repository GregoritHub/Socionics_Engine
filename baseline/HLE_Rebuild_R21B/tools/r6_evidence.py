#!/usr/bin/env python3
"""Reproduce declared R6 controls, source identification and descriptive profile."""
import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from hle.codec import encode
from hle.contracts import Kind,Ref,WorkStatus
from hle.demo import ALICE,BOB,BOX,TOOL,request
from hle.metabolism_records import MetabolicCommand,ProcessingPolicy
from hle.model_a import TYPES
from hle.socion import SocionWorld
from hle.socion_demo import demand,learned_pair,run_socion_demo,settle,world
from hle.socion_records import AgentPolicy,AssessDyads,ConfigureAgent,DeclareDyad,ReceiveCommand
from hle.world_records import Attempt,INSPECT,Tick,TRANSFER,Witness
from tests.test_socion import message_world
from tests.reference_socion import complete_round


def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def save_case(folder,name,w,summary):
    p=folder/name;p.mkdir(parents=True,exist_ok=True)
    (p/'checkpoint.json').write_text(w.checkpoint())
    write(p/'summary.json',summary)
    write(p/'goals.json',[encode(g) for g in w._goal_results.values()])
    write(p/'receptions.json',[encode(r) for r in w._receptions.values()])
    write(p/'reports.json',[encode(r) for r in w._dyad_reports.values()])
    with (p/'events.jsonl').open('w') as f:
        for tx in w._journal:f.write(json.dumps(encode(tx),sort_keys=True)+'\n')
    assert SocionWorld.restore(w.checkpoint()).checkpoint()==w.checkpoint()


def goal_summary(w,u):
    account=w._records[u.account];app=w._records[u.application]
    return {'actor':u.owner.key,'item':u.goal.item.key,'received':None if u.received is None else u.received.key,
        'prediction':None if account.claim is None else account.claim.object.key,
        'guard_used':account.guard is not None,'first_action':w._records[app.enactments[0]].request.operation.key,
        'outcome':app.outcome.value,'discrepancy':app.discrepancy,
        'retained_checking':bool(w._records[u.retained].capabilities)}


def controls(folder):
    w,summary=run_socion_demo();save_case(folder,'integrated',w,summary)
    for r in w._round_results.values():
        assert (r.identity,r.path,r.meaning,r.units)==complete_round(w.config,tuple(w._journal),r.start)
    base=learned_pair();save_case(folder,'independent_learning',base,
        {'goals':[goal_summary(base,u) for u in base._goal_results.values()],
         'both_learned':all(base.agent_state(a).lesson is not None for a in base.config.actors)})
    matched=[]
    for enabled in (False,True):
        c=SocionWorld.restore(base.checkpoint())
        resources={a.key:encode(c._wallets[a]) for a in c.config.actors}
        for a in c.config.actors:c.execute(ConfigureAgent('ablate:'+a.key,
            replace(c._agent_policies[a],use_lesson=enabled),'matched prospective access to retained checking'))
        start=len(c._journal);u=demand(c,'heldout',ALICE,TOOL,BOB)
        row={'lesson_access':enabled,'common_prefix_sha256':hashlib.sha256(base.checkpoint().encode()).hexdigest(),
            'initial_resources':resources,**goal_summary(c,u),
            'responder_inspections':sum(type(t.command) is Attempt and t.command.action.actor==BOB and
                t.command.action.operation==INSPECT for t in c._journal[start:])}
        matched.append(row);save_case(folder,'lesson_'+str(enabled).lower(),c,row)
    assert matched[0]['common_prefix_sha256']==matched[1]['common_prefix_sha256']
    assert matched[0]['initial_resources']==matched[1]['initial_resources']
    assert [(r['guard_used'],r['first_action'],r['responder_inspections']) for r in matched]==[
        (False,'r2.transfer',0),(True,'r2.inspect',1)]
    write(folder/'matched_lessons.json',matched)
    factorial=[]
    for receiver_enabled,sender_enabled in ((False,False),(False,True),(True,False),(True,True)):
        c=SocionWorld.restore(base.checkpoint())
        for a,enabled in ((ALICE,receiver_enabled),(BOB,sender_enabled)):
            c.execute(ConfigureAgent('factor:'+a.key,replace(c._agent_policies[a],use_lesson=enabled),
                'independently crossed source/receiver lesson access'))
        start=len(c._journal);u=demand(c,'heldout',ALICE,TOOL,BOB)
        row={'receiver_lesson':receiver_enabled,'sender_lesson':sender_enabled,**goal_summary(c,u),
            'responder_inspections':sum(type(t.command) is Attempt and t.command.action.actor==BOB and
                t.command.action.operation==INSPECT for t in c._journal[start:])}
        assert row['guard_used']==receiver_enabled and bool(row['responder_inspections'])==sender_enabled
        assert row['first_action']==('r2.inspect' if receiver_enabled else 'r2.transfer')
        factorial.append(row)
    write(folder/'matched_lessons_factorial.json',factorial)
    communication=[]
    for ask in (False,True):
        c=world(agents=(AgentPolicy(ALICE,ask=ask),AgentPolicy(BOB)));settle(c)
        c.execute(Attempt('give','give',request(BOB,TRANSFER,(TOOL,ALICE))));settle(c)
        before={a.key:encode(c._wallets[a]) for a in c.config.actors}
        u=demand(c,'act',ALICE,TOOL,BOB)
        row={'ask':ask,'initial_resources':before,**goal_summary(c,u)}
        communication.append(row);save_case(folder,'query_'+str(ask).lower(),c,row)
    assert communication[0]['initial_resources']==communication[1]['initial_resources']
    assert [r['first_action'] for r in communication]==['r2.inspect','r2.transfer']
    write(folder/'communication.json',communication)
    responses=[]
    for response in ('adaptive','fresh','silent'):
        c=world(agents=(AgentPolicy(ALICE,patience=80),AgentPolicy(BOB,response=response)));settle(c)
        start=len(c._journal);u=demand(c,'g',ALICE,BOX,BOB)
        responses.append({'response_policy':response,**goal_summary(c,u),'responder_inspections':sum(
            type(t.command) is Attempt and t.command.action.actor==BOB and t.command.action.operation==INSPECT
            for t in c._journal[start:])})
    write(folder/'response_policies.json',responses)
    observations=[]
    for mode in ('occurrence','full'):
        c=world(witnesses=(Witness(ALICE,TOOL,mode),));settle(c)
        c.execute(Attempt('give','give',request(BOB,TRANSFER,(TOOL,ALICE))));settle(c)
        from hle.socion_policy import item_key
        observations.append({'visibility':mode,'retained_owner':c.memory_head(ALICE,item_key(TOOL)).content[0].object.key})
    write(folder/'observation_access.json',observations)
    return summary


def type_controls(folder):
    rows=[]
    for typed in (False,True):
        for prices in (False,True):
            for sender in TYPES:
                for receiver in TYPES:
                    w,o=message_world((sender,receiver),ProcessingPolicy(typed,prices))
                    w.execute(ReceiveCommand('receive','receive',BOB,o.ref))
                    r=w._receptions[(BOB,'receive')]
                    rows.append({'typed_routing':typed,'positional_prices':prices,'sender':sender,'receiver':receiver,
                        'source_position':r.source_position,'landing_position':r.landing_position,
                        'path':r.plan.path,'positions':r.plan.positions,'units':r.plan.required,
                        'completed':r.outcome.value,'claim':encode(o.content[0])})
    assert len(rows)==1024 and all(r['completed']=='completed' for r in rows)
    for prices in (False,True):
        assert len({r['units'] for r in rows if not r['typed_routing'] and r['positional_prices']==prices})==1
    write(folder/'type_price_receptions.json',rows)
    integrated=[]
    for typed in (False,True):
        for prices in (False,True):
            for t in TYPES:
                w=world(types=('lse',t),processing=ProcessingPolicy(typed,prices));settle(w)
                # A fixed world intervention supplies the same information asymmetry.
                w.execute(Attempt('give','give',request(BOB,TRANSFER,(TOOL,ALICE))));settle(w)
                u=demand(w,'g',ALICE,TOOL,BOB)
                integrated.append({'typed_routing':typed,'positional_prices':prices,'responder_type':t,
                    'charged':{a.key:w._spent[a] for a in w.config.actors},**goal_summary(w,u)})
    assert len(integrated)==64 and all(r['first_action']=='r2.transfer' and not r['discrepancy'] for r in integrated)
    write(folder/'integrated_type_controls.json',integrated)
    return {'paid_reception_cases':len(rows),'integrated_type_cases':len(integrated),
        'typed_positional_reception_units':sorted({r['units'] for r in rows if r['typed_routing'] and r['positional_prices']})}


def profile():
    rows=[]
    for inactive,unrelated in ((0,0),(2000,0),(0,100),(2000,100)):
        w=world();settle(w)
        demand(w,'warm:out',ALICE,BOX,BOB);demand(w,'warm:back',BOB,BOX,ALICE)
        w.execute(DeclareDyad('profile','profile',ALICE,BOB,BOX))
        for i in range(unrelated):w.execute(DeclareDyad('other:'+str(i),'other:'+str(i),ALICE,BOB,TOOL))
        w.execute(AssessDyads('initial',unrelated+1))
        for i in range(inactive):w.execute(Tick('inactive:'+str(i)))
        active=[];visits=[];units=[]
        for i in range(6):
            before=sum(w._spent.values());before_visits=w.dyad_visits;t=time.perf_counter()
            demand(w,f'cycle:{i}:out',ALICE,BOX,BOB);demand(w,f'cycle:{i}:back',BOB,BOX,ALICE)
            w.execute(AssessDyads('active:'+str(i)))
            active.append((time.perf_counter()-t)*1000);visits.append(w.dyad_visits-before_visits)
            units.append(sum(w._spent.values())-before)
        t=time.perf_counter();cp=w.checkpoint();save=(time.perf_counter()-t)*1000
        t=time.perf_counter();c=SocionWorld.restore(cp);replay=(time.perf_counter()-t)*1000
        assert c.checkpoint()==cp and visits==[1]*6
        rows.append({'inactive_ticks':inactive,'unrelated_studies':unrelated,
            'roundtrip_and_assessment_ms_median':statistics.median(active),'samples_ms':active,
            'charged_units_per_cycle':units,'assessment_visits':visits,
            'events':len(w._journal),'checkpoint_bytes':len(cp.encode()),'save_ms':save,'replay_ms':replay})
    return rows


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--tests',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    tests=json.loads(args.tests.read_text());assert tests['successful']
    current_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ('hle','tests','tools','docs') for p in sorted((ROOT/folder).rglob('*'))
        if p.is_file() and '__pycache__' not in p.parts}
    for name,digest in current_hashes.items():
        if name.startswith(('hle/','tests/')):assert tests['source_hashes'].get(name)==digest,('tests/source mismatch',name)
    preserved=json.loads((ROOT/'docs/inherited_R5_sha256.json').read_text())
    for f in preserved['unchanged_files']:
        assert hashlib.sha256((ROOT/f['path']).read_bytes()).hexdigest()==f['sha256'],f['path']
    inherited=[t for t in tests['tests'] if not t['test'].startswith('tests.test_socion.')]
    assert len(inherited)==187 and all(t['status']=='passed' for t in inherited)
    write(args.output/'source_preservation.json',{**preserved,'passed':True,'inherited_tests_passed':187})
    summary=controls(args.output)
    print('behavioral controls complete',flush=True)
    type_summary=type_controls(args.output);print('type/price controls complete',flush=True)
    write(args.output/'profile.json',profile());print('descriptive profile complete',flush=True)
    seeds=[]
    code="import sys,hashlib;sys.path.insert(0,sys.argv[1]);from hle.socion_demo import run_socion_demo;print(hashlib.sha256(run_socion_demo()[0].checkpoint().encode()).hexdigest())"
    for seed in (0,1,2):
        p=subprocess.run([sys.executable,'-I','-c',code,str(ROOT)],env={**os.environ,'PYTHONHASHSEED':str(seed)},
            capture_output=True,text=True,check=True)
        # -I ignores PYTHONHASHSEED. A second nonisolated run explicitly tests it.
        q=subprocess.run([sys.executable,'-c',code,str(ROOT)],env={**os.environ,'PYTHONHASHSEED':str(seed)},
            capture_output=True,text=True,check=True)
        seeds.append({'seed':seed,'isolated':p.stdout.strip(),'seeded':q.stdout.strip()})
    assert len({r[k] for r in seeds for k in ('isolated','seeded')})==1
    write(args.output/'hash_seed_controls.json',seeds)
    gate=json.loads((ROOT/'docs/acceptance_plan_R6.json').read_text())
    write(args.output/'acceptance_panel.json',{'scope':gate['scope'],'gates':[
        {**g,'status':'passed','tests':[t['test'] for t in tests['tests'] if g['id'] in t['rules']],
         'additional_evidence':'source_preservation.json and complete extracted-release verification' if g['id']=='X09' else None}
        for g in gate['gates']]})
    write(args.output/'environment.json',{'python':sys.version,'platform':platform.platform(),
        'cpu':next((x.split(':',1)[1].strip() for x in Path('/proc/cpuinfo').read_text().splitlines() if x.startswith('model name')),'unknown'),
        'command':sys.argv,'source_hashes':current_hashes,'test_source_hashes':tests['source_hashes']})
    write(args.output/'summary.json',{**summary,**type_summary,'tests_run':tests['tests_run'],
        'all_acceptance_controls_passed':True,'sustained_efficiency_acceptance':'R10 remains open'})
    print(json.dumps({'tests':tests['tests_run'],**type_summary,'controls_passed':True}))


if __name__=='__main__':main()
