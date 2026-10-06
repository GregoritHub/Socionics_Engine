"""R9 supplied opportunities; participant operations choose terms and responses."""
from dataclasses import replace
from .organization import OrganizationWorld, terms_id
from .organization_records import *
from .language_records import Act, Speech, Produce, Interpret, Learn
from .language_demo import acquire, finish, deliver, enact
from .contracts import Kind, Ref, WorkStatus
from .demo import ALICE, BOB, BOX, ROOM, request
from .metabolism_records import Profile, ProcessingPolicy
from .socion_records import AgentPolicy, ReceiveCommand
from .world_records import Entity, Ownership, Wallet, WorldConfig, Attempt, TRANSFER

CARA=Ref(Kind.ENTITY,'cara',1)
DARA=Ref(Kind.ENTITY,'dara',1)
ACTORS=(ALICE,BOB,CARA,DARA)


def world(energy=20000,time=20000,token='kept',policies=None,types=('lse','iee','lsi','eii')):
    cfg=WorldConfig(ROOM,tuple(Entity(a,a.key,'actor') for a in ACTORS)+(Entity(BOX,'Box','object'),),
        ACTORS,(Ownership(BOX,ALICE),),tuple(Wallet(a,energy,time) for a in ACTORS),(),
        tuple((a,b) for a in ACTORS for b in ACTORS if a!=b))
    w=OrganizationWorld(cfg,tuple(Profile(a,t) for a,t in zip(ACTORS,types)),ProcessingPolicy(),
        tuple(AgentPolicy(a) for a in ACTORS),policies)
    return w


def org(w,actor,payload,key,limit=64):
    for n in range(10000):
        w.execute(OrganizationCommand(f'{key}:{n}',key,actor,payload,limit))
        job=w.organization_job(actor,key)
        if job.outcome in (WorkStatus.COMPLETED,WorkStatus.FAILED) or not min(w._wallets[actor].energy,w._wallets[actor].time):
            return job.result
    raise RuntimeError('organization work did not finish')


def send(w,actor,record,recipient,key):
    w.execute(w.send_organization(actor,record,recipient,key))
    observations=[o for o in w._journal[-1].observations if o.observer==recipient and o.source.kind==Kind.MESSAGE]
    if not observations: return None
    obs=observations[0].ref
    for n in range(10000):
        w.execute(ReceiveCommand(f'{key}:receive:{n}',key+':receive',recipient,obs))
        if (recipient,obs) in w._completed_reception or not min(w._wallets[recipient].energy,w._wallets[recipient].time): return obs
    raise RuntimeError('organization reception did not finish')


def train(w,actor,recipient,key,steps=('transfer',),token='kept'):
    access=acquire(w,actor,(BOX,),key+':access')
    speech=Speech('request',(w.word(recipient,token,(BOX,actor)),),
        tuple(Act(s,BOX,recipient if s=='transfer' else None) for s in steps))
    utterance=finish(w,recipient,Produce(speech),key+':produce').result
    obs=deliver(w,recipient,utterance,actor,key+':tell')
    r=finish(w,actor,Interpret(obs,access),key+':interpret').result
    if enact(w,actor,r)!='fulfilled': raise RuntimeError('training did not fulfill')
    return r


def move(w,actor,recipient,key):
    w.execute(Attempt(key,key,request(actor,TRANSFER,(BOX,recipient))))


def prepared(token='kept',steps=('transfer',),policies=None):
    w=world(policies=policies)
    for a in ACTORS[:3]:
        access=acquire(w,a,(BOX,),a.key+':concept')
        finish(w,a,Learn(token,access),a.key+':learn')
    for i,peer in enumerate((BOB,CARA)):
        train(w,ALICE,peer,'example:'+str(i),steps,token)
        move(w,peer,ALICE,'return:'+str(i))
    return w


def propose(w,actor,key,state=None):
    access=acquire(w,actor,(BOX,),key+':evidence')
    return org(w,actor,Formulate(access,state),key+':formulate')


def agree(w,actor,proposal,key):
    t=w.organization_record(actor,proposal).terms
    reviews={}
    for member in t.members:
        received=proposal if member==actor else send(w,actor,proposal,member,key+':offer:'+member.key)
        access=acquire(w,member,(BOX,),key+':check:'+member.key)
        reviews[member]=org(w,member,ReviewTerms(received,access),key+':review:'+member.key)
    for member in t.members:
        votes=tuple(send(w,other,reviews[other],member,key+':vote:'+other.key+':'+member.key)
            for other in t.members if other!=member)
        state=org(w,member,Ratify(reviews[member],votes),key+':ratify:'+member.key)
        if w.organization_record(member,state).status!='active': raise RuntimeError('agreement did not form')
    return t.identity


def perform(w,actor,identity,key):
    access=acquire(w,actor,(BOX,),key+':access')
    r=org(w,actor,Perform(w.organization_state(actor,identity).ref,access),key+':plan')
    for _ in range(10000):
        cmd=w.next_organization_action(actor,r)
        if cmd is None or not min(w._wallets[actor].energy,w._wallets[actor].time): break
        w.execute(cmd)
    return r


def run_organization_demo():
    w=prepared(); p=propose(w,ALICE,'initial'); identity=agree(w,ALICE,p,'initial:agreement')
    checkpoints=[w.checkpoint()]
    recurring=[]
    for n,a in enumerate((ALICE,BOB,CARA)*2):
        r=perform(w,a,identity,'recurring:'+str(n)); recurring.append(w.organization_outcome(a,r))
    # A scheduled intervention invalidates an accepted retained claim. No update
    # to that claim is smuggled into local interpretation.
    access=acquire(w,ALICE,(BOX,),'dispute:access')
    run=org(w,ALICE,Perform(w.organization_state(ALICE,identity).ref,access),'dispute:plan')
    move(w,ALICE,BOB,'dispute:intervention')
    w.execute(w.next_organization_action(ALICE,run))
    dispute=org(w,ALICE,Dispute(run),'dispute:raise')
    for peer in (BOB,CARA):
        obs=send(w,ALICE,dispute,peer,'dispute:tell:'+peer.key)
        org(w,peer,Attend(w.organization_state(peer,identity).ref,obs),'dispute:attend:'+peer.key)
    checkpoints.append(w.checkpoint())
    unresolved=propose(w,BOB,'no:alternative',w.organization_state(BOB,identity).ref)
    for n in range(2):
        train(w,BOB,CARA,'alternative:'+str(n),('inspect','transfer'))
        move(w,CARA,BOB,'alternative:return:'+str(n))
    revised=propose(w,BOB,'revised',w.organization_state(BOB,identity).ref)
    agree(w,BOB,revised,'revised:agreement')
    for n,a in enumerate((BOB,CARA,ALICE)):
        perform(w,a,identity,'revised:use:'+str(n))
    checkpoints.append(w.checkpoint())
    # Newcomer must acquire the language independently before requesting a seat.
    access=acquire(w,DARA,(BOX,),'newcomer:access')
    definition=deliver(w,BOB,w.lexeme(BOB,'kept').ref,DARA,'newcomer:definition')
    finish(w,DARA,Learn('kept',access,definition),'newcomer:learn')
    offer=send(w,BOB,w.organization_state(BOB,identity).ref,DARA,'newcomer:offer')
    join=org(w,DARA,Join(offer,access),'newcomer:join')
    for peer in (ALICE,BOB,CARA):
        notice=send(w,DARA,join,peer,'join:tell:'+peer.key)
        org(w,peer,Attend(w.organization_state(peer,identity).ref,notice),'join:attend:'+peer.key)
    departure=org(w,ALICE,Leave(w.organization_state(ALICE,identity).ref,'founder chooses to leave'),'founder:leave')
    for peer in (BOB,CARA):
        obs=send(w,ALICE,departure,peer,'founder:tell:'+peer.key)
        org(w,peer,Attend(w.organization_state(peer,identity).ref,obs),'founder:attend:'+peer.key)
    successor=propose(w,BOB,'succession',w.organization_state(BOB,identity).ref)
    agree(w,BOB,successor,'succession:agreement')
    successor_runs=[]
    for n,a in enumerate((BOB,CARA,DARA,BOB,CARA,DARA)):
        r=perform(w,a,identity,'successor:use:'+str(n)); successor_runs.append(w.organization_outcome(a,r))
    checkpoints.append(w.checkpoint())
    for peer in (CARA,DARA):
        ex=org(w,peer,Leave(w.organization_state(peer,identity).ref,'end participation'),peer.key+':leave')
        obs=send(w,peer,ex,BOB,peer.key+':leave:tell')
        org(w,BOB,Attend(w.organization_state(BOB,identity).ref,obs),peer.key+':leave:attend')
    checkpoints.append(w.checkpoint())
    summary={'milestone':'R9','events':len(w._journal),'initial_members':[x.key for x in w._records[p].terms.members],
        'initial_steps':w._records[p].terms.steps,'recurring_outcomes':recurring,
        'disputed_outcome':w.organization_outcome(ALICE,run),'without_alternative':w._records[unresolved].status,
        'revised_steps':w._records[revised].terms.steps,'successor_members':[x.key for x in w._records[successor].terms.members],
        'successor_outcomes':successor_runs,'founder_state':w.organization_state(ALICE,identity).status,
        'remaining_member_state':w.organization_state(BOB,identity).status,
        'generations':[w._records[r].terms.generation for r in (p,revised,successor)],
        'scope':'supplied finite compositors; participant-selected experienced terms; local exact consent',
        'next':'R10: sustained evaluation and release'}
    return w,summary,checkpoints
