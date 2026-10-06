"""R20 shared closure on the continuing R19 journal.

Participant planning uses owned or explicitly shared records. Physical effects
remain R18 production, R17 returns and R9 enacted duties. The evaluator observes
those effects; neither a name nor a supplied success flag settles a duty.
"""
from dataclasses import replace
import hashlib
from .clearance import ClearanceWorld
from .closure_records import *
from .closure_policy import search, allocate
from .composition_records import CompositionRevision, UnfoldResult
from .contracts import ActionRequest, Cause, ClaimStatus, Moment, Proposition, ResourceAmount, TimeScope
from .conversion_records import ConversionUse
from .individuation_records import CircuitSignal
from .organization_records import OrganizationResult, OrganizationTransaction, Dispute
from .organization import terms_id
from .organization_policy import select, action_cost
from .language import fingerprint
from .socion_records import ReceiveCommand, Notice
from .world import amounts, memory_key, ref_order
from .world_records import Attempt, MessageDraft, SEND, TRANSFER, ENERGY, TIME, Wallet

CLOSURE_SEAL=hashlib.sha256(b'r20-v1:finite-consent:inherited-obligations:exact-shared-access:scoped-dependencies').hexdigest()

class ClosureWorld(ClearanceWorld):
    def __init__(self,*args,**kwargs):
        self._closure_jobs={}; self._closure_outgoing={}; self._closure_shared={}
        self._closure_demands={}; self._closure_plans={}; self._closure_active={};self._closure_executions={}
        self._closure_duties={}; self._closure_claims={}; self._closure_invalid={}
        self._closure_watch={}; self._closure_root_watch={}; self._closure_state_watch={};self._closure_origin_watch={}
        self._closure_production={};self._closure_native_index={};self._closure_retained={}
        self._closure_history=[]; self.closure_invalidation_visits=0
        super().__init__(*args,**kwargs)
        for r in (CLOSURE_RULE,CLOSURE_WORK):self._records[r]=r
        for known in self._known.values():known.update((CLOSURE_RULE,CLOSURE_WORK))

    def _owned(self,actor,ref,types):
        r=self._records.get(ref)
        if ref in self._closure_shared.get(actor,()) and type(r) in types:
            if type(r) in (MemoryRevision,CompositionRevision,NativeBinding,SharedDemand,SearchResult,SharedPlan,ClosureResult):
                return r
        return super()._owned(actor,ref,types)

    def _closure_record(self,a,r,types):return self._owned(a,r,types)

    def _access_root(self,a,ref):
        access=self._owned(a,ref,(UnfoldResult,))
        if access.query.context!=self.config.context or access.truncated:
            raise ValueError('complete contextual paid unfolding required')
        for r in access.nodes:
            node=self._owned(a,r,(MemoryRevision,CompositionRevision))
            head=self._composition_heads.get(r.key) if type(node) is CompositionRevision else self._memory_heads[node.owner].get(r.key)
            if head!=node or not self._evidence_live(r):raise ValueError('a lower organization changed')
        return access

    def _binding_live(self,b):
        return (self._accessible(b.owner) and self._signature(b.owner)==b.capacities
            and len(b.capacities)==9 and all(self._evidence_live(r) for r in
            b.capacities+(b.material,b.production,b.conditional_use,b.returned)))

    def _read_closure(self,a,ref):
        if not self._evidence_live(ref):raise ValueError('withdrawn shared evidence')
        r=self._records.get(ref)
        if type(r) in (SharedPlan,SharedVote) and r.owner==a:
            return ClosurePacket(a,r)
        o=self._owned(a,ref,(Observation,))
        if (a,ref) not in self._completed_reception:raise ValueError('complete paid reception first')
        m=self._records.get(o.source)
        if type(m) is not Message or len(o.content)!=1 or o.content[0].relation!='r20_wire':
            raise ValueError('authenticated R20 delivery required')
        from .codec import loads
        packet=loads(o.content[0].object)
        if type(packet) is not ClosurePacket or packet.sender!=m.sender or packet.record.owner!=m.sender:
            raise ValueError('wrong packet sender')
        if not self._evidence_live(packet.record.ref):raise ValueError('originating shared commitment withdrawn')
        return packet

    def _own_cycle(self,a,identity):
        s=self.organization_state(a,identity)
        return s if s is not None and s.status=='active' else None

    def _prepare_organization(self,c):
        if type(c.payload) is Dispute and type(self._records.get(c.payload.run)) is SharedVote:
            vote=self._owned(c.actor,c.payload.run,(SharedVote,));state=self._records[vote.state]
            if vote.approved or self.organization_state(c.actor,state.terms.identity)!=state:
                raise ValueError('own current refused cumulative obligation required')
            ref=Ref(Kind.EVIDENCE,'organization:'+memory_key(c.actor,c.task_id),1)
            return 3,OrganizationResult(ref,c.actor,'dispute',state.terms,'suspended',
                'experienced cumulative burden refused under own participation limit',
                (vote.ref,state.ref),state.ref)
        return super()._prepare_organization(c)

    def _plan_departed(self,a,d):
        if d.previous_terms is None:return ()
        # Only departure notices actually received by this participant.
        return tuple(sorted(self._departures.get((a,d.previous_terms),{}),key=ref_order))

    def _prepare_closure(self,c):
        a=c.actor;ins=c.inputs
        if a not in self._actors:raise ValueError('known participant required')
        ref=Ref(Kind.EVIDENCE,'closure:'+memory_key(a,c.task_id),1)
        def result(value,units,basis=ins):return value,max(1,units),tuple(dict.fromkeys(basis))
        if c.operation=='bind':
            if len(ins)!=4:raise ValueError('unfold, own production, own conditional use, actual return required')
            access=self._access_root(a,ins[0]); sig=self._signature(a)
            mentioned={p.object for r in access.nodes if type(self._records[r]) is MemoryRevision for p in self._records[r].content if p.relation=='r20.capacity'}
            if len(sig)!=9 or not set(sig)<=mentioned or not self._accessible(a):raise ValueError('all current retained lower procedures required')
            production=self._records.get(ins[1]);use=self._owned(a,ins[2],(ConversionUse,))
            if type(production) is not CircuitSignal or production.observer!=a or production.ref not in self._known[a]:
                raise ValueError('own delivered production required')
            event=self._records.get(ins[3]);order=self._circuit_orders[production.order]
            tx=self._commands.get(getattr(self._journal[event.when.tick].command,'command_id',None)) if type(event) is WorldEvent else None
            if (not production.success or production.performer!=a or not order.closed or not order.credited
                or set(order.uses)!=set(sig[1:]) or use.capacity!=sig[0] or use.owner!=a
                or tx is None or getattr(tx.command,'operation',None)!='return' or tx.command.actor!=a
                or tx.command.inputs!=(use.item,) or event.outcome!=WorkStatus.COMPLETED
                or use.event.revision!=1 or self._origins[use.ref].key==event.ref.key
                or self._origins[use.ref] not in self._records
                or self._records[self._origins[use.ref]].when>=event.when):
                raise ValueError('real own production followed by grounded own return required')
            b=NativeBinding(ref,a,access.query.root,access.ref,self._tensions[a].ref,sig,production.ref,use.ref,event.ref)
            if not self._binding_live(b):raise ValueError('live native evidence required')
            return result(b,4+len(access.nodes)+len(sig))
        if c.operation=='learn':
            if len(ins)!=1:raise ValueError('one delivered procedure required')
            p=self._read_closure(a,ins[0]);plan=p.record
            if type(plan) is not SharedPlan or a not in plan.members or not p.readable:raise ValueError('explicitly shared procedure required')
            state=self._own_cycle(a,plan.identity)
            if state is None or terms_id(state.terms)!=plan.terms_digest:raise ValueError('independently accepted same practice required')
            return result(RootGrant(ref,a,ins[0],plan.ref,p.readable),2+len(p.readable))
        if c.operation=='open':
            if len(ins)!=1:raise ValueError('native binding required')
            b=self._closure_record(a,ins[0],(NativeBinding,))
            choices=self.practices(a)
            p=select(choices,self._organization_policies[a],{x.meaning.token:self.lexeme(a,x.meaning.token) for x in choices if self.lexeme(a,x.meaning.token) is not None})
            if p is None or len(p.partners)<2 or p.item!=self._records[b.conditional_use].item:
                raise ValueError('repeated actual practice with two partners on the returned material required')
            members=tuple(sorted(set(p.partners)|{a},key=ref_order))
            if self._closure_production.get(b.production,0)+len(members)>self._records[b.production].produced:
                raise ValueError('actual credited production does not cover additional obligations')
            d=SharedDemand(ref,a,b.ref,p.item,members,tuple(ref.key+':duty:'+str(i) for i in range(len(members))))
            return result(d,2+len(members)+len(choices),ins+p.examples)
        if c.operation=='renew':
            if len(ins)!=1:raise ValueError('one retained shared procedure required')
            plan=self._closure_record(a,ins[0],(SharedPlan,));d=self._records[plan.demand];b=self._records[d.binding]
            if plan.operation!='consent_cycle':raise ValueError('lower cycle required')
            if self._closure_production.get(b.production,0)+len(plan.members)>self._records[b.production].produced:
                raise ValueError('actual credited production does not cover renewed obligations')
            new=SharedDemand(ref,a,d.binding,d.item,plan.members,tuple(ref.key+':duty:'+str(i) for i in range(len(plan.members))),plan.ref,plan.identity,plan.generation)
            return result(new,2+len(plan.members))
        if c.operation=='search':
            if len(ins)!=1:raise ValueError('one actual unresolved demand required')
            d=self._closure_record(a,ins[0],(SharedDemand,));departed=self._plan_departed(a,d)
            current=()
            if d.parent is not None:
                current=('consent_cycle',)
                # Retained activated procedures are participant evidence. An
                # evaluator's status, depth or invalidation is never consulted.
                if 'carry_obligations' in self._closure_retained.get(a,()):current+=('carry_obligations',)
            mode='carry' if departed else 'shared'
            if c.label=='single':mode='single'
            elif c.label:raise ValueError('only declared single-action comparison is supported')
            done=self._closure_duties.get(d.ref,{})
            unfinished=tuple(x for x in d.obligations if x not in done)
            rows,candidates,minima,status=search(mode,current,c.search_limit,len(unfinished))
            return result(SearchResult(ref,a,d.ref,current,rows,candidates,minima,status,mode,unfinished,departed),1+len(rows)+sum(x[1] for x in candidates))
        if c.operation=='propose':
            if len(ins)!=4:raise ValueError('demand, complete search, paid root access, current owned R9 state required')
            d=self._closure_record(a,ins[0],(SharedDemand,));s=self._closure_record(a,ins[1],(SearchResult,))
            access=self._access_root(a,ins[2]);state=self.organization_record(a,ins[3]);t=state.terms
            if s.demand!=d.ref or s.status not in ('necessary_in_declared_repertoire','horizontal') or not s.unfinished:raise ValueError('completed meaningful search required')
            if s.unfinished!=tuple(x for x in d.obligations if x not in self._closure_duties[d.ref]):
                raise ValueError('outstanding obligations changed after search')
            if t is None or self._own_cycle(a,t.identity)!=state or t.item!=d.item:raise ValueError('current participant-generated local rule required')
            op='carry_obligations' if s.required=='carry' else 'consent_cycle'
            if s.status=='necessary_in_declared_repertoire' and op not in s.equal_minima:raise ValueError('minimal sufficient extension required')
            b=self._records[d.binding];parent_root=b.root if d.parent is None else self._records[d.parent].root
            props=[p for r in access.nodes if type(self._records[r]) is MemoryRevision for p in self._records[r].content]
            if parent_root not in access.nodes or not any(p.relation=='r20.operator' and p.object==op for p in props):
                raise ValueError('actual lower root and executable operator required')
            # Start at the holder evidenced by owned R9 access, never hidden Truth.
            _,facts,_,stale=self._access(a,self._records[state.sources[0]].sources[1]) if state.kind=='agreement' else (None,(),0,True)
            owners={owner for item,owner in facts if item==d.item}
            if stale or len(owners)!=1 or not owners<=set(t.members):raise ValueError('owned current cohort holder evidence required')
            start=next(iter(owners));assignments=allocate(s.unfinished,t.members,start)
            if op=='consent_cycle' and set(t.members)!=set(d.members):raise ValueError('changed cohort requires obligation carry')
            if op=='carry_obligations' and (d.parent is None or t.identity!=d.previous_terms or t.generation<=d.previous_generation or not s.departed or set(s.departed)&set(t.members)):
                raise ValueError('exact old lineage, observed departure and newly agreed successor cohort required')
            plan=SharedPlan(ref,a,d.ref,access.query.root,access.ref,s.ref,op,t.identity,t.generation,terms_id(t),t.members,assignments,start,state.ref,parent_root)
            return result(plan,3+len(access.nodes)+len(assignments))
        if c.operation=='review':
            if len(ins)!=1:raise ValueError('one authenticated proposal required')
            p=self._read_closure(a,ins[0]);plan=p.record
            if type(plan) is not SharedPlan:raise ValueError('shared plan required')
            state=self._own_cycle(a,plan.identity)
            if state is None:raise ValueError('independently agreed own R9 state required')
            policy=self._organization_policies[a];units=sum(member==a for _,member in plan.assignments)*action_cost(state.terms.steps)
            matching=(a in plan.members and terms_id(state.terms)==plan.terms_digest)
            approved=matching and 0<units<=policy.max_action_cost and self._agent_policies[a].response!='silent'
            reason='exact inherited duties and own cumulative work limit accepted' if approved else 'terms, own participation or cumulative burden refused'
            return result(SharedVote(ref,a,plan.ref,approved,reason,state.ref,units,policy.max_action_cost),2+len(plan.assignments),ins+(state.ref,))
        if c.operation=='activate':
            if len(ins)<2:raise ValueError('proposal and exact member consents required')
            plan=self._closure_record(a,ins[0],(SharedPlan,));votes=[self._read_closure(a,r).record for r in ins[1:]]
            if (any(type(v) is not SharedVote or v.plan!=plan.ref or not v.approved for v in votes)
                or len(votes)!=len(plan.members) or {v.owner for v in votes}!=set(plan.members)):
                raise ValueError('all distinct exact-version consents required')
            state=self._own_cycle(a,plan.identity)
            if state is None or terms_id(state.terms)!=plan.terms_digest:raise ValueError('own agreed state changed')
            if plan.demand in self._closure_executions:raise ValueError('demand already has an execution')
            return result(SharedActivation(ref,a,plan.ref,ins[1:]),2+len(votes))
        if len(ins)!=1:raise ValueError('one active execution required')
        active=self._closure_record(a,ins[0],(SharedActivation,));plan=self._records[active.plan];d=self._records[plan.demand]
        if self._closure_executions.get(d.ref)!=active.ref:raise ValueError('recorded execution required')
        b=self._records[d.binding];s=self._records[plan.search]
        done=self._closure_duties.get(d.ref,{})
        duties=tuple((key,done[key][0],done[key][1]) for key in d.obligations if key in done)
        states=tuple(self.organization_state(m,plan.identity) for m in plan.members)
        parents=[x for x in self._closure_claims.values() if x.plan==d.parent and x.status=='established']
        consent_live=True;vote_refs=[]
        for source in active.votes:
            try:
                vote=self._read_closure(a,source).record
                consent_live &= type(vote) is SharedVote and vote.approved and vote.plan==plan.ref
                vote_refs.append(vote.ref)
            except ValueError:consent_live=False
        predicates={
            'native_current':self._binding_live(b) and self.clearance_monitor.status=='cleared_in_scope',
            'obligations_preserved':set(done)==set(d.obligations),
            'own_responsibilities':all(done.get(key,(None,))[0]==member for key,member in plan.assignments),
            'current_exact_consent':consent_live and all(st is not None and st.status=='active' and terms_id(st.terms)==plan.terms_digest for st in states),
            'every_member_performs':{x[1] for x in duties}==set(plan.members),
            'lower_structure_usable':self._roots_live(plan.access),
            'successive':d.parent is None or bool(parents) and self._records[d.parent].root==plan.parent_root and all(self._evidence_live(r) for p in parents for r in p.dependencies),
            'necessary':s.status=='necessary_in_declared_repertoire',
        }
        status='established' if all(predicates.values()) else 'horizontal' if all(v for k,v in predicates.items() if k!='necessary') else 'unresolved'
        depth=(1 if d.parent is None else max(x.depth for x in parents)+1) if status=='established' else 0
        access=self._records[plan.access]
        deps=set((b.ref,b.material,b.production,b.conditional_use,b.returned,plan.ref,active.ref,s.ref,d.ref)+b.capacities+access.nodes)
        deps.update(r for _,_,r in duties)
        deps.update(active.votes)
        deps.update(vote_refs)
        for parent in parents:
            # Historical consent versions need not remain the current cohort,
            # but withdrawn evidence cannot continue to prove the lower closure.
            deps.update(parent.dependencies);deps.add(parent.ref)
        # Native acquisition is relevant to both parents; retain all exact sources.
        for cap in b.capacities:
            record=self._records[cap]
            deps.update(getattr(record,'acquisition',()))
            p=getattr(record,'practice',());deps.update(p if type(p) is tuple else (p,))
            deps.update(getattr(record,'dependencies',()))
        study=self._studies[b.owner];capacity=self._capacities[b.owner]
        deps.update((study.material,study.concept_origin,study.account_material,capacity.rule))
        deps.update(self._candidates[capacity.rule].sources)
        refs=tuple(st.ref for st in states if st is not None)
        out=ClosureResult(ref,a,plan.ref,active.ref,duties,plan.root,depth,status,tuple(predicates.items()),tuple(sorted(deps,key=ref_order)),refs)
        return result(out,3+len(d.obligations)+len(deps),ins)

    def _roots_live(self,access):
        q=self._records[access]
        for r in q.nodes:
            rec=self._records[r]
            head=self._composition_heads.get(r.key) if type(rec) is CompositionRevision else self._memory_heads[rec.owner].get(r.key)
            if head!=rec or not self._evidence_live(r):return False
        return True

    def execute(self,c):
        if type(c) is not ClosureCommand:return super().execute(c)
        prior=self._commands.get(c.command_id)
        if prior is not None:
            if prior.command!=c:raise ValueError('command identity reused')
            return prior.event
        if c.operation=='settle':
            # Observer boundary: no participant receives a verdict, and no
            # participant wallet is charged for the external assessment.
            candidate,required,basis=self._prepare_closure(c)
            when=Moment(len(self._journal),0);er=Ref(Kind.EVENT,'event:'+str(when.tick),1)
            event=WorldEvent(er,when,(),(),'r20.assess',self.config.context,(),(),(),WorkStatus.COMPLETED,
                'observer-only finite closure assessment')
            job=ClosureJob(c,required,candidate,basis,0,WorkStatus.COMPLETED,candidate.ref)
            self._commit(ClosureTransaction(c,event,extra=(candidate,),job=job))
            return event
        old=self._closure_jobs.get((c.actor,c.task_id))
        if old is not None and (old.outcome in (WorkStatus.COMPLETED,WorkStatus.FAILED) or (old.command.operation,old.command.inputs,old.command.label,old.command.search_limit)!=(c.operation,c.inputs,c.label,c.search_limit)):
            raise ValueError('terminal or changed closure continuation')
        invalid=None
        try:candidate,required,basis=self._prepare_closure(c)
        except ValueError as error:
            if old is None:raise
            candidate,required,basis=old.candidate,old.required,old.basis;invalid=str(error)
        if old is None:old=ClosureJob(c,required,candidate,basis)
        elif (candidate,required,basis)!=(old.candidate,old.required,old.basis):invalid='support changed during paid work'
        wallet=self._wallets[c.actor]
        spent=0 if invalid else min(c.work_limit,wallet.energy,wallet.time,old.required-old.paid)
        paid=old.paid+spent
        status=WorkStatus.FAILED if invalid else WorkStatus.COMPLETED if paid==old.required else WorkStatus.PARTIAL if paid else WorkStatus.DEFERRED
        when=Moment(len(self._journal),0);er=Ref(Kind.EVENT,'event:'+str(when.tick),1)
        work=WorkRecord(Ref(Kind.WORK,'work:'+str(when.tick)+':0',1),c.actor,CLOSURE_WORK,amounts(wallet),(),
            (ResourceAmount(ENERGY,spent),ResourceAmount(TIME,spent)),amounts(Wallet(c.actor,wallet.energy-spent,wallet.time-spent)),
            old.required-old.paid,spent,status,invalid or 'paid finite shared-obligation processing')
        origins=tuple(dict.fromkeys(r if r.kind==Kind.EVENT else self._origins[r] for r in old.basis))
        event=WorldEvent(er,when,(c.actor,),(),'r20.'+c.operation,self.config.context,(),tuple(Cause(r,CLOSURE_RULE) for r in origins),(work.ref,),status,work.reason)
        extra=(candidate,) if status==WorkStatus.COMPLETED else ()
        job=replace(old,paid=paid,outcome=status,result=candidate.ref if extra else None)
        observations=() if not extra else (self._observation(c.actor,er,when,
            (self._prop(c.actor,'r20.result',candidate.ref,when),),'own shared-processing receipt','local result; no developmental verdict supplied'),)
        self._commit(ClosureTransaction(c,event,(work,),observations=observations,extra=extra,job=job))
        return event

    def send_closure(self,a,record,recipient,key):
        r=self._owned(a,record,(SharedPlan,SharedVote))
        readable=()
        if type(r) is SharedPlan:
            if recipient not in r.members:raise ValueError('only offered members may read shared lower structure')
            d=self._records[r.demand];b=self._records[d.binding]
            readable=tuple(dict.fromkeys(self._records[r.access].nodes+(r.ref,d.ref,b.ref,r.search)+(() if d.parent is None else (d.parent,))))
        packet=ClosurePacket(a,r,readable)
        from .codec import dumps
        prop=Proposition(a,'r20_wire',dumps(packet),self.config.context,TimeScope(self.now,None))
        return Attempt(key,key,ActionRequest(a,SEND,(recipient,),()),MessageDraft((prop,)))

    def _validate_attempt(self,c):
        if c.message is not None and any(p.relation=='r20_wire' for p in c.message.content):
            if len(c.message.content)!=1:raise ValueError('one closure packet required')
            p=c.message.content[0]
            from .codec import loads
            packet=loads(p.object)
            if (type(packet) is not ClosurePacket or packet.sender!=c.action.actor or packet.record.owner!=c.action.actor
                or self._records.get(packet.record.ref)!=packet.record or packet.record.ref not in self._known[c.action.actor]):
                raise ValueError('packet lacks committed owned origin')
            canonical=self.send_closure(c.action.actor,packet.record.ref,c.action.inputs[0],c.command_id)
            if c.message!=canonical.message:raise ValueError('altered closure packet or access grant')
        return super()._validate_attempt(c)

    def _invalidate_closure(self,refs,reason):
        affected=set()
        for r in refs:
            affected.update(self._closure_watch.get(r,()))
            affected.update(self._closure_origin_watch.get(r,()))
            affected.update(self._closure_root_watch.get((r.kind,r.key),()))
            affected.update(self._closure_state_watch.get(r,()))
        for r in sorted(affected,key=ref_order):
            self.closure_invalidation_visits+=1
            if r not in self._closure_invalid:
                self._closure_invalid[r]=reason
                self._closure_history.append((self._journal[-1].event.ref,r,reason))

    def _commit(self,tx):
        c=tx.command
        clearance_before=None if self.clearance_monitor is None else self.clearance_monitor.status
        target=self._organization_action_owner.get(getattr(c,'command_id',None))
        prior_states=()
        if type(tx) is OrganizationTransaction:
            prior_states=tuple(self.organization_state(r.owner,r.terms.identity) for r in tx.extra if r.terms is not None)
        super()._commit(tx)
        if type(tx) is ClosureTransaction:
            for r in tx.extra:
                if type(r) is ClosureResult:
                    self._records[r.ref]=r;self._origins[r.ref]=tx.event.ref
                else:self._register(r.ref,r,r.owner,tx.event.ref)
                if type(r) is RootGrant:
                    self._closure_shared.setdefault(r.owner,set()).update(r.readable)
                    self._known[r.owner].update(r.readable)
                elif type(r) is SharedDemand:
                    self._closure_demands[r.ref]=r;self._closure_duties[r.ref]={}
                    production=self._records[r.binding].production
                    self._closure_production[production]=self._closure_production.get(production,0)+len(r.obligations)
                elif type(r) is SharedPlan:self._closure_plans[r.ref]=r
                elif type(r) is SharedActivation:
                    demand=self._records[r.plan].demand
                    self._closure_active[demand]=r.ref;self._closure_executions[demand]=r.ref
                    self._closure_retained.setdefault(r.owner,set()).add(self._records[r.plan].operation)
                elif type(r) is ClosureResult:
                    self._closure_claims[r.ref]=r
                    owner=self._records[self._records[self._records[r.plan].demand].binding].owner
                    self._closure_native_index.setdefault(owner,set()).add(r.ref)
                    for dep in r.dependencies:
                        self._closure_watch.setdefault(dep,set()).add(r.ref)
                        self._closure_origin_watch.setdefault(self._origins.get(dep,dep),set()).add(r.ref)
                    for dep in self._records[self._records[r.plan].access].nodes:
                        self._closure_root_watch.setdefault((dep.kind,dep.key),set()).add(r.ref)
                    for dep in r.current_states:self._closure_state_watch.setdefault(dep,set()).add(r.ref)
            self._closure_jobs[c.actor,c.task_id]=tx.job
        for o in tx.observations:
            m=self._records.get(o.source)
            if type(m) is Message and len(o.content)==1 and o.content[0].relation=='r20_wire':
                self._notice_by_observation[o.observer,o.ref]=Notice(o.ref,o.source,m.sender,'closure',o.content[0],None,self._profiles[m.sender].tim,self.processing_state(m.sender).active)
        # Each real completed R9 transfer can discharge at most one duty in
        # one execution. Plans and inspection receipts do not count as actions.
        if (target is not None and type(c) is Attempt and c.action.operation==TRANSFER
            and tx.event.outcome==WorkStatus.COMPLETED):
            run=self._records[target]
            for demand,active_ref in tuple(self._closure_active.items()):
                plan=self._records[self._records[active_ref].plan];done=self._closure_duties[demand]
                pending=[pair for pair in plan.assignments if pair[0] not in done]
                if (pending and run.terms is not None and terms_id(run.terms)==plan.terms_digest
                    and c.action.actor==pending[0][1] and c.action.inputs[0]==self._records[demand].item
                    and self.organization_outcome(run.owner,run.ref)=='fulfilled'):
                    key,member=pending[0];done[key]=(member,tx.event.ref)
                    if len(done)==len(self._records[demand].obligations):
                        # Participant execution completion, independent of the
                        # observer's later assessment. Retain the activation
                        # for audit and avoid revisiting completed executions.
                        self._closure_active.pop(demand,None)
                    break
        changed=list(tx.memories)
        changed_refs=[r.ref for r in changed]
        for r in getattr(tx,'extra',()):
            if type(r) is CompositionRevision:changed_refs.append(r.ref)
        if changed_refs:self._invalidate_closure(changed_refs,'lower organization revision changed')
        withdrawn=getattr(c,'source',None) if type(c).__name__=='WithdrawEvidence' else None
        if withdrawn is not None:
            self._invalidate_closure((withdrawn,),'support evidence withdrawn')
        if tx.event.corrects is not None:
            self._invalidate_closure((tx.event.corrects,),'origin corrected')
        for before in prior_states:
            if before is not None and self.organization_state(before.owner,before.terms.identity)!=before:
                self._invalidate_closure((before.ref,),'shared membership, consent or rule changed')
        if getattr(c,'operator',None) in ('withdraw','restrict'):
            for ref in self._closure_native_index.get(c.actor,()):
                claim=self._closure_claims[ref]
                b=self._records[self._records[self._records[claim.plan].demand].binding]
                if b.owner==c.actor and not self._binding_live(b):self._invalidate_closure((b.ref,),'retained native capacity or material unavailable')
        if clearance_before=='cleared_in_scope' and self.clearance_monitor.status!='cleared_in_scope':
            for r in self._closure_native_index.get(self.clearance_monitor.actor,()):
                b=self._records[self._records[self._records[self._closure_claims[r].plan].demand].binding]
                self._invalidate_closure((b.ref,),'supporting individual clearance reopened')

    def closure_report(self):
        from .shell_assessment import reftext
        rows=[]
        for r in self._closure_claims.values():
            reason=self._closure_invalid.get(r.ref)
            rows.append({'claim':reftext(r.ref),'depth':r.depth,'historical_status':r.status,
                'current_status':'invalidated' if reason else r.status,'reason':reason,
                'predicates':dict(r.predicates),'duties':len(r.duties),'root':reftext(r.root)})
        return {'schema':'r20-closure-report-v1','claims':rows,'invalidation_visits':self.closure_invalidation_visits,
            'scope':'finite consent/obligation grammar; shared custody succession, not successor individual manufacturing competence'}

    def checkpoint(self):
        from .codec import dumps
        return dumps(ClosureCheckpoint('hle-r20-v1',super()._checkpoint_value(),CLOSURE_SEAL))

    @classmethod
    def restore(cls,text):
        from .codec import loads
        cp=loads(text)
        if type(cp) is not ClosureCheckpoint or cp.schema!='hle-r20-v1' or cp.seal!=CLOSURE_SEAL:
            raise ValueError('unsupported R20 checkpoint')
        if cp.base.schema!='hle-r19-v1':raise ValueError('wrong R19 base')
        from .clearance import CLEARANCE_SEAL
        if cp.base.seal!=CLEARANCE_SEAL:raise ValueError('R19 seal mismatch')
        return cls._restore_checkpoint(cp.base.base)

    @classmethod
    def import_r19(cls,text):return super().restore(text)
