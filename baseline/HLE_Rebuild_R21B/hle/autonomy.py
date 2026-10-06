"""R14: workshop consequences and participant-generated work, one R13 journal.

Physics may read world facts. The participant policy receives only LocalView.
The public scheduler supplies an actor opportunity, never a problem or solution.
"""
from dataclasses import replace
from .contracts import (Ref,Kind,Moment,TimeScope,Proposition,Change,Cause,Observation,
    MemoryRevision,WorkRecord,WorkStatus,WorldEvent,ResourceAmount,ClaimStatus)
from .crux import FormalMovement,Route,Perspective,Polarity
from .developmental import DevelopmentalWorld
from .development_contracts import (DevelopmentalDemand,Origin,ResourceEnvelope,Requirement)
from .autonomy_records import *
from .autonomy_policy import decide,decode_packet,key_for,PRICES,unique
from .memory_records import MemoryCommand,RecallQuery,DetailQuery
from .socion_records import Notice,ReceiveCommand
from .metabolism_records import RoutePlan,ProcessingState
from .processing import _route_geometry,route_active
from .world import amounts,fact_key
from .world_records import Wallet,ENERGY,TIME,Attempt,Message,Transaction,Tick,Credit

DONE=(WorkStatus.COMPLETED,WorkStatus.FAILED)


class AutonomousWorld(DevelopmentalWorld):
    def __init__(self,config,profiles,policy,agents,organization_policies=None,semantic_policy=None,
                 workshop=None,autonomy=()):
        self.workshop=workshop or WorkshopConfig()
        declared={e.ref:e for e in config.entities};owned={o.item for o in config.ownership}
        if any(i not in declared or declared[i].role!='object' or i not in owned for i,_ in self.workshop.conditions):
            raise ValueError('workshop conditions require declared owned objects')
        if len(autonomy)!=len(config.actors) or {p.owner for p in autonomy}!=set(config.actors):raise ValueError('one explicit autonomy policy per actor')
        self.autonomy=autonomy;self._autonomy_policies={p.owner:p for p in autonomy}
        self._autonomy_states={a:AutonomyState(Ref(Kind.CURSOR,'r14:'+a.key+':'+str(a.revision),1),a) for a in config.actors}
        self._workshop_jobs={};self._turn_jobs={};self._active_turn={};self._demands={};self._demand_records={};self._quiet_seen={}
        super().__init__(config,profiles,policy,agents,organization_policies,semantic_policy or SemanticPolicy())
        for r in (POLICY_RULE,DOMAIN_RULE,POLICY_WORK,DEMAND_PROTOCOL)+tuple(Ref(Kind.PROCEDURE,'r14.'+n,1) for n in PRIMITIVES):
            self._records[r]=r
            for known in self._known.values():known.add(r)
        for state in self._autonomy_states.values():self._register(state.ref,state,state.owner,self._journal[0].event.ref)

    def _register(self,ref,value,actor,event):
        self._records[ref]=value;self._origins[ref]=event;self._known[actor].add(ref)

    def autonomy_state(self,actor):
        if actor not in self._actors:raise ValueError('unknown actor')
        return self._autonomy_states[actor]

    def own_demands(self,actor):
        self.autonomy_state(actor)
        return tuple(v for (a,_),v in sorted(self._demands.items(),key=lambda kv:kv[0][1]) if a==actor)

    def _message_sender(self,observation):
        m=None if observation is None else self._records.get(observation.source)
        return m.sender if type(m) is Message else None

    def local_view(self,actor):
        """Owned projection: no Truth calls, foreign memory or global-history walk."""
        s=self.autonomy_state(actor);policy=self._autonomy_policies[actor]
        observation=self._inboxes[actor][s.cursor] if s.cursor<len(self._inboxes[actor]) else None
        sender=self._message_sender(observation)
        packet=decode_packet(observation) if sender is not None else None
        status=result=None;memories=();recall=None;access_valid=True
        if s.pending is not None:
            command=s.pending
            tx=self._commands.get(command.command_id)
            if tx is not None:
                status=self._pending_status(actor,command)
                if type(command) is MemoryCommand:
                    job=self.memory_job(actor,command.task_id)
                    result=job.result
                    if result is None and status==WorkStatus.COMPLETED:
                        from .memory_records import WriteDraft,BindDraft
                        if type(command.payload) is WriteDraft:result=self.memory_head(actor,command.payload.key).ref
                        elif type(command.payload) is BindDraft:result=self.binding_head(actor,command.payload.key).ref
                    if type(command.payload) in (RecallQuery,DetailQuery) and result is not None and status==WorkStatus.COMPLETED:
                        recall=self.recall_result(actor,result)
                        try:self._dependency_check(actor,recall.bindings)
                        except ValueError:access_valid=False
                        selected=[]
                        for hit in recall.hits:
                            m=self.read_revision(actor,hit.memory)
                            if access_valid and self._memory_heads[actor].get(m.ref.key)==m and m.claim_status not in (ClaimStatus.RETRACTED,ClaimStatus.DISPUTED):
                                selected.append(replace(m,content=tuple(m.content[i] for i in hit.proposition_indexes)))
                        memories=tuple(selected)
                elif type(command) is ReceiveCommand:
                    observation=self._owned(actor,command.observation,(Observation,));sender=self._message_sender(observation);packet=decode_packet(observation)
        if s.patches:k=s.patches[0].key
        elif not s.initialized:k='r14:motives'
        elif observation is not None and packet is not None:k='r14:packet:'+observation.ref.key
        elif observation is not None:
            items=sorted({p.subject for p in observation.content if p.relation in FACTS},key=lambda r:(r.key,r.revision))
            k=key_for(items[0]) if items else None
        else:k=None
        head=None if k is None else self.memory_head(actor,k)
        binding=None if k is None else self.binding_head(actor,k)
        origins=[]
        for m in memories:
            for r in m.observations:
                o=self._owned(actor,r,(Observation,))
                origins.append((r,self._origins[o.source]))
        w=self._wallets[actor]
        return LocalView(s,policy,self.now,self.config.context,observation,sender,packet,head,
            None if binding is None else binding.ref,status,result,memories,recall,w.energy,w.time,unique(origins),access_valid)

    def _freeze_view(self,v):
        selections=[]
        for memory in v.memories:
            original=self.read_revision(v.state.owner,memory.ref)
            indexes=tuple(i for i,p in enumerate(original.content) if p in memory.content)
            selections.append((memory.ref,indexes))
        return ViewSnapshot(v.state.ref,v.now,None if v.observation is None else v.observation.ref,
            None if v.head is None else v.head.ref,v.binding,v.pending_status,v.result,tuple(selections),
            None if v.recall is None else v.recall.ref,v.energy,v.time,v.access_valid)

    def _thaw_view(self,snapshot,actor):
        state=self._records.get(snapshot.state)
        if type(state) is not AutonomyState or state.owner!=actor:raise ValueError("snapshot must be this actor's exact policy state")
        observation=None if snapshot.observation is None else self._owned(actor,snapshot.observation,(Observation,))
        head=None if snapshot.head is None else self.read_revision(actor,snapshot.head)
        memories=[];origins=[]
        for ref,indexes in snapshot.memories:
            m=self.read_revision(actor,ref)
            if any(i<0 or i>=len(m.content) for i in indexes):raise ValueError('invalid retained snapshot projection')
            memories.append(replace(m,content=tuple(m.content[i] for i in indexes)))
            for obs in m.observations:
                o=self._owned(actor,obs,(Observation,));origins.append((obs,self._origins[o.source]))
        recall=None if snapshot.recall is None else self.recall_result(actor,snapshot.recall)
        sender=self._message_sender(observation)
        return LocalView(state,self._autonomy_policies[actor],snapshot.now,self.config.context,observation,sender,
            decode_packet(observation) if sender is not None else None,head,snapshot.binding,snapshot.pending_status,
            snapshot.result,tuple(memories),recall,snapshot.energy,snapshot.time,unique(origins),snapshot.access_valid)

    def _pending_status(self,actor,command):
        if command.command_id not in self._commands:return None
        if type(command) is WorkshopCommand:return self._workshop_jobs[(actor,command.task_id)].outcome
        if type(command) is MemoryCommand:return self.memory_job(actor,command.task_id).outcome
        if type(command) is ReceiveCommand:return self._receptions[(actor,command.task_id)].outcome
        return self._tasks[(actor,command.task_id)].outcome

    def autonomy_ready(self,actor):
        s=self.autonomy_state(actor)
        if min(self._wallets[actor].energy,self._wallets[actor].time)==0:return False
        return (actor in self._active_turn or s.pending is not None or not s.initialized or bool(s.patches)
                or s.cursor<len(self._inboxes[actor]) or s.dirty)

    def autonomy_step(self,actor):
        """Exactly one selected decision quantum or one selected operation."""
        s=self.autonomy_state(actor)
        if not self.autonomy_ready(actor):return None
        active=self._active_turn.get(actor)
        if active is not None:
            c=self._turn_jobs[(actor,active)].command
            return self.execute(replace(c,command_id='r14:resume:'+actor.key+':'+str(len(self._journal))))
        if s.pending is not None:
            status=self._pending_status(actor,s.pending)
            if status is None:return self.execute(s.pending)
            if status not in DONE:
                # Mechanical continuation of already-selected work is not a new
                # policy decision and must not contend with its processing lock.
                return self.execute(replace(s.pending,command_id='r14:work_resume:'+actor.key+':'+str(len(self._journal))))
        key='r14:turn:'+actor.key+':'+str(s.ref.revision)
        return self.execute(AutonomyTurn(key,key,actor,self._autonomy_policies[actor].work_limit))

    def _snapshot(self,item,when):
        return tuple(self._prop(item,rel,p.object,when) for rel in FACTS
            if (p:=self._facts.get((item,rel,self.config.context))) is not None)

    def _workshop(self,cmd):
        old=self._workshop_jobs.get((cmd.actor,cmd.task_id))
        if cmd.actor not in self._actors:raise ValueError('unknown actor')
        expected=2 if cmd.operation in ('use','lend') else 1
        if len(cmd.inputs)!=expected or any(i not in self._items for i in cmd.inputs[:1]):raise ValueError('invalid physical inputs')
        if cmd.operation=='use' and cmd.inputs[1] not in self._items:raise ValueError('tool required')
        if cmd.operation=='lend' and (cmd.inputs[1] not in self._actors or cmd.inputs[1]==cmd.actor):raise ValueError('distinct borrower required')
        if self.processing_state(cmd.actor).busy is not None:raise ValueError('personal processing reserved')
        for ref in cmd.based_on:self._owned(cmd.actor,ref,(Observation,MemoryRevision))
        if old is not None and (old.outcome in DONE or replace(cmd,command_id=old.command.command_id,work_limit=old.command.work_limit)!=old.command):raise ValueError('changed/terminal workshop continuation')
        if cmd.operation=='lend':
            if cmd.request is None:raise ValueError('accepted loan request required')
            o=self._owned(cmd.actor,cmd.request,(Observation,));message=self._records.get(o.source);packet=decode_packet(o)
            if (type(message) is not Message or message.sender!=cmd.inputs[1] or packet is None or packet.kind!='loan_request'
                or packet.item!=cmd.inputs[0] or not packet.accept_return or (cmd.actor,o.ref) not in self._completed_reception):
                raise ValueError('actual received borrower consent required')
        elif cmd.request is not None:raise ValueError('request only belongs to lending')
        now=Moment(len(self._journal),0);event_ref=Ref(Kind.EVENT,'event:'+str(now.tick),1)
        old=old or WorkshopJob(cmd,PRICES[cmd.operation]);wallet=self._wallets[cmd.actor]
        spent=min(old.required-old.paid,cmd.work_limit,wallet.energy,wallet.time);paid=old.paid+spent
        status=WorkStatus.COMPLETED if paid==old.required else WorkStatus.PARTIAL if paid else WorkStatus.DEFERRED
        changes=[];reason='paid finite workshop operation';seen={cmd.actor};affected=cmd.inputs[:1];extra=[]
        def fact(item,name):return self._facts.get((item,name,self.config.context))
        def val(item,name):
            f=fact(item,name);return None if f is None else f.object
        def set_fact(item,name,value):
            before=fact(item,name)
            if before is None or before.object!=value:changes.append(Change(before,self._prop(item,name,value,now)))
        if status==WorkStatus.COMPLETED:
            item=cmd.inputs[0];own=val(item,'owned_by')==cmd.actor
            if cmd.operation=='use':
                tool=cmd.inputs[1];affected=(item,tool)
                valid=(own and val(item,'workshop_kind')=='workpiece' and val(item,'condition')=='raw'
                    and val(tool,'workshop_kind')=='tool' and val(tool,'owned_by')==cmd.actor and val(tool,'condition')=='clean')
                if valid:
                    set_fact(item,'condition','ready')
                    if self.workshop.wear_after_use:set_fact(tool,'condition','dirty')
                    if val(tool,'loan_active') and self.workshop.due_after_use:set_fact(tool,'return_due',True)
                    extra.append(self._prop(cmd.actor,'r14.skill','use',now))
            elif cmd.operation=='clean':
                valid=own and val(item,'workshop_kind')=='tool' and val(item,'condition')=='dirty'
                if valid:set_fact(item,'condition','clean')
            elif cmd.operation=='lend':
                valid=own and val(item,'workshop_kind')=='tool' and val(item,'condition')=='clean' and val(item,'loan_active') is False
                if valid:
                    set_fact(item,'owned_by',cmd.inputs[1]);set_fact(item,'borrower',cmd.inputs[1]);set_fact(item,'loan_active',True);set_fact(item,'return_to',cmd.actor);set_fact(item,'return_due',False);seen.add(cmd.inputs[1])
            elif cmd.operation=='return':
                lender=val(item,'return_to')
                valid=own and val(item,'condition')=='clean' and val(item,'loan_active') is True and lender in self._actors and lender!=cmd.actor
                if valid:
                    set_fact(item,'owned_by',lender);set_fact(item,'loan_active',False);set_fact(item,'return_due',False);seen.add(lender)
            else:valid=True
            if not valid:status=WorkStatus.FAILED;reason='physical precondition failed after paid work; observe before revising the next choice'
        op=Ref(Kind.PROCEDURE,'r14.'+cmd.operation,1)
        work=WorkRecord(Ref(Kind.WORK,'work:'+str(now.tick)+':workshop',1),cmd.actor,op,amounts(wallet),(),
            (ResourceAmount(ENERGY,spent),ResourceAmount(TIME,spent)),amounts(Wallet(cmd.actor,wallet.energy-spent,wallet.time-spent)),
            old.required-old.paid,spent,status,reason)
        causes=unique(Cause(self._origins[r],DOMAIN_RULE) for r in cmd.based_on+(() if cmd.request is None else (cmd.request,)))
        event=WorldEvent(event_ref,now,(cmd.actor,),affected,op.key,self.config.context,tuple(changes),causes,(work.ref,),status,reason)
        # The world produces explicit observable effects. No participant reads
        # these fact tables directly, including when the event fails.
        observed=[]
        if status in DONE:
            for item in affected:
                snapshot={p.relation:p for p in self._snapshot(item,now)}
                for change in changes:
                    if change.after is not None and change.after.subject==item:snapshot[change.after.relation]=change.after
                observed.extend(snapshot.values())
            observed+=extra
        for item in affected:
            for witness in self._witnesses.get(item,()):
                if witness.mode=='full':seen.add(witness.observer)
        observations=tuple(self._observation(a,event_ref,now,tuple(observed) if status in DONE else (),
            'own workshop outcome or explicitly permitted consequence witness','exact local visible projection') for a in sorted(seen,key=lambda r:r.key))
        self._commit(AutonomousTransaction(cmd,event,(work,),observations,workshop_job=replace(old,paid=paid,outcome=status)))
        return event

    def _demand_changes(self,view,state,when,event_ref):
        if state.decision is None or state.pending is not None and state.phase in ('write','bind','recall','receive'):return ()
        # Only a completed selection over a paid RecallResult may generate/close.
        if view.recall is None:return ()
        decision=state.decision;origins=dict(view.origins);seen=set();out=[]
        for d in decision.demands:
            key=state.owner.key+':'+d.family+':'+d.item.key;seen.add(key)
            old=self._demands.get((state.owner,key));prior=None if old is None else old.specification.ref
            ref=Ref(Kind.DEMAND,'r14:'+key,1 if prior is None else prior.revision+1)
            sources=unique(origins[o] for o in d.observations if o in origins)
            if not sources:raise ValueError('generated demand lacks owned observed source')
            if old is not None:sources=unique(old.specification.origin_events+sources)
            status='unresolved' if decision.kind=='search_exhausted' else decision.kind if decision.kind in ('unresolved','waiting','refused','resource_limited') else 'active'
            spec=DevelopmentalDemand(ref,Origin.PARTICIPANT if d.family=='production' else Origin.CONSEQUENCE,sources,d.observations,
                d.family,DEMAND_PROTOCOL,(d.goal,),
                (FormalMovement(Route(Perspective.I,Perspective.IT),Polarity.EXPENDITURE),),view.context,(state.owner,),d.material,
                ('only owned or voluntarily accepted authority','preserve remembered lineage','no forced treatment of missing resources'),
                TimeScope(when,None),ResourceEnvelope(view.energy,view.time,None),(Requirement('primitive_work_units',d.units),),prior)
            out.append(DemandRecord(spec,state.owner,d.item,status,decision.reason))
        for (actor,key),old in tuple(self._demands.items()):
            if actor==state.owner and key not in seen and old.status!='resolved':
                if view.recall is None or view.recall.truncated or not view.access_valid:continue
                facts={p.relation:p.object for m in view.memories for p in m.content if p.subject==old.item}
                satisfied=(old.specification.family=='maintenance' and facts.get('condition')=='clean'
                    or old.specification.family=='return_commitment' and facts.get('loan_active') is False
                    or old.specification.family=='production' and facts.get('condition')=='ready')
                status='resolved' if satisfied else 'unresolved'
                spec=replace(old.specification,ref=replace(old.specification.ref,revision=old.specification.ref.revision+1),prior_demand=old.specification.ref)
                out.append(DemandRecord(spec,actor,old.item,status,'new permitted recall establishes satisfied condition; not a clearance verdict' if satisfied else 'missing/withdrawn retained intention or material is not evidence of satisfaction'))
        return tuple(out)

    def _selection_extent(self,view):
        return 1+sum(len(m.content) for m in view.memories)

    def _selection_sources(self,view):
        return ()

    def _select_participant(self,view,key):
        return decide(view,key)

    def _turn(self,cmd):
        if cmd.actor not in self._actors:raise ValueError('unknown actor')
        old=self._turn_jobs.get((cmd.actor,cmd.task_id));processing=self.processing_state(cmd.actor)
        if old is not None:
            if old.outcome in DONE or self._active_turn.get(cmd.actor)!=cmd.task_id:raise ValueError('terminal or unowned turn')
        else:
            if processing.busy is not None or cmd.actor in self._receiving or processing.perspective!=Perspective.I:raise ValueError('policy needs available personal processing')
            view=self.local_view(cmd.actor)
            if view.state.pending is not None and view.pending_status is None:raise ValueError('pending operation not executed')
            # Index projection is not a demand oracle; reasoning itself is paid.
            extent=self._selection_extent(view)
            tim=self._profiles[cmd.actor].tim if self.policy.typed_routing else 'ile'
            target='ne' if view.recall is not None else 'ti'
            path,seats,support,offset,units,price=_route_geometry(tim,processing.active,target,Polarity.ACCUMULATION,self.policy.positional_prices)
            plan=RoutePlan(self._profiles[cmd.actor].tim,tim,path,seats,support,offset,units,extent*price)
            old=AutonomyJob(cmd,self._freeze_view(view),plan)
        when=Moment(len(self._journal),0);event_ref=Ref(Kind.EVENT,'event:'+str(when.tick),1)
        wallet=self._wallets[cmd.actor];spent=min(old.plan.required-old.paid,cmd.work_limit,wallet.energy,wallet.time);paid=old.paid+spent
        outcome=WorkStatus.COMPLETED if paid==old.plan.required else WorkStatus.PARTIAL if paid else WorkStatus.DEFERRED
        view=replace(self._thaw_view(old.snapshot,cmd.actor),energy=wallet.energy-spent,time=wallet.time-spent)
        participant=self._select_participant(view,'r14:choice:'+cmd.actor.key+':'+str(self._autonomy_states[cmd.actor].ref.revision)) if outcome==WorkStatus.COMPLETED else None
        demands=() if participant is None else self._demand_changes(view,participant,when,event_ref)
        state=replace(processing,ref=replace(processing.ref,revision=processing.ref.revision+1),active=route_active(old.plan,paid),busy=None if outcome==WorkStatus.COMPLETED else 'r14:'+cmd.task_id)
        work=WorkRecord(Ref(Kind.WORK,'work:'+str(when.tick)+':policy',1),cmd.actor,POLICY_WORK,amounts(wallet),(),
            (ResourceAmount(ENERGY,spent),ResourceAmount(TIME,spent)),amounts(Wallet(cmd.actor,wallet.energy-spent,wallet.time-spent)),
            old.plan.required-old.paid,spent,outcome,'paid selection from frozen owned view; no result before completion')
        sources=(old.snapshot.state,)+(() if old.snapshot.result is None else (old.snapshot.result,))+self._selection_sources(view)
        causes=unique(Cause(self._origins[r],POLICY_RULE) for r in sources)
        event=WorldEvent(event_ref,when,(cmd.actor,),(),'r14.consider',self.config.context,(),causes,(work.ref,),outcome,work.reason)
        self._commit(AutonomousTransaction(cmd,event,(work,),decision_job=replace(old,paid=paid,outcome=outcome),participant=participant,processing=state,demands=demands))
        return event

    def execute(self,cmd):
        previous=self._commands.get(cmd.command_id)
        if previous is not None:
            if previous.command!=cmd:raise ValueError('command identity reused')
            return previous.event
        if type(cmd) is WorkshopCommand:return self._workshop(cmd)
        if type(cmd) is AutonomyTurn:return self._turn(cmd)
        actor=cmd.action.actor if type(cmd) is Attempt else getattr(cmd,'actor',None)
        if actor in self._active_turn and type(cmd) not in (Credit,Tick):raise ValueError('R14 decision owns personal processing')
        return super().execute(cmd)

    def _validate_attempt(self,cmd):
        old=super()._validate_attempt(cmd)
        if cmd.message is not None:
            props=[p for p in cmd.message.content if p.relation==PACKET_REL]
            if props:
                from .codec import loads
                if len(props)!=1 or props[0].subject!=cmd.action.actor:raise ValueError('packet sender must be acting participant')
                packet=loads(props[0].object)
                if type(packet) is not WorkshopPacket or packet.item not in self._known[cmd.action.actor]:raise ValueError('known typed packet required')
                if packet.kind=='lesson':
                    contents=tuple(p for r in cmd.action.based_on for p in self._owned(cmd.action.actor,r,(Observation,MemoryRevision)).content)
                    if any(p not in contents for p in packet.explanation) or not any(p.relation=='r14.skill' and p.object=='use' for p in packet.explanation):raise ValueError('lesson must cite own retained or observed use evidence')
        return old

    def _commit(self,tx):
        if tx.event.action=='genesis' and self.workshop.conditions:
            extra=[];owners={o.item:o.owner for o in self.config.ownership}
            for item,condition in self.workshop.conditions:
                extra.append(Change(None,self._prop(item,'condition',condition,tx.event.when)))
                extra.append(Change(None,self._prop(item,'workshop_kind','tool' if condition in ('clean','dirty') else 'workpiece',tx.event.when)))
                if condition in ('clean','dirty'):
                    extra.extend(Change(None,self._prop(item,k,value,tx.event.when)) for k,value in
                        (('loan_active',False),('return_due',False),('return_to',owners[item]),('borrower',owners[item])))
            props=tuple(c.after for c in extra)
            tx=replace(tx,event=replace(tx.event,changes=tx.event.changes+tuple(extra)),
                observations=tuple(replace(o,content=o.content+props) for o in tx.observations))
        super()._commit(tx)
        if type(tx) is AutonomousTransaction:
            if tx.workshop_job is not None:self._workshop_jobs[(tx.command.actor,tx.command.task_id)]=tx.workshop_job
            if tx.decision_job is not None:
                self._turn_jobs[(tx.command.actor,tx.command.task_id)]=tx.decision_job
                if tx.decision_job.outcome==WorkStatus.COMPLETED:self._active_turn.pop(tx.command.actor,None)
                else:self._active_turn[tx.command.actor]=tx.command.task_id
            if tx.processing is not None:
                s=tx.processing;self._register(s.ref,s,s.owner,tx.event.ref);self._processing_states[s.owner]=s
                self._processing_changes[-1]=(tx.event.ref,(s.owner,))
            if tx.participant is not None:
                s=tx.participant;self._autonomy_states[s.owner]=s;self._register(s.ref,s,s.owner,tx.event.ref)
            for d in tx.demands:
                k=d.specification.ref.key.removeprefix('r14:')
                self._demands[(d.owner,k)]=d;self._demand_records[d.specification.ref]=d
                self._register(d.specification.ref,d.specification,d.owner,tx.event.ref)
        for observation in tx.observations:
            sender=self._message_sender(observation)
            if sender is not None:
                packet=decode_packet(observation)
                if packet is not None:
                    ie='te' if packet.kind=='lesson' else 'fi'
                    self._notice_by_observation[(observation.observer,observation.ref)]=Notice(observation.ref,observation.source,sender,'workshop',observation.content[0],None,self._profiles[sender].tim,ie)
                elif (observation.observer,observation.ref) not in self._notice_by_observation:
                    claim=observation.content[0] if observation.content else self._prop(sender,'r14.opaque_message',observation.source,observation.source_time)
                    self._notice_by_observation[(observation.observer,observation.ref)]=Notice(observation.ref,observation.source,sender,'uninterpreted',claim,None,self._profiles[sender].tim,'ti')

    def checkpoint(self):
        from .codec import dumps
        return dumps(AutonomousCheckpoint('hle-r14-v1',self.config,self.profiles,self.policy,self.agents,
            self.organization_policies,self.semantic_policy,self.workshop,self.autonomy,tuple(self._journal)))

    @classmethod
    def restore(cls,text):
        from .codec import loads
        cp=loads(text)
        if type(cp) is not AutonomousCheckpoint or cp.schema!='hle-r14-v1' or not cp.journal:raise ValueError('unsupported R14 checkpoint')
        w=cls(cp.config,cp.profiles,cp.policy,cp.agents,cp.organization_policies,cp.semantic_policy,cp.workshop,cp.autonomy)
        if w._journal[0]!=cp.journal[0]:raise ValueError('genesis mismatch')
        for tx in cp.journal[1:]:
            if tx.command is None or tx.command.command_id in w._commands:raise ValueError('missing/duplicate command')
            w.execute(tx.command)
            if w._journal[-1]!=tx:raise ValueError('R14 replay mismatch')
        return w
