"""R8 supplied dialogue goals; meanings acquired from paid retained structures."""
from .language import LanguageWorld
from .language_records import Act, Interpret, Intend, LanguageCommand, Learn, Produce, Speech
from .composition_demo import complete
from .composition_records import FoldDraft, Part, UnfoldDraft
from .contracts import ClaimStatus, WorkStatus
from .demo import ALICE, BOB, BOX, TOOL, ROOM, config, request
from .metabolism_records import ProcessingPolicy, Profile
from .socion_records import AgentPolicy, ReceiveCommand
from .world_records import Attempt, INSPECT, RETAIN, MemoryDraft


def world(energy=5000,time=5000,cfg=None):
    return LanguageWorld(cfg or config(energy,time),(Profile(ALICE,'lse'),Profile(BOB,'iee')),
        ProcessingPolicy(),(AgentPolicy(ALICE),AgentPolicy(BOB)))


def acquire(w,actor,items,key):
    parts=[]
    for n,item in enumerate(items):
        k=f'{key}:item:{n}'
        w.execute(Attempt(k+':inspect',k+':inspect',request(actor,INSPECT,(item,))))
        obs=w._journal[-1].observations[0]
        facts=tuple(p for p in obs.content if p.relation=='owned_by')
        w.execute(Attempt(k+':retain',k+':retain',request(actor,RETAIN,basis=(obs.ref,)),
            memory=MemoryDraft(k,facts,ClaimStatus.ENDORSED,'retain own inspection')))
        parts.append(Part(str(n),w.memory_head(actor,k).ref,w.config.context))
    root=complete(w,FoldDraft(key,tuple(parts)),key+':fold',actor).result
    return complete(w,UnfoldDraft(root,w.config.context,w.now),key+':access',actor).result


def finish(w,actor,payload,key,limit=64):
    for n in range(10000):
        w.execute(LanguageCommand(f'{key}:{n}',key,actor,payload,limit))
        job=w.language_job(actor,key)
        if job.outcome in (WorkStatus.COMPLETED,WorkStatus.FAILED) or not min(w._wallets[actor].energy,w._wallets[actor].time): return job
    raise RuntimeError('demo operation did not finish')


def deliver(w,actor,record,recipient,key):
    w.execute(w.send_language(actor,record,recipient,key))
    observations=[o for o in w._journal[-1].observations if o.observer==recipient and o.source.kind.value=='message']
    if not observations: return None
    obs=observations[0].ref
    for n in range(10000):
        w.execute(ReceiveCommand(f'{key}:receive:{n}',key+':receive',recipient,obs))
        if (recipient,obs) in w._completed_reception: return obs
        if not min(w._wallets[recipient].energy,w._wallets[recipient].time): return obs
    raise RuntimeError('demo reception did not finish')


def enact(w,actor,record):
    for _ in range(10000):
        cmd=w.next_language_action(actor,record)
        if cmd is None or not min(w._wallets[actor].energy,w._wallets[actor].time): break
        w.execute(cmd)
    return w.language_outcome(actor,record)


def run_language_demo():
    w=world()
    a=acquire(w,ALICE,(BOX,),'alice:train')
    b=acquire(w,BOB,(TOOL,),'bob:held-out')
    learned=finish(w,ALICE,Learn('kept',a),'learn').result
    teach=deliver(w,ALICE,learned,BOB,'teach')
    speech=Speech('explain',(w.word(ALICE,'kept',(TOOL,BOB)),),
        (Act('inspect',TOOL),Act('transfer',TOOL,ALICE)))
    utterance=finish(w,ALICE,Produce(speech),'produce').result
    obs=deliver(w,ALICE,utterance,BOB,'tell')
    failed=finish(w,BOB,Interpret(obs,b),'before:repair').result
    acquired=finish(w,BOB,Learn('kept',b,teach),'receiver:learn').result
    understood=finish(w,BOB,Interpret(obs,b),'after:repair').result
    outcome=enact(w,BOB,understood)
    return w,{'milestone':'R8','events':len(w._journal),
        'before_repair':w.language_record(BOB,failed).status,
        'after_repair':w.language_record(BOB,understood).status,'action_outcome':outcome,
        'actions':[x.operation for x in speech.actions],
        'receiver_definition':acquired.key,'held_out_item':TOOL.key,
        'scope':'acquired relation patterns and supplied finite speech/action grammar',
        'next':'R9: participant-generated organization'}
