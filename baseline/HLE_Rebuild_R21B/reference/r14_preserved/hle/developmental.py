"""R13 main world: finite content and learned meaning in the R2–R11 journal.

Participant-facing operations accept delivered observations, exact own memory,
and completed paid recall. Truth is used by neither content nor meaning policy.
All indexes below are reconstructible views of the same typed command journal.
"""
from dataclasses import replace
import hashlib
import json

from . import content_operators as ops
from .contracts import (ActionRequest, Cause, ClaimStatus, CueBinding, Kind, MemoryRevision,
    Moment, Observation, Proposition, Ref, ResourceAmount, TimeScope, WorkRecord, WorkStatus, WorldEvent)
from .content_records import (CONTENT_RULE, CONTENT_WORK, MEANING_WORK, WIRE, MEANING_PROPOSAL, DONE,
    ContentCommand, MeaningCommand, CancelDevelopment, DevelopmentJob, DevelopmentTransaction, DevelopmentCheckpoint)
from .crux import Perspective, Polarity
from .development_contracts import RetainedCapacity, CapacityStatus
from .memory import in_scope
from .memory_records import MemoryCommand, WriteDraft, BindDraft, RecallQuery, RecallResult, RecallHit
from .metabolism_records import (RoutePlan, Application, Enactment, EmbodyDraft, MetabolicCommand, TheorizeDraft, ApplyDraft)
from .organization import OrganizationWorld
from .processing import _route_geometry, route_active
from .socion_records import Notice, ReceiveCommand
from .world import amounts, memory_key
from .world_records import Attempt, Credit, Tick, Wallet, Message, MessageDraft, ENERGY, TIME, SEND, RETAIN
from .meaning_learning import read_meaning, learn, experienced_unavailability


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)


def pack(body):
    text=canonical(ops.validate(body))
    return canonical({'body':json.loads(text),'sha256':hashlib.sha256(text.encode()).hexdigest()})


def unpack(text):
    def unique(items):
        result={}
        for k,v in items:
            if k in result: raise ValueError('duplicate content key')
            result[k]=v
        return result
    try:
        env=json.loads(text,object_pairs_hook=unique)
        if type(env) is not dict or set(env)!={'body','sha256'}: raise ValueError('invalid content envelope')
        body=ops.validate(env['body'])
        if hashlib.sha256(canonical(body).encode()).hexdigest()!=env['sha256']: raise ValueError('content identity mismatch')
        return body
    except (TypeError,KeyError,IndexError) as e:
        raise ValueError('malformed finite content') from e


def _wire(record):
    return len(record.content)==1 and record.content[0].relation==WIRE


def _cap(body): return body['kind'] in ('search_rule','boundary_rule')


class DevelopmentalWorld(OrganizationWorld):
    """The full main runtime with typed content/meaning jobs and exact replay."""
    def __init__(self,*args,**kwargs):
        self._development_jobs={}
        self._development_debits={}
        self._content_output_jobs={}
        self._memory_debits={}
        self._capacity_origins={}
        self._meaning_sample_uses=set()
        self._meaning_publications={}
        self._capacity_practice={}
        self._content_sends={}
        self._current_content_messages={}
        super().__init__(*args,**kwargs)
        for ref in (CONTENT_RULE,CONTENT_WORK,MEANING_WORK)+tuple(Ref(Kind.PROCEDURE,'r13.'+op,1) for op in ops.TARGET): self._records[ref]=ref
        for known in self._known.values(): known.update((CONTENT_RULE,CONTENT_WORK,MEANING_WORK))

    def development_job(self,actor,key):
        if actor not in self._actors: raise ValueError('unknown actor')
        job=self._development_jobs.get((actor,key))
        # Status is participant-visible; an unfunded candidate is not. The full
        # private candidate is retained only in the replay-checked journal.
        return replace(job,candidate='unpublished') if job is not None and job.outcome!=WorkStatus.COMPLETED else job

    def _current(self,actor,ref):
        m=self.read_revision(actor,ref)
        if self._memory_heads[actor].get(ref.key)!=m or m.claim_status in (ClaimStatus.RETRACTED,ClaimStatus.DISPUTED):
            raise ValueError('capacity or meaning withdrawn/superseded')
        return m

    def _dependency_check(self,actor,refs):
        pending=list(refs); visited=set()
        while pending:
            r=pending.pop()
            if r in visited: continue
            visited.add(r)
            if r.kind==Kind.MEMORY:
                m=self._current(actor,r)
                # Only executable declared dependencies recurse. Historical
                # experience links are not blanket live-version requirements.
                if r in self._capacity_origins: pending.extend(m.links)
            elif r.kind==Kind.BINDING:
                b=self.resolve_binding(actor,r)
                if self._binding_heads.get((actor,r.key))!=b or not in_scope(b.scope,self.now):
                    raise ValueError('contextual binding changed or expired')
            else: raise ValueError('unsupported current dependency')

    def content(self,actor,ref):
        """Inspect owned content. Executable use additionally needs paid recall."""
        record=self._owned(actor,ref,(Observation,MemoryRevision))
        if type(record) is Observation:
            if record.delivered_at>self.now: raise ValueError('undelivered observation')
            if type(self._records.get(record.source)) is Message and (actor,ref) not in self._completed_reception:
                raise ValueError('message must finish paid reception')
        if not _wire(record): raise ValueError('not a finite content record')
        body=unpack(record.content[0].object)
        if type(record) is MemoryRevision and _cap(body):
            self._current(actor,ref)
            if record.claim_status != ClaimStatus.ENDORSED or ref not in self._capacity_origins:
                raise ValueError('no currently endorsed acquired capacity')
            self._dependency_check(actor,record.links)
        return body

    def _recall_step(self,job,when):
        # A new paid contextual binding may apply a task-independent executable
        # rule in a new scene. Ordinary factual propositions retain R3 filtering.
        result=super()._recall_step(job,when)
        if job.selected_at is not None and job.frontier:
            visit=job.frontier[0]; m=self.read_revision(job.command.actor,visit.memory)
            if _wire(m) and _cap(unpack(m.content[0].object)):
                q=job.command.payload; p=m.content[0]
                bound=any(self.resolve_binding(job.command.actor,b).target==m.ref for b in job.bindings)
                if (bound and q.relation in (None,WIRE) and q.subject in (None,p.subject)
                        and in_scope(p.scope,q.at) and not any(h.memory==m.ref for h in result.hits)):
                    result=replace(result,hits=result.hits+(RecallHit(m.ref,(0,)),))
        return result

    def _content_recall(self,actor,access):
        r=self.recall_result(actor,access)
        if r.truncated: raise ValueError('truncated access cannot choose executable capacity')
        self._dependency_check(actor,r.bindings)
        values=[]; sources=[]; deps=list(r.bindings)
        for hit in r.hits:
            m=self.read_revision(actor,hit.memory)
            if not _wire(m) or 0 not in hit.proposition_indexes: continue
            if not in_scope(m.content[0].scope,self.now): raise ValueError('recalled content scope expired')
            body=self.content(actor,m.ref)
            values.append(body); sources.append(m.ref)
            if _cap(body): deps.extend((m.ref,)+m.links)
        return values,tuple(sources),tuple(dict.fromkeys(deps))

    def contextual_meaning(self,actor,access):
        """Return a personally learned association selected by actual paid recall."""
        r=self.recall_result(actor,access)
        if r.truncated: raise ValueError('truncated meaning access')
        self._dependency_check(actor,r.bindings)
        found=[]
        for hit in r.hits:
            m=self.read_revision(actor,hit.memory)
            if any(m.content[i].relation=='meaning.scene' for i in hit.proposition_indexes):
                self._current(actor,m.ref)
                if any(not in_scope(p.scope,self.now) for p in m.content): raise ValueError('meaning expired')
                found.append(read_meaning(m,actor))
        if len(found)>1: raise ValueError('ambiguous personally meaningful context')
        return found[0] if found else None

    def _prepare_content(self,cmd):
        if cmd.operator not in ops.TARGET: raise ValueError('unknown content operator')
        values=[]; sources=list(cmd.sources); deps=[]
        for ref in cmd.sources:
            body=self.content(cmd.actor,ref)
            # A paid inference receipt is evidence, not a retained executable rule.
            # Even current capacity addresses may not bypass contextual retrieval.
            if _cap(body) and cmd.operator!='hold':
                raise ValueError('executable rules require paid contextual recall; receipt/address bypass rejected')
            values.append(body)
        if cmd.access is not None:
            recalled,selected,dependencies=self._content_recall(cmd.actor,cmd.access)
            values.extend(recalled); sources.extend((cmd.access,)+selected); deps.extend(dependencies)
        if not values: raise ValueError('content input required')
        if cmd.operator in ('content_fi','content_fe'):
            for ref in cmd.sources:
                body=self.content(cmd.actor,ref)
                if body['kind'] in ('consent','acknowledgment'):
                    o=self._owned(cmd.actor,ref,(Observation,)); message=self._records.get(o.source)
                    claimed=body.get('partner',body.get('sender'))
                    if type(message) is not Message or message.sender.key!=claimed:
                        raise ValueError('specific consent/acknowledgment needs its actual sender')
                    key=(cmd.actor,message.sender,body['kind'],body['task'])
                    if self._current_content_messages.get(key)!=o.ref:
                        raise ValueError('consent/acknowledgment has been superseded by a received response')
            if cmd.access is not None and any(v['kind'] in ('consent','acknowledgment') for v in recalled):
                raise ValueError('consent needs authenticated received content, not arbitrary memory text')
        # Prevent wire injection masquerading as receiver acknowledgment.
        if cmd.operator=='content_fe':
            for ref in cmd.sources:
                b=self.content(cmd.actor,ref)
                if b['kind']=='acknowledgment':
                    o=self._owned(cmd.actor,ref,(Observation,))
                    message=self._records.get(o.source)
                    if type(message) is not Message or message.sender.key!=b['sender']:
                        raise ValueError('shared acknowledgment requires actual authenticated receiver response')
            if cmd.access is not None and any(v['kind']=='acknowledgment' for v in recalled):
                raise ValueError('shared acknowledgment needs the delivered response, not arbitrary memory text')
        out,extent=ops.transform(cmd.operator,values)
        return pack(out),max(1,extent),tuple(dict.fromkeys(sources)),tuple(dict.fromkeys(deps)),ops.TARGET[cmd.operator]

    def _prepare_meaning(self,cmd,at):
        if cmd.cue not in self._known[cmd.actor] or cmd.context not in self._known[cmd.actor]:
            raise ValueError('unknown cue or private context')
        access=self.recall_result(cmd.actor,cmd.access)
        if access.query.context!=cmd.context or cmd.cue not in access.query.cues:
            raise ValueError('meaning revision needs matching contextual retrieval')
        previous=self.contextual_meaning(cmd.actor,cmd.access)
        if previous and (previous.cue!=cmd.cue or previous.scene!=cmd.scene):
            raise ValueError('recalled personal association belongs to another scene/cue')
        if (None if previous is None else previous.ref)!=cmd.expected:
            raise ValueError('meaning predecessor must be the one actually recalled')
        exp=self.read_revision(cmd.actor,cmd.experience)
        app=self.processing_record(cmd.actor,cmd.application)
        if type(app) is not Application or not app.enactments or app.outcome not in DONE:
            raise ValueError('completed consequential application required')
        origin=self._records[self._origins[exp.ref]]
        source=self._journal[origin.when.tick].command  # One exact indexed origin, not history traversal.
        if type(source) is not MetabolicCommand or type(source.payload) is not EmbodyDraft or source.payload.application!=app.ref:
            raise ValueError('meaning sample must be the actual embodied application')
        first=self.processing_record(cmd.actor,app.enactments[0])
        if type(first) is not Enactment: raise ValueError('actual first action required')
        obs=self._owned(cmd.actor,first.observation,(Observation,))
        sample_key=(cmd.actor,cmd.context,cmd.scene,exp.ref)
        if sample_key in self._meaning_sample_uses: raise ValueError('experience already published in this scene')
        unavailable=experienced_unavailability(cmd.actor,first.request.inputs[0],first,obs)
        draft=learn(cmd.actor,cmd.cue,cmd.context,cmd.scene,previous,exp,unavailable,cmd.key,cmd.expected,at)
        refs=(cmd.access,exp.ref,app.ref,first.ref,obs.ref)+draft.links+(() if previous is None else (previous.ref,))
        deps=access.bindings+(() if previous is None else (previous.ref,))
        return draft,1+len(draft.links)+len(draft.content),tuple(dict.fromkeys(refs)),tuple(dict.fromkeys(deps)),'ti'

    def _development(self,cmd):
        prior=self._commands.get(cmd.command_id)
        if prior is not None:
            if prior.command!=cmd: raise ValueError('command ID reused with different input')
            return prior.event
        if cmd.actor not in self._actors: raise ValueError('unknown actor')
        state=self.processing_state(cmd.actor)
        old=self._development_jobs.get((cmd.actor,cmd.task_id))
        cancelling=type(cmd) is CancelDevelopment
        if old is None:
            if cancelling: raise ValueError('no unfinished development work to cancel')
            if state.busy is not None or cmd.actor in self._receiving or cmd.actor in self._semantic_owners or state.perspective!=Perspective.I:
                raise ValueError('content needs available personal processing')
        else:
            if old.outcome in DONE or state.busy!='r13:'+cmd.task_id: raise ValueError('terminal or unowned content continuation')
            if not cancelling and replace(cmd,command_id=old.command.command_id,work_limit=old.command.work_limit)!=old.command:
                raise ValueError('changed content continuation specification')
        when=Moment(len(self._journal),0); invalid=None
        if cancelling:
            candidate,extent,sources,deps,target=old.candidate,0,old.sources,old.dependencies,None
            invalid='cancelled: '+cmd.reason
        else:
            try:
                if old: self._dependency_check(cmd.actor,old.dependencies)
                candidate,extent,sources,deps,target=(self._prepare_content(cmd) if type(cmd) is ContentCommand else
                    self._prepare_meaning(cmd,old.started_at if old else when))
                if old and (candidate!=old.candidate or sources!=old.sources or deps!=old.dependencies):
                    invalid='content or contextual dependency changed while processing'
            except ValueError as e:
                if old is None: raise
                candidate,sources,deps=old.candidate,old.sources,old.dependencies
                invalid='input no longer usable: '+str(e)
        if old is None:
            tim=self._profiles[cmd.actor].tim if self.policy.typed_routing else 'ile'
            polarity=Polarity.ACCUMULATION if target in ('ne','ni','ti','si') else Polarity.EXPENDITURE
            path,seats,support,offset,units,price=_route_geometry(tim,state.active,target,polarity,self.policy.positional_prices)
            plan=RoutePlan(self._profiles[cmd.actor].tim,tim,path,seats,support,offset,units,extent*price)
            old=DevelopmentJob(cmd,when,plan,candidate,sources,deps)
        wallet=self._wallets[cmd.actor]
        spent=0 if invalid else min(old.plan.required-old.paid,cmd.work_limit,wallet.energy,wallet.time)
        paid=old.paid+spent
        status=(WorkStatus.FAILED if invalid else WorkStatus.COMPLETED if paid==old.plan.required else
                WorkStatus.PARTIAL if paid else WorkStatus.DEFERRED)
        event_ref=Ref(Kind.EVENT,f'event:{when.tick}',1); observations=()
        if status==WorkStatus.COMPLETED:
            if type(old.command) is ContentCommand: relation,text=WIRE,candidate
            else:
                from .codec import dumps
                relation,text=MEANING_PROPOSAL,dumps(candidate)
            prop=Proposition(cmd.actor,relation,text,self.config.context,TimeScope(when,None))
            observations=(self._observation(cmd.actor,event_ref,when,(prop,),'owned completed R13 operation','finite contract; no world-truth assertion'),)
        job=replace(old,paid=paid,outcome=status,result=observations[0].ref if observations else None)
        newstate=replace(state,ref=replace(state.ref,revision=state.ref.revision+1),active=route_active(old.plan,paid),busy=None if status in DONE else 'r13:'+cmd.task_id)
        op=CONTENT_WORK if type(old.command) is ContentCommand else MEANING_WORK
        work=WorkRecord(Ref(Kind.WORK,f'work:{when.tick}:development',1),cmd.actor,op,amounts(wallet),(),
            (ResourceAmount(ENERGY,spent),ResourceAmount(TIME,spent)),amounts(Wallet(cmd.actor,wallet.energy-spent,wallet.time-spent)),
            old.plan.required-old.paid,spent,status,invalid or 'paid routing and finite content work')
        causes=tuple(dict.fromkeys(Cause(self._origins[r],CONTENT_RULE) for r in (state.ref,)+old.sources))
        action='r13.cancel' if cancelling else 'r13.meaning' if type(cmd) is MeaningCommand else 'r13.'+cmd.operator
        event=WorldEvent(event_ref,when,(cmd.actor,),(),action,self.config.context,(),causes,(work.ref,),status,invalid or 'completed result only after funded work')
        self._commit(DevelopmentTransaction(cmd,event,(work,),observations,newstate,job))
        return event

    def _inputs(self,actor,payload):
        values,basis,size=super()._inputs(actor,payload)
        if type(payload) is TheorizeDraft:
            recall,memories,caps=values
            live_bindings=True
            try: self._dependency_check(actor,recall.bindings)
            except ValueError: live_bindings=False
            allowed={r for m in memories if self._memory_heads[actor].get(m.ref.key)==m
                     and m.claim_status not in (ClaimStatus.RETRACTED,ClaimStatus.DISPUTED) and live_bindings for r in m.capabilities}
            caps={r:c for r,c in caps.items() if r in allowed}
            values=(recall,memories,caps)
            # Historical propositions remain accessible; only executable access
            # loses its current authority. Ignorance is not declared a Shell.
            basis=tuple(r for r in basis if r.kind!=Kind.PROCEDURE or r in caps)
        elif type(payload) is ApplyDraft and values[0].guard is not None:
            account=values[0]
            memory=[self.read_revision(actor,r) for r in account.evidence if r.kind==Kind.MEMORY]
            owners=[m for m in memory if account.guard in m.capabilities]
            if not owners: raise ValueError('guard has no retained owner')
            for m in owners: self._current(actor,m.ref)
            self._dependency_check(actor,self.recall_result(actor,account.recall).bindings)
        return values,basis,size

    def _inference_job(self,actor,observation,body):
        o=self._owned(actor,observation,(Observation,))
        key=self._content_output_jobs.get(o.ref)
        if key is None: raise ValueError('retention needs this actor\'s completed inference')
        job=self._development_jobs[key]
        if type(job.command) is not ContentCommand or job.command.actor!=actor or job.command.operator!='infer_'+body['kind'].removesuffix('_rule'):
            raise ValueError('wrong inference origin')
        if job.result!=o.ref or self.content(actor,o.ref)!=body: raise ValueError('inference content mismatch')
        self._dependency_check(actor,job.dependencies)
        return job

    def _proposal(self,actor,observation):
        o=self._owned(actor,observation,(Observation,))
        key=self._content_output_jobs.get(o.ref)
        if key is None: raise ValueError('paid meaning proposal required')
        j=self._development_jobs[key]
        if type(j.command) is not MeaningCommand or j.command.actor!=actor or j.result!=o.ref:
            raise ValueError('wrong meaning proposal origin')
        self._dependency_check(actor,j.dependencies)
        return j

    def _validate_memory(self,cmd):
        old=super()._validate_memory(cmd)
        if type(cmd.payload) is WriteDraft:
            p=cmd.payload
            for prop in p.content:
                if prop.relation==WIRE:
                    if len(p.content)!=1: raise ValueError('one finite envelope per record')
                    body=unpack(prop.object)
                    if _cap(body):
                        if p.attitude!=ClaimStatus.ENDORSED:
                            previous=self.read_revision(cmd.actor,p.expected) if p.expected else None
                            if previous is None or previous.content!=p.content or previous.links!=p.links:
                                raise ValueError('withdrawal must preserve exact capacity content and lineage')
                        else:
                            candidates=[]
                            for r in cmd.based_on:
                                if r.kind==Kind.OBSERVATION:
                                    try: candidates.append(self._inference_job(cmd.actor,r,body))
                                    except ValueError: pass
                            if len(candidates)!=1: raise ValueError('endorsed capacity needs one own completed inference')
                            # Executable dependencies are declared exact links, not all historical sources.
                            self._dependency_check(cmd.actor,p.links)
                elif prop.relation.startswith('meaning.'):
                    if p.attitude in (ClaimStatus.RETRACTED,ClaimStatus.DISPUTED):
                        previous=self.read_revision(cmd.actor,p.expected) if p.expected else None
                        if previous is None or previous.content!=p.content or previous.links!=p.links:
                            raise ValueError('meaning withdrawal must preserve content and lineage')
                        break
                    proposals=[]
                    for r in cmd.based_on:
                        if r.kind==Kind.OBSERVATION:
                            try: proposals.append(self._proposal(cmd.actor,r))
                            except ValueError: pass
                    if len(proposals)!=1 or proposals[0].candidate!=p:
                        raise ValueError('meaning publication must match the completed paid proposal exactly')
                    c=proposals[0].command
                    if (c.actor,c.context,c.scene,c.experience) in self._meaning_sample_uses:
                        raise ValueError('sample already incorporated')
                    break
        return old

    def _validate_attempt(self,cmd):
        actor=cmd.action.actor
        for draft in (cmd.message,cmd.memory):
            if draft is None: continue
            for prop in draft.content:
                if prop.relation==MEANING_PROPOSAL or prop.relation.startswith('meaning.'):
                    raise ValueError('personal meaning uses paid contextual Write/Bind')
                if prop.relation==WIRE:
                    if len(draft.content)!=1: raise ValueError('one envelope per message')
                    body=unpack(prop.object)
                    if cmd.memory is not None and _cap(body): raise ValueError('capacity retention uses contextual Write, not bare RETAIN')
                    if cmd.message is not None:
                        # Sending arbitrary input dictionaries is not authentication.
                        if not any(self.content(actor,r)==body for r in cmd.action.based_on):
                            raise ValueError('send must cite the exact owned content')
                        if body['kind']=='acknowledgment' and body['sender']!=actor.key:
                            raise ValueError('acknowledgment sender mismatch')
        return super()._validate_attempt(cmd)

    def execute(self,cmd):
        if type(cmd) in (ContentCommand,MeaningCommand,CancelDevelopment): return self._development(cmd)
        # Preserve idempotent retries, including commands preceding pending work.
        if cmd.command_id in self._commands:
            tx=self._commands[cmd.command_id]
            if tx.command!=cmd: raise ValueError('command ID reused')
            return tx.event
        actor=cmd.action.actor if type(cmd) is Attempt else getattr(cmd,'actor',None)
        if actor in self._actors and type(cmd) not in (Credit,Tick,MemoryCommand):
            if (self.processing_state(actor).busy or '').startswith('r13:'):
                raise ValueError('finish/cancel R13 processing before another processing family or action')
        return super().execute(cmd)

    def _commit(self,tx):
        super()._commit(tx)
        if type(tx) is DevelopmentTransaction:
            state,job=tx.state,tx.job
            self._records[state.ref]=state; self._origins[state.ref]=tx.event.ref; self._known[state.owner].add(state.ref)
            self._processing_states[state.owner]=state
            self._processing_changes[-1]=(tx.event.ref,(state.owner,))
            key=(tx.command.actor,tx.command.task_id)
            self._development_jobs[key]=job
            self._development_debits.setdefault(key,[]).extend(w.ref for w in tx.works)
            if job.result is not None:
                self._content_output_jobs[job.result]=key
                for r in job.dependencies:
                    if r.kind==Kind.MEMORY and r in self._capacity_origins:
                        self._capacity_practice.setdefault(r,[]).append(tx.event.ref)
        if type(tx.command) is MemoryCommand:
            key=(tx.command.actor,tx.command.task_id)
            self._memory_debits.setdefault(key,[]).extend(w.ref for w in tx.works)
            for m in tx.memories:
                if _wire(m):
                    b=unpack(m.content[0].object)
                    if _cap(b) and m.claim_status==ClaimStatus.ENDORSED:
                        jobs=[self._content_output_jobs[r] for r in tx.command.based_on
                              if r in self._content_output_jobs and type(self._development_jobs[self._content_output_jobs[r]].command) is ContentCommand
                              and self._development_jobs[self._content_output_jobs[r]].command.operator=='infer_'+b['kind'].removesuffix('_rule')]
                        self._capacity_origins[m.ref]=(jobs[0],key)
                if any(p.relation=='meaning.scene' for p in m.content):
                    for r in tx.command.based_on:
                        jkey=self._content_output_jobs.get(r)
                        if jkey is not None and type(self._development_jobs[jkey].command) is MeaningCommand:
                            c=self._development_jobs[jkey].command
                            self._meaning_sample_uses.add((c.actor,c.context,c.scene,c.experience))
            for b in getattr(tx,'bindings',()):
                m=self._records[b.target]
                if any(p.relation=='meaning.scene' for p in m.content):
                    self._meaning_publications[(b.owner,b.context,b.cue)]=b.ref
        if type(tx.command) is ReceiveCommand:
            c=tx.command
            if (c.actor,c.observation) in self._completed_reception:
                o=self._records[c.observation]
                if _wire(o):
                    b=unpack(o.content[0].object); message=self._records[o.source]
                    if b['kind'] in ('consent','acknowledgment'):
                        self._current_content_messages[(c.actor,message.sender,b['kind'],b['task'])]=o.ref
        for observation in tx.observations:
            message=self._records.get(observation.source)
            if type(message) is Message and _wire(observation):
                body=unpack(observation.content[0].object)
                self._notice_by_observation[(observation.observer,observation.ref)]=Notice(
                    observation.ref,observation.source,message.sender,'content',observation.content[0],None,
                    self._profiles[message.sender].tim,ops.ASPECT[body['kind']])

    def retained_capacity(self,actor,access,kind):
        """Resolved R12 contract view, never a second authority/store of capacity."""
        values,selected,deps=self._content_recall(actor,access)
        pairs=[(r,b) for r,b in zip(selected,values) if b['kind']==kind]
        if len(pairs)!=1 or not _cap(pairs[0][1]): raise ValueError('one acquired capacity required')
        ref,body=pairs[0]; m=self.read_revision(actor,ref); recall=self.recall_result(actor,access)
        binding=next((self.resolve_binding(actor,b) for b in recall.bindings if self.resolve_binding(actor,b).target==ref),None)
        if binding is None: raise ValueError('capacity must have its contextual binding')
        inference,retention=self._capacity_origins[ref]
        work=tuple(self._development_debits[inference]+self._memory_debits[retention])
        op=Ref(Kind.PROCEDURE,'r13.'+('search' if kind=='search_rule' else 'relate'),1)
        return RetainedCapacity(ref,actor,ops.ASPECT[kind],op,binding.ref,binding.context,(ref,)+m.links,work,
            tuple(self._capacity_practice.get(ref,())),tuple(dict.fromkeys(m.links+(binding.ref,))),CapacityStatus.CURRENT,m.replaces)

    def checkpoint(self):
        from .codec import dumps
        return dumps(DevelopmentCheckpoint('hle-r13-v1',self.config,self.profiles,self.policy,self.agents,
            self.organization_policies,self.semantic_policy,tuple(self._journal)))

    @classmethod
    def restore(cls,text):
        from .codec import loads
        cp=loads(text)
        if type(cp) is not DevelopmentCheckpoint or cp.schema!='hle-r13-v1' or not cp.journal:
            raise ValueError('unsupported or empty R13 checkpoint')
        w=cls(cp.config,cp.profiles,cp.policy,cp.agents,cp.organization_policies,cp.semantic_policy)
        if w._journal[0]!=cp.journal[0]: raise ValueError('genesis mismatch')
        for tx in cp.journal[1:]:
            if tx.command is None or tx.command.command_id in w._commands: raise ValueError('missing or duplicate command')
            w.execute(tx.command)
            if w._journal[-1]!=tx: raise ValueError('R13 replay mismatch')
        return w
