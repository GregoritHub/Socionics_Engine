"""Attention costs conditional on type, actual emission and receiver history."""
from dataclasses import replace
from itertools import permutations
import hashlib
from .common import *
from hle.model_a import TYPES, ELEMENT, element_at, position_of, fields
from hle.socion import reception_plan
from hle.socion_records import Notice
from hle.metabolism_records import Profile
from hle.relations import landing_position, landing_permutation


def oracle(receiver,start,element):
    """Independent positional cube enumeration; no engine paths or route cache."""
    p=position_of(receiver,start)-1;t=position_of(receiver,element)-1
    prices={0:1,1:2,2:3,3:4,4:4,5:3,6:2,7:1}
    def segments(a,b):
        bits=[1<<i for i in range(3) if (a^b)&(1<<i)]
        result=[]
        for ordering in permutations(bits):
            at=a;cost=0
            for bit in ordering:
                at^=bit;cost+=prices[at]
            result.append(cost)
        return result
    return min(x+y for s in (4,6) for x in segments(p,s) for y in segments(s,t))+prices[t]


def charge(w,sender,receiver,element,start):
    obs=w._journal[0].observations[0]
    notice=Notice(obs.ref,obs.source,DARA,'report',obs.content[0],sender_type=sender,element=element)
    p=Profile(ALICE,receiver)
    state=replace(w.processing_state(ALICE),active=start)
    source,landing,plan=reception_plan(p,state,notice,w.policy)
    assert plan.required==oracle(receiver,start,element)
    return {'source_position':source,'landing_position':landing,'units':plan.required,'path':list(plan.path)}


def empirical(sender,receiver,history=False,opportunity=False):
    w=world(types=(receiver,'iee','lsi',sender));m=Meter(w)
    accesses={}
    for a in (ALICE,DARA):
        acc=m.call('setup:'+a.key+':access',lambda:acquire(w,a,(BOX,),a.key+':access'))
        accesses[a]=acc
        m.call('setup:'+a.key+':learn',lambda:finish(w,a,Learn('kept',acc),a.key+':learn'))
    before=snapshot(w)
    payload=Produce(speech(w,DARA,ALICE))
    if opportunity:
        m.call('produce',lambda:w.execute(LanguageCommand('produce','produce',DARA,payload,20)))
        job=w.language_job(DARA,'produce')
        return {'sender':sender,'required':job.required,'paid':job.paid,'status':job.outcome.value,
            'has_published_utterance':job.result is not None,'active':w.processing_state(DARA).active}
    job=m.call('produce',lambda:finish(w,DARA,payload,'produce'))
    utterance=job.result
    from hle.codec import dumps
    utterance_sha256=hashlib.sha256(dumps(w.language_record(DARA,utterance)).encode()).hexdigest()
    after_produce=snapshot(w)
    if history:
        prior=w.lexeme(DARA,'kept').ref
        m.call('sender:relearn',lambda:finish(w,DARA,Learn('kept',accesses[DARA],expected=prior),'sender:relearn'))
    element=w.processing_state(DARA).active;start=w.processing_state(ALICE).active
    expected=charge(w,sender,receiver,element,start)
    obs=m.call('send',lambda:emit(w,DARA,utterance,ALICE,'send'))
    rec=m.call('read',lambda:read(w,ALICE,obs,'read'))
    acc=m.call('receiver:access',lambda:acquire(w,ALICE,(BOX,),'receiver:current'))
    interpreted=m.call('interpret',lambda:finish(w,ALICE,Interpret(obs,acc),'interpret'))
    assert rec.plan.required==expected['units']
    return {'sender':sender,'receiver':receiver,'history':'after_relearn' if history else 'after_produce',
        'element':element,'receiver_start':start,'produce_units':delta(before,after_produce)['dara'],
        'utterance_sha256':utterance_sha256,
        'read_units':rec.plan.required,'interpret_units':interpreted.required,
        'interpretation':w.language_record(ALICE,interpreted.result).status,
        'landing_position':rec.landing_position,'source_position':rec.source_position,
        'path':list(rec.plan.path),'ledger':m.rows}


def run():
    w=world();labels=json.loads((Path(__file__).resolve().parents[1]/'sources/relation_labels.json').read_text())
    seat_one=[];actual_fe=[];states=[]
    for a in TYPES:
        for b in TYPES:
            label=labels[a+':'+b]
            assert tuple(label['landing_permutation'])==landing_permutation(a,b)
            row={'sender':a,'receiver':b,'relation':label['relation']}
            seat_one.append(dict(row,**charge(w,a,b,element_at(a,1),element_at(b,1))))
            actual_fe.append(dict(row,**charge(w,a,b,'fe',element_at(b,1))))
            for e in ELEMENT:
                assert element_at(b,landing_position(a,position_of(a,e),b))==e
    for b in TYPES:
        for start in ELEMENT:
            for element in ELEMENT:
                states.append({'receiver':b,'start':start,'element':element,**charge(w,'eii',b,element,start)})
    empirical_rows=[];history_rows=[]
    for a in TYPES:
        for b in TYPES:
            empirical_rows.append(empirical(a,b))
            history_rows.append(empirical(a,b,history=True))
    return {'analytic_seat_one':seat_one,'analytic_fe_receiver_seat_one':actual_fe,
        'analytic_element_state':states,'empirical':empirical_rows,'history_control':history_rows,
        'twenty_unit_opportunity':[empirical(t,'lse',opportunity=True) for t in TYPES],
        'element_preservation_checks':2048,'oracle_comparisons':1536+512}
