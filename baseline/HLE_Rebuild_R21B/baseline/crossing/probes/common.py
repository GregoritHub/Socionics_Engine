"""Shared instrumentation. Policies use explicit goals and delivered outcomes.

Private world reads below are evaluator instrumentation, not policy inputs.
"""
import json
from dataclasses import replace
from pathlib import Path
from hle.organization_demo import (world, ACTORS, ALICE, BOB, CARA, DARA, BOX,
    train, move, propose, agree, perform, org, send)
from hle.language_demo import acquire, finish, deliver, enact
from hle.language_records import Speech, Act, Produce, Learn, Interpret, LanguageCommand
from hle.socion_records import ReceiveCommand
from hle.contracts import Kind, WorkStatus
from hle.world_records import ENERGY, TIME

MEMBERS = ACTORS[:3]


def snapshot(w):
    return {a.key: (w._wallets[a].energy, w._wallets[a].time) for a in ACTORS}


def delta(before, after):
    return {a: before[a][0] - after[a][0] for a in before}


class Meter:
    def __init__(self, w):
        self.w = w
        self.rows = []

    def call(self, label, fn):
        w = self.w
        start = len(w._journal)
        before = snapshot(w)
        result = fn()
        after = snapshot(w)
        observed = {a.key: [0, 0] for a in ACTORS}
        for tx in w._journal[start:]:
            for work in tx.works:
                for d in work.charged:
                    index = 0 if d.unit == ENERGY else 1 if d.unit == TIME else None
                    if index is not None:
                        observed[work.owner.key][index] += d.amount
        differences = {a: [before[a][0]-after[a][0], before[a][1]-after[a][1]] for a in before}
        assert differences == observed, (label, differences, observed)
        self.rows.append({'label': label, 'first_event': start, 'event_count': len(w._journal)-start,
            'debits': differences, 'active': {a.key:w.processing_state(a).active for a in ACTORS}})
        return result


def prepared(types=('lse', 'iee', 'lsi', 'eii'), organization=True):
    w = world(types=types)
    m = Meter(w)
    for a in MEMBERS:
        acc = m.call('setup:acquire:'+a.key, lambda: acquire(w,a,(BOX,),a.key+':concept'))
        m.call('setup:learn:'+a.key, lambda: finish(w,a,Learn('kept',acc),a.key+':learn'))
    for i,peer in enumerate((BOB,CARA)):
        m.call('setup:train:'+peer.key,lambda:train(w,ALICE,peer,'example:'+str(i)))
        m.call('setup:return:'+peer.key,lambda:move(w,peer,ALICE,'return:'+str(i)))
    acc = m.call('setup:dara:access',lambda:acquire(w,DARA,(BOX,),'dara:access'))
    definition = m.call('setup:dara:definition',lambda:deliver(w,BOB,w.lexeme(BOB,'kept').ref,DARA,'dara:definition'))
    m.call('setup:dara:learn',lambda:finish(w,DARA,Learn('kept',acc,definition),'dara:learn'))
    identity = None
    if organization:
        p = m.call('setup:proposal',lambda:propose(w,ALICE,'initial'))
        identity = m.call('setup:agreement',lambda:agree(w,ALICE,p,'initial:agreement'))
    return w,m,identity


def emit(w, sender, record, recipient, key):
    w.execute(w.send_language(sender, record, recipient, key))
    tx = w._journal[-1]
    observations = [o for o in tx.observations if o.observer==recipient and o.source.kind==Kind.MESSAGE]
    if not observations:
        raise RuntimeError('funded message not delivered')
    return observations[0].ref


def read(w, actor, obs, key):
    for n in range(10000):
        w.execute(ReceiveCommand(f'{key}:{n}',key,actor,obs))
        if (actor,obs) in w._completed_reception:
            return w._receptions[(actor,key)]
        if min(w._wallets[actor].energy,w._wallets[actor].time)==0:
            raise RuntimeError('insufficient reading resources')
    raise RuntimeError('reading did not finish')


def speech(w, sender, target, mode='request', actions=True):
    return Speech(mode, (w.word(sender,'kept',(BOX,target)),),
        (Act('transfer',BOX,sender),) if actions else (Act('inspect',BOX),))


def ask(w, m, target, key, response):
    """One supplied solicitation. No owner lookup participates in the choice."""
    before = snapshot(w)
    utt=m.call(key+':produce',lambda:finish(w,DARA,Produce(speech(w,DARA,target)),key+':produce').result)
    element=w.processing_state(DARA).active
    active=w.processing_state(target).active
    obs=m.call(key+':send',lambda:emit(w,DARA,utt,target,key+':send'))
    outcome='ignored'
    interpretation=None
    receipt=None
    reply=False
    if response!='ignore':
        receipt=m.call(key+':read',lambda:read(w,target,obs,key+':read'))
        acc=m.call(key+':acquire',lambda:acquire(w,target,(BOX,),key+':access'))
        result=m.call(key+':interpret',lambda:finish(w,target,Interpret(obs,acc),key+':interpret').result)
        interpretation=w.language_record(target,result).status
        # A reply is a paid neutral explanation. Emotion/hostility is not encoded.
        reply_utt=m.call(key+':reply_produce',lambda:finish(w,target,
            Produce(speech(w,target,target,'explain',False)),key+':reply_produce').result)
        reply_obs=m.call(key+':reply_send',lambda:emit(w,target,reply_utt,DARA,key+':reply_send'))
        m.call(key+':reply_read',lambda:read(w,DARA,reply_obs,key+':reply_read'))
        reply=True
        if response=='yield':
            outcome=m.call(key+':enact',lambda:enact(w,target,result))
        else:
            outcome='declined_after_reply'
    return {'target':target.key,'response':response,'element':element,'receiver_start':active,
        'read_units':None if receipt is None else receipt.plan.required,
        'landing':None if receipt is None else receipt.landing_position,
        'interpretation':interpretation,'outcome':outcome,'reply_delivered':reply,
        'payoff':int(reply)+int(outcome=='fulfilled'),'spent':delta(before,snapshot(w))}


def owner(w):
    return w.truth.current_fact(BOX,'owned_by',w.config.context).object.key


def write_json(path, obj):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n')
