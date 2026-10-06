"""Versioned recursive organization over the unchanged R6 simulation journal."""
from bisect import insort
from dataclasses import replace
from .contracts import (Cause, ClaimStatus, Kind, MemoryRevision, Moment, Ref,
    ResourceAmount, WorkRecord, WorkStatus, WorldEvent)
from .memory import in_scope
from .memory_records import RecallHit
from .metabolism_records import (Account, Application, Capability, EmbodyDraft,
    MetabolicTransaction, TheorizeDraft)
from .socion import SocionWorld
from .world import amounts, memory_key, ref_order
from .world_records import ENERGY, TIME, Wallet
from .composition_records import (AssessCompositions, COMPOSITION, FOLD, UNFOLD,
    CompositionCheckpoint, CompositionCommand, CompositionJob, CompositionReport,
    CompositionRevision, CompositionTest, CompositionTransaction,
    DeclareCompositionTest, Edge, FoldDraft, UnfoldDraft, UnfoldResult, UseWitness)


def named(ref): return ref.kind, ref.key


def leaf_hits(memory, context, at):
    return tuple(i for i,p in enumerate(memory.content)
                 if p.context == context and in_scope(p.scope, at))


class ComposedWorld(SocionWorld):
    def __init__(self, config, profiles, policy, agents):
        self._composition_heads, self._composition_jobs = {}, {}
        self._composition_tests, self._composition_reports = {}, {}
        self._composition_dirty, self._composition_due = set(), []
        self._parents, self._view_tests, self._key_contexts, self._fact_tests = {}, {}, {}, {}
        self._accesses, self._uses, self._path_units = {}, {}, {}
        self._account_units, self._application_units = {}, {}
        self.composition_visits = self.invalidation_visits = 0
        super().__init__(config, profiles, policy, agents)
        for ref in (COMPOSITION,FOLD,UNFOLD): self._records[ref] = ref
        for known in self._known.values(): known.update((COMPOSITION,FOLD,UNFOLD))

    def composition_head(self, actor, key):
        if actor not in self._actors: raise ValueError("unknown owner")
        return self._composition_heads.get("composition:" + memory_key(actor,key))

    def composition_record(self, actor, ref):
        return self._owned(actor,ref,(CompositionRevision,UnfoldResult))

    def composition_job(self, actor, key):
        if actor not in self._actors: raise ValueError("unknown owner")
        return self._composition_jobs.get((actor,key))

    def unfold_records(self, actor, ref):
        """Diagnostic export of exactly the completed result; no implicit expansion."""
        r = self._owned(actor,ref,(UnfoldResult,))
        return tuple(self._owned(actor,x,(CompositionRevision,MemoryRevision,Capability))
                     for x in r.nodes + r.capabilities)

    def _inputs(self, actor, payload):
        if type(payload) is TheorizeDraft and type(self._records.get(payload.recall)) is UnfoldResult:
            recall = self._owned(actor,payload.recall,(UnfoldResult,))
            if (recall.query.context != self.config.context or payload.item not in self._items
                    or payload.recipient not in self._actors or payload.recipient == actor):
                raise ValueError("ownership use requires completed world-context access and a valid demand")
            memories = tuple(self.read_revision(actor,h.memory) for h in recall.hits)
            caps = {r:self._owned(actor,r,(Capability,)) for m in memories for r in m.capabilities}
            basis = (recall.ref,) + tuple(m.ref for m in memories) + tuple(caps)
            return (recall,memories,caps),basis,1+sum(len(h.proposition_indexes) for h in recall.hits)
        return super()._inputs(actor,payload)

    def _parts(self, node, context):
        return tuple(p for p in node.parts if context is None or p.context == context)

    def _node_cost(self, record, context):
        if type(record) is CompositionRevision: return 1 + len(self._parts(record,context))
        return 1 + len(record.content) + len(record.capabilities)

    def _validate_composition(self, cmd):
        actor,p = cmd.actor,cmd.payload
        if actor not in self._actors: raise ValueError("unknown owner")
        if type(p) is FoldDraft:
            for part in p.parts:
                self._owned(actor,part.target,(CompositionRevision,MemoryRevision))
                if part.context not in self._known[actor]: raise ValueError("inaccessible context")
            if p.expected is not None:
                old = self._owned(actor,p.expected,(CompositionRevision,))
                if old.ref.key != "composition:" + memory_key(actor,p.key):
                    raise ValueError("wrong named predecessor")
        else:
            self._owned(actor,p.root,(CompositionRevision,))
            if p.at > self.now or p.context is not None and p.context not in self._known[actor]:
                raise ValueError("future query or inaccessible context")
        old = self.composition_job(actor,cmd.task_id)
        if old is not None:
            if old.outcome in (WorkStatus.COMPLETED,WorkStatus.FAILED) or old.command.payload != p:
                raise ValueError("terminal job or changed continuation")
            return old
        return CompositionJob(cmd,frontier=() if type(p) is FoldDraft else (p.root,))

    def _unfold_step(self, job):
        q = job.command.payload
        ref,*remaining = job.frontier
        node = self._owned(job.command.actor,ref,(CompositionRevision,MemoryRevision))
        nodes,edges,hits,caps = job.nodes+(ref,),job.edges,job.hits,job.capabilities
        if type(node) is CompositionRevision:
            parts = self._parts(node,q.context)
            edges += tuple(Edge(ref,p) for p in parts)
            enqueued = set(nodes) | set(remaining)
            for part in parts:
                if part.target not in enqueued:
                    remaining.append(part.target); enqueued.add(part.target)
        else:
            caps = tuple(dict.fromkeys(caps + node.capabilities))
            if q.context is not None:
                indexes = leaf_hits(node,q.context,q.at)
                if indexes or node.capabilities: hits += (RecallHit(ref,indexes),)
        return replace(job,node_paid=0,frontier=tuple(remaining),nodes=nodes,edges=edges,hits=hits,capabilities=caps)

    def execute(self, cmd):
        if type(cmd) not in (CompositionCommand,DeclareCompositionTest,AssessCompositions):
            return super().execute(cmd)
        prior = self._commands.get(cmd.command_id)
        if prior is not None:
            if prior.command != cmd: raise ValueError("command ID reused")
            return prior.event
        when=Moment(len(self._journal),0); event_ref=Ref(Kind.EVENT,f"event:{when.tick}",1)
        extra=works=causes=actors=observations=(); job=None; status=WorkStatus.COMPLETED
        if type(cmd) is CompositionCommand:
            job=self._validate_composition(cmd); p=cmd.payload; actor=cmd.actor
            actors=(actor,); op=FOLD if type(p) is FoldDraft else UNFOLD
            basis=tuple(x.target for x in p.parts)+(() if p.expected is None else (p.expected,)) if type(p) is FoldDraft else (p.root,)
            causes=tuple(sorted({Cause(self._origins[r],COMPOSITION) for r in basis},key=lambda c:ref_order(c.event)))
            wallet=self._wallets[actor]; budget=min(cmd.work_limit,wallet.energy,wallet.time)
            spent=0; status=WorkStatus.PARTIAL; reason="paid progress retained"
            if type(p) is FoldDraft:
                remaining=1+len(p.parts)-job.completed; paid=min(budget,remaining)
                spent=paid; job=replace(job,completed=job.completed+paid)
                if paid == remaining:
                    head=self.composition_head(actor,p.key)
                    if (None if head is None else head.ref) != p.expected:
                        status=WorkStatus.FAILED; reason="expected organization revision changed after paid work"
                    else:
                        ref=Ref(Kind.MEMORY,"composition:"+memory_key(actor,p.key),1 if head is None else head.ref.revision+1)
                        node=CompositionRevision(ref,actor,when,p.parts,p.expected)
                        extra=(node,); job=replace(job,result=ref); status=WorkStatus.COMPLETED
            else:
                # Iterative traversal; no recursion/depth cap and no expansion of unpaid nodes.
                while job.frontier and budget:
                    node=self._owned(actor,job.frontier[0],(CompositionRevision,MemoryRevision))
                    required=self._node_cost(node,p.context)-job.node_paid
                    paid=min(required,budget); spent+=paid; budget-=paid
                    job=replace(job,completed=job.completed+paid,node_paid=job.node_paid+paid)
                    if paid == required: job=self._unfold_step(job)
                remaining=(self._node_cost(self._records[job.frontier[0]],p.context)-job.node_paid) if job.frontier else 0
                if not job.frontier:
                    result=UnfoldResult(Ref(Kind.EVIDENCE,"unfold:"+memory_key(actor,cmd.task_id),1),actor,p,
                        job.nodes,job.edges,job.hits,job.capabilities,job.completed)
                    extra=(result,); job=replace(job,result=result.ref); status=WorkStatus.COMPLETED
            if status==WorkStatus.PARTIAL and job.completed==0: status=WorkStatus.DEFERRED
            if status==WorkStatus.COMPLETED: reason="exact addressed operation completed; accuracy remains separate"
            after=Wallet(actor,wallet.energy-spent,wallet.time-spent)
            # For traversal, required counts this funded slice plus the outstanding current node.
            required=spent if status in (WorkStatus.COMPLETED,WorkStatus.FAILED) else spent+max(1,remaining if type(p) is UnfoldDraft else 1+len(p.parts)-job.completed)
            work=WorkRecord(Ref(Kind.WORK,f"work:{when.tick}:0",1),actor,op,amounts(wallet),(),
                (ResourceAmount(ENERGY,spent),ResourceAmount(TIME,spent)),amounts(after),required,spent,
                status if spent or status==WorkStatus.FAILED else WorkStatus.DEFERRED,reason)
            works=(work,); job=replace(job,outcome=status)
            observations=(self._observation(actor,event_ref,when,(self._prop(event_ref,"outcome",status.value,when),),
                "private composition receipt","operation outcome; no evaluator conclusion"),)
        else:
            from .composition_assessment import assess, declaration
            if type(cmd) is DeclareCompositionTest: extra=(declaration(self,cmd,when),)
            else: extra=tuple(assess(self,self._composition_tests[r],when) for r in self.pending_compositions()[:cmd.limit])
            reason="evaluator-only composition assessment; no participant delivery"
        event=WorldEvent(event_ref,when,actors,(),"r7."+type(cmd).__name__,self.config.context,(),causes,
            tuple(w.ref for w in works),status,reason)
        self._commit(CompositionTransaction(cmd,event,works,observations,extra=extra,job=job))
        return event

    def _watch(self, ref, context):
        self._key_contexts.setdefault(named(ref),set()).add(context)
        return named(ref)+(context,)

    def _invalidate(self, refs):
        todo=list(dict.fromkeys(named(r)+(c,) for r in refs for c in self._key_contexts.get(named(r),())))
        visited=set()
        while todo:
            key=todo.pop()
            if key in visited: continue
            visited.add(key); self.invalidation_visits+=1
            self._composition_dirty.update(self._view_tests.get(key,()))
            todo.extend(self._parents.get(key,()))

    def _commit(self, tx):
        extra=tx.extra if type(tx) is CompositionTransaction else ()
        if len({r.ref for r in extra}) != len(extra) or any(r.ref in self._records for r in extra):
            raise ValueError("duplicate composition record")
        super()._commit(tx)
        changed=[m.ref for m in tx.memories]
        for r in extra:
            self._records[r.ref]=r; self._origins[r.ref]=tx.event.ref
            if type(r) is CompositionRevision:
                self._composition_heads[r.ref.key]=r; self._known[r.owner].add(r.ref); changed.append(r.ref)
                for p in r.parts:
                    parent=self._watch(r.ref,p.context)
                    self._parents.setdefault(self._watch(p.target,p.context),set()).add(parent)
            elif type(r) is UnfoldResult:
                self._known[r.owner].add(r.ref)
                self._accesses.setdefault((r.query.root,r.query.context),[]).append(r.ref)
                self._composition_dirty.update(self._view_tests.get(named(r.query.root)+(r.query.context,),()))
            elif type(r) is CompositionTest:
                self._composition_tests[r.ref]=r; self._composition_dirty.add(r.ref)
                s=r.request; self._view_tests.setdefault(self._watch(s.root,s.context),set()).add(r.ref)
                from .composition_assessment import snapshot
                nodes,_,_,_=snapshot(self,s.root,s.context,self.now)
                for ref in nodes:
                    record=self._records[ref]
                    if type(record) is MemoryRevision:
                        for p in record.content:
                            if p.context != s.context: continue
                            self._fact_tests.setdefault((p.subject,p.relation,p.context),set()).add(r.ref)
                            for at in (p.scope.start,p.scope.end):
                                if at is not None and at>self.now:
                                    insort(self._composition_due,(-at.tick,-at.order,ref_order(r.ref),r.ref))
            else:
                self._composition_reports[r.test]=r; self._composition_dirty.discard(r.test); self.composition_visits+=1
        if type(tx) is CompositionTransaction and tx.job is not None:
            self._composition_jobs[(tx.command.actor,tx.command.task_id)]=tx.job
        if type(tx) is MetabolicTransaction:
            key=(tx.command.actor,tx.command.task_id)
            self._path_units[key]=self._path_units.get(key,0)+sum(w.completed_units for w in tx.works)
            for r in tx.extra:
                if type(r) is Account: self._account_units[r.ref]=self._path_units[key]
                if type(r) is Application: self._application_units[r.ref]=self._path_units[key]
            if tx.memories and type(tx.command.payload) is EmbodyDraft:
                app=self._records[tx.command.payload.application]; account=self._records[app.account]
                access=self._records[account.recall]
                if type(access) is UnfoldResult:
                    use=UseWitness(access.ref,account.ref,app.ref,tx.memories[0].ref,
                        access.units+self._account_units[account.ref]+self._application_units[app.ref]+self._path_units[key])
                    view=(access.query.root,access.query.context)
                    self._uses.setdefault(view,[]).append(use)
                    self._composition_dirty.update(self._view_tests.get(named(view[0])+(view[1],),()))
        self._invalidate(changed)
        for c in tx.event.changes:
            p=c.before or c.after
            self._composition_dirty.update(self._fact_tests.get((p.subject,p.relation,p.context),()))
        while self._composition_due and (-self._composition_due[-1][0],-self._composition_due[-1][1]) <= (self.now.tick,self.now.order):
            self._composition_dirty.add(self._composition_due.pop()[3])

    def pending_compositions(self): return tuple(sorted(self._composition_dirty,key=ref_order))
    def composition_report(self, test): return self._composition_reports.get(test)
    def composition_report_is_current(self, report):
        return self._composition_reports.get(report.test)==report and report.test not in self._composition_dirty

    def checkpoint(self):
        from .codec import dumps
        return dumps(CompositionCheckpoint("hle-r7-v1",self.config,self.profiles,self.policy,self.agents,tuple(self._journal)))

    @classmethod
    def restore(cls, text):
        from .codec import loads
        cp=loads(text)
        if type(cp) is not CompositionCheckpoint or cp.schema!="hle-r7-v1" or not cp.journal:
            raise ValueError("unsupported or empty composition checkpoint")
        w=cls(cp.config,cp.profiles,cp.policy,cp.agents)
        if cp.journal[0]!=w._journal[0]: raise ValueError("genesis mismatch")
        for entry in cp.journal[1:]:
            if entry.command is None or entry.command.command_id in w._commands: raise ValueError("missing/duplicate command")
            w.execute(entry.command)
            if w._journal[-1]!=entry: raise ValueError("composition replay mismatch")
        return w
