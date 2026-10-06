"""Pure R14 policy: accepts only a detached LocalView, never a world/evaluator.

Rules and motives are declared finite engineering choices. Goals instantiate
from observed consequences, not from the scheduler, type labels or success bits.
"""
from dataclasses import replace
import hashlib
from .contracts import (Ref,Kind,Proposition,TimeScope,Moment,ClaimStatus,ActionRequest,WorkStatus)
from .autonomy_records import (AutonomyState,MemoryPointer,ObservationPatch,LocalRequest,
    LocalDecision,DemandSketch,WorkshopCommand,WorkshopPacket,PACKET_REL,INTENT_REL,FACTS)
from .memory_records import MemoryCommand,WriteDraft,BindDraft,RecallQuery
from .socion_records import ReceiveCommand
from .socion_policy import object_cue
from .world_records import Attempt,MessageDraft,SEND

DONE=(WorkStatus.COMPLETED,WorkStatus.FAILED)
PRICES={'inspect':1,'use':3,'clean':2,'lend':2,'return':2,'send':1}


def key_for(item):return 'r14:facts:'+item.key+':'+str(item.revision)
def cue_for(item):return object_cue(item)
def unique(seq):return tuple(dict.fromkeys(seq))
def repeated(s):return sum(max(0,s.failed_targets.count(k)-1) for k in set(s.failed_targets))


def decode_packet(observation):
    from .codec import loads
    props=[p for p in observation.content if p.relation==PACKET_REL]
    if len(props)!=1 or type(props[0].object) is not str:return None
    try:
        packet=loads(props[0].object)
        return packet if type(packet) is WorkshopPacket else None
    except ValueError:return None


def decide(v,key):
    """One paid interpretation/selection result; no mutation or external calls."""
    s,p=v.state,v.policy;actor=s.owner
    s=replace(s,ref=replace(s.ref,revision=s.ref.revision+1))
    def issue(phase,command,kind,reason,**kw):
        return replace(s,phase=phase,pending=command,decision=LocalDecision(kind,reason,discrepancy_count=s.discrepancies,repeated_unsuccessful_attempts=repeated(s)),**kw)
    def memory(phase,payload,basis=(),kind='revision',**kw):
        return issue(phase,MemoryCommand(key,key,actor,payload,unique(basis),p.work_limit),kind,'paid relational memory operation',**kw)
    def archive():
        nonlocal s
        patch=s.patches[0];old=v.head
        if patch.key=='r14:motives' or patch.key.startswith('r14:packet:'):
            content=patch.content
        else:
            merged={} if old is None else {x.relation:x for x in old.content}
            changed=sum(1 for x in patch.content if x.relation in merged and merged[x.relation].object!=x.object)
            s=replace(s,discrepancies=s.discrepancies+changed)
            # Ignore older testimony for the same explicit relation/time.
            for x in patch.content:
                if x.relation not in merged or x.scope.start>=merged[x.relation].scope.start:merged[x.relation]=x
            content=tuple(merged[k] for k in sorted(merged))
        basis=(patch.observation,)+(() if old is None else (old.ref,))
        return memory('write',WriteDraft(patch.key,content,(),ClaimStatus.TENTATIVE if patch.sender else ClaimStatus.ENDORSED,
            None if old is None else old.ref,'owned delivered evidence; provenance retained, testimony remains fallible'),basis)
    def patches_from(o,sender,packet):
        if packet is not None:
            content=o.content
            if packet.kind=='lesson':
                content+=(Proposition(actor,'r14.skill',packet.topic,v.context,TimeScope(v.now,None)),)
            return (ObservationPatch('r14:packet:'+o.ref.key,actor,content,o.ref,sender),)
        groups={}
        for fact in o.content:
            if fact.relation in FACTS:groups.setdefault(fact.subject,[]).append(fact)
        return tuple(ObservationPatch(key_for(item),item,tuple(props),o.ref,sender) for item,props in sorted(groups.items(),key=lambda row:(row[0].key,row[0].revision)))

    if s.pending is not None:
        if v.pending_status is None:raise ValueError('selected work must execute before another decision')
        if v.pending_status not in DONE:
            return replace(s,pending=replace(s.pending,command_id=key),decision=LocalDecision('resume','continue exact partly funded operation'))
        phase=s.phase;previous_command=s.pending
        if v.pending_status==WorkStatus.FAILED and phase in ('write','bind','recall','receive'):
            return replace(s,pending=None,phase='blocked',decision=LocalDecision('unresolved','memory/reception operation failed; no forced completion'))
        s=replace(s,pending=None)
        if phase=='receive':
            # The detached view holds only this recipient's observation.
            if v.observation is None:raise ValueError('received observation absent')
            s=replace(s,patches=patches_from(v.observation,v.sender,v.packet),cursor=s.cursor+1,
                active_notice=None if v.packet is None else LocalRequest(v.observation.ref,v.sender,v.packet))
            if s.patches:return archive()
            return replace(s,phase='observe',active_notice=None,decision=LocalDecision('unresolved','received content is outside the declared grammar; consume once without treating it as a goal'))
        elif phase=='write':
            if v.result is None:raise ValueError('paid write produced no memory')
            patch=s.patches[0]
            return memory('bind',BindDraft(patch.key,cue_for(patch.item),v.context,v.result,TimeScope(Moment(0,0),None),v.binding),
                (v.result,)+(() if v.binding is None else (v.binding,)))
        elif phase=='bind':
            patch=s.patches[0]
            if v.head is None or v.result is None:raise ValueError('paid binding result missing')
            pointer=MemoryPointer(patch.key,patch.item,v.head.ref,v.result)
            catalog=tuple(c for c in s.catalog if c.key!=patch.key)+(pointer,)
            requests=s.requests
            if s.active_notice is not None and s.active_notice.observation==patch.observation:
                requests+=(replace(s.active_notice,memory=v.head.ref),)
            s=replace(s,catalog=catalog,requests=requests,patches=s.patches[1:],active_notice=None,
                initialized=s.initialized or patch.key=='r14:motives',dirty=True,phase='observe')
            # Next patch requires its own current head in a fresh view.
            return replace(s,decision=LocalDecision('revision','archived material; refresh the next owned context before further work'))
        elif phase=='recall':
            s=replace(s,last_access=v.result,dirty=False)
            return select(v, s, key)
        else:
            failed=v.pending_status==WorkStatus.FAILED
            target=(previous_command.operation+':'+previous_command.inputs[0].key) if type(previous_command) is WorkshopCommand else type(previous_command).__name__
            s=replace(s,phase='observe',dirty=True,failures=s.failures+failed,failed_targets=s.failed_targets+((target,) if failed else ()))

    if not s.initialized:
        if v.observation is None:raise ValueError('initial public observation required')
        facts=tuple(Proposition(actor,INTENT_REL,g,v.context,TimeScope(v.now,None)) for g in p.intentions)
        facts+=tuple(Proposition(actor,'r14.native_operation',g,v.context,TimeScope(v.now,None)) for g in p.primitives)
        # Empty intentions and repertoire are legitimate; retain explicit rest stance.
        if not facts:facts=(Proposition(actor,INTENT_REL,'no_standing_work',v.context,TimeScope(v.now,None)),)
        s=replace(s,patches=(ObservationPatch('r14:motives',actor,facts,v.observation.ref),))
        return archive()
    if s.patches:return archive()
    if v.observation is not None:
        if v.sender is not None:
            return issue('receive',ReceiveCommand(key,key,actor,v.observation.ref,p.work_limit),'interpret','paid reception before considering partner content')
        patches=patches_from(v.observation,None,None)
        s=replace(s,cursor=s.cursor+1,patches=patches)
        if patches:return archive()
        wake=s.decision is not None and s.decision.kind=='resource_limited'
        return replace(s,dirty=s.dirty or wake,decision=s.decision if not s.dirty else LocalDecision('observe','receipt without new relevant material'))
    if s.dirty:
        cues=unique(cue_for(c.item) for c in s.catalog)
        if not cues:return replace(s,phase='rest',dirty=False,decision=LocalDecision('rest','no retained work motive or observations'))
        return memory('recall',RecallQuery(cues,v.context,v.now,visit_limit=8192),kind='recall')
    return replace(s,phase='rest' if s.decision is None else s.phase,decision=s.decision or LocalDecision('rest','no relevant changed condition'))


def select(v,s,key):
    """Generate needs and choose an operation from remembered conditions.

    No state-machine phase dictates clean/return/use: they compete after each
    actual recall against the changed state, local constraints and repertoire.
    """
    p=v.policy;actor=s.owner
    if v.recall is None or v.recall.truncated or not v.access_valid:
        return replace(s,phase='blocked',decision=LocalDecision('unresolved','memory search incomplete; no empty-repertoire theorem'))
    memories=v.memories
    by_item={};material={};goals=[];goal_refs=[];skills=set();skill_sources=[]
    for m in memories:
        for prop in m.content:
            if prop.relation==INTENT_REL and prop.subject==actor:
                goals.append(prop.object);goal_refs.append(m.ref)
            elif prop.relation=='r14.native_operation' and prop.subject==actor:skills.add(prop.object)
            elif prop.relation=='r14.skill' and prop.object=='use':
                skills.add('use');skill_sources.append(m.ref)
            elif prop.relation in FACTS:
                by_item.setdefault(prop.subject,{})[prop.relation]=prop.object
                material[prop.subject]=m
    tools=sorted((i for i,f in by_item.items() if f.get('workshop_kind')=='tool'),key=lambda r:r.key)
    people=sorted((i for i,f in by_item.items() if f.get('role')=='actor' and i!=actor),key=lambda r:r.key)
    pieces=sorted((i for i,f in by_item.items() if f.get('workshop_kind')=='workpiece'),key=lambda r:r.key)
    requirements=[]
    def need(family,item,goal,cost,priority):
        m=material[item]
        requirements.append(DemandSketch(family,item,unique((m.ref,)+tuple(goal_refs)),m.observations,goal,cost,priority))
    for item in tools:
        f=by_item[item]
        if f.get('owned_by')==actor and f.get('condition')=='dirty' and 'care_for_used_tools' in goals:need('maintenance',item,'restore clean usable tool',2,0)
        if f.get('borrower')==actor and f.get('loan_active') is True and f.get('return_due') is True and 'honor_accepted_loans' in goals:
            need('return_commitment',item,'return clean entrusted tool to accepted lender',2,1)
    for item in pieces:
        if by_item[item].get('owned_by')==actor and by_item[item].get('condition')=='raw' and 'prepare_owned_workpieces' in goals:
            need('production',item,'make the owned raw workpiece ready',3,2)
    requirements=tuple(sorted(requirements,key=lambda d:(d.priority,d.item.key)))
    active_request=None
    def result(kind,reason,pending=None,**kw):
        if kind=='resource_limited' and active_request is not None:
            kw.setdefault('handled',tuple(r for r in s.handled if r!=active_request))
        minimum=min((d.units for d in requirements),default=0)
        decision=LocalDecision(kind,reason,requirements,len(requirements),s.discrepancies,
            max(0,minimum-min(v.energy,v.time)),repeated(s))
        return replace(s,phase='act' if pending is not None else kind,pending=pending,decision=decision,**kw)
    def fingerprint(item):
        # Meaningful observed facts only; no evaluator, global event count or outcome label.
        f=by_item.get(item,{})
        body=repr(tuple(sorted((k,repr(val)) for k,val in f.items())))
        return item.key+':'+hashlib.sha256(body.encode()).hexdigest()[:16]
    def send(packet,target,basis,kind='help',reason='seek an actual participant response',token=None):
        if min(v.energy,v.time)-p.reserve<1:return result('resource_limited','insufficient reserve for an actual message')
        from .codec import dumps
        prop=Proposition(actor,PACKET_REL,dumps(packet),v.context,TimeScope(v.now,None))
        cmd=Attempt(key,key,ActionRequest(actor,SEND,(target,),unique(basis)),MessageDraft((prop,)))
        return result(kind,reason,cmd,asked=s.asked+(() if token is None else (token,)))
    def work(op,inputs,basis=(),request=None):
        if op not in skills:return result('unresolved','no available primitive for '+op)
        units=PRICES[op]
        if min(v.energy,v.time)-p.reserve<units:return result('resource_limited','known action is presently unaffordable; demand is retained')
        signature=op+':'+':'.join(fingerprint(i) for i in inputs)
        if signature in s.attempts:
            # One finite observation retry can distinguish stale belief from a persistent obstacle.
            token='inspect:'+fingerprint(inputs[0])
            if op!='inspect' and 'inspect' in skills and token not in s.attempts:
                return work('inspect',(inputs[0],),basis)
            return result('search_exhausted','declared local primitive alternatives exhausted at this observed state')
        cmd=WorkshopCommand(key,key,actor,op,inputs,unique(basis),request,p.work_limit)
        return result('investigate' if op=='inspect' else 'action','selected '+op+' from present preconditions and retained requirements',cmd,
            attempts=s.attempts+(signature,))
    # Partner requests do not arrive as commands. Consider them using own remembered
    # authority, resources, needs and evidence; a refusal is a complete reply.
    for request in s.requests:
        if request.observation in s.handled:continue
        packet=request.packet;active_request=request.observation
        s=replace(s,handled=s.handled+(request.observation,))
        basis=(() if request.memory is None else (request.memory,))
        if packet.kind in ('refusal','lesson'):continue
        if packet.kind=='help':
            if packet.topic=='use' and skill_sources:
                source=next(m for m in memories if m.ref==skill_sources[0])
                explanation=tuple(x for x in source.content if x.relation=='r14.skill')
                return send(WorkshopPacket('lesson',packet.item,'use',explanation=explanation),request.sender,basis+(source.ref,),
                    'teach','share a technique from own retained consequence evidence')
            return send(WorkshopPacket('refusal',packet.item,packet.topic),request.sender,basis,'refuse','no retained example supporting the requested lesson')
        f=by_item.get(packet.item,{})
        reserved=any(d.family=='production' for d in requirements)
        if not p.may_lend or reserved or f.get('owned_by')!=actor or f.get('condition')!='clean' or f.get('loan_active'):
            return send(WorkshopPacket('refusal',packet.item,'loan'),request.sender,basis,'refuse','declared boundary, own need or unavailable clean property')
        return work('lend',(packet.item,request.sender),basis+(material[packet.item].ref,),request.observation)
    active_request=None
    if not requirements:return result('rest','standing conditions satisfied; no demand-driven departure is needed')
    d=requirements[0];f=by_item[d.item];basis=d.material
    if d.family=='maintenance':return work('clean',(d.item,),basis)
    if d.family=='return_commitment':
        if f.get('owned_by')!=actor:return result('unresolved','accepted return obligation persists although another actor now holds the tool')
        if f.get('condition')=='dirty':return work('clean',(d.item,),basis)
        return work('return',(d.item,),basis)
    owned=[t for t in tools if by_item[t].get('owned_by')==actor]
    clean=[t for t in owned if by_item[t].get('condition')=='clean']
    if clean:
        if 'use' in skills:return work('use',(d.item,clean[0]),basis+(material[clean[0]].ref,))
        for peer in people:
            token='help:use:'+d.item.key+':'+peer.key
            if p.may_ask and token not in s.asked:
                return send(WorkshopPacket('help',d.item,'use'),peer,basis,token=token)
        replied={r.sender for r in s.requests if r.packet.item==d.item and r.packet.topic=='use' and r.packet.kind in ('refusal','lesson')}
        if any('help:use:'+d.item.key+':'+peer.key in s.asked and peer not in replied for peer in people):
            return result('waiting','a requested technique has no interpreted reply yet')
        return result('unresolved','technique absent; no further unasked known peer in the declared repertoire')
    if owned:
        dirty=[t for t in owned if by_item[t].get('condition')=='dirty']
        if dirty:return work('clean',(dirty[0],),basis+(material[dirty[0]].ref,))
        return work('inspect',(owned[0],),basis)
    for tool in tools:
        f=by_item[tool];owner=f.get('owned_by')
        token='loan:'+fingerprint(tool)+':'+getattr(owner,'key','unknown')
        if isinstance(owner,Ref) and owner!=actor and f.get('condition')=='clean' and not f.get('loan_active') and p.may_ask and token not in s.asked:
            return send(WorkshopPacket('loan_request',tool,'loan',True),owner,basis+(material[tool].ref,),token=token)
    pending=[tool for tool in tools if any(token.startswith('loan:'+fingerprint(tool)+':') for token in s.asked)
        and not any(r.packet.kind=='refusal' and r.packet.topic=='loan' and r.packet.item==tool for r in s.requests)]
    if pending:return result('waiting','request sent; no permitted response yet changes the need')
    if any(r.packet.kind=='refusal' and r.packet.topic=='loan' for r in s.requests):
        return result('search_exhausted','known holders refused; no forced transfer or fabricated alternative')
    return result('search_exhausted','no known usable tool or available request in the finite local repertoire')
