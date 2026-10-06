"""Supplied bounded opportunities; no recipe or route reaches the selector."""
from dataclasses import replace
from tests_c5.fixtures import *
from hle_unified.selection_execution import SelectionEngine
from hle_unified.selection_records import SelectionRequest,NAMES,FACES,loads
from hle_unified.self_content import encode

def training(e,key='skill'):
    event=perform(e,OperationRequest(key+'-practice',ALICE,'repair',ROOM,target=SAW2,tool=KIT,stock=STOCK,evidence=evidence(e,ALICE,SAW2)),limit=100000)
    # Explicit event observation plus paid processing precede acquired use.
    show(e,ALICE,event,key=key+'-event')
    perform(e,OperationRequest(key+'-acquire',ALICE,'acquire',ROOM,procedure=REPAIR,practice=event),limit=100000)
    for item in (KIT,STOCK):expose(e,ALICE,e.world.head(item.identity).ref)
    return event

def need(e,key,weights=(0,0,0,10),commit=False,scope='quantity',collective=False,actor=ALICE,target=SAW,context=ROOM):
    # `seed` performs native paid binding of an initial owned intention.
    return seed(e,key,encode(dict(kind='need',weights=weights,commit=commit,scope=scope,amount=4,collective=collective)),
        actor=actor,target=target,relation='c6.need',status=ClaimStatus.TENTATIVE,context=context)

def fixture(name,face,tim='iee',inactive=0,shared_history=False,generate=False):
    e=setup(tim,inactive=inactive,shared=shared_history,generate=generate,engine_type=SelectionEngine,
        actual='serviceable' if name=='Act' and face=='expenditure' else 'damaged')
    if name=='Act' and face=='accumulation':training(e)
    dev.supply8(e,'neutral')
    prepared=prepare(e,name,face,key='available')
    for obj in (SAW,KIT,STOCK,SUPPLY):expose(e,ALICE,e.world.head(obj.identity).ref)
    weights=tuple(10 if i==NAMES.index(name)%4 else 0 for i in range(4))
    demand=need(e,'owned-need',weights,face=='expenditure','condition' if name in ('Contemplate','Act','Integrate') else 'quantity',
        collective=name in ('Identify','Mobilize','Commune','Institutionalize','Share','Coordinate','Educate'))
    r=SelectionRequest('automatic',ALICE,ROOM,CUE5,SAW,demand,stock=SUPPLY,tool=KIT,repair_stock=STOCK,procedure=REPAIR,
        peer=BOB,group=prepared.group)
    return e,r

def finish_selection(e,r,quantum=1000000,restore_at=None):
    for i in range(10000):
        value=e.participate('opportunity-'+r.key+'-'+str(i),r,quantum)
        if i==restore_at:e=SelectionEngine.restore(e.checkpoint())
        if value is None:break
        if value['status']=='partial' and min(e.wallet(r.actor)[x] for x in ('energy','time'))==0:break
    else:raise AssertionError('bounded continuation did not stop')
    return e,attrs(e.world.resolve(address('c6.decision',r.actor,r.key))) if address('c6.decision',r.actor,r.key).identity in e.world._heads else None

def witness(name,face,tim='iee'):
    e,r=fixture(name,face,tim)
    e,d=finish_selection(e,r)
    if d['recipe']!=name.lower()+'-'+face+'-v1':raise AssertionError((name,face,d))
    if d['failure']:raise AssertionError(d)
    job=e.job_status(ALICE,r.key+':movement')
    if job['status']!='succeeded':raise AssertionError(job)
    native=e._movement_inputs[e._jobs[ALICE,r.key+':movement'].identity][0]
    later=downstream(e,native,name,face)
    return e,r,d,later

def transfer_fixture(local_cap=1,observe=True):
    from tests_c4.fixtures import comp
    other=ref('c6-held-out-context')
    e=setup(generate=False,engine_type=SelectionEngine)
    e.declare('context-anchor',(ObjectVersion(other,WRITER,'A separate allocation context',(Role.CONTEXT,)),));show(e,ALICE,other)
    source=model(e,'previous-model',cap=5)
    own=seed(e,'local-intent',encode(dict(kind='intention',cap=local_cap,consent=True)),context=other,relation='c3.data',status=ClaimStatus.TENTATIVE)
    if observe:
        event=perform(e,OperationRequest('local-stock',ALICE,'inspect',other,target=SUPPLY,evidence=evidence(e,ALICE,SUPPLY)),limit=100000)
        observation=receive(e,event,ALICE,'local-stock-result')
    else:observation=None
    dev.supply8(e,'local-opportunity',context=other)
    demand=need(e,'local-need',context=other)
    r=SelectionRequest('transfer',ALICE,other,CUE5,SAW,demand,stock=SUPPLY,peer=BOB)
    return e,r,source,observation

def transfer_witness(local_cap=1,observe=True):
    e,r,source,observation=transfer_fixture(local_cap,observe)
    e,d=finish_selection(e,r)
    output=e.job_status(ALICE,r.key+':movement')['binding']
    out=data(e,output)
    consumer=work(e,replace(req(e,'local-consumer','use-system-v1',(output,),stock=SUPPLY,demand=4),context=r.context))
    return e,r,d,out,data(e,consumer),source,observation
