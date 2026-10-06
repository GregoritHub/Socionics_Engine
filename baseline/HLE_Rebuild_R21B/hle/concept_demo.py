"""R14.5 bounded integration demonstrations and reproducible history contrasts."""
from dataclasses import replace
from .autonomy_demo import world as old_world,run,report
from .conceptual import ConceptualWorld
from .concept_records import ConceptCommand
from .autonomy_records import WorkshopCommand
from .contracts import Ref,Kind,ActionRequest
from .world_records import Entity,Ownership,Attempt,TRANSFER


def world(**kwargs):
    b=old_world(**kwargs)
    return ConceptualWorld(b.config,b.profiles,b.policy,b.agents,b.organization_policies,b.semantic_policy,b.workshop,b.autonomy)


def history_world(training=True,**kwargs):
    b=old_world(**kwargs);worker,partner=b.config.actors
    held=Ref(Kind.ENTITY,'held-out-piece',1)
    heldtool=Ref(Kind.ENTITY,'held-out-tool',1);spare=Ref(Kind.ENTITY,'partner-piece',1)
    extra=tuple(Entity(r,r.key,'object') for r in (held,heldtool,spare))
    config=replace(b.config,entities=b.config.entities+extra,ownership=b.config.ownership+tuple(Ownership(r,partner) for r in (held,heldtool,spare)))
    conditions=tuple((r,'ready' if not training and c=='raw' else c) for r,c in b.workshop.conditions)+((held,'raw'),(heldtool,'dirty'),(spare,'raw'))
    policies=(b.autonomy[0],replace(b.autonomy[1],intentions=()))
    return ConceptualWorld(config,b.profiles,b.policy,b.agents,workshop=replace(b.workshop,conditions=conditions),autonomy=policies)


def fund_command(w,command):
    while True:
        event=w.execute(command)
        if event.outcome.value in ('completed','failed'):return event
        if min(w._wallets[command.actor].energy,w._wallets[command.actor].time)==0:return event
        command=replace(command,command_id=command.command_id+':resume')


def introduce_held_out(w):
    actor,partner=w.config.actors;item=Ref(Kind.ENTITY,'held-out-piece',1)
    oldtool=next(r for r,c in w.workshop.conditions if r.key.endswith(':tool'))
    fund_command(w,WorkshopCommand('held:retire','held:retire',partner,'use',(Ref(Kind.ENTITY,'partner-piece',1),oldtool)))
    fund_command(w,WorkshopCommand('held:prepare','held:prepare',partner,'clean',(Ref(Kind.ENTITY,'held-out-tool',1),)))
    w.execute(Attempt('held:transfer','held:transfer',ActionRequest(partner,TRANSFER,(item,actor),())))
    fund_command(w,WorkshopCommand('held:inspect','held:inspect',actor,'inspect',(item,)))
    fund_command(w,WorkshopCommand('held:tool','held:tool',actor,'inspect',(Ref(Kind.ENTITY,'held-out-tool',1),)))
    fund_command(w,WorkshopCommand('held:old','held:old',actor,'inspect',(oldtool,)))


def history_case(training=True,**kwargs):
    w=history_world(training,**kwargs);first=run(w,2000);cut=len(w._journal)
    introduce_held_out(w);second=run(w,2000)
    actions=[t.command.operation for t in w._journal[cut:] if type(t.command) is WorkshopCommand and t.command.actor==w.config.actors[0] and t.command.inputs[0].key!='held-out-piece']
    return w,{'training':training,'first':first,'second':second,'cut':cut,'held_out_tool_actions':actions,
        'practiced':w.conceptual_state(w.config.actors[0]).practiced}


def main_demo():
    w=world();s=run(w);r=report(w,s)
    r.update(milestone='R14.5',exact_restore=ConceptualWorld.restore(w.checkpoint()).checkpoint()==w.checkpoint(),
        conceptual_relations=w.conceptual_state(w.config.actors[0]).relations,
        unresolved_tensions=w.conceptual_state(w.config.actors[0]).tensions,
        practiced=w.conceptual_state(w.config.actors[0]).practiced)
    return r


def classroom(mode='none',retained_trial=False,**kwargs):
    from .world_records import Wallet
    from .metabolism_records import Profile
    from .socion_records import AgentPolicy
    from .autonomy_records import AutonomyPolicy
    b=history_world(True,**kwargs);teacher,holder=b.config.actors;learner=Ref(Kind.ENTITY,'learner',1)
    actors=b.config.actors+(learner,)
    config=replace(b.config,entities=b.config.entities+(Entity(learner,'learner','actor'),),actors=actors,
        wallets=b.config.wallets+(Wallet(learner,20000,20000),),message_links=tuple((a,c) for a in actors for c in actors if a!=c))
    future=tuple(Ref(Kind.ENTITY,k,1) for k in ('future-tool','future-piece','retire-piece'))
    config=replace(config,entities=config.entities+tuple(Entity(r,r.key,'object') for r in future),ownership=config.ownership+tuple(Ownership(r,holder) for r in future))
    workshop=replace(b.workshop,conditions=b.workshop.conditions+tuple(zip(future,('dirty','raw','raw'))))
    w=ConceptualWorld(config,b.profiles+(Profile(learner,'iee','ne'),),b.policy,b.agents+(AgentPolicy(learner),),
        workshop=workshop,autonomy=b.autonomy+(AutonomyPolicy(learner),))
    run(w,2000)
    item=Ref(Kind.ENTITY,'held-out-tool',1)
    if mode in ('static','live','revoked'):
        op='teach' if mode=='static' else 'supply'
        fund_command(w,ConceptCommand('class:'+op,'class:'+op,teacher,op,recipient=learner,item=item if op=='supply' else None))
        run(w,2000)
    if mode=='revoked':fund_command(w,ConceptCommand('class:revoke','class:revoke',teacher,'revoke'))
    before=w.conceptual_state(learner)
    oldtool=next(r for r,c in w.workshop.conditions if r.key.endswith(':tool'))
    fund_command(w,WorkshopCommand('class:retire','class:retire',holder,'use',(Ref(Kind.ENTITY,'partner-piece',1),oldtool)))
    fund_command(w,WorkshopCommand('class:prepare','class:prepare',holder,'clean',(item,)))
    piece=Ref(Kind.ENTITY,'held-out-piece',1)
    w.execute(Attempt('class:transfer','class:transfer',ActionRequest(holder,TRANSFER,(piece,learner),())))
    for i,obj in enumerate((piece,item,oldtool)):
        fund_command(w,WorkshopCommand('class:inspect:'+str(i),'class:inspect:'+str(i),learner,'inspect',(obj,)))
    cut=len(w._journal);schedule=run(w,2000)
    actions=[t.command.operation for t in w._journal[cut:] if type(t.command) is WorkshopCommand and t.command.actor==learner]
    after=w.conceptual_state(learner)
    retained=[]
    if retained_trial:
        fund_command(w,ConceptCommand('final:remove-supplier','final:remove-supplier',teacher,'revoke'))
        fund_command(w,WorkshopCommand('final:retire','final:retire',holder,'use',(future[2],item)))
        fund_command(w,WorkshopCommand('final:prepare','final:prepare',holder,'clean',(future[0],)))
        w.execute(Attempt('final:transfer','final:transfer',ActionRequest(holder,TRANSFER,(future[1],learner),())))
        for i,obj in enumerate((future[1],future[0],item)):
            fund_command(w,WorkshopCommand('final:inspect:'+str(i),'final:inspect:'+str(i),learner,'inspect',(obj,)))
        final_cut=len(w._journal);final_schedule=run(w,2000)
        retained=[t.command.operation for t in w._journal[final_cut:] if type(t.command) is WorkshopCommand and t.command.actor==learner]
    return w,{'mode':mode,'retained_trial_actions':retained,'before_relations':() if before is None else before.relations,'before_practiced':before is not None and before.practiced,
        'actions':actions,'after_practiced':after is not None and after.practiced,'scheduling':schedule,'cut':cut}
