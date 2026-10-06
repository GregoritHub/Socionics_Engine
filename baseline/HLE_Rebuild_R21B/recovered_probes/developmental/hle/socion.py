"""Independently adapting participants over AssessedWorld's single journal.

PlanTurn is a journaled deterministic policy decision, followed by a normal paid
R2/R3/R4 operation. Partial jobs and pending decisions are separately resumable.
No policy receives Truth, global history, other private memories or reports.
"""
from dataclasses import replace
from .assessment import AssessedWorld
from .contracts import (Cause, EvidenceStatus as E, Kind, MemoryRevision, Moment,
    Ref, ResourceAmount, WorkRecord, WorkStatus, WorldEvent)
from .crux import Polarity, Perspective
from .memory_records import MemoryCommand
from .metabolism_records import (Account, Application, MetabolicCommand,
    ProcessingState, RoutePlan)
from .model_a import element_at, position_of
from .processing import _route_geometry, route_active
from .relations import landing_position
from .socion_records import (AddGoal, AgentState, AgentView, AssessDyads, CloseRound, ConfigureAgent,
    DeclareDyad, Dyad, DyadReport, GoalResult, Notice, OpenRound, PlanTurn, RECEIVE,
    ReceiveCommand, Reception, RoundResult, RoundStart, SOCION, SocionCheckpoint,
    SocionTransaction)
from .socion_policy import binding_key, decide, item_key
from .world import amounts, ref_order
from .world_records import Attempt, ENERGY, Message, SEND, TIME, Wallet


def reception_plan(profile, state, notice, policy):
    sender=notice.sender_type if policy.typed_routing else "ile"
    receiver=profile.tim if policy.typed_routing else "ile"
    source=position_of(sender,notice.element)
    landing=landing_position(sender,source,receiver)
    target=element_at(receiver,landing)
    path,positions,seat,at,units,price=_route_geometry(receiver,state.active,target,
        Polarity.ACCUMULATION,policy.positional_prices)
    return source,landing,RoutePlan(profile.tim,receiver,path,positions,seat,at,units,price)


class SocionWorld(AssessedWorld):
    def __init__(self,config,profiles,policy,agents):
        if len(agents)!=len(config.actors) or {a.owner for a in agents}!=set(config.actors):
            raise ValueError("one explicit policy per participant required")
        self.agents=agents
        self._agent_policies={a.owner:a for a in agents}
        self._agent_states={a:AgentState(Ref(Kind.CURSOR,"socion:"+a.key+":"+str(a.revision),1),a)
                            for a in config.actors}
        self._notices={a:[] for a in config.actors}
        self._notice_by_observation={}
        self._receptions={}
        self._completed_reception={}
        self._receiving={}
        self._goal_keys=set()
        self._goal_results={}
        self._goals_by_item={}
        self._spent={a:0 for a in config.actors}
        self._dyads,self._round_starts,self._round_results,self._dyad_reports={},{},{},{}
        self._dyad_rounds,self._dyad_dependents={},{}
        self._dyad_dirty,self._dyad_open=set(),set()
        self.dyad_visits=0
        super().__init__(config,profiles,policy)
        self._records[SOCION]=SOCION; self._records[RECEIVE]=RECEIVE
        for state in self._agent_states.values():
            self._records[state.ref]=state;self._origins[state.ref]=self._journal[0].event.ref
            self._known[state.owner].update((state.ref,SOCION,RECEIVE))

    def agent_state(self,actor):
        if actor not in self._actors: raise ValueError("unknown actor")
        return self._agent_states[actor]

    def agent_view(self,actor):
        s=self.agent_state(actor)
        notices=self._notices[actor]
        n=notices[s.cursor] if s.cursor<len(notices) else None
        item=s.item if s.pending is not None or s.phase not in ("idle","await") else (
            n.claim.subject if n else s.goal.item if s.goal else s.goals[0].item if s.goals else None)
        memory=None if item is None else self.memory_head(actor,item_key(item))
        lesson=None if s.lesson is None else self.read_revision(actor,s.lesson)
        binding=None if item is None else self.binding_head(actor,binding_key(item))
        lb=self.binding_head(actor,"socion:lesson")
        result=status=None;observations=()
        if s.pending is not None:
            tx=self._commands.get(s.pending.command_id)
            if tx is not None:
                status=tx.event.outcome
                observations=tuple(o for o in tx.observations if o.observer==actor)
                if type(s.pending) is MemoryCommand:
                    job=self.memory_job(actor,s.pending.task_id)
                    result=job.result or (tx.memories[-1].ref if tx.memories else None)
                elif type(s.pending) is MetabolicCommand:
                    result=self.processing_job(actor,s.pending.task_id).result
                elif type(s.pending) is ReceiveCommand:
                    result=self._receptions[(actor,s.pending.task_id)].ref
                elif tx.messages: result=tx.messages[0].ref
        account=None if s.account is None else self.processing_record(actor,s.account)
        app=None if s.application is None else self.processing_record(actor,s.application)
        wallet=self._wallets[actor]
        return AgentView(s,self._agent_policies[actor],self.config.context,self.now,n,memory,lesson,
            None if binding is None else binding.ref,None if lb is None else lb.ref,
            result,account,app,observations,status,wallet.energy,wallet.time)

    def ready(self,actor):
        s=self.agent_state(actor)
        if s.phase=="blocked":return False
        return s.pending is not None or s.goal is not None or bool(s.goals) or s.cursor<len(self._notices[actor])

    def advance(self,actor):
        """One decision OR one operation; no scripted response is supplied here."""
        s=self.agent_state(actor)
        if s.pending is not None and s.pending.command_id not in self._commands:
            return self.execute(s.pending)
        return self.execute(PlanTurn(f"turn:{actor.key}:{s.ref.revision}",actor))

    def _receive(self,cmd,when,event_ref):
        n=self._notice_by_observation.get((cmd.actor,cmd.observation))
        if n is None or n.sender is None: raise ValueError("own delivered message required")
        state=self.processing_state(cmd.actor)
        if state.busy is not None or state.perspective!=Perspective.I:
            raise ValueError("reception requires an available personal processing state")
        old=self._receptions.get((cmd.actor,cmd.task_id))
        if self._receiving.get(cmd.actor,cmd.task_id)!=cmd.task_id:
            raise ValueError("another reception is unfinished")
        if old is not None and (old.command.observation!=cmd.observation or old.outcome==WorkStatus.COMPLETED):
            raise ValueError("changed or terminal reception")
        if old is None:
            source,landing,plan=reception_plan(self._profiles[cmd.actor],state,n,self.policy)
            old=Reception(Ref(Kind.EVIDENCE,"reception:"+cmd.actor.key+":"+cmd.task_id,1),cmd.actor,
                cmd,n.source,n.sender,source,landing,plan,0,WorkStatus.PENDING)
        remaining=old.plan.required-old.completed
        wallet=self._wallets[cmd.actor]
        spent=min(remaining,wallet.energy,wallet.time,cmd.work_limit)
        status=WorkStatus.COMPLETED if spent==remaining else WorkStatus.PARTIAL if spent else WorkStatus.DEFERRED
        after=Wallet(cmd.actor,wallet.energy-spent,wallet.time-spent)
        work=WorkRecord(Ref(Kind.WORK,f"work:{when.tick}:0",1),cmd.actor,RECEIVE,
            amounts(wallet),(),(ResourceAmount(ENERGY,spent),ResourceAmount(TIME,spent)),amounts(after),
            remaining,spent,status,"paid Model A reception; delivery does not imply interpretation")
        ref=replace(old.ref,revision=1 if (cmd.actor,cmd.task_id) not in self._receptions else old.ref.revision+1)
        job=replace(old,ref=ref,completed=old.completed+spent,outcome=status)
        active=route_active(old.plan,job.completed)
        newstate=replace(state,ref=replace(state.ref,revision=state.ref.revision+1),active=active)
        return (job,newstate),(work,),(Cause(self._origins[cmd.observation],SOCION),),status

    def execute(self,cmd):
        if type(cmd) not in (AddGoal,ConfigureAgent,PlanTurn,ReceiveCommand,DeclareDyad,OpenRound,CloseRound,AssessDyads):
            if type(cmd) is MetabolicCommand and cmd.actor in self._receiving and cmd.command_id not in self._commands:
                raise ValueError("reception must finish before another processing operation")
            return super().execute(cmd)
        if not cmd.command_id.strip():raise ValueError("blank command ID")
        old=self._commands.get(cmd.command_id)
        if old is not None:
            if old.command!=cmd:raise ValueError("command ID reused")
            return old.event
        when=Moment(len(self._journal),0);event_ref=Ref(Kind.EVENT,f"event:{when.tick}",1)
        extra=works=causes=actors=()
        status=WorkStatus.COMPLETED
        if type(cmd) is ConfigureAgent:
            if cmd.policy.owner not in self._actors or not cmd.reason.strip():raise ValueError("explicit policy intervention required")
            state=self.agent_state(cmd.policy.owner)
            if state.pending is not None or state.goal is not None:raise ValueError("configure an idle actor between goals")
            actors=(cmd.policy.owner,)
        elif type(cmd) is AddGoal:
            g=cmd.goal
            if g.actor not in self._actors or g.partner not in self._actors or g.item not in self._items or g.key in self._goal_keys:
                raise ValueError("unknown or repeated goal")
            s=self.agent_state(g.actor)
            extra=(replace(s,ref=replace(s.ref,revision=s.ref.revision+1),goals=s.goals+(g,)),)
            actors=(g.actor,)
        elif type(cmd) is PlanTurn:
            v=self.agent_view(cmd.actor)
            state,result=decide(v,cmd.command_id+":work")
            extra=(state,)+(() if result is None else (result,))
            actors=(cmd.actor,)
            bases=(v.state.ref,)+(() if v.notice is None else (v.notice.observation,))
            if v.state.pending is not None and v.state.pending.command_id in self._commands:
                bases+=(self._commands[v.state.pending.command_id].event.ref,)
            causes=tuple(sorted({Cause(r if r.kind==Kind.EVENT else self._origins[r],SOCION) for r in bases},
                key=lambda c:ref_order(c.event)))
        elif type(cmd) is ReceiveCommand:
            extra,works,causes,status=self._receive(cmd,when,event_ref);actors=(cmd.actor,)
        else:
            from .socion_assessment import assess_command
            extra=assess_command(self,cmd)
        event=WorldEvent(event_ref,when,actors,(),"r6."+type(cmd).__name__,self.config.context,
            (),causes,tuple(w.ref for w in works),status,
            "local policy dispatch or paid reception" if actors else "evaluator-only dyadic test; no delivery")
        self._commit(SocionTransaction(cmd,event,works,extra=extra))
        return event

    def _commit(self,tx):
        extra=tx.extra if type(tx) is SocionTransaction else ()
        if len({r.ref for r in extra})!=len(extra) or any(r.ref in self._records for r in extra):
            raise ValueError("duplicate social record")
        # Capture emission coordinates before later receiver/sender activation changes.
        emissions={m.ref:(self._profiles[m.sender].tim,self.processing_state(m.sender).active)
            for m in tx.messages}
        super()._commit(tx)
        for work in tx.works:
            self._spent[work.owner]+=sum(r.amount for r in work.charged if r.unit==ENERGY)
        for record in extra:
            self._records[record.ref]=record;self._origins[record.ref]=tx.event.ref
            if type(record) is AgentState:
                self._agent_states[record.owner]=record;self._known[record.owner].add(record.ref)
            elif type(record) is Reception:
                self._receptions[(record.owner,record.command.task_id)]=record
                self._known[record.owner].add(record.ref)
                if record.outcome==WorkStatus.COMPLETED:
                    self._completed_reception[(record.owner,record.command.observation)]=record.ref
                    self._receiving.pop(record.owner,None)
                else:self._receiving[record.owner]=record.command.task_id
            elif type(record) is ProcessingState:
                self._processing_states[record.owner]=record;self._known[record.owner].add(record.ref)
                self._processing_changes[-1]=(tx.event.ref,(record.owner,))
            elif type(record) is GoalResult:
                self._goal_results[record.ref]=record
                self._goals_by_item.setdefault(record.goal.item,[]).append(record)
                self._known[record.owner].add(record.ref)
            elif type(record) is Dyad:
                self._dyads[record.ref]=record
                self._dyad_dependents.setdefault(record.request.item,set()).add(record.ref)
                self._dyad_rounds[record.ref]=[];self._dyad_dirty.add(record.ref)
            elif type(record) is RoundStart:
                self._round_starts[record.ref]=record;self._dyad_open.add(record.study)
                self._dyad_dirty.add(record.study)
            elif type(record) is RoundResult:
                self._round_results[record.ref]=record;self._dyad_open.remove(record.study)
                self._dyad_rounds[record.study].append(record.ref);self._dyad_dirty.add(record.study)
            elif type(record) is DyadReport:
                self._dyad_reports[record.study]=record;self._dyad_dirty.discard(record.study);self.dyad_visits+=1
        if type(tx.command) is AddGoal:self._goal_keys.add(tx.command.goal.key)
        if type(tx.command) is ConfigureAgent:self._agent_policies[tx.command.policy.owner]=tx.command.policy
        for o in tx.observations:
            message=self._records.get(o.source)
            sender=message.sender if type(message) is Message else None
            st,element=emissions.get(o.source,("ile","ne"))
            reply=next((p.object for p in o.content if p.relation=="reply_to" and type(p.object) is Ref),None)
            if sender is not None:
                queries=tuple(p for p in o.content if p.relation=="query_owner")
                owners=tuple(p for p in o.content if p.relation=="owned_by")
                replies=tuple(p for p in o.content if p.relation=="reply_to")
                valid_query=len(queries)==1 and len(o.content)==1 and queries[0].object==sender
                valid_report=(len(owners)==1 and not queries and len(replies)<=1
                    and len(o.content)==len(owners)+len(replies)
                    and (not replies or (replies[0].subject==owners[0].subject and reply is not None)))
                if not (valid_query or valid_report):continue
            for p in o.content:
                if p.context!=self.config.context or p.subject not in self._items:continue
                if p.relation=="query_owner" and sender is not None and p.object==sender:
                    kind="query"
                elif p.relation=="owned_by" and p.object in self._actors:
                    # Apply and controller inspections already retain their own consequences.
                    pending=self._agent_states[o.observer].pending
                    if sender is None and pending is not None and tx.command==pending:continue
                    kind="report" if sender else "direct"
                else:continue
                n=Notice(o.ref,o.source,sender,kind,p,reply,st,element)
                self._notices[o.observer].append(n)
                if sender:self._notice_by_observation[(o.observer,o.ref)]=n
        # Completed return snapshots are immutable. Current reports also depend on
        # the dyad's item; unrelated study/history work never enters this path.
        items={p.subject for c in tx.event.changes for p in (c.before or c.after,) if p.relation=="owned_by"}
        items.update(r.goal.item for r in extra if type(r) is GoalResult)
        for item in items:self._dyad_dirty.update(self._dyad_dependents.get(item,()))

    def pending_dyads(self):return tuple(sorted(self._dyad_dirty,key=ref_order))
    def dyad_report(self,ref):return self._dyad_reports.get(ref)
    def dyad_report_is_current(self,report):
        return self._dyad_reports.get(report.study)==report and report.study not in self._dyad_dirty

    def checkpoint(self):
        from .codec import dumps
        return dumps(SocionCheckpoint("hle-r6-v1",self.config,self.profiles,self.policy,self.agents,tuple(self._journal)))

    @classmethod
    def restore(cls,text):
        from .codec import loads
        cp=loads(text)
        if type(cp) is not SocionCheckpoint or cp.schema!="hle-r6-v1" or not cp.journal:
            raise ValueError("unsupported or empty Socion checkpoint")
        w=cls(cp.config,cp.profiles,cp.policy,cp.agents)
        if cp.journal[0]!=w._journal[0]:raise ValueError("genesis mismatch")
        for entry in cp.journal[1:]:
            if entry.command is None or entry.command.command_id in w._commands:raise ValueError("missing/duplicate command")
            w.execute(entry.command)
            if w._journal[-1]!=entry:raise ValueError("Socion replay mismatch")
        return w
