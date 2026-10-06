#!/usr/bin/env python3
"""R8 deterministic behavioral panel, exact traces and descriptive cost profile."""
import argparse, hashlib, json, os, platform, statistics, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from hle.language import LanguageWorld
from hle.language_demo import world,acquire,finish,deliver,enact,run_language_demo
from hle.language_records import Act,Learn,Produce,Speech,Interpret
from hle.demo import ALICE,BOB,BOX,TOOL,config
from hle.metabolism_records import Profile,ProcessingPolicy
from hle.socion_records import AgentPolicy
from hle.model_a import TYPES
from hle.world_records import Tick


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--tests',type=Path,required=True)
    args=parser.parse_args(); out=args.output;out.mkdir(parents=True,exist_ok=True)
    tests=json.loads(args.tests.read_text());assert tests['successful']
    for name,digest in tests['source_hashes'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    def save(name,value): (out/name).write_text(json.dumps(value,indent=2)+'\n')
    w,demo=run_language_demo();save('demo.json',demo);(out/'demo.checkpoint.json').write_text(w.checkpoint())
    ledger=[]
    for tx in w._journal:
        ledger.append({'event':tx.event.ref.key,'action':tx.event.action,'outcome':tx.event.outcome.value,
            'charged_units':sum(x.completed_units for x in tx.works),
            'results':[{'ref':x.ref.key,'status':getattr(x,'status',None)} for x in getattr(tx,'extra',())]})
    save('demo-ledger.json',ledger)
    panel=[]
    for tim in sorted(TYPES):
        for mode in ('request','explain'):
            w=LanguageWorld(config(5000,5000),(Profile(ALICE,'lse'),Profile(BOB,tim)),ProcessingPolicy(),(AgentPolicy(ALICE),AgentPolicy(BOB)))
            a=acquire(w,ALICE,(BOX,),'a');b=acquire(w,BOB,(TOOL,),'b')
            l=finish(w,ALICE,Learn('kept',a),'learn').result
            msg=deliver(w,ALICE,l,BOB,'teach')
            finish(w,BOB,Learn('kept',b,msg),'adopt')
            speech=Speech(mode,(w.word(ALICE,'kept',(TOOL,BOB)),),(Act('inspect',TOOL),Act('transfer',TOOL,ALICE)))
            u=finish(w,ALICE,Produce(speech),'produce').result
            msg=deliver(w,ALICE,u,BOB,'send');r=finish(w,BOB,Interpret(msg,b),'interpret').result
            outcome=enact(w,BOB,r);assert outcome=='fulfilled'
            panel.append({'sender':'lse','receiver':tim,'mode':mode,'outcome':outcome,
                'alice_units':5000-w._wallets[ALICE].energy,'bob_units':5000-w._wallets[BOB].energy})
    save('type-panel.json',panel)
    profiles=[]
    for history in (0,2000):
        w=world();a=acquire(w,ALICE,(BOX,),'a');finish(w,ALICE,Learn('kept',a),'learn')
        for i in range(history):w.execute(Tick('inactive:'+str(i)))
        speech=Speech('request',(w.word(ALICE,'kept',(BOX,ALICE)),),(Act('inspect',BOX),))
        times=[];units=[]
        for i in range(7):
            before=w._wallets[ALICE].energy;t=time.perf_counter();finish(w,ALICE,Produce(speech),'profile:'+str(i));duration=time.perf_counter()-t
            if i:times.append(duration*1000);units.append(before-w._wallets[ALICE].energy)
        t=time.perf_counter();cp=w.checkpoint();save_ms=(time.perf_counter()-t)*1000
        t=time.perf_counter();clone=LanguageWorld.restore(cp);replay_ms=(time.perf_counter()-t)*1000
        assert cp==clone.checkpoint()
        profiles.append({'inactive_ticks':history,'active_units':units,'active_median_ms':statistics.median(times),'checkpoint_bytes':len(cp.encode()),'save_ms':save_ms,'replay_ms':replay_ms})
    save('profile.json',{'platform':platform.platform(),'python':sys.version,'workload':'one known one-call/one-action utterance production; warmup excluded; six cycles','conditions':profiles,'acceptance':'descriptive only; R10 open'})
    hashes=[]
    code='from hle.language_demo import run_language_demo; import hashlib; print(hashlib.sha256(run_language_demo()[0].checkpoint().encode()).hexdigest())'
    for seed in ('0','17','83'):
        env=dict(os.environ,PYTHONHASHSEED=seed)
        result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,text=True,capture_output=True,check=True)
        hashes.append({'seed':seed,'checkpoint_sha256':result.stdout.strip()})
    assert len({x['checkpoint_sha256'] for x in hashes})==1;save('hash-seeds.json',hashes)
    save('summary.json',{'milestone':'R8','tests':tests['tests_run'],'test_failures':tests['failures'],'test_errors':tests['errors'],'panel_cases':len(panel),'panel_passed':len(panel),'demo':demo,'general_language_closure':'unassessed','sustained_efficiency':'unassessed'})
    print(json.dumps({'tests':tests['tests_run'],'panel_cases':len(panel),'passed':True}))

if __name__=='__main__':main()
