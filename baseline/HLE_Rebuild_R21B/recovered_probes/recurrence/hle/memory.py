"""Relational memory over the one R2 event/record store (F01--F10).

The algorithms and prices are declared choices in docs/Memory_R3.md. Participant
helpers receive immutable permitted inputs, never the evaluator interface.
"""
from dataclasses import replace
from .cards import CARDS
from .contracts import (Cause, Change, ClaimStatus, CueBinding, CursorState, Kind,
    MemoryRevision, Observation, ParticipantInput, Ref, ResourceAmount,
    WorkRecord, WorkStatus, WorldEvent, Moment)
from .memory_records import (AckDraft, BindDraft, ContextDraft, CursorDraft,
    InboxState, LINKED, MEMORY_RULE, MemoryCheckpoint, MemoryCommand,
    MemoryContext, MemoryJob, MemoryTransaction, Navigation, OPERATIONS,
    RecallHit, RecallQuery, RecallResult, Visit, WriteDraft, operation, write_cost)
from .world import World, amounts, memory_key, ref_order
from .world_records import ENERGY, TIME, INSPECT, TRANSFER, Wallet
from .contracts import ActionRequest


def in_scope(scope, at):
    return scope.start <= at and (scope.end is None or at < scope.end)


class RelationalWorld(World):
    """Single journal; additional indexes contain references to its records."""

    def __init__(self, config):
        self._binding_heads, self._buckets = {}, {}
        self._navigation, self._inbox_state, self._memory_jobs = {}, {}, {}
        super().__init__(config)
        for cue in CARDS:
            self._records[cue.ref] = cue
        for ref in OPERATIONS + (MEMORY_RULE,):
            self._records[ref] = ref
        for known in self._known.values():
            known.update(c.ref for c in CARDS)
            known.update(OPERATIONS + (MEMORY_RULE,))

    def _owned(self, actor, ref, types):
        value = self._records.get(ref)
        owner = value.observer if type(value) is Observation else getattr(value, "owner", None)
        if type(value) not in types or owner != actor:
            raise ValueError("record is unresolved or belongs to another participant")
        return value

    def read_revision(self, owner, ref):
        return self._owned(owner, ref, (MemoryRevision,))

    def resolve_binding(self, owner, binding):
        return self._owned(owner, binding, (CueBinding,))

    def recall_result(self, owner, ref):
        return self._owned(owner, ref, (RecallResult,))

    def memory_head(self, owner, key):
        if owner not in self._actors: raise ValueError("unknown owner")
        return self._memory_heads[owner].get(memory_key(owner, key))

    def binding_head(self, owner, key):
        if owner not in self._actors: raise ValueError("unknown owner")
        return self._binding_heads.get((owner, memory_key(owner, key)))

    def navigation(self, owner):
        if owner not in self._actors: raise ValueError("unknown owner")
        return self._navigation.get(owner)

    def memory_job(self, owner, key):
        if owner not in self._actors: raise ValueError("unknown owner")
        return self._memory_jobs.get((owner, key))

    def select_input(self, actor, *, memories=(), after=None):
        """Only requested owned revisions and this actor's inbox suffix."""
        if actor not in self._actors:
            raise ValueError("unknown actor")
        if after is None:
            cursor = self._inbox_state.get(actor)
            after = 0 if cursor is None else cursor.after
        if type(after) is not int or not 0 <= after <= len(self._inboxes[actor]):
            raise ValueError("invalid inbox cursor")
        if type(memories) is not tuple or len(set(memories)) != len(memories):
            raise ValueError("unique memory addresses required")
        selected = tuple(self.read_revision(actor, ref) for ref in memories)
        inbox = self._inboxes[actor]
        return ParticipantInput(actor, self.now, tuple(inbox[after:]), selected,
                                amounts(self._wallets[actor]), ()), len(inbox)

    def _validate_memory(self, cmd):
        actor, p = cmd.actor, cmd.payload
        if actor not in self._actors: raise ValueError("unknown actor")
        evidence_types = (Observation, MemoryRevision, CueBinding, RecallResult,
                          Navigation, MemoryContext, InboxState)
        for ref in cmd.based_on: self._owned(actor, ref, evidence_types)
        known = self._known[actor]
        if type(p) is WriteDraft:
            for proposition in p.content:
                refs = (proposition.subject, proposition.context) + ((proposition.object,) if type(proposition.object) is Ref else ())
                if any(r not in known for r in refs):
                    raise ValueError("content contains an inaccessible reference")
            for ref in p.links: self.read_revision(actor, ref)
            if p.expected is not None:
                previous = self.read_revision(actor, p.expected)
                if previous.ref.key != memory_key(actor, p.key) or p.expected not in cmd.based_on:
                    raise ValueError("revision must cite the exact named predecessor")
            if not cmd.based_on:
                raise ValueError("retention needs explicit participant provenance")
        elif type(p) is BindDraft:
            if p.cue not in known or p.cue.kind != Kind.CUE or p.context not in known:
                raise ValueError("unknown cue or context")
            self.read_revision(actor, p.target)
            if p.target not in cmd.based_on:
                raise ValueError("binding must cite its target")
            if p.expected is not None:
                old = self.resolve_binding(actor, p.expected)
                if old.ref.key != memory_key(actor, p.key) or p.expected not in cmd.based_on:
                    raise ValueError("rebind must cite the exact named predecessor")
        elif type(p) is CursorDraft:
            if len(set(p.cues)) != len(p.cues) or any(r.kind != Kind.CUE or r not in known for r in p.cues):
                raise ValueError("unknown or duplicate cursor cue")
            if p.expected is not None:
                self._owned(actor, p.expected, (Navigation,))
                if p.expected not in cmd.based_on:
                    raise ValueError("cursor revision must cite its predecessor")
        elif type(p) is AckDraft:
            if p.through > len(self._inboxes[actor]):
                raise ValueError("cannot acknowledge an undelivered inbox position")
        elif type(p) is RecallQuery:
            if p.context not in known or any(r not in known for r in p.cues):
                raise ValueError("unknown cue or context")
            if p.at > self.now or p.subject is not None and p.subject not in known:
                raise ValueError("future recall or unknown referent")
        old = self._memory_jobs.get((actor, cmd.task_id))
        if old is not None:
            original = old.command
            if (old.outcome in (WorkStatus.COMPLETED, WorkStatus.FAILED)
                    or (original.actor, original.payload, original.based_on) != (actor, p, cmd.based_on)):
                raise ValueError("terminal job or changed continuation specification")
        return old

    def _plan_write(self, cmd, when):
        """Pure completion plan; head preconditions are checked after paid work."""
        actor, p = cmd.actor, cmd.payload
        memories, bindings, contexts, navigations, inboxes, changes = [], [], [], [], [], []
        if type(p) is WriteDraft:
            old = self.memory_head(actor, p.key)
            if (None if old is None else old.ref) != p.expected:
                return None
            ref = Ref(Kind.MEMORY, memory_key(actor, p.key), 1 if old is None else old.ref.revision + 1)
            memory = MemoryRevision(ref, actor, when, p.content, p.links,
                tuple(r for r in cmd.based_on if r.kind == Kind.OBSERVATION),
                tuple(r for r in cmd.based_on if r.kind == Kind.MEMORY), p.attitude, (), p.expected, p.reason)
            memories.append(memory)
            if old is not None:
                changes.append(Change(self._facts[(old.ref, "held_by", self.config.context)], None))
            changes.append(Change(None, self._prop(ref, "held_by", actor, when)))
        elif type(p) is BindDraft:
            old = self.binding_head(actor, p.key)
            if (None if old is None else old.ref) != p.expected: return None
            bindings.append(CueBinding(Ref(Kind.BINDING, memory_key(actor, p.key),
                1 if old is None else old.ref.revision + 1), actor, p.cue, p.context,
                p.target, p.scope, cmd.based_on))
        elif type(p) is ContextDraft:
            ref = Ref(Kind.CONTEXT, "memory-context:" + memory_key(actor, p.key), 1)
            if ref in self._records: return None
            contexts.append(MemoryContext(ref, actor, p.label))
        elif type(p) is CursorDraft:
            old = self._navigation.get(actor)
            if (None if old is None else old.ref) != p.expected: return None
            cursor = CursorState(Ref(Kind.CURSOR, "navigation:" + memory_key(actor, "cursor"),
                1 if old is None else old.ref.revision + 1), actor, p.cues, p.policy, cmd.based_on)
            navigations.append(Navigation(cursor, p.max_hops))
        elif type(p) is AckDraft:
            old = self._inbox_state.get(actor)
            if (0 if old is None else old.after) != p.expected: return None
            inboxes.append(InboxState(Ref(Kind.CURSOR, "inbox:" + memory_key(actor, "cursor"),
                1 if old is None else old.ref.revision + 1), actor, p.through))
        return tuple(memories), tuple(bindings), tuple(contexts), tuple(navigations), tuple(inboxes), tuple(changes)

    def _recall_step(self, job, when):
        """One funded operation, using only selected buckets/revisions."""
        actor, q = job.command.actor, job.command.payload
        if job.selected_at is None:
            bindings, frontier, enqueued = [], [], set()
            for cue in q.cues:
                for binding_ref in self._buckets.get((actor, cue, q.context), {}).values():
                    binding = self._records[binding_ref]
                    if in_scope(binding.scope, q.at):
                        bindings.append(binding.ref)
                        if binding.target not in enqueued:
                            enqueued.add(binding.target)
                            frontier.append(Visit(binding.target, None, 0))
            nav = self._navigation.get(actor)
            return replace(job, selected_at=when, bindings=tuple(bindings), frontier=tuple(frontier),
                navigation=None if nav is None else nav.ref,
                max_hops=0 if nav is None else nav.max_hops,
                completed_units=job.completed_units + 1)
        visit, *remaining = job.frontier
        memory = self._records[visit.memory]
        matching = tuple(i for i, p in enumerate(memory.content)
            if p.context == q.context and in_scope(p.scope, q.at)
            and (q.subject is None or p.subject == q.subject)
            and (q.relation is None or p.relation == q.relation))
        hits = job.hits + ((RecallHit(memory.ref, matching),) if matching else ())
        visited = job.visited + (visit,)
        enqueued = {v.memory for v in visited} | {v.memory for v in remaining}
        if visit.depth < job.max_hops:
            for link in memory.links:
                if link not in enqueued:
                    enqueued.add(link)
                    remaining.append(Visit(link, memory.ref, visit.depth + 1))
        truncated = bool(remaining) and len(visited) >= q.visit_limit
        return replace(job, completed_units=job.completed_units + 1, visited=visited,
                       hits=hits, frontier=() if truncated else tuple(remaining), truncated=truncated)

    def execute(self, cmd):
        if type(cmd) is not MemoryCommand:
            return super().execute(cmd)
        previous = self._commands.get(cmd.command_id)
        if previous is not None:
            if previous.command != cmd: raise ValueError("command ID reused with different input")
            return previous.event
        old = self._validate_memory(cmd)
        job = old or MemoryJob(cmd, 0, WorkStatus.PENDING)
        when = Moment(len(self._journal), 0)
        event_ref = Ref(Kind.EVENT, f"event:{when.tick}", 1)
        op = operation(cmd.payload)
        wallet = self._wallets[cmd.actor]
        works, recalls = [], []
        memories = bindings = contexts = navigations = inboxes = changes = ()
        outcome, reason = WorkStatus.PARTIAL, "funded progress retained"
        if type(cmd.payload) is RecallQuery:
            for _ in range(cmd.work_limit):
                spent = min(1, wallet.energy, wallet.time)
                after = Wallet(cmd.actor, wallet.energy - spent, wallet.time - spent)
                works.append(WorkRecord(Ref(Kind.WORK, f"work:{when.tick}:{len(works)}", 1),
                    cmd.actor, op, amounts(wallet), (), (ResourceAmount(ENERGY, spent), ResourceAmount(TIME, spent)),
                    amounts(after), 1, spent, WorkStatus.COMPLETED if spent else WorkStatus.DEFERRED,
                    "one recall operation" if spent else "no affordable recall operation"))
                wallet = after
                if not spent:
                    outcome = WorkStatus.PARTIAL if job.completed_units else WorkStatus.DEFERRED
                    reason = "recall awaits resources; prior work preserved"
                    break
                job = self._recall_step(job, when)
                if not job.frontier:
                    result = RecallResult(Ref(Kind.EVIDENCE, "recall:" + memory_key(cmd.actor, cmd.task_id), 1),
                        cmd.actor, cmd.payload, job.selected_at, job.navigation, job.max_hops,
                        job.bindings, job.visited, job.hits, job.truncated)
                    recalls.append(result)
                    job = replace(job, result=result.ref)
                    outcome, reason = WorkStatus.COMPLETED, "declared recall completed; accuracy unassessed"
                    break
        else:
            required = write_cost(cmd.payload) - job.completed_units
            spent = min(required, wallet.energy, wallet.time, cmd.work_limit)
            after = Wallet(cmd.actor, wallet.energy - spent, wallet.time - spent)
            done = job.completed_units + spent
            if spent == required:
                plan = self._plan_write(cmd, when)
                if plan is None:
                    outcome, reason = WorkStatus.FAILED, "expected current revision changed after paid processing"
                else:
                    memories, bindings, contexts, navigations, inboxes, changes = plan
                    outcome, reason = WorkStatus.COMPLETED, "explicit memory operation completed"
            elif done == 0:
                outcome, reason = WorkStatus.DEFERRED, "no affordable memory operation"
            work_outcome = (outcome if spent == required else
                WorkStatus.PARTIAL if spent else WorkStatus.DEFERRED)
            works.append(WorkRecord(Ref(Kind.WORK, f"work:{when.tick}:0", 1), cmd.actor, op,
                amounts(wallet), (), (ResourceAmount(ENERGY, spent), ResourceAmount(TIME, spent)),
                amounts(after), required, spent, work_outcome, reason))
            job = replace(job, completed_units=done)
        job = replace(job, outcome=outcome)
        causes = tuple(sorted({Cause(self._origins[r], MEMORY_RULE) for r in cmd.based_on},
                              key=lambda c: (ref_order(c.event), ref_order(c.rule))))
        event = WorldEvent(event_ref, when, (cmd.actor,), (), op.key, self.config.context,
            changes, causes, tuple(w.ref for w in works), outcome, reason)
        receipt = self._observation(cmd.actor, event_ref, when,
            (self._prop(event_ref, "outcome", outcome.value, when),),
            "private memory processing receipt", "exact local outcome under experimental memory rules")
        tx = MemoryTransaction(cmd, event, tuple(works), (receipt,), (), memories, None,
                               bindings, contexts, navigations, inboxes, tuple(recalls), job)
        self._commit(tx)
        return event

    def _commit(self, tx):
        if type(tx) is not MemoryTransaction:
            return super()._commit(tx)
        extra = tx.bindings + tx.contexts + tx.navigations + tx.inboxes + tx.recalls
        if len({x.ref for x in extra}) != len(extra) or any(x.ref in self._records for x in extra):
            raise ValueError("duplicate memory record")
        super()._commit(tx)
        for record in extra:
            self._records[record.ref] = record
            self._origins[record.ref] = tx.event.ref
            self._known[record.owner].add(record.ref)
        for binding in tx.bindings:
            key = (binding.owner, binding.ref.key)
            old = self._binding_heads.get(key)
            if old is not None:
                old_bucket = (old.owner, old.cue, old.context)
                del self._buckets[old_bucket][old.ref.key]
                if not self._buckets[old_bucket]: del self._buckets[old_bucket]
            self._binding_heads[key] = binding
            self._buckets.setdefault((binding.owner, binding.cue, binding.context), {})[binding.ref.key] = binding.ref
        for nav in tx.navigations: self._navigation[nav.owner] = nav
        for state in tx.inboxes: self._inbox_state[state.owner] = state
        self._memory_jobs[(tx.command.actor, tx.command.task_id)] = tx.job

    def checkpoint(self):
        from .codec import dumps
        return dumps(MemoryCheckpoint("hle-r3-v1", self.config, tuple(self._journal)))

    @classmethod
    def restore(cls, text):
        from .codec import loads
        cp = loads(text)
        if type(cp) is not MemoryCheckpoint or cp.schema != "hle-r3-v1" or not cp.journal:
            raise ValueError("unsupported or empty relational checkpoint")
        world = cls(cp.config)
        if world._journal[0] != cp.journal[0]: raise ValueError("genesis mismatch")
        for entry in cp.journal[1:]:
            if entry.command is None or entry.command.command_id in world._commands:
                raise ValueError("missing or duplicate command")
            world.execute(entry.command)
            if world._journal[-1] != entry: raise ValueError("relational replay mismatch")
        return world


def observed_revision(view, observation_ref, subject, relation, key, previous=None, links=()):
    """Experimental participant policy: exact observation copy, explicit scope.

    No world reference is accepted. A newer observation is not automatically
    more accurate; testimony stays tentative and evaluator accuracy is separate.
    """
    matches = [o for o in view.observations if o.ref == observation_ref]
    if len(matches) != 1: raise ValueError("selected observation is not in delivered input")
    observation = matches[0]
    content = tuple(p for p in observation.content if p.subject == subject and p.relation == relation)
    if len(content) != 1: raise ValueError("observation must provide one unambiguous selected proposition")
    if previous is not None and previous not in view.own_memories:
        raise ValueError("previous memory is not in permitted input")
    attitude = ClaimStatus.TENTATIVE if observation.source.kind == Kind.MESSAGE else ClaimStatus.ENDORSED
    draft = WriteDraft(key, content, links, attitude, None if previous is None else previous.ref,
                       "copied selected delivered content under r3 observed revision policy")
    basis = (observation.ref,) + (() if previous is None else (previous.ref,))
    return draft, basis


def ownership_action(view, item, recipient, context, at):
    """Small example policy; ambiguity/absence requests a permitted inspection."""
    claims = [(m.ref, p) for m in view.own_memories if m.claim_status != ClaimStatus.RETRACTED
        for p in m.content if p.subject == item and p.relation == "owned_by"
        and p.context == context and in_scope(p.scope, at)]
    owners = {p.object for _, p in claims}
    basis = tuple(dict.fromkeys(ref for ref, _ in claims))
    if owners == {view.actor}:
        return ActionRequest(view.actor, TRANSFER, (item, recipient), basis)
    return ActionRequest(view.actor, INSPECT, (item,), basis)
