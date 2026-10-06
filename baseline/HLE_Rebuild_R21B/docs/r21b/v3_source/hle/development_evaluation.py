"""Bounded R13 executable witnesses; no R14 autonomous-generation claim."""
from dataclasses import replace
import hashlib
from .development_demo import *
from .content_records import DevelopmentTransaction
from .world_records import Credit
from .contracts import ResourceAmount


def restart(w):
    return DevelopmentalWorld(w.config,w.profiles,w.policy,w.agents,w.organization_policies,w.semantic_policy)


def accounting(w):
    """Independent wallet fold from genesis, credits and exact work debits."""
    balance={a:[wlt.energy,wlt.time] for a in w.config.actors for wlt in w.config.wallets if wlt.actor==a}
    totals={a:0 for a in w.config.actors}; rows=0
    for tx in w._journal[1:]:
        for work in tx.works:
            before={r.unit:r.amount for r in work.before}
            charged={r.unit:r.amount for r in work.charged}
            after={r.unit:r.amount for r in work.after}
            from .world_records import ENERGY,TIME
            if [before[ENERGY],before[TIME]]!=balance[work.owner]: raise AssertionError('before wallet mismatch')
            debit=[charged.get(ENERGY,0),charged.get(TIME,0)]
            credited={r.unit:r.amount for r in work.credited}
            for i,resource in enumerate((ENERGY,TIME)): balance[work.owner][i]+=credited.get(resource,0)-debit[i]
            if [after[ENERGY],after[TIME]]!=balance[work.owner] or min(balance[work.owner])<0: raise AssertionError('debit mismatch')
            if type(tx.command) is not Credit and debit!=[work.completed_units,work.completed_units]: raise AssertionError('unreconciled work')
            totals[work.owner]+=debit[0]; rows+=1
    for a,b in balance.items():
        wallet=w._wallets[a]
        if b!=[wallet.energy,wallet.time]: raise AssertionError('final wallet mismatch')
    for key,job in w._development_jobs.items():
        paid=sum(w._records[r].completed_units for r in w._development_debits[key])
        if paid!=job.paid: raise AssertionError('processing paid progress mismatch')
    return {'work_records':rows,'units':{a.key:n for a,n in totals.items()},'wallets':{a.key:b for a,b in balance.items()},'passed':True}


def continuation_trace():
    """One trace containing partial memory/content/reception and revised meaning."""
    items=tuple(Ref(Kind.ENTITY,'trace:'+str(i),1) for i in range(3))
    w=world(items=items)
    body={'kind':'training','cases':[{'offered':['a','b'],'accepts':['b']}]}
    ref=store(w,HELPER,'partial:input',body,chunk=1)
    bind(w,HELPER,'partial:binding',SEARCH_CUE,ref,chunk=1)
    a=recall(w,HELPER,'partial:recall',(SEARCH_CUE,),chunk=1)
    out=process(w,HELPER,'partial:content','demonstrate_search',(ref,),chunk=1)
    obs=send(w,HELPER,out,LEARNER,'partial:send',receive=False)
    finish(w,ReceiveCommand('partial:receive','partial:receive',LEARNER,obs,work_limit=1))
    for i,flag in enumerate((True,False)):
        exp,app=embodied_experience(w,items[i],str(i),flag)
        publish_meaning(w,exp,app,'meaning:'+str(i),chunk=1)
    access=recall(w,LEARNER,'final:meaning',(MEANING_CUE,),relation='meaning.scene',chunk=1)
    w.execute(meaning_action(w,LEARNER,access,items[-1],PARTNER,'final:action'))
    return w


def all_prefix_continuation(w):
    """Restart each prefix, execute the original remaining commands, compare all state."""
    expected=w.checkpoint(); current=restart(w); counts={}; checked=0
    for n in range(1,len(w._journal)+1):
        if n>1: current.execute(w._journal[n-1].command)
        restored=DevelopmentalWorld.restore(current.checkpoint())
        for tx in w._journal[n:]: restored.execute(tx.command)
        if restored.checkpoint()!=expected: raise AssertionError('continuation mismatch at prefix '+str(n))
        checked+=1
        tx=w._journal[n-1]
        if tx.command is not None:
            key=type(tx.command).__name__+':'+tx.event.outcome.value
            counts[key]=counts.get(key,0)+1
    return {'prefixes':checked,'cutpoint_kinds':counts,'final_sha256':hashlib.sha256(expected.encode()).hexdigest(),'passed':True}


def distinct_personal_histories():
    left=tuple(Ref(Kind.ENTITY,'left:'+str(i),1) for i in range(4))
    right=tuple(Ref(Kind.ENTITY,'right:'+str(i),1) for i in range(4))
    w=world(items=left+right,owners={r:HELPER for r in right})
    for i in range(3):
        for actor,item,flag,label in ((LEARNER,left[i],True,'left'),(HELPER,right[i],False,'right')):
            exp,app=embodied_experience(w,item,label+':'+str(i),flag,actor)
            publish_meaning(w,exp,app,label+':'+str(i),actor=actor)
    # Restore before fresh contextual retrieval and policy selection. Neither
    # selected action nor retained addresses are copied from the first controller.
    r=DevelopmentalWorld.restore(w.checkpoint()); histories=[]
    for x in (w,r):
        commands=[]; rows=[]
        for actor,item in ((LEARNER,left[-1]),(HELPER,right[-1])):
            access=recall(x,actor,actor.key+':fresh',(MEANING_CUE,),relation='meaning.scene')
            value=x.contextual_meaning(actor,access)
            action=meaning_action(x,actor,access,item,PARTNER,actor.key+':decision')
            commands.append(action); rows.append({'actor':actor.key,'cue':MEANING_CUE.key,'check':value.check,'action':action.action.operation.key,'meaning_revision':value.ref.revision})
        for cmd in commands: x.execute(cmd)
        histories.append((commands,rows))
    if histories[0]!=histories[1] or w.checkpoint()!=r.checkpoint(): raise AssertionError('two-actor fresh-controller continuation mismatch')
    commands,rows=histories[0]
    return w,{'actors':rows,'actions_completed':all(w._commands[c.command_id].event.outcome==WorkStatus.COMPLETED for c in commands),'exact_continuation':True}
