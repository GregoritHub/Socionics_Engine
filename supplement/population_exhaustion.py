"""Supplied opportunities for sustained groups; all rules/votes/work are outputs.

The initial resource quantities, types, material thresholds and blame histories
are declared experimental inputs. This driver is NOT a general society policy.
"""
from dataclasses import replace
import time
from u14_support import *
from tests_u12 import fixtures as f
from hle_unified.compact import unseal
from hle_unified.cognition import profile
from hle_unified.institution_audit import audit
from hle_unified.records import Material
from hle.model_a import TYPES

TIMS = tuple(sorted(TYPES))


def setup_case(case):
    seed = case['seed']; size = case['population']; domain = case['domain']
    founders = (f.ALICE, f.BOB) + tuple(f.ref('member-' + str(i)).identity for i in range(size-3))
    actors = (*founders, f.EVE)
    base = f.setup11(tim=case['tim'], budget=case['budget'], train_bob=False)
    original = f.OperationStore.restore(unseal(base.checkpoint(), base.SCHEMA)['initial'])
    world = f.OperationStore()
    types = {a: TIMS[(TIMS.index(case['tim']) + i*5) % 16] for i, a in enumerate(actors)}
    for tx in original.journal():
        versions = []
        for v in tx.versions:
            d = f.attrs(v)
            if v.ref.identity.namespace == 'u5.profile': v = profile(d['actor'], types[d['actor']])
            if v.ref.identity.key.startswith('u11-repair-'):
                v = replace(v, facets=(replace(v.facet(Material), quantity=case['repair_stock']),))
            if v.ref.identity.key.startswith('u11-care-'):
                v = replace(v, facets=(replace(v.facet(Material), quantity=case['care_stock']),))
            versions.append(v)
        world.create(tx.key, f.WRITER, tuple(versions))
    extra = []
    for actor in founders[2:]:
        extra += [f.ObjectVersion(f.ObjectRef(actor, 1), f.WRITER, actor.key, (f.Role.PERSON,)),
                  f.record(f.wallet_address(actor), 'Finite release allocation', dict(record_type='wallet', actor=actor,
                    energy=case['budget'], time=case['budget'], initial_energy=case['budget'], initial_time=case['budget'])),
                  profile(actor, types[actor])]
        for name in ('repair', 'transfer', 'use', 'care', 'consume'):
            extra.append(f.tool(f.ref('u11-practice-'+actor.key+'-'+name), owner=actor,
                                damaged=name=='repair', wear=int(name=='care'), maximum=20))
        extra += [f.tool(f.ref('u11-kit-'+actor.key), owner=actor, maximum=60),
                  f.stock(f.ref('u11-repair-'+actor.key), 'repair', case['repair_stock'], actor),
                  f.stock(f.ref('u11-care-'+actor.key), 'care', case['care_stock'], actor),
                  f.stock(f.ref('u11-consume-'+actor.key), 'consume', 20, actor)]
    materials = tuple(f.tool(f.ref('u12-'+domain+'-'+a.key), owner=a,
                            damaged=case['damaged'], maximum=case['max_wear']) for a in actors)
    world.create('u14-initial-opportunities', f.WRITER,
                 (*extra, *materials, f.definition(f.TRIGGER, 'Entrusted performance affordance')))
    e = f.InstitutionEngine(world, f.LAW_REF)
    for actor in actors:
        for obj in (f.ROOM, f.CUE5, *(f.ObjectRef(a,1) for a in actors)): f.expose12(e, actor, obj)
        if actor != f.EVE: f.train(e, actor, ('repair', 'transfer', 'use', 'care', 'consume'))
        e.configure_patterns('patterns-'+actor.key, f.PatternPolicy(actor))
        f.expose12(e, actor, f.TRIGGER); f.slots12(e, actor, domain)
        if case['blame_history'] and actor != f.EVE:
            for j in range(case['blame_history']):
                f.encounter12(e, 'history-'+actor.key+'-'+str(j), actor, domain, feedback='blame')
        f.encounter12(e, 'present-'+actor.key, actor, domain)
    resources = tuple(v.ref for v in materials) + tuple(
        e.world.head(f.ref('u11-'+n+'-'+a.key).identity).ref
        for a in actors for n in ('kit', 'repair', 'care'))
    group = f.group(e, 'release-'+str(seed), resources=resources)
    for actor in founders[1:]: group = f.join(e, group, actor=actor, key='founder-'+actor.key)
    return e, group, founders, actors


def attempt(e, rule, actor, case, key, *, out=None, checkpoint=False):
    """One offered practice. Censoring stays a result and retains partial work."""
    domain=case['domain']; slots=f.slots12(e, actor, domain)
    f.expose12(e, actor, rule['ref'])
    f.expose12(e, actor, e._heads11[rule['group'].identity])
    req=f.InstitutionRequest(key, actor, 'apply', f.ROOM, f.CUE5, rule['ref'],
        encounter=f.current_encounter(e,actor,domain), slots=slots)
    e.start('start:'+key, req)
    e.advance('partial:'+key,actor,key,1)
    clone=None; cpmeta=None
    if checkpoint:
        cp=e.checkpoint()
        save_gzip(out/(key+'.partial.checkpoint.json.gz'),cp)
        t=time.perf_counter(); clone=f.InstitutionEngine.restore(cp)
        cpmeta=dict(partial_status=e.job_status(actor,key)['status'], restore_seconds=time.perf_counter()-t,
                    prefix_exact=clone.checkpoint()==cp)
    def complete(x):
        x.advance('finish:'+key,actor,key,1000000)
        d=x.job_status(actor,key)
        if d['status']!='ready': return dict(status=d['status'], reason=d['failure'], events=0)
        x.commit('commit:'+key,actor,key); d=x.job_status(actor,key)
        records=[x._records11[r] for r in f.indexed(d,'output.')]
        run=next((r for r in records if r['kind']=='run'),None)
        if run is None:
            return dict(status=d['status'] if d['status']!='succeeded' else 'public_wait',
                        reason=d['failure'], events=0)
        values=f.work(x,key+'-consent','accept',actor=actor,focus=run['ref'],expect=False)
        if not values: return dict(status='consent_failed',reason=x.job_status(actor,key+'-consent')['failure'],events=0)
        # Selection may lawfully fail on a consumed or changed resource.
        while run['status']=='active':
            index=run['index']; step=key+'-work-'+str(index)
            scope,worker,_,roles=run['agenda'][index]
            for role,obj in roles:
                if role in ('target','tool','stock','relation'): f.expose(x,worker,x.world.head(obj).ref)
            selected=f.work(x,step+'-select','select',actor=worker,focus=run['ref'],expect=False)
            if not selected:
                return dict(status='selection_failed',reason=x.job_status(worker,step+'-select')['failure'],events=len(run['events']))
            selection,run=selected
            x.enact(step+'-enact',worker,step+'-physical',selection['ref'])
            x.advance(step+'-advance',worker,step+'-physical',1000000)
            if x.job_status(worker,step+'-physical')['status']!='ready':
                return dict(status='partial',reason='resource_budget',events=len(run['events']))
            event=x.commit(step+'-commit',worker,step+'-physical')
            obs=f.receive(x,event,worker,step+'-observed')
            run=f.work(x,step+'-settle','observe',actor=worker,focus=run['ref'],observation=obs)[0]
        if run['status']=='succeeded':
            f.slots12(x,actor,domain)
            practice=f.op12(x,key+'-record','record',actor=actor,focus=run['ref'],domain=domain)[0]
            f.expose12(x,actor,practice['ref'])
        return dict(status=run['status'],reason=run.get('reason',''),events=len(run['events']),
                    run=f'{run["ref"].identity.namespace}:{run["ref"].identity.key}@{run["ref"].revision}')
    result=complete(e)
    if clone is not None:
        other=complete(clone)
        cpmeta['continuation_exact']=result==other and e.checkpoint()==clone.checkpoint()
        if not cpmeta['prefix_exact'] or not cpmeta['continuation_exact']: raise ValueError('partial continuation differs')
        del clone
    return result,cpmeta


def run_case(case,out):
    out=Path(out); out.mkdir(parents=True,exist_ok=False)
    write_json(out/'case.json',case)
    e,g,founders,actors=setup_case(case); domain=case['domain']; checks={}; rows=[]; checkpoints=[]
    proposal=f.propose12(e,g,domain=domain); votes=f.vote12(e,proposal,domain=domain)
    rule=f.ratify12(e,proposal)
    checks['generated_program_and_independent_consent']=proposal['considered']>0 and len(votes)==len(founders) and all(v['choice']=='accept' for v in votes)
    for i in range(2):
        result,_=attempt(e,rule,f.ALICE,case,'trial-'+str(i)); rows.append(dict(stage='trial',actor=f.ALICE.key,**result))
        if result['status']!='succeeded': raise ValueError('funded trial did not perform')
    maintain=f.propose12(e,rule,'maintain',intent='maintain',domain=domain)
    f.vote12(e,maintain,'maintain-votes',domain=domain); rule=f.ratify12(e,maintain,'maintained')
    checks['maintenance_follows_real_work']=rule['status']=='active'
    if case['blame_history']:
        original=e.world.resolve(rule['ref'])
        delay=f.op12(e,'public-burden','apply',actor=f.BOB,focus=rule['ref'],slots=f.slots12(e,f.BOB,domain),domain=domain)
        consequence=next(v for v in delay if v['kind']=='consequence')
        dispute=f.op12(e,'dispute','dispute',actor=f.BOB,focus=consequence['ref'],domain=domain)[0]
        f.correct12(e,f.ALICE,'private-correction',domain)
        review=f.propose12(e,rule,'review',intent='review',support=dispute['ref'],domain=domain)
        vs=f.vote12(e,review,'review-votes',domain=domain)
        for v in vs:f.expose12(e,f.ALICE,v['ref'])
        f.op12(e,'unilateral','ratify',focus=review['ref'],expect=False,domain=domain)
        checks['private_change_preserves_public_consequence']=e.world.resolve(rule['ref'])==original and e.world.head(rule['ref'].identity)==original and e.job_status(f.ALICE,'unilateral')['status']=='failed'
        for actor in founders[1:]: f.correct12(e,actor,'correct-'+actor.key,domain)
        counter=f.op12(e,'counter','counter',actor=f.BOB,focus=review['ref'],slots=f.slots12(e,f.BOB,domain),domain=domain)[0]
        f.vote12(e,counter,'counter-votes',domain=domain); rule=f.ratify12(e,counter,'collective-revision',actor=f.BOB)
        checks['public_revision_has_exact_consents']=rule['gate']=='self_check' and e._records11[consequence['ref']]==consequence
    initial_rule=rule['ref']
    active=list(founders)
    for turn in range(case['opportunities']):
        if turn==case['join_at']:
            current=e._records11[e._heads11[rule['group'].identity]]
            inv=f.work(e,'invite-newcomer','invite',focus=current['ref'],peer=f.EVE)[0]
            f.work(e,'join-newcomer','join',actor=f.EVE,focus=inv['ref'])
            lesson=f.op12(e,'teach-newcomer','teach',focus=rule['ref'],peer=f.EVE,domain=domain)[0]
            understanding=f.op12(e,'understand','learn',actor=f.EVE,focus=lesson['ref'],domain=domain)[0]
            f.op12(e,'assent','assent',actor=f.EVE,focus=understanding['ref'],domain=domain)
            checks['teaching_does_not_give_skill']=not e.participant_view(f.EVE).can_use(f.ref('u11-primitive-use'),f.ROOM)
            f.train(e,f.EVE,('repair','use','care')); active.append(f.EVE)
        if turn==case['leave_at']:
            succession=f.propose12(e,rule,'succession',intent='succession',peer=f.BOB,domain=domain)
            f.vote12(e,succession,'succession-votes',domain=domain)
            rule=f.ratify12(e,succession,'successor')
            group=f.work(e,'founder-leaves','leave',focus=rule['group'])[0]
            active.remove(f.ALICE)
            checks['consented_succession']=rule['steward']==f.BOB and f.ALICE not in group['members']
        actor=active[(turn+case['seed'])%len(active)]
        # Repeat changed demand on different owners; stock is finite, never refilled.
        result,cp=attempt(e,rule,actor,case,'opportunity-'+str(turn),out=out,
                          checkpoint=turn in case['checkpoints'])
        rows.append(dict(stage='sustained',turn=turn,actor=actor.key,**result))
        if cp:checkpoints.append(dict(turn=turn,**cp))
        write_json(out/'progress.json',dict(rows=rows,checkpoints=checkpoints))
    sustained=[r for r in rows if r['stage']=='sustained']
    successes=sum(r['status']=='succeeded' for r in sustained)
    checks['all_opportunities_accounted']=len(sustained)==case['opportunities']
    checks['sustained_useful_work']=successes>=case['minimum_successes']
    checks['declared_scarcity_visible']=case['regime']!='scarce' or successes<len(sustained)
    checks['historical_rules_preserved']=e.world.resolve(initial_rule).ref==initial_rule
    checks['three_partial_continuations']=len(checkpoints)==3 and all(r['continuation_exact'] and r['prefix_exact'] for r in checkpoints)
    artifact=keep_engine(out,'final',e,audit)
    checks['raw_audits']=artifact['accounting']['passed'] and artifact['semantic']['passed']
    result=dict(case=case,passed=all(checks.values()),checks=checks,rows=rows,
                checkpoints=checkpoints,successes=successes,artifact=artifact)
    write_json(out/'summary.json',result)
    return result
