"""Execute deterministic bounded R14.5 behavioral, replay and cost panels."""
import sys,json,hashlib,time,platform
from pathlib import Path
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from hle.concept_demo import world,history_case,classroom
from hle.autonomy_demo import world as old_world,run,report
from hle.autonomy import AutonomousWorld
from hle.autonomy_policy import decide
from hle.conceptual import ConceptualWorld
from hle.concept_records import ConceptTransaction
from hle.codec import dumps,loads
from hle.model_a import TYPES
from hle.memory_records import MemoryCommand,DetailQuery
from hle.world_records import Tick,ENERGY,TIME

OUT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'evidence/r145/panel'
OUT.mkdir(parents=True,exist_ok=True)
def save(name,data):
    (OUT/(name+'.json')).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
def stats(w):
    # Resource unit labels are read from actual work rather than inferred.
    return {'events':len(w._journal),'charged_work':sum(work.completed_units for tx in w._journal for work in tx.works),
        'bindings':len(w._binding_heads),'concept_revisions':sum(type(t) is ConceptTransaction and t.concept is not None for t in w._journal),
        'checkpoint_bytes':len(w.checkpoint().encode())}

rows=[]
for tim in TYPES:
    w=world(tim=tim);schedule=run(w,2000);s=w.conceptual_state(w.config.actors[0])
    assert s.practiced and not s.tensions and not schedule['horizon_exhausted']
    rows.append({'type':tim,'relations':s.relations,'tensions':s.tensions,**stats(w)})
save('types',rows);print('16 types passed',flush=True)
rows=[]
for tim in TYPES:
    cases=[]
    for training in (False,True):
        w,r=history_case(training,tim=tim);assert r['practiced'] and not r['second']['horizon_exhausted'];cases.append(r)
    assert cases[0]['held_out_tool_actions'][-3:]==['clean','inspect','return']
    assert cases[1]['held_out_tool_actions'][-2:]==['clean','return']
    rows.append({'type':tim,'cases':cases})
save('history_contrast',rows);print('16 history pairs passed',flush=True)
rows=[]
for mode in ('none','static','live','revoked'):
    w,r=classroom(mode,retained_trial=(mode=='live'));rows.append(r)
    assert not r['before_practiced'] and r['after_practiced'] and not r['scheduling']['horizon_exhausted']
    if mode=='live':assert r['retained_trial_actions']==['use','clean','return']
    (OUT/('classroom_'+mode+'.checkpoint.json')).write_text(w.checkpoint())
save('content_supply_retention',rows);print('content/supply/retention passed',flush=True)
w=world();run(w,2000);cp=loads(w.checkpoint());final=w.checkpoint()
(OUT/'standard.checkpoint.json').write_text(final)
for n in range(1,len(cp.journal)+1):
    restored=ConceptualWorld.restore(dumps(replace(cp,journal=cp.journal[:n])))
    for tx in cp.journal[n:]:
        restored.execute(tx.command);assert restored._journal[-1]==tx
    assert restored.checkpoint()==final
save('replay',{'prefixes':len(cp.journal),'all_exact':True});print('all prefixes replayed',flush=True)
# Reconstruct independent actor schedulers at completed rounds, not scripted suffixes.
source=world();snapshots=[]
for turn in range(12):
    for actor in source.config.actors:
        if source.autonomy_ready(actor):source.autonomy_step(actor)
    if turn in (0,2,5,8,11):snapshots.append(source.checkpoint())
for checkpoint in snapshots:
    a=ConceptualWorld.restore(checkpoint);b=ConceptualWorld.restore(checkpoint)
    run(a,2000);run(b,2000);assert a.checkpoint()==b.checkpoint()
save('scheduler_reconstruction',{'cases':len(snapshots),'all_exact':True})
class DetailsOnly(AutonomousWorld):
    def _select_participant(self,v,key):return decide(v,key,direct_details=True)
performance=[]
for mode in ('r14','details_only','integrated'):
    times=[]
    for _ in range(3):
        b=old_world()
        w=b if mode=='r14' else DetailsOnly(b.config,b.profiles,b.policy,b.agents,workshop=b.workshop,autonomy=b.autonomy) if mode=='details_only' else world()
        start=time.perf_counter();run(w,2000);times.append(time.perf_counter()-start)
    performance.append({'mode':mode,'elapsed_seconds':times,**stats(w)})
save('cost_comparison',{'platform':platform.platform(),'python':sys.version,'cases':performance})
class IndexedOnly(list):
    def __iter__(self):raise AssertionError('ordinary detail lookup scanned the journal')
    def __reversed__(self):raise AssertionError('ordinary detail lookup reversed the journal')
inactive=[]
for ticks in (0,100,1000):
    w=ConceptualWorld.restore(final);a=w.config.actors[0]
    for i in range(ticks):w.execute(Tick('inactive:'+str(i)))
    key=w.autonomy_state(a).catalog[0].key;before=w._wallets[a].energy
    w._journal=IndexedOnly(w._journal)
    start=time.perf_counter();w.execute(MemoryCommand('bounded-lookup','bounded-lookup',a,DetailQuery((key,),w.config.context,w.now)))
    elapsed=time.perf_counter()-start;paid=before-w._wallets[a].energy
    w._journal=w._journal[:]
    start=time.perf_counter();checkpoint=w.checkpoint();encoding=time.perf_counter()-start
    inactive.append({'inactive_ticks':ticks,'lookup_work':paid,'lookup_seconds':elapsed,'checkpoint_bytes':len(checkpoint),'checkpoint_seconds':encoding})
assert len({r['lookup_work'] for r in inactive})==1
save('inactive_history',inactive)
# Account balances independently from the original wallets and all posted work.
for a in w.config.actors:
    initial=next(x for x in w.config.wallets if x.actor==a)
    units={ENERGY:initial.energy,TIME:initial.time}
    for tx in w._journal:
        for work in tx.works:
            if work.owner==a:
                # Resource names are versioned strings in the inherited contract.
                before={x.unit:x.amount for x in work.before};after={x.unit:x.amount for x in work.after}
                assert before==units
                for unit in before:
                    assert after[unit]==before[unit]+sum(x.amount for x in work.credited if x.unit==unit)-sum(x.amount for x in work.charged if x.unit==unit)
                units=after
    assert units=={ENERGY:w._wallets[a].energy,TIME:w._wallets[a].time}
summary={'passed':True,'types':16,'history_pairs':16,'classroom_conditions':4,'held_out_after_supply_removal':True,
    'checkpoint_prefixes':len(cp.journal),'scheduler_reconstructions':len(snapshots),'inactive_history_cases':3,
    'shell_generation':'unassessed','full_individuation':'unassessed','full_rank_semantics':'not claimed'}
save('summary',summary);print(json.dumps(summary),flush=True)
