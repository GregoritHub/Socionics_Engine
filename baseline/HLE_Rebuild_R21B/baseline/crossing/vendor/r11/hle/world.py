"""Deterministic ownership world and simulator-owned Truth record (R2).

Participant policies receive detached immutable values only. This is an API
boundary for cooperative policies, not a sandbox against hostile Python code.
No memory navigation, learned policy, IDEA return or Shell detector lives here.
"""
from bisect import bisect_right

from .contracts import (ActionRequest, Cause, Change, EvidenceStatus, Kind,
    MemoryRevision, Moment, Observation, ParticipantInput, Proposition, Ref,
    ResourceAmount, TimeScope, WorkRecord, WorkStatus, WorldEvent)
from .world_records import (Attempt, BASIS, CHANNEL, CORRECTION, COSTS, CREDIT,
    Checkpoint, Correction, Credit, ENERGY, FactCheck, INSPECT, Message,
    PRECONDITION, RETAIN, SEND, TIME, TRANSFER, Task, Tick, Transaction, Wallet,
    WorldConfig)


def ref_order(ref):
    return ref.kind.value, ref.key, ref.revision


def fact_key(proposition):
    return proposition.subject, proposition.relation, proposition.context


def amounts(wallet):
    return (ResourceAmount(ENERGY, wallet.energy), ResourceAmount(TIME, wallet.time))


def memory_key(actor, local_key):
    return f"{len(actor.key)}:{actor.key}:{actor.revision}:{local_key}"


class TruthView:
    """Evaluator interface; never supplied to ParticipantPolicy.choose."""

    def __init__(self, world):
        self._world = world

    def resolve(self, ref):
        """Exact revision lookup; never resolve 'latest' implicitly."""
        return self._world._records[ref]

    def event(self, ref):
        value = self.resolve(ref)
        if type(value) is not WorldEvent:
            raise ValueError("not an event reference")
        return value

    def fact_at(self, subject, relation, context, at):
        w = self._world
        if at > w.now:
            return None
        key = (subject, relation, context)
        times = w._times.get(key, ())
        i = bisect_right(times, at) - 1
        return None if i < 0 else w._timeline[key][i][1]

    def current_fact(self, subject, relation, context):
        return self._world._facts.get((subject, relation, context))

    def is_current(self, result):
        w = self._world
        return (result.dependency_revision == w._revisions.get(fact_key(result.claim), 0)
                and not (result.at > result.checked_at and w.now > result.checked_at))

    def check(self, claim, at):
        """Pointwise factual check at an explicit moment within the claim scope.

        Unknown semantics/refs, future or out-of-scope times remain unassessed.
        This is not an IDEA identity-return or whole-interval assessment.
        """
        if type(claim) is not Proposition or type(at) is not Moment:
            raise ValueError("a proposition and explicit moment are required")
        w = self._world
        key = fact_key(claim)
        query = (claim, at)
        cached = w._checks.get(query)
        if cached is not None and self.is_current(cached):
            return cached
        status, evidence = EvidenceStatus.UNASSESSED, ()
        reason = "unknown relation, referent, context or time"
        scoped = claim.scope.start <= at and (claim.scope.end is None or at < claim.scope.end)
        known_refs = (claim.subject in w._records and claim.context == w.config.context
                      and (type(claim.object) is not Ref or claim.object in w._records))
        times = w._times.get(key, ())
        if known_refs and scoped and at <= w.now and times:
            i = bisect_right(times, at) - 1
            if i >= 0:
                event, fact = w._timeline[key][i]
                status = EvidenceStatus.ESTABLISHED if fact is not None and type(fact.object) is type(claim.object) and fact.object == claim.object else EvidenceStatus.FAILED
                evidence = (event,)
                reason = "as-recorded pointwise agreement" if status == EvidenceStatus.ESTABLISHED else "as-recorded pointwise contradiction"
        result = FactCheck(claim, at, status, evidence, w._revisions.get(key, 0), w.now, reason)
        w._checks[query] = result
        w._check_dependents.setdefault(key, set()).add(query)
        return result

    def changed_since(self, event_count):
        """Indexed suffix for affected-work consumers; cursor is len(journal)."""
        w = self._world
        if type(event_count) is not int or not 0 <= event_count <= len(w._journal):
            raise ValueError("invalid change cursor")
        return tuple(w._changes[event_count:]), len(w._journal)

    def wallet(self, actor):
        return self._world._wallets[actor]

    def task(self, actor, key):
        return self._world._tasks[(actor, key)]

    def journal(self):
        """Explicit offline export; ordinary commits never traverse this log."""
        return tuple(self._world._journal)


class World:
    def __init__(self, config):
        if type(config) is not WorldConfig:
            raise ValueError("WorldConfig required")
        self.config = config
        self._records = {e.ref: e for e in config.entities}
        self._records[config.context] = config.context
        for ref in (ENERGY, TIME, CHANNEL, BASIS, PRECONDITION, CORRECTION, CREDIT) + tuple(p for p, _ in COSTS):
            self._records[ref] = ref
        self._actors = set(config.actors)
        self._items = {o.item for o in config.ownership}
        self._costs = dict(COSTS)
        self._links = set(config.message_links)
        self._witnesses = {}
        for witness in config.witnesses:
            self._witnesses.setdefault(witness.item, []).append(witness)
        self._wallets = {w.actor: w for w in config.wallets}
        self._facts, self._heads, self._times, self._timeline, self._revisions = {}, {}, {}, {}, {}
        self._journal, self._changes = [], []
        self._commands, self._tasks, self._origins = {}, {}, {}
        self._inboxes = {a: [] for a in config.actors}
        self._memory_heads = {a: {} for a in config.actors}
        public = set(self._records)
        self._known = {a: set(public) for a in config.actors}
        self._checks, self._check_dependents = {}, {}
        self.truth = TruthView(self)
        when = Moment(0, 0)
        changes = [Change(None, self._prop(o.item, "owned_by", o.owner, when)) for o in config.ownership]
        for entity in config.entities:
            changes.extend((Change(None, self._prop(entity.ref, "named", entity.label, when)),
                            Change(None, self._prop(entity.ref, "role", entity.role, when))))
        event = WorldEvent(Ref(Kind.EVENT, "event:0", 1), when, config.actors,
            tuple(o.item for o in config.ownership), "genesis", config.context,
            tuple(changes), (), (), WorkStatus.COMPLETED, "declared initial world")
        observations = tuple(self._observation(a, event.ref, when, tuple(c.after for c in changes),
            "public initial identity and ownership", "exact under declared initial rules") for a in config.actors)
        self._commit(Transaction(None, event, (), observations, (), (), None))

    @property
    def now(self):
        return Moment(len(self._journal) - 1, 1)

    def _prop(self, subject, relation, value, when):
        return Proposition(subject, relation, value, self.config.context, TimeScope(when, None))

    def _observation(self, observer, source, at, content, visibility, uncertainty, offset=0):
        local = len(self._inboxes[observer]) + offset + 1
        ref = Ref(Kind.OBSERVATION, f"{len(observer.key)}:{observer.key}:{observer.revision}:{local}", 1)
        return Observation(ref, observer, source, at, Moment(at.tick, 1), content, CHANNEL, visibility, uncertainty)

    def participant_input(self, actor, after=0):
        """Read only this actor's inbox suffix and active beliefs; return cursor.

        Pass the returned cursor on the next call to avoid revisiting old
        observations. No input construction walks the global event history.
        R3 will supply selective retrieval over a participant's retained memory.
        """
        if actor not in self._actors or type(after) is not int or not 0 <= after <= len(self._inboxes[actor]):
            raise ValueError("unknown actor or invalid inbox cursor")
        inbox = self._inboxes[actor]
        memories = tuple(self._memory_heads[actor][k] for k in sorted(self._memory_heads[actor]))
        return ParticipantInput(actor, self.now, tuple(inbox[after:]), memories, amounts(self._wallets[actor]), ()), len(inbox)

    def run_policy(self, actor, policy, after=0):
        view, cursor = self.participant_input(actor, after)
        action = policy.choose(view)
        if action is None:
            return None, cursor
        if type(action) is not ActionRequest or action.actor != actor:
            raise ValueError("policy may act only as its own actor")
        return self.apply(action), cursor

    def apply(self, action):
        """R1 WorldPort for inspect/transfer; envelopes carry send/retain payloads."""
        key = f"apply:{len(self._journal)}"
        return self.execute(Attempt(key, key, action))

    def _validate_attempt(self, cmd):
        a = cmd.action
        if a.actor not in self._actors or a.operation not in self._costs:
            raise ValueError("unknown actor or operation")
        if a.operation == TRANSFER:
            valid = len(a.inputs) == 2 and a.inputs[0] in self._items and a.inputs[1] in self._actors
        elif a.operation == INSPECT:
            valid = len(a.inputs) == 1 and a.inputs[0] in self._items
        elif a.operation == SEND:
            valid = len(a.inputs) == 1 and a.inputs[0] in self._actors and cmd.message is not None
        else:
            valid = not a.inputs and cmd.memory is not None
        if not valid or (a.operation == SEND) != (cmd.message is not None) or (a.operation == RETAIN) != (cmd.memory is not None):
            raise ValueError("operation and payload disagree")
        if len(set(a.based_on)) != len(a.based_on):
            raise ValueError("duplicate action basis")
        for ref in a.based_on:
            value = self._records.get(ref)
            if not ((type(value) is Observation and value.observer == a.actor and value.delivered_at <= self.now)
                    or (type(value) is MemoryRevision and value.owner == a.actor and value.retained_at <= self.now)):
                raise ValueError("basis is not this actor's delivered observation or retained memory")
        for draft in (cmd.message, cmd.memory):
            if draft is not None:
                for proposition in draft.content:
                    refs = (proposition.subject, proposition.context) + ((proposition.object,) if type(proposition.object) is Ref else ())
                    if any(ref not in self._known[a.actor] for ref in refs):
                        raise ValueError("content refers to an inaccessible or unresolved revision")
        old = self._tasks.get((a.actor, cmd.task_id))
        if old is not None and (old.request != a or old.message != cmd.message or old.memory != cmd.memory
                                or old.outcome in (WorkStatus.COMPLETED, WorkStatus.FAILED)):
            raise ValueError("task is terminal or continuation changes its specification")
        return old

    def execute(self, cmd):
        """Simulator command boundary. Credit/correction/tick are harness-only.

        Malformed/unauthorized requests reject before mutation. A valid but
        unsuccessful domain attempt is committed with its actual resource cost.
        """
        if type(cmd) not in (Attempt, Credit, Correction, Tick):
            raise ValueError("unknown command type")
        previous = self._commands.get(cmd.command_id)
        if previous is not None:
            if previous.command != cmd:
                raise ValueError("command ID reused with different input")
            return previous.event
        tick = len(self._journal)
        when, event_ref = Moment(tick, 0), Ref(Kind.EVENT, f"event:{tick}", 1)
        changes, works, messages, memories, observations, causes = [], [], [], [], [], []
        actors, objects, task, corrects = (), (), None, None
        outcome, reason, action_name = WorkStatus.COMPLETED, "public clock advanced", "tick"
        extra = ()
        if type(cmd) is Attempt:
            old = self._validate_attempt(cmd)
            a = cmd.action
            actors, action_name = (a.actor,), a.operation.key
            objects = (a.inputs[0],) if a.operation in (TRANSFER, INSPECT) else ()
            required = self._costs[a.operation]
            done = old.completed if old is not None else 0
            remaining = required - done
            before = self._wallets[a.actor]
            spent = min(remaining, before.energy, before.time)
            after = Wallet(a.actor, before.energy - spent, before.time - spent)
            outcome = WorkStatus.DEFERRED if spent == 0 else (WorkStatus.PARTIAL if spent < remaining else WorkStatus.COMPLETED)
            reason = {WorkStatus.DEFERRED: "no affordable work unit", WorkStatus.PARTIAL: "unfinished work retained", WorkStatus.COMPLETED: "operation completed"}[outcome]
            for basis in a.based_on:
                causes.append(Cause(self._origins[basis], BASIS))
            if outcome == WorkStatus.COMPLETED:
                if a.operation in (TRANSFER, INSPECT):
                    fact = self._facts[(a.inputs[0], "owned_by", self.config.context)]
                    causes.append(Cause(self._heads[fact_key(fact)], PRECONDITION))
                    if a.operation == INSPECT:
                        extra = (self._prop(fact.subject, fact.relation, fact.object, when),)
                    elif fact.object != a.actor or a.inputs[1] == a.actor:
                        outcome, reason = WorkStatus.FAILED, "transfer precondition failed after paid processing"
                    else:
                        changes.append(Change(fact, self._prop(fact.subject, "owned_by", a.inputs[1], when)))
                        extra = (changes[-1].after,)
                elif a.operation == SEND:
                    recipient = a.inputs[0]
                    if (a.actor, recipient) not in self._links:
                        outcome, reason = WorkStatus.FAILED, "directed message channel unavailable after paid processing"
                    else:
                        message = Message(Ref(Kind.MESSAGE, f"message:{tick}", 1), a.actor, recipient,
                            event_ref, when, cmd.message.content, a.based_on)
                        messages.append(message)
                        observations.append(self._observation(recipient, message.ref, when, message.content,
                            "explicit directed message", "testimony; accuracy unverified"))
                elif a.operation == RETAIN:
                    draft = cmd.memory
                    key = memory_key(a.actor, draft.key)
                    previous_memory = self._memory_heads[a.actor].get(key)
                    revision = 1 if previous_memory is None else previous_memory.ref.revision + 1
                    memory = MemoryRevision(Ref(Kind.MEMORY, key, revision), a.actor, when, draft.content, (),
                        tuple(r for r in a.based_on if r.kind == Kind.OBSERVATION),
                        tuple(r for r in a.based_on if r.kind == Kind.MEMORY), draft.attitude, (),
                        None if previous_memory is None else previous_memory.ref, draft.reason)
                    memories.append(memory)
                    if previous_memory is not None:
                        changes.append(Change(self._facts[(previous_memory.ref, "held_by", self.config.context)], None))
                    changes.append(Change(None, self._prop(memory.ref, "held_by", a.actor, when)))
            task = Task(a.actor, cmd.task_id, a, cmd.message, cmd.memory, required, done + spent, outcome)
            works.append(WorkRecord(Ref(Kind.WORK, f"work:{tick}", 1), a.actor, a.operation,
                amounts(before), (), (ResourceAmount(ENERGY, spent), ResourceAmount(TIME, spent)),
                amounts(after), remaining, spent, outcome, reason))
        elif type(cmd) is Credit:
            if cmd.actor not in self._actors:
                raise ValueError("unknown credit recipient")
            before = self._wallets[cmd.actor]
            after = Wallet(cmd.actor, before.energy + cmd.energy, before.time + cmd.time)
            actors, action_name, reason = (cmd.actor,), "external_credit", cmd.reason
            works.append(WorkRecord(Ref(Kind.WORK, f"work:{tick}", 1), cmd.actor, CREDIT,
                amounts(before), (ResourceAmount(ENERGY, cmd.energy), ResourceAmount(TIME, cmd.time)),
                (), amounts(after), 1, 1, WorkStatus.COMPLETED, reason))
        elif type(cmd) is Correction:
            target = self.truth.event(cmd.target)
            candidates = [c.after for c in target.changes if c.after is not None and c.after.relation == "owned_by"]
            if len(candidates) != 1 or cmd.replacement_owner not in self._actors:
                raise ValueError("correction requires one ownership assertion and a known owner")
            old_fact = candidates[0]
            if self._heads.get(fact_key(old_fact)) != target.ref:
                raise ValueError("only the current ownership head can be prospectively corrected")
            if old_fact.object == cmd.replacement_owner:
                raise ValueError("correction must change the recorded owner")
            changes.append(Change(old_fact, self._prop(old_fact.subject, "owned_by", cmd.replacement_owner, when)))
            objects, corrects, action_name, reason = (old_fact.subject,), target.ref, "record_correction", cmd.reason
            causes.append(Cause(target.ref, CORRECTION))
        # All command validation and planning completes before any mutation.
        event = WorldEvent(event_ref, when, actors, objects, action_name, self.config.context,
            tuple(changes), tuple(sorted(set(causes), key=lambda c: (ref_order(c.event), ref_order(c.rule)))),
            tuple(w.ref for w in works), outcome, reason, corrects)
        if actors:
            actor = actors[0]
            receipt = (self._prop(event_ref, "outcome", outcome.value, when),) + extra
            observations.insert(0, self._observation(actor, event_ref, when, receipt,
                "private action/resource receipt", "exact local outcome under world rules"))
        if type(cmd) is Attempt and cmd.action.operation == TRANSFER:
            for witness in self._witnesses.get(cmd.action.inputs[0], ()):
                if witness.observer == cmd.action.actor:
                    continue
                content = tuple(c.after for c in changes if c.after is not None) if witness.mode == "full" else ()
                observations.append(self._observation(witness.observer, event_ref, when, content,
                    "transfer " + witness.mode, "exact visible projection; omitted fields unknown"))
        transaction = Transaction(cmd, event, tuple(works), tuple(observations), tuple(messages), tuple(memories), task)
        self._commit(transaction)
        return event

    def _commit(self, tx):
        """Apply a prepared transaction once using only direct/affected indexes."""
        event = tx.event
        if event.when != Moment(len(self._journal), 0) or event.ref in self._records:
            raise ValueError("event order or identity invalid")
        if any(c.event not in self._records or self.truth.event(c.event).when >= event.when for c in event.causes):
            raise ValueError("invalid causal predecessor")
        if tuple(w.ref for w in tx.works) != event.work:
            raise ValueError("event/work mismatch")
        seen = set()
        for change in event.changes:
            for fact in (change.before, change.after):
                if fact is not None and fact.context != self.config.context:
                    raise ValueError("foreign fact context")
            key = fact_key(change.before or change.after)
            if key in seen or (change.after is not None and fact_key(change.after) != key):
                raise ValueError("duplicate or mismatched fact change")
            seen.add(key)
            if self._facts.get(key) != change.before:
                raise ValueError("before fact does not match current state")
        records = (event,) + tx.works + tx.messages + tx.memories + tx.observations
        if len({r.ref for r in records}) != len(records) or any(r.ref in self._records for r in records):
            raise ValueError("duplicate record identity")
        planned_balances = {}
        for work in tx.works:
            before = planned_balances.get(work.owner, amounts(self._wallets[work.owner]))
            if before != work.before:
                raise ValueError("wallet/work mismatch")
            planned_balances[work.owner] = work.after
        # No validation after this point: commit only prepared immutable values.
        self._journal.append(tx)
        if tx.command is not None:
            self._commands[tx.command.command_id] = tx
        for record in records:
            self._records[record.ref] = record
            self._origins[record.ref] = event.ref
        changed_keys = []
        for change in event.changes:
            key = fact_key(change.before or change.after)
            if change.after is None:
                self._facts.pop(key, None)
            else:
                self._facts[key] = change.after
            self._heads[key] = event.ref
            self._times.setdefault(key, []).append(event.when)
            self._timeline.setdefault(key, []).append((event.ref, change.after))
            self._revisions[key] = self._revisions.get(key, 0) + 1
            changed_keys.append(key)
            for query in self._check_dependents.pop(key, ()):
                self._checks.pop(query, None)
        self._changes.append((event.ref, tuple(changed_keys)))
        for work in tx.works:
            balance = {r.unit: r.amount for r in work.after}
            self._wallets[work.owner] = Wallet(work.owner, balance[ENERGY], balance[TIME])
        if tx.task is not None:
            self._tasks[(tx.task.actor, tx.task.key)] = tx.task
        for memory in tx.memories:
            self._memory_heads[memory.owner][memory.ref.key] = memory
            self._known[memory.owner].add(memory.ref)
        for observation in tx.observations:
            self._inboxes[observation.observer].append(observation)
            known = self._known[observation.observer]
            known.update((observation.ref, observation.source))
            for fact in observation.content:
                known.update((fact.subject, fact.context))
                if type(fact.object) is Ref:
                    known.add(fact.object)

    def state(self):
        """Explicit diagnostic snapshot, excluded from ordinary execution."""
        facts = tuple(sorted(self._facts.values(), key=lambda p: (ref_order(p.subject), p.relation, ref_order(p.context))))
        wallets = tuple(self._wallets[a] for a in sorted(self._actors, key=ref_order))
        tasks = tuple(self._tasks[k] for k in sorted(self._tasks, key=lambda k: (ref_order(k[0]), k[1])))
        memories = tuple(m for a in sorted(self._actors, key=ref_order)
                         for _, m in sorted(self._memory_heads[a].items()))
        return self.now, facts, wallets, tasks, memories

    def checkpoint(self):
        from .codec import dumps
        return dumps(Checkpoint("hle-r2-v1", self.config, tuple(self._journal)))

    @classmethod
    def restore(cls, text):
        from .codec import loads
        checkpoint = loads(text)
        if type(checkpoint) is not Checkpoint or checkpoint.schema != "hle-r2-v1" or not checkpoint.journal:
            raise ValueError("unsupported or empty world checkpoint")
        world = cls(checkpoint.config)
        if world._journal[0] != checkpoint.journal[0]:
            raise ValueError("genesis differs from declared configuration")
        for entry in checkpoint.journal[1:]:
            if entry.command is None or entry.command.command_id in world._commands:
                raise ValueError("missing or repeated journal command")
            world.execute(entry.command)
            if world._journal[-1] != entry:
                raise ValueError("journal disagrees with deterministic command replay")
        return world
