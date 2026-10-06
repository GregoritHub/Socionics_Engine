"""Supplied R20 opportunities; paid participant operations choose and enact rules."""
from dataclasses import replace
from .closure import ClosureWorld
from .closure_records import *
from .contracts import ActionRequest, ClaimStatus, Kind, Proposition, TimeScope, WorkStatus, Observation, MemoryRevision
from .memory_records import MemoryCommand, WriteDraft
from .composition_records import CompositionCommand, FoldDraft, Part, UnfoldDraft
from .world_records import Attempt, TRANSFER
from .language_records import Learn, Produce, Interpret, Speech, Act
from .language_demo import acquire, finish, deliver, enact
from .organization_records import Formulate, ReviewTerms, Ratify, Perform, Leave, Attend, Dispute
from .organization_demo import org, send
from .socion_records import ReceiveCommand
from .clearance_demo import prepared, panel, borrow, own_return, replenish
from .individuation_demo import make_offer, run_order
from .conversion_records import ConversionTransaction
from .concept_demo import fund_command

def key(w,s):return 'r20:'+s+':'+str(len(w._journal))

def job(w,a,operation,inputs=(),label='',limit=256,search_limit=64):
    k=key(w,operation)
    event=fund_command(w,ClosureCommand(k,k,a,operation,inputs,label,limit,search_limit))
    j=w._closure_jobs[a,k]
    if event.outcome!=WorkStatus.COMPLETED:raise ValueError('closure work unfinished: '+event.reason)
    return j.result

def compose(w,a,payload,label):
    k=key(w,label)
    e=fund_command(w,CompositionCommand(k,k,a,payload,256))
    if e.outcome!=WorkStatus.COMPLETED:raise ValueError('composition unfinished')
    return w.composition_job(a,k).result

def write(w,a,label,content,basis=(),expected=None):
    k=key(w,label)
    origins=[]
    for r in basis:
        if type(w._records[r]) in (Observation,MemoryRevision):origins.append(r)
        else:
            event=w._records[w._origins[r]]
            origins.extend(o.ref for o in w._journal[event.when.tick].observations if o.observer==a)
    basis=tuple(dict.fromkeys(origins))
    e=fund_command(w,MemoryCommand(k,k,a,WriteDraft(label,content,(),ClaimStatus.ENDORSED,expected,'retain exact shared procedure references'),basis,256))
    if e.outcome!=WorkStatus.COMPLETED:raise ValueError('retention unfinished')
    return w.memory_head(a,label).ref

def native(w):
    a,b,c=w.config.actors
    f=make_offer(w,key(w,'native-order'),'si',held=True,all_traps=True)
    order=run_order(w,f)
    item=w.clearance_monitor.original_item
    borrow(w,item,b);event=own_return(w,item)
    use=next(t.use for t in reversed(w._journal) if type(t) is ConversionTransaction and t.use is not None and t.use.item==item)
    props=tuple(Proposition(a,'r20.capacity',r,w.config.context,TimeScope(w.now,None)) for r in w._signature(a))
    leaf=write(w,a,'native-reference',props,tuple(o.ref for o in w._journal[-1].observations if o.observer==a))
    root=compose(w,a,FoldDraft('r20-native',(Part('retained individual procedures',leaf,w.config.context),)),'native-fold')
    access=compose(w,a,UnfoldDraft(root,w.config.context,w.now),'native-unfold')
    binding=job(w,a,'bind',(access,order.outcome,use.ref,event.ref))
    return binding,item

def move(w,actor,recipient,item):
    if actor==recipient:return
    k=key(w,'transfer')
    e=fund_command(w,Attempt(k,k,ActionRequest(actor,TRANSFER,(item,recipient),())))
    if e.outcome!=WorkStatus.COMPLETED:raise ValueError('physical move failed')

def training(w,item,steps=('inspect','inspect','inspect','transfer')):
    actors=w.config.actors;a=actors[0]
    # Environment relocates property only through its actual owner's paid action.
    owner=w._facts[item,'owned_by',w.config.context].object
    move(w,owner,a,item)
    access=acquire(w,a,(item,),key(w,'learn-access'))
    definition=finish(w,a,Learn('held',access),key(w,'learn')).result
    repair=[]
    for peer in actors[1:]:
        own=acquire(w,peer,(item,),key(w,'peer-access'))
        speech=Speech('explain',(w.word(a,'held',(item,a)),),(Act('inspect',item),Act('transfer',item,peer)))
        utterance=finish(w,a,Produce(speech),key(w,'explain')).result
        obs=deliver(w,a,utterance,peer,key(w,'explanation'))
        before=finish(w,peer,Interpret(obs,own),key(w,'before-teaching')).result
        teach=deliver(w,a,definition,peer,key(w,'definition'))
        finish(w,peer,Learn('held',own,teach),key(w,'peer-learn'))
        after=finish(w,peer,Interpret(obs,own),key(w,'after-teaching')).result
        repair.append((w._records[before].status,w._records[after].status))
    for performer in actors:
        for recipient in actors:
            if performer==recipient:continue
            owner=w._facts[item,'owned_by',w.config.context].object
            move(w,owner,performer,item)
            teach_actions(w,performer,recipient,item,steps)
    owner=w._facts[item,'owned_by',w.config.context].object
    move(w,owner,a,item)
    return repair

def teach_actions(w,performer,recipient,item,steps):
    teacher=recipient
    access=acquire(w,performer,(item,),key(w,'practice-access'))
    s=Speech('explain',(w.word(teacher,'held',(item,performer)),),tuple(Act(x,item,recipient if x=='transfer' else None) for x in steps))
    u=finish(w,teacher,Produce(s),key(w,'practice-explain')).result
    obs=deliver(w,teacher,u,performer,key(w,'practice-tell'))
    r=finish(w,performer,Interpret(obs,access),key(w,'practice-interpret')).result
    if enact(w,performer,r)!='fulfilled':raise ValueError('explained procedure was not enacted')
    return r

def negotiate(w,actor,item,state=None):
    access=acquire(w,actor,(item,),key(w,'proposal-access'))
    proposal=org(w,actor,Formulate(access,state),key(w,'formulate'))
    terms=w._records[proposal].terms
    if terms is None:raise ValueError('no participant-generated terms')
    reviews={}
    for member in terms.members:
        obs=proposal if member==actor else send(w,actor,proposal,member,key(w,'offer'))
        access=acquire(w,member,(item,),key(w,'review-access'))
        reviews[member]=org(w,member,ReviewTerms(obs,access),key(w,'review-terms'))
        if w._records[reviews[member]].status!='accepted':raise ValueError('terms refused')
    for member in terms.members:
        votes=tuple(send(w,other,reviews[other],member,key(w,'consent')) for other in terms.members if other!=member)
        st=org(w,member,Ratify(reviews[member],votes),key(w,'ratify'))
        if w._records[st].status!='active':raise ValueError('exact agreement failed')
    return terms.identity

def send_shared(w,a,ref,peer):
    k=key(w,'share');fund_command(w,w.send_closure(a,ref,peer,k))
    obs=next(o.ref for o in w._journal[-1].observations if o.observer==peer)
    k=key(w,'receive-shared');fund_command(w,ReceiveCommand(k,k,peer,obs,256))
    return obs

def compile_plan(w,a,demand,search,identity,operation):
    d=w._records[demand];b=w._records[d.binding]
    child=b.root if d.parent is None else w._records[d.parent].root
    marker=write(w,a,key(w,'operator'),(Proposition(a,'r20.operator',operation,w.config.context,TimeScope(w.now,None)),),(demand,search))
    root=compose(w,a,FoldDraft(key(w,'shared-root'),(Part('preserved lower organization',child,w.config.context),Part('new executable relation',marker,w.config.context))),'shared-fold')
    access=compose(w,a,UnfoldDraft(root,w.config.context,w.now),'shared-unfold')
    return job(w,a,'propose',(demand,search,access,w.organization_state(a,identity).ref))

def vote(w,plan_ref):
    plan=w._records[plan_ref];votes={};deliveries={}
    for member in plan.members:
        obs=plan_ref if member==plan.owner else send_shared(w,plan.owner,plan_ref,member)
        deliveries[member]=obs
        votes[member]=job(w,member,'review',(obs,))
        if member!=plan.owner:job(w,member,'learn',(obs,))
    return votes,deliveries

def activate(w,plan,votes):
    p=w._records[plan]
    observed=tuple(votes[m] if m==p.owner else send_shared(w,m,votes[m],p.owner) for m in p.members)
    return job(w,p.owner,'activate',(plan,)+observed)

def execute_duties(w,active):
    plan=w._records[w._records[active].plan];d=w._records[plan.demand]
    for obligation,member in plan.assignments:
        if obligation in w._closure_duties[d.ref]:continue
        access=acquire(w,member,(d.item,),key(w,'duty-access'))
        run=org(w,member,Perform(w.organization_state(member,plan.identity).ref,access),key(w,'duty-plan'))
        for _ in range(20):
            cmd=w.next_organization_action(member,run)
            if cmd is None:break
            fund_command(w,cmd)
        if w.organization_outcome(member,run)!='fulfilled':raise ValueError('duty not fulfilled')

def first_closure(w):
    a,b,c=w.config.actors
    binding,item=native(w)
    repair=training(w,item)
    demand=job(w,a,'open',(binding,))
    searched=job(w,a,'search',(demand,))
    identity=negotiate(w,a,item)
    plan=compile_plan(w,a,demand,searched,identity,'consent_cycle')
    votes,_=vote(w,plan);active=activate(w,plan,votes)
    execute_duties(w,active)
    claim=job(w,a,'settle',(active,))
    if w._records[claim].status!='established':raise ValueError('first closure failed')
    # Explicit sharing after settlement includes this exact historical claim.
    for member in (b,c):job(w,member,'learn',(send_shared(w,a,plan,member),))
    return {'binding':binding,'item':item,'demand':demand,'search':searched,'identity':identity,'plan':plan,'claim':claim,'teaching':repair}

def succession(w,first):
    a,b,c=w.config.actors;item=first['item'];identity=first['identity']
    demand=job(w,b,'renew',(first['plan'],))
    # Founder exits with outstanding duties; property is handed to successor
    # before the recorded departure. No founder performs the successor work.
    owner=w._facts[item,'owned_by',w.config.context].object
    move(w,owner,b,item)
    ex=org(w,a,Leave(w.organization_state(a,identity).ref,'founder leaves shared custody'),key(w,'founder-leave'))
    departure_index=len(w._journal)
    for peer in (b,c):
        obs=send(w,a,ex,peer,key(w,'departure-notice'))
        org(w,peer,Attend(w.organization_state(peer,identity).ref,obs),key(w,'attend-departure'))
    searched=job(w,b,'search',(demand,))
    negotiate(w,b,item,w.organization_state(b,identity).ref)
    costly=compile_plan(w,b,demand,searched,identity,'carry_obligations')
    refused,_=vote(w,costly)
    if all(w._records[v].approved for v in refused.values()):raise ValueError('burden control did not refuse')
    failed=next(v for v in refused.values() if not w._records[v].approved)
    actor=w._records[failed].owner
    dispute=org(w,actor,Dispute(failed),key(w,'burden-dispute'))
    for peer in (b,c):
        if peer==actor:continue
        notice=send(w,actor,dispute,peer,key(w,'dispute-tell'))
        org(w,peer,Attend(w.organization_state(peer,identity).ref,notice),key(w,'dispute-attend'))
    # Paid explanation and actual practice supply an alternative with less
    # redundant checking. No new terms are assigned by the environment.
    for _ in range(2):
        teach_actions(w,b,c,item,('inspect','transfer'))
        teach_actions(w,c,b,item,('inspect','transfer'))
    negotiate(w,b,item,w.organization_state(b,identity).ref)
    plan=compile_plan(w,b,demand,searched,identity,'carry_obligations')
    votes,_=vote(w,plan);active=activate(w,plan,votes)
    execute_duties(w,active)
    claim=job(w,b,'settle',(active,))
    return {'demand':demand,'search':searched,'costly':costly,'refused':tuple(refused.values()),
        'dispute':dispute,'plan':plan,'active':active,'claim':claim,'departure_index':departure_index}

def clone(w,stop=None):
    q=ClosureWorld(w.config,w.profiles,w.policy,w.agents,w.organization_policies,w.semantic_policy,
        w.workshop,w.autonomy,release=w.release,reviewers=w.reviewers,account_policy=w.account_policy,
        conversion_policy=w.conversion_policy,circuit_policy=w.circuit_policy,partners=w.circuit_partners)
    for tx in w._journal[1:stop]:
        q.execute(tx.command)
        if q._journal[-1]!=tx:raise ValueError('continuing prefix changed')
    return q

def run(w=None):
    w=clone(panel(prepared())) if w is None else w
    start=len(w._journal);first=first_closure(w);second=succession(w,first)
    return w,first,second,{'start':start,'events':len(w._journal),'first_depth':w._records[first['claim']].depth,
        'second_depth':w._records[second['claim']].depth,'report':w.closure_report(),
        'native_clearance':w.clearance_report()['status'],'teaching_repair':first['teaching'],
        'successor_members':[a.key for a in w._records[second['plan']].members]}

def main():
    import json
    _,_,_,summary=run()
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
