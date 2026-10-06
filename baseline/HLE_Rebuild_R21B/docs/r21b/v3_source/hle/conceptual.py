"""Integrated R14.5 runtime: particulars, conceptual tension and paid realization.

One journal. Semantic changes enqueue only affected owned observations. Exact
particulars use indexed detail lookup; conceptual state references evidence.
Finite learning and action policies are hypotheses, not a Shell diagnosis.
"""
from dataclasses import replace
from .autonomy import AutonomousWorld
from .autonomy_policy import decide
from .autonomy_records import WorkshopCommand, LocalDecision, AutonomousCheckpoint
from .concept_records import *
from .concept_structure import RELATIONS, SEAL, conceptual_path
from .contracts import (Moment, Proposition, TimeScope, ResourceAmount, Cause, ClaimStatus)
from .crux import Polarity, FormalMovement
from .processing import _route_geometry, route_active
from .metabolism_records import RoutePlan
from .world_records import Wallet, ENERGY, TIME, Attempt, Credit, Tick
from .world import amounts
from .memory_records import MemoryCommand, WriteDraft, BindDraft, DetailQuery

DONE=(WorkStatus.COMPLETED,WorkStatus.FAILED)
PACKET='concept.entrusted_use.v1'

class ConceptualWorld(AutonomousWorld):
    def __init__(self,*args,**kwargs):
        self._concepts={};self._concept_jobs={};self._concept_active={}
        self._concept_queue={};self._concept_processed=set();self._concept_signatures={}
        self._examined=set();self._care_practice={};self._live_supply={};self._migration_prefix=0;self._legacy_replay=False
        super().__init__(*args,**kwargs)
        for ref in (CONCEPT_RULE,CONCEPT_WORK,ENTRUSTED):
            self._records[ref]=ref
            for known in self._known.values():known.add(ref)

    def conceptual_state(self,actor):
        if actor not in self._actors: raise ValueError('unknown actor')
        return self._concepts.get(actor)

    @staticmethod
    def _loan_signature(item,facts):
        # No names, dates or incidental event IDs enter the conceptual decision.
        return (item,facts.get('borrower'),facts.get('return_to'))

    def _selection_extent(self,view):
        s=self._concepts.get(view.state.owner)
        return super()._selection_extent(view)+(len(s.relations)+len(s.tensions) if s is not None and view.recall is not None and not self._legacy_replay else 0)

    def _selection_sources(self,view):
        if self._legacy_replay or view.recall is None:return ()
        s=self._concepts.get(view.state.owner)
        return (() if s is None else (s.ref,))+tuple(r for (actor,item,sender),r in self._live_supply.items() if actor==view.state.owner)

    def _select_participant(self,view,key):
        if self._legacy_replay:return super()._select_participant(view,key)
        selected=decide(view,key,direct_details=True)
        c=selected.pending
        if type(c) is not WorkshopCommand or c.operation!='return':return selected
        actor=c.actor;state=self._concepts.get(actor)
        facts={p.relation:p.object for m in view.memories for p in m.content if p.subject==c.inputs[0]}
        signature=self._loan_signature(c.inputs[0],facts)
        supplies=tuple(o for (a,item,_),o in self._live_supply.items() if a==actor and item==c.inputs[0])
        mastered=state is not None and state.practiced and set(RELATIONS)<=set(state.relations)
        if not mastered and signature not in self._examined and not supplies:
            available=any(p.relation=='r14.native_operation' and p.object=='inspect' for m in view.memories for p in m.content)
            if not available:return replace(selected,pending=None,phase='unresolved',decision=replace(selected.decision,kind='unresolved',reason='conceptual exploration requires an unavailable inspection operation'))
            c=replace(c,operation='inspect',request=None)
            selected=replace(selected,attempts=view.state.attempts)
            reason='unpracticed care/release relation: inspect before realizing the accepted return'
        else:
            if supplies:c=replace(c,based_on=tuple(dict.fromkeys(c.based_on+supplies)))
            reason=('retained independent care/release composition' if mastered else
                    'currently supplied guidance for this item' if supplies else 'own inspection supports trying the bounded return; retention awaits consequence')
        return replace(selected,pending=c,decision=replace(selected.decision,reason=reason))

    def autonomy_ready(self,actor):
        base=super().autonomy_ready(actor)
        return base or (min(self._wallets[actor].energy,self._wallets[actor].time)>0 and
                       bool(self._concept_queue.get(actor) or actor in self._concept_active))

    def autonomy_step(self,actor):
        if actor in self._concept_active:
            old=self._concept_jobs[(actor,self._concept_active[actor])]
            return self.execute(replace(old.command,command_id='r145:resume:'+actor.key+':'+str(len(self._journal))))
        processing=self.processing_state(actor)
        s=self.autonomy_state(actor)
        if (not self._legacy_replay and self._concept_queue.get(actor) and processing.busy is None
                and actor not in self._receiving and actor not in self._active_turn
                and (s.pending is None or self._pending_status(actor,s.pending) in DONE)):
            key='r145:integrate:'+actor.key+':'+str(len(self._journal))
            return self.execute(ConceptCommand(key,key,actor,'integrate',tuple(self._concept_queue[actor]),work_limit=self._autonomy_policies[actor].work_limit))
        return super().autonomy_step(actor)

    def _concept_plan(self,actor,extent):
        state=self.processing_state(actor);tim=self._profiles[actor].tim if self.policy.typed_routing else 'ile'
        path=(state.active,);units=();content=0;support=5;offset=0
        # The explicit Fold bridge chooses the processing families. Model A
        # determines their seats, internal paths and prices; neither replaces it.
        for edge in conceptual_path(tim):
            p,seats,sup,at,u,price=_route_geometry(tim,path[-1],edge.element,Polarity.ACCUMULATION,self.policy.positional_prices)
            if len(path)==1:support,offset=sup,at
            path+=p[1:];units+=u;content+=max(1,extent)*price
        from .model_a import position_of
        return RoutePlan(self._profiles[actor].tim,tim,path,tuple(position_of(tim,e) for e in path),support,offset,units,content)

    def _validate_concept(self,cmd):
        if cmd.actor not in self._actors:raise ValueError('unknown actor')
        state=self._concepts.get(cmd.actor)
        sources=tuple(self._owned(cmd.actor,r,(Observation,)) for r in cmd.sources)
        if any(o.delivered_at>self.now for o in sources):raise ValueError('undelivered material')
        if cmd.operator=='integrate':
            if not sources:raise ValueError('integration needs owned encountered material')
            if any((cmd.actor,o.ref) in self._concept_processed for o in sources):raise ValueError('encounter already integrated')
            for o in sources:
                if o.source.kind==Kind.MESSAGE: raise ValueError('ordinary testimony is not authenticated conceptual instruction or own practice')
                if not any(p.relation in ('loan_active',PACKET) for p in o.content):raise ValueError('no relevant conceptual encounter')
                if any(p.relation==PACKET for p in o.content):self._instruction(o)
        elif cmd.operator in ('teach','supply'):
            if sources:raise ValueError('instruction uses retained concept, not arbitrary sources')
            if state is None or not state.practiced:raise ValueError('supplier lacks independently practiced composition')
            if cmd.recipient not in self._actors or (cmd.actor,cmd.recipient) not in self.config.message_links:
                raise ValueError('no permitted directed channel')
            if cmd.item is not None and cmd.item not in self._known[cmd.actor]:raise ValueError('unknown supplied item')
        elif cmd.operator=='revoke':
            if sources:raise ValueError('revocation does not ingest material')
        return state,sources

    def _instruction(self,o):
        tx=self._journal[o.source_time.tick]
        if type(tx) is not ConceptTransaction or tx.event.ref!=o.source or tx.command.operator not in ('teach','supply'):
            raise ValueError('concept instruction must be a funded authentic delivery')
        if tx.command.recipient!=o.observer or o not in tx.observations:raise ValueError('wrong instruction recipient')
        return tx.command.operator

    def _integrated(self,cmd,prior,sources,when):
        relations=set(() if prior is None else prior.relations)
        practiced=False if prior is None else prior.practiced
        for observation in sorted(sources,key=lambda o:o.source_time):
            if any(p.relation==PACKET for p in observation.content):
                if self._instruction(observation)=='teach':relations.update(RELATIONS)
                continue  # live supply remains external and does not confer retention
            items={p.subject for p in observation.content if p.relation=='loan_active'}
            for item in items:
                f={p.relation:p.object for p in observation.content if p.subject==item}
                if f.get('borrower')!=cmd.actor:continue
                if f.get('loan_active') is True:
                    relations.add(RELATIONS[0])
                    if f.get('condition')=='dirty':relations.add(RELATIONS[1])
                if (f.get('loan_active') is False and f.get('owned_by')==f.get('return_to') and f.get('return_to')!=cmd.actor
                        and f.get('condition')=='clean'):
                    relations.add(RELATIONS[2])
                    # Only the actor's own completed work can establish practice.
                    tx=self._journal[observation.source_time.tick]
                    c=tx.command
                    own_return=(type(c) is WorkshopCommand and c.actor==cmd.actor and c.operation=='return'
                                and tx.event.ref==observation.source and tx.event.outcome==WorkStatus.COMPLETED)
                    care=self._care_practice.get((cmd.actor,item))
                    if own_return and care is not None and self._records[care].source_time < observation.source_time and set(RELATIONS)<=relations:practiced=True
        tensions=(() if practiced else ('unpracticed_composition',) if set(RELATIONS)<=relations else
                  ('care_vs_release',) if RELATIONS[0] in relations and RELATIONS[1] in relations else ())
        ref=Ref(Kind.MEMORY,'r145:concept:'+cmd.actor.key,1 if prior is None else prior.ref.revision+1)
        return ConceptState(ref,cmd.actor,ENTRUSTED,self.config.context,ConceptAddress(5,'Coin',1,self.config.context,Ref(Kind.CUE,'arcana:5',1)),tuple(sorted(relations)),tensions,
            cmd.sources,None if prior is None else prior.ref,practiced)

    def _concept(self,cmd):
        old=self._concept_jobs.get((cmd.actor,cmd.task_id));processing=self.processing_state(cmd.actor)
        if old is not None:
            if old.outcome in DONE or self._concept_active.get(cmd.actor)!=cmd.task_id:raise ValueError('terminal or unowned conceptual work')
            if replace(cmd,command_id=old.command.command_id,work_limit=old.command.work_limit)!=old.command:raise ValueError('changed conceptual continuation')
        elif processing.busy is not None or cmd.actor in self._receiving or cmd.actor in self._active_turn:
            raise ValueError('personal processing is busy')
        prior,sources=self._validate_concept(cmd)
        previous=None if prior is None else prior.ref
        if old is not None and old.previous!=previous:raise ValueError('concept predecessor changed')
        old=old or ConceptJob(cmd,self._concept_plan(cmd.actor,1+sum(len(o.content) for o in sources)),previous,tuple(FormalMovement(e.route,Polarity.ACCUMULATION) for e in conceptual_path(self._profiles[cmd.actor].tim if self.policy.typed_routing else 'ile')))
        when=Moment(len(self._journal),0);event_ref=Ref(Kind.EVENT,'event:'+str(when.tick),1)
        wallet=self._wallets[cmd.actor];spent=min(old.plan.required-old.paid,cmd.work_limit,wallet.energy,wallet.time);paid=old.paid+spent
        status=WorkStatus.COMPLETED if paid==old.plan.required else WorkStatus.PARTIAL if paid else WorkStatus.DEFERRED
        result=None;observations=()
        if status==WorkStatus.COMPLETED:
            if cmd.operator=='integrate':result=self._integrated(cmd,prior,sources,when)
            elif cmd.operator=='revoke':
                recipients=sorted({a for (a,item,sender) in self._live_supply if sender==cmd.actor},key=lambda a:a.key)
                observations=tuple(self._observation(a,event_ref,when,(Proposition(cmd.actor,'concept.supply_status','revoked',self.config.context,TimeScope(when,None)),),
                    'permitted supplier withdrawal notice','supply unavailable; retained learner capacity unchanged') for a in recipients)
            elif cmd.operator in ('teach','supply'):
                props=(Proposition(cmd.actor,PACKET,ENTRUSTED,self.config.context,TimeScope(when,None)),)
                observations=(self._observation(cmd.recipient,event_ref,when,props,'funded conceptual '+cmd.operator,'shared reference; mastery is not transmitted'),)
        state=replace(processing,ref=replace(processing.ref,revision=processing.ref.revision+1),active=route_active(old.plan,paid),busy=None if status in DONE else 'r145:'+cmd.task_id)
        work=WorkRecord(Ref(Kind.WORK,'work:'+str(when.tick)+':concept',1),cmd.actor,CONCEPT_WORK,amounts(wallet),(),
            (ResourceAmount(ENERGY,spent),ResourceAmount(TIME,spent)),amounts(Wallet(cmd.actor,wallet.energy-spent,wallet.time-spent)),
            old.plan.required-old.paid,spent,status,'paid conceptual relation processing; no result before full funding')
        basis=cmd.sources+(() if previous is None else (previous,))
        causes=tuple(dict.fromkeys(Cause(self._origins[r],CONCEPT_RULE) for r in basis))
        event=WorldEvent(event_ref,when,(cmd.actor,),(),'r145.'+cmd.operator,self.config.context,(),causes,(work.ref,),status,work.reason)
        self._commit(ConceptTransaction(cmd,event,(work,),observations,job=replace(old,paid=paid,outcome=status),processing=state,concept=result))
        return event

    def execute(self,cmd):
        prior=self._commands.get(cmd.command_id)
        if prior is not None:
            if prior.command!=cmd:raise ValueError('command identity reused')
            return prior.event
        if type(cmd) is ConceptCommand:return self._concept(cmd)
        actor=cmd.action.actor if type(cmd) is Attempt else getattr(cmd,'actor',None)
        if actor in self._concept_active and type(cmd) not in (Credit,Tick):raise ValueError('unfinished conceptual work owns processing')
        # Concepts are not injectable as unvalidated factual memory or wire text.
        payload=cmd.payload if type(cmd) is MemoryCommand else None
        if type(payload) is WriteDraft and any(p.relation.startswith('concept.') for p in payload.content):
            raise ValueError('use paid conceptual integration')
        if type(cmd) is Attempt:
            for draft in (cmd.message,cmd.memory):
                if draft is not None and any(p.relation.startswith('concept.') for p in draft.content):raise ValueError('concept delivery must have an authenticated retained origin')
        return super().execute(cmd)

    def _commit(self,tx):
        super()._commit(tx)
        if type(tx) is ConceptTransaction:
            actor=tx.command.actor;j=tx.job
            self._concept_jobs[(actor,tx.command.task_id)]=j
            if j.outcome in DONE:self._concept_active.pop(actor,None)
            else:self._concept_active[actor]=tx.command.task_id
            self._processing_states[actor]=tx.processing
            self._register(tx.processing.ref,tx.processing,actor,tx.event.ref)
            self._processing_changes[-1]=(tx.event.ref,(actor,))
            if tx.concept is not None:
                self._concepts[actor]=tx.concept;self._register(tx.concept.ref,tx.concept,actor,tx.event.ref)
                for r in tx.command.sources:self._concept_processed.add((actor,r))
                self._concept_queue[actor]=[r for r in self._concept_queue.get(actor,[]) if (actor,r) not in self._concept_processed]
            if j.outcome==WorkStatus.COMPLETED:
                if tx.command.operator=='supply':
                    self._live_supply[(tx.command.recipient,tx.command.item,actor)]=tx.observations[0].ref
                elif tx.command.operator=='revoke':
                    self._live_supply={k:v for k,v in self._live_supply.items() if k[2]!=actor}
        for o in tx.observations:
            if any(p.relation==PACKET for p in o.content):
                # Supplied work is not a learned conceptual relation. Teaching
                # is queued for the recipient's separately funded integration.
                if type(tx) is ConceptTransaction and tx.command.operator=='teach':self._concept_queue.setdefault(o.observer,[]).append(o.ref)
                continue
            # No arbitrary testimony gets a direct physical-experience status.
            if o.source.kind==Kind.MESSAGE:continue
            items={p.subject for p in o.content if p.relation=='loan_active'}
            for item in items:
                f={p.relation:p.object for p in o.content if p.subject==item}
                if f.get('borrower')!=o.observer or f.get('return_to')==o.observer:continue
                relevant=tuple((k,f.get(k)) for k in ('loan_active','condition','borrower','return_to','return_due'))
                key=(o.observer,item)
                if relevant!=self._concept_signatures.get(key):
                    self._examined.discard(self._loan_signature(item,f))
                    self._concept_signatures[key]=relevant
                    queue=self._concept_queue.setdefault(o.observer,[])
                    if o.ref not in queue:queue.append(o.ref)
                c=tx.command
                if f.get('loan_active') is True and f.get('return_due') is False:self._care_practice.pop((o.observer,item),None)
                if (type(c) is WorkshopCommand and c.actor==o.observer and c.operation=='clean' and tx.event.outcome==WorkStatus.COMPLETED
                        and f.get('loan_active') is True):self._care_practice[(o.observer,item)]=o.ref
                if type(c) is WorkshopCommand and c.actor==o.observer and c.operation=='inspect' and f.get('condition')=='clean' and f.get('loan_active') is True:
                    self._examined.add(self._loan_signature(item,f))
                if f.get('loan_active') is False:
                    self._examined.discard(self._loan_signature(item,f))
                    self._live_supply={k:v for k,v in self._live_supply.items() if k[:2]!=(o.observer,item)}

    def checkpoint(self):
        from .codec import dumps
        # Only one journal is serialized. Base holds configuration, no duplicate history.
        base=AutonomousCheckpoint('hle-r14-v1',self.config,self.profiles,self.policy,self.agents,self.organization_policies,
            self.semantic_policy,self.workshop,self.autonomy,())
        return dumps(ConceptCheckpoint('hle-r145-v1',base,tuple(self._journal),self._migration_prefix,SEAL))

    @classmethod
    def restore(cls,text):
        from .codec import loads
        cp=loads(text)
        if type(cp) is not ConceptCheckpoint or cp.schema!='hle-r145-v1' or not cp.journal or cp.reference_seal!=SEAL:raise ValueError('unsupported conceptual checkpoint/reference version')
        if not 0<=cp.migration_prefix<=len(cp.journal):raise ValueError('invalid migration prefix')
        b=cp.base;w=cls(b.config,b.profiles,b.policy,b.agents,b.organization_policies,b.semantic_policy,b.workshop,b.autonomy)
        w._migration_prefix=cp.migration_prefix
        if w._journal[0]!=cp.journal[0]:raise ValueError('genesis mismatch')
        for i,tx in enumerate(cp.journal[1:],1):
            w._legacy_replay=i<cp.migration_prefix
            if tx.command is None or tx.command.command_id in w._commands:raise ValueError('missing/duplicate command')
            w.execute(tx.command)
            if w._journal[-1]!=tx:raise ValueError('R14.5 replay mismatch at '+str(i))
        w._legacy_replay=False
        return w

    @classmethod
    def import_r14(cls,text):
        from .codec import loads
        # Validate the old history under its original behavioral policy first.
        source=AutonomousWorld.restore(text);b=loads(text)
        w=cls(b.config,b.profiles,b.policy,b.agents,b.organization_policies,b.semantic_policy,b.workshop,b.autonomy)
        w._legacy_replay=True
        for tx in b.journal[1:]:
            w.execute(tx.command)
            if w._journal[-1]!=tx:raise ValueError('migration changed historical transactions')
        w._migration_prefix=len(b.journal);w._legacy_replay=False
        return w
