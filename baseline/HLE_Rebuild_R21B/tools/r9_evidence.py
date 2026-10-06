#!/usr/bin/env python3
"""R9 bounded lifecycle evidence, source preservation and descriptive profile."""
import argparse,hashlib,json,os,platform,statistics,subprocess,sys,time
from dataclasses import replace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from hle.organization import OrganizationWorld,terms_id
from hle.organization_demo import prepared,propose,agree,perform,run_organization_demo,ALICE,BOB,CARA
from hle.organization_records import Formulate,OrganizationCommand,OrganizationTransaction
from hle.language_demo import acquire
from hle.model_a import TYPES
from hle.world_records import Tick
from tests.reference_organization import consent,actions


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--tests',type=Path,required=True)
    args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
    tests=json.loads(args.tests.read_text());assert tests['successful']
    for name,digest in tests['source_hashes'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    def save(name,value): (out/name).write_text(json.dumps(value,indent=2)+'\n')
    w,demo,prefixes=run_organization_demo();save('demo.json',demo)
    cp=w.checkpoint();(out/'demo.checkpoint.json').write_text(cp)
    replay=[]
    for n,prefix in enumerate(prefixes):
        c=OrganizationWorld.restore(prefix);assert c.checkpoint()==prefix
        begin=len(c._journal)
        for tx in w._journal[begin:]:c.execute(tx.command)
        assert c.checkpoint()==cp
        replay.append({'phase':n,'prefix_events':begin,'continued_events':len(c._journal)-begin,'equal':True})
    save('continuation.json',replay)
    ledger=[];oracles=[];runs=[]
    for tx in w._journal:
        ledger.append({'event':tx.event.ref.key,'action':tx.event.action,'outcome':tx.event.outcome.value,
            'charged_units':sum(x.completed_units for x in tx.works),
            'results':[{'ref':r.ref.key,'owner':getattr(getattr(r,'owner',None),'key',None),
                'kind':getattr(r,'kind',None),'status':getattr(r,'status',None),
                'terms':None if getattr(r,'terms',None) is None else terms_id(r.terms)} for r in getattr(tx,'extra',())]})
        if type(tx) is OrganizationTransaction:
            for r in tx.extra:
                if r.kind=='agreement' and r.status=='active':
                    valid=consent(w._journal,r.owner,r.ref);assert valid
                    oracles.append({'owner':r.owner.key,'ref':r.ref.key,'exact_consent':valid,'terms':terms_id(r.terms)})
                if r.kind=='run':
                    runs.append({'owner':r.owner.key,'ref':r.ref.key,'outcome':w.organization_outcome(r.owner,r.ref),
                        'actual_actions':[[a.key,op,[x.key for x in inputs],status,energy] for a,op,inputs,status,energy in actions(w._journal,r.ref)]})
    save('demo-ledger.json',ledger);save('consent-oracle.json',oracles);save('physical-runs.json',runs)
    panel=[]
    base=prepared()
    for tim in sorted(TYPES):
        profiles=tuple(replace(x,tim=tim) if x.owner==BOB else x for x in base.profiles)
        q=OrganizationWorld(base.config,profiles,base.policy,base.agents,base.organization_policies)
        for tx in base._journal[1:]:q.execute(tx.command)
        p=propose(q,ALICE,'panel');identity=agree(q,ALICE,p,'panel:agree')
        outcomes=[]
        for n,a in enumerate((ALICE,BOB,CARA)):
            run=perform(q,a,identity,'panel:use:'+str(n));outcomes.append(q.organization_outcome(a,run))
        assert outcomes==['fulfilled']*3
        panel.append({'varied_participant':'bob','type':tim,'outcomes':outcomes,'bob_units':base.config.wallets[1].energy-q._wallets[BOB].energy})
    save('type-panel.json',panel)
    profiles=[]
    for history in (0,2000):
        q=prepared();access=acquire(q,ALICE,(base.config.ownership[0].item,),'profile:access')
        before=q.organization_candidate_visits
        for n in range(history):q.execute(Tick('inactive:'+str(n)))
        assert q.organization_candidate_visits==before
        times=[];units=[];visits=[]
        for n in range(7):
            cmd=OrganizationCommand('profile:'+str(n),'profile:'+str(n),ALICE,Formulate(access))
            wallet=q._wallets[ALICE];v=q.organization_candidate_visits;t=time.perf_counter()
            q.execute(cmd);duration=time.perf_counter()-t
            if n:times.append(duration*1000);units.append(wallet.energy-q._wallets[ALICE].energy);visits.append(q.organization_candidate_visits-v)
        t=time.perf_counter();cp=q.checkpoint();save_ms=(time.perf_counter()-t)*1000
        t=time.perf_counter();c=OrganizationWorld.restore(cp);replay_ms=(time.perf_counter()-t)*1000
        assert c.checkpoint()==cp
        profiles.append({'inactive_ticks':history,'active_units':units,'candidate_visits':visits,'active_median_ms':statistics.median(times),
            'checkpoint_bytes':len(cp.encode()),'save_ms':save_ms,'replay_ms':replay_ms})
    save('profile.json',{'platform':platform.platform(),'python':sys.version,'workload':'formulate from one indexed template with two successes and two partners; six measured runs after warmup',
        'conditions':profiles,'gate':'descriptive only; R10 sustained acceptance open'})
    hashes=[]
    code='from hle.organization_demo import run_organization_demo; import hashlib; print(hashlib.sha256(run_organization_demo()[0].checkpoint().encode()).hexdigest())'
    for seed in ('0','1','77'):
        env=dict(os.environ,PYTHONHASHSEED=seed)
        p=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,text=True,capture_output=True,check=True,timeout=60)
        hashes.append({'seed':seed,'checkpoint_sha256':p.stdout.strip()})
    assert len({x['checkpoint_sha256'] for x in hashes})==1;save('hash-seeds.json',hashes)
    inherited=json.loads((ROOT/'docs/inherited_R8_sha256.json').read_text())
    changed=[name for name,digest in inherited.items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
    allowed=['docs/acceptance_plan.json','docs/rules.json','hle/__init__.py','hle/__main__.py','hle/codec.py','tools/package_source.py']
    assert sorted(changed)==sorted(allowed),changed
    save('preservation.json',{'inherited_files':len(inherited),'changed':changed,'unchanged':len(inherited)-len(changed),
        'all_inherited_tests_and_references_unchanged':not any(x.startswith(('tests/','reference/')) for x in changed)})
    save('summary.json',{'milestone':'R9','tests':tests['tests_run'],'test_failures':tests['failures'],'test_errors':tests['errors'],
        'r9_tests':sum(x['test'].startswith('tests.test_organization.') for x in tests['tests']),
        'panel_cases':len(panel),'panel_passed':len(panel),'consent_oracle_cases':len(oracles),'demo':demo,
        'institution_family':'finite ownership procedure grammar','unrestricted_invention':'unassessed','sustained_efficiency':'unassessed'})
    print(json.dumps({'tests':tests['tests_run'],'panel_cases':len(panel),'oracle_cases':len(oracles),'passed':True}))

if __name__=='__main__':main()
