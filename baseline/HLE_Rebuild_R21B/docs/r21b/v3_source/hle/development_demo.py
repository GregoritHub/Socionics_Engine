"""R13 reproducible fixtures and fresh-controller operations, not R14 autonomy.

The harness offers tasks and training; acquired programs determine selection.
Every participant calculation uses owned records and delivered observations.
"""
from dataclasses import replace
from .contracts import ActionRequest, ClaimStatus, Kind, Moment, Proposition, Ref, TimeScope, WorkStatus
from .cards import card
from .content_records import ContentCommand, MeaningCommand, WIRE, DONE
from .developmental import DevelopmentalWorld, pack
from .memory_records import MemoryCommand, WriteDraft, BindDraft, ContextDraft, RecallQuery
from .metabolism_records import ProcessingPolicy, Profile, MetabolicCommand, TheorizeDraft, ApplyDraft, EmbodyDraft
from .socion_records import AgentPolicy, ReceiveCommand
from .world_records import WorldConfig, Wallet, Entity, Ownership, Attempt, MessageDraft, SEND, INSPECT, TRANSFER
from .model_a import ego

LEARNER,HELPER,PARTNER,SECOND=(Ref(Kind.ENTITY,k,1) for k in ('learner','helper','partner','second_partner'))
ACTORS=(LEARNER,HELPER,PARTNER,SECOND)
ROOM=Ref(Kind.CONTEXT,'finite_crossing_task',1)
SEARCH_CUE=card('arcana:19').ref
BOUNDARY_CUE=card('arcana:20').ref
MEANING_CUE=card('arcana:21').ref
SCOPE=TimeScope(Moment(0,0),None)
TRAINING={'kind':'training','cases':[{'offered':['train_a','train_b'],'accepts':['train_b']},
    {'offered':['train_c','train_d','train_e'],'accepts':['train_c','train_e']}]}


def task_panel():
    before=[dict(kind='task',key=f'before_{i}',offered=[f'before_{i}_{j}' for j in range(3)],accepts=[f'before_{i}_1'],recipient=PARTNER.key) for i in range(2)]
    after=[]
    for width in (3,4,5):
        for accepted in range(width):
            key=f'held_{width}_{accepted}'
            after.append(dict(kind='task',key=key,offered=[f'{key}_{j}' for j in range(width)],accepts=[f'{key}_{accepted}'],recipient=PARTNER.key if accepted%2 else SECOND.key))
    return before,after


def world(tasks=(),tim='sli',energy=10000,items=(),owners=None):
    refs=tuple(dict.fromkeys(tuple(Ref(Kind.ENTITY,k,1) for t in tasks for k in t['offered'])+tuple(items)))
    cfg=WorldConfig(ROOM,tuple(Entity(a,a.key,'actor') for a in ACTORS)+tuple(Entity(i,i.key,'object') for i in refs),ACTORS,
        tuple(Ownership(i,(owners or {}).get(i,LEARNER)) for i in refs),tuple(Wallet(a,energy,energy) for a in ACTORS),(),tuple((a,b) for a in ACTORS for b in ACTORS if a!=b))
    return DevelopmentalWorld(cfg,(Profile(LEARNER,tim,ego(tim)[0]),Profile(HELPER,'iee','ne'),Profile(PARTNER,'lsi','ti'),Profile(SECOND,'ese','fe')),
        ProcessingPolicy(),tuple(AgentPolicy(a) for a in ACTORS))


def finish(w,cmd):
    """Issue explicit resumption commands; a caller can stop after any one."""
    for _ in range(10000):
        c=replace(cmd,command_id=cmd.command_id+':'+str(len(w._journal)))
        event=w.execute(c)
        if event.outcome in DONE or not min(w._wallets[cmd.actor].energy,w._wallets[cmd.actor].time): return event
    raise RuntimeError('declared fixture work limit exceeded')


def process(w,actor,key,op,sources=(),access=None,chunk=64):
    event=finish(w,ContentCommand(key,key,actor,op,tuple(sources),access,chunk))
    return w.development_job(actor,key).result


def store(w,actor,key,body,basis=(),links=(),context=None,chunk=64,attitude=ClaimStatus.ENDORSED):
    old=w.memory_head(actor,key)
    basis=tuple(dict.fromkeys(tuple(basis)+tuple(links)+(() if old is None else (old.ref,))))
    if not basis: basis=(w.select_input(actor)[0].observations[0].ref,)
    p=Proposition(actor,WIRE,pack(body),context or ROOM,TimeScope(w.now,None))
    draft=WriteDraft(key,(p,),tuple(links),attitude,None if old is None else old.ref,'retained finite content from cited input')
    cmd=MemoryCommand('store:'+key+':'+str(len(w._journal)),'store:'+key+':'+str(len(w._journal)),actor,draft,basis,chunk)
    event=finish(w,cmd)
    return w.memory_head(actor,key).ref if event.outcome==WorkStatus.COMPLETED else None


def bind(w,actor,key,cue,target,context=None,chunk=64):
    old=w.binding_head(actor,key)
    basis=(target,)+(() if old is None else (old.ref,))
    d=BindDraft(key,cue,context or ROOM,target,SCOPE,None if old is None else old.ref)
    ident='bind:'+key+':'+str(len(w._journal))
    finish(w,MemoryCommand(ident,ident,actor,d,basis,chunk))
    return w.binding_head(actor,key).ref


def recall(w,actor,key,cues,context=None,relation=WIRE,chunk=64):
    query=RecallQuery(tuple(cues),context or ROOM,w.now,relation=relation)
    finish(w,MemoryCommand(key,key,actor,query,work_limit=chunk))
    return w.memory_job(actor,key).result


def send(w,actor,ref,recipient,key,receive=True):
    body=w.content(actor,ref)
    p=Proposition(actor,WIRE,pack(body),ROOM,TimeScope(w.now,None))
    event=w.execute(Attempt(key,key,ActionRequest(actor,SEND,(recipient,),(ref,)),MessageDraft((p,))))
    if event.outcome!=WorkStatus.COMPLETED: return None
    observation=next(o.ref for o in w._journal[-1].observations if o.observer==recipient)
    if receive: finish(w,ReceiveCommand(key+':receive',key+':receive',recipient,observation))
    return observation


def train(w,families=('search','boundary')):
    training=store(w,HELPER,'training',TRAINING)
    retained={}; inference={}
    for family in ('search','boundary'):
        demo=process(w,HELPER,'demo:'+family,'demonstrate_'+family,(training,))
        obs=send(w,HELPER,demo,LEARNER,'teach:'+family)
        output=process(w,LEARNER,'infer:'+family,'infer_'+family,(obs,))
        inference[family]=output
        if family in families:
            m=store(w,LEARNER,'capacity:'+family,w.content(LEARNER,output),(output,))
            bind(w,LEARNER,'capacity:'+family,SEARCH_CUE if family=='search' else BOUNDARY_CUE,m)
            retained[family]=m
    return retained,inference


def trial(w,t,key=None,context=None,enact=True):
    key=key or t['key']; recipient=next(a for a in ACTORS if a.key==t['recipient'])
    request=store(w,recipient,'request:'+key,t)
    obs=send(w,recipient,request,LEARNER,key+':request')
    search=recall(w,LEARNER,key+':recall_search',(SEARCH_CUE,),context)
    options=process(w,LEARNER,key+':search','search',(obs,),search)
    boundary=recall(w,LEARNER,key+':recall_boundary',(BOUNDARY_CUE,),context)
    related=process(w,LEARNER,key+':relate','relate',(obs,options),boundary)
    plan_ref=process(w,LEARNER,key+':prepare','prepare',(obs,related))
    plan=w.content(LEARNER,plan_ref); completed=False
    if enact and plan['item'] is not None:
        item=Ref(Kind.ENTITY,plan['item'],1)
        e=w.execute(Attempt(key+':inspect',key+':inspect',ActionRequest(LEARNER,INSPECT,(item,),(plan_ref,))))
        observed=next(o for o in w._journal[-1].observations if o.observer==LEARNER)
        if e.outcome==WorkStatus.COMPLETED and any(p.subject==item and p.relation=='owned_by' and p.object==LEARNER for p in observed.content):
            e=w.execute(Attempt(key+':return',key+':return',ActionRequest(LEARNER,TRANSFER,(item,recipient),(plan_ref,observed.ref))))
            completed=e.outcome==WorkStatus.COMPLETED
    # Evaluator only; never fed back into the operations above.
    return {'task':t['key'],'chosen':plan['item'],'accepted_return':completed and plan['item'] in t['accepts'],
        'search_access':search.key,'boundary_access':boundary.key,'options':w.content(LEARNER,options)['items'],
        'admissible':w.content(LEARNER,related)['items'],'plan':plan_ref.key}


def crossing(condition='both_retained',tim='sli'):
    families={'no_instruction':None,'help_only':(),'search_only':('search',),'boundary_only':('boundary',),
              'both_retained':('search','boundary'),'both_without_return':('search','boundary')}[condition]
    before,after=task_panel(); w=world(before+after,tim)
    pre=[trial(w,t) for t in before]
    retained,inferences=({}, {}) if families is None else train(w,families)
    start=len(w._journal)
    rows=[trial(w,t,enact=condition!='both_without_return') for t in after]
    units={a.key:sum(x.completed_units for tx in w._journal[start:] for x in tx.works if x.owner==a) for a in ACTORS}
    return w,{'condition':condition,'tim':tim,'before':pre,'after':rows,'successes':sum(r['accepted_return'] for r in rows),
        'helper_units_after_training':units[HELPER.key],'post_training_units':units,'retained':{k:v.key for k,v in retained.items()}}


def embodied_experience(w,item,key,unavailable=False,actor=LEARNER):
    # Harness change is explicit and separated from the actor's delivered memory.
    genesis=w.select_input(actor)[0].observations[0]
    p=next(p for p in genesis.content if p.subject==item and p.relation=='owned_by')
    d=WriteDraft('episode:'+key,(p,),(),ClaimStatus.ENDORSED,None,'initial observed ownership')
    finish(w,MemoryCommand(key+':episode',key+':episode',actor,d,(genesis.ref,)))
    m=w.memory_head(actor,'episode:'+key)
    bind(w,actor,'episode:'+key,SEARCH_CUE,m.ref)
    if unavailable:
        e=w.execute(Attempt(key+':external',key+':external',ActionRequest(actor,TRANSFER,(item,HELPER if actor!=HELPER else LEARNER),())))
        if e.outcome!=WorkStatus.COMPLETED: raise RuntimeError('fixture change failed')
    access=recall(w,actor,key+':ownership',(SEARCH_CUE,),relation='owned_by')
    finish(w,MetabolicCommand(key+':theory',key+':theory',actor,TheorizeDraft(access,item,PARTNER)))
    account=w.processing_job(actor,key+':theory').result
    finish(w,MetabolicCommand(key+':apply',key+':apply',actor,ApplyDraft(account)))
    app=w.processing_job(actor,key+':apply').result
    finish(w,MetabolicCommand(key+':embody',key+':embody',actor,EmbodyDraft(app,'experience:'+key)))
    return w.memory_head(actor,'experience:'+key).ref,app


def publish_meaning(w,experience,application,key,scene='home',context=None,chunk=64,actor=LEARNER,cue=MEANING_CUE):
    context=context or ROOM
    access=recall(w,actor,key+':meaning_access',(cue,),context,'meaning.scene',chunk)
    previous=w.contextual_meaning(actor,access)
    cmd=MeaningCommand(key+':learn',key+':learn',actor,cue,context,scene,experience,application,access,
        'meaning:'+scene,None if previous is None else previous.ref,chunk)
    finish(w,cmd); job=w.development_job(actor,key+':learn')
    if job.outcome!=WorkStatus.COMPLETED: return None
    d=job.candidate
    basis=tuple(dict.fromkeys((job.result,experience)+d.links+(() if previous is None else (previous.ref,))))
    finish(w,MemoryCommand(key+':meaning_write',key+':meaning_write',actor,d,basis,chunk))
    m=w.memory_head(actor,'meaning:'+scene)
    bind(w,actor,'meaning:'+scene,cue,m.ref,context,chunk)
    return m.ref


def meaning_action(w,actor,access,item,recipient,key):
    """Explicit bounded controller; no history label or evaluator supplied."""
    meaning=w.contextual_meaning(actor,access)
    check=meaning is None or meaning.check
    operation=INSPECT if check else TRANSFER
    basis=() if meaning is None else (meaning.ref,)
    return Attempt(key,key,ActionRequest(actor,operation,(item,) if check else (item,recipient),basis))


def meaning_history(unavailable=(True,True,True,False,False,False)):
    items=tuple(Ref(Kind.ENTITY,'experience-item:'+str(i),1) for i in range(len(unavailable)+1))
    w=world(items=items,tim='iee'); rows=[]
    for i,flag in enumerate(unavailable):
        exp,app=embodied_experience(w,items[i],str(i),flag)
        m=publish_meaning(w,exp,app,'meaning:'+str(i))
        access=recall(w,LEARNER,'use:'+str(i),(MEANING_CUE,),relation='meaning.scene')
        value=w.contextual_meaning(LEARNER,access)
        action=meaning_action(w,LEARNER,access,items[-1],PARTNER,'action:'+str(i))
        rows.append({'encounter':i,'sample':flag,'check':value.check,'revision':m.revision,'selected_action':action.action.operation.key,
                     'samples':[v for v,_ in value.samples]})
    return w,rows


def run_demo():
    w,result=crossing()
    r=DevelopmentalWorld.restore(w.checkpoint())
    mw,meanings=meaning_history()
    return {'milestone':'R13','crossing':result,'exact_restore':r.checkpoint()==w.checkpoint(),'meaning_revisions':meanings,
        'generated_demands':'R14 pending','full_individuation':'unassessed','shell_clearance':'unassessed'}
