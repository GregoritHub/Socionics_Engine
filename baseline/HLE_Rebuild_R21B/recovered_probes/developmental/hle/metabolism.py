"""Paid Crux operators over the existing relational world and single journal.

The processing module receives detached owned inputs. Only _enact reads world
ownership; its result is delivered through the same explicit action channels.
"""
from dataclasses import replace
from .contracts import (Cause, Change, Kind, MemoryRevision, Moment,
    MovementRecord, Observation, ProcessingStep, Ref, ResourceAmount,
    WorkRecord, WorkStatus, WorldEvent)
from .memory import RelationalWorld
from .memory_records import RecallResult
from .metabolism_records import (Account, Application, ApplyDraft, Capability,
    EmbodyDraft, Enactment, METABOLISM, MetabolicCheckpoint, MetabolicCommand,
    MetabolicJob, MetabolicTransaction, OPERATIONS, ProcessingPolicy,
    ProcessingState, Profile, TheorizeDraft, UnderstandDraft, movement, operation)
from .processing import (after_inspection, derive_account, observed_content,
    plan_route, select_action, route_active)
from .world import amounts, fact_key, memory_key, ref_order
from .world_records import ENERGY, TIME, INSPECT, PRECONDITION, TRANSFER, Wallet


class MetabolicWorld(RelationalWorld):
    def __init__(self, config, profiles, policy=ProcessingPolicy()):
        if (type(profiles) is not tuple or any(type(p) is not Profile for p in profiles)
                or len(profiles) != len(config.actors)
                or {p.owner for p in profiles} != set(config.actors)
                or type(policy) is not ProcessingPolicy):
            raise ValueError("one explicit profile per actor and a processing policy required")
        self.profiles, self.policy = profiles, policy
        self._profiles = {p.owner: p for p in profiles}
        self._processing_states, self._processing_jobs = {}, {}
        self._processing_changes = []
        super().__init__(config)
        for ref in (METABOLISM,) + OPERATIONS:
            self._records[ref] = ref
        for profile in profiles:
            state = ProcessingState(Ref(Kind.CURSOR, "processing:" + memory_key(profile.owner, "state"), 1),
                                    profile.owner, profile.active, profile.perspective, None)
            self._processing_states[profile.owner] = state
            self._records[state.ref] = state
            self._origins[state.ref] = self._journal[0].event.ref
            self._known[profile.owner].update((state.ref, METABOLISM) + OPERATIONS)

    def processing_state(self, actor):
        if actor not in self._actors: raise ValueError("unknown actor")
        return self._processing_states[actor]

    def processing_job(self, actor, task_id):
        if actor not in self._actors: raise ValueError("unknown actor")
        return self._processing_jobs.get((actor, task_id))

    def processing_record(self, actor, ref):
        return self._owned(actor, ref, (Account, Application, Capability, Enactment, ProcessingState))

    def processing_changed_since(self, cursor):
        if type(cursor) is not int or not 0 <= cursor <= len(self._journal):
            raise ValueError("invalid processing change cursor")
        return tuple(self._processing_changes[cursor:]), len(self._journal)

    def _inputs(self, actor, payload):
        """Resolve only explicit owned addresses, never current ownership facts."""
        if type(payload) is TheorizeDraft:
            recall = self._owned(actor, payload.recall, (RecallResult,))
            if payload.item not in self._items or payload.recipient not in self._actors or payload.recipient == actor:
                raise ValueError("known item and another recipient required")
            if recall.query.context != self.config.context:
                raise ValueError("ownership operator requires the declared world context")
            memories = tuple(self.read_revision(actor, h.memory) for h in recall.hits)
            caps = {r: self._owned(actor, r, (Capability,)) for m in memories for r in m.capabilities}
            basis = (recall.ref,) + tuple(m.ref for m in memories) + tuple(caps)
            return (recall, memories, caps), basis, 1 + sum(len(h.proposition_indexes) for h in recall.hits)
        if type(payload) in (ApplyDraft, UnderstandDraft):
            account = self._owned(actor, payload.account, (Account,))
            values, basis, size = (account,), (account.ref,) + account.evidence, 1 + len(account.evidence)
        else:
            application = self._owned(actor, payload.application, (Application,))
            account = self._owned(actor, application.account, (Account,))
            observations = tuple(self._owned(actor, r, (Observation,)) for r in application.observations)
            values = application, account, observations
            basis = (application.ref, account.ref) + account.evidence + application.observations
            size = 1 + len(observations) + len(account.evidence) + int(application.discrepancy)
        if type(payload) in (EmbodyDraft, UnderstandDraft) and payload.expected is not None:
            old = self.read_revision(actor, payload.expected)
            if old.ref.key != memory_key(actor, payload.key): raise ValueError("wrong named predecessor")
            basis += (old.ref,)
        return values, tuple(dict.fromkeys(basis)), size

    def _validate_processing(self, cmd):
        if cmd.actor not in self._actors: raise ValueError("unknown actor")
        state = self._processing_states[cmd.actor]
        old = self._processing_jobs.get((cmd.actor, cmd.task_id))
        if old is not None:
            if (old.outcome in (WorkStatus.COMPLETED, WorkStatus.FAILED)
                    or old.command.payload != cmd.payload or state.busy != cmd.task_id):
                raise ValueError("terminal job or changed continuation")
        elif state.busy is not None or state.perspective != movement(cmd.payload).route.origin:
            raise ValueError("unfinished movement or wrong content perspective")
        values, basis, size = self._inputs(cmd.actor, cmd.payload)
        if old is None:
            plan = plan_route(self._profiles[cmd.actor], state.active,
                              movement(cmd.payload), cmd.payload, size, self.policy)
            old = MetabolicJob(cmd, plan, basis)
        return old, values

    def _enact(self, actor, account, action, when, event_ref):
        """Only executor step: mirror R2 inspect/transfer semantics and visibility."""
        fact = self._facts[(account.item, "owned_by", self.config.context)]
        cause = Cause(self._heads[fact_key(fact)], PRECONDITION)
        changes, content = (), ()
        outcome = WorkStatus.COMPLETED
        if action.operation == INSPECT:
            content = (self._prop(fact.subject, fact.relation, fact.object, when),)
        elif fact.object != actor or action.inputs[1] == actor:
            outcome = WorkStatus.FAILED
        else:
            changes = (Change(fact, self._prop(account.item, "owned_by", action.inputs[1], when)),)
            content = (changes[0].after,)
        receipt = self._observation(actor, event_ref, when,
            (self._prop(event_ref, "outcome", outcome.value, when),) + content,
            "private action receipt during Apply", "exact local outcome under world rules")
        witnesses = []
        if action.operation == TRANSFER:
            for witness in self._witnesses.get(account.item, ()):
                if witness.observer != actor:
                    witnesses.append(self._observation(witness.observer, event_ref, when,
                        content if witness.mode == "full" else (),
                        "transfer " + witness.mode, "exact visible projection; omitted fields unknown"))
        return outcome, changes, receipt, tuple(witnesses), cause

    def execute(self, cmd):
        if type(cmd) is not MetabolicCommand: return super().execute(cmd)
        previous = self._commands.get(cmd.command_id)
        if previous is not None:
            if previous.command != cmd: raise ValueError("command ID reused with different input")
            return previous.event
        job, inputs = self._validate_processing(cmd)
        actor, payload = cmd.actor, cmd.payload
        old_state = self._processing_states[actor]
        when = Moment(len(self._journal), 0)
        event_ref = Ref(Kind.EVENT, f"event:{when.tick}", 1)
        key = memory_key(actor, cmd.task_id)
        op = operation(payload)
        works, extra, memories, observations, changes = [], [], [], [], []
        causes = {Cause(self._origins[r], METABOLISM) for r in job.basis + job.observations}
        wallet, budget = self._wallets[actor], cmd.work_limit
        outcome, reason = WorkStatus.PARTIAL, "funded movement progress retained"

        def charge(required, procedure):
            nonlocal wallet, budget
            spent = min(required, wallet.energy, wallet.time, budget)
            after = Wallet(actor, wallet.energy - spent, wallet.time - spent)
            status = WorkStatus.COMPLETED if spent == required else WorkStatus.PARTIAL if spent else WorkStatus.DEFERRED
            work = WorkRecord(Ref(Kind.WORK, f"work:{when.tick}:{len(works)}", 1), actor,
                procedure, amounts(wallet), (), (ResourceAmount(ENERGY, spent), ResourceAmount(TIME, spent)),
                amounts(after), required, spent, status, "paid routing/content/action work; unfinished units retained")
            works.append(work)
            wallet, budget = after, budget - spent
            return spent

        if job.phase == "processing":
            spent = charge(job.plan.required - job.completed_units, op)
            job = replace(job, completed_units=job.completed_units + spent)
            if job.completed_units == job.plan.required:
                if type(payload) is TheorizeDraft:
                    account = derive_account(Ref(Kind.EVIDENCE, "account:" + key, 1), actor, payload, *inputs)
                    extra.append(account)
                    job = replace(job, result=account.ref)
                    outcome, reason = WorkStatus.COMPLETED, "checkable account derived from permitted recalled content"
                elif type(payload) is ApplyDraft:
                    job = replace(job, phase="enact", action=select_action(inputs[0]))
                else:
                    current = self.memory_head(actor, payload.key)
                    if (None if current is None else current.ref) != payload.expected:
                        outcome, reason = WorkStatus.FAILED, "expected memory revision changed after paid processing"
                    else:
                        if type(payload) is EmbodyDraft:
                            application, account, delivered = inputs
                            content, attitude = observed_content(account, delivered)
                            guard = account.guard
                            if application.discrepancy and guard is None:
                                capability = Capability(Ref(Kind.PROCEDURE, "guard:" + key, 1), actor,
                                    "inspect_before_transfer", application.ref, application.observations)
                                guard = capability.ref
                                extra.append(capability)
                        else:
                            account, = inputs
                            content, attitude = observed_content(account, ())
                            guard = account.guard
                        memory = MemoryRevision(Ref(Kind.MEMORY, memory_key(actor, payload.key),
                            1 if current is None else current.ref.revision + 1), actor, when, content,
                            account.evidence, tuple(r for r in job.basis if r.kind == Kind.OBSERVATION),
                            tuple(dict.fromkeys(account.evidence + (() if payload.expected is None else (payload.expected,)))),
                            attitude, () if guard is None else (guard,), payload.expected,
                            "experience-derived content/capacity" if type(payload) is EmbodyDraft else "personal interpretation of a recalled account")
                        memories.append(memory)
                        if current is not None:
                            changes.append(Change(self._facts[(current.ref, "held_by", self.config.context)], None))
                        changes.append(Change(None, self._prop(memory.ref, "held_by", actor, when)))
                        job = replace(job, result=memory.ref)
                        outcome, reason = WorkStatus.COMPLETED, "explicitly retained content and usable procedure references"
        # At most one physical action per transaction. A successful inspection
        # can schedule a transfer, which must cite the committed observation.
        if job.phase == "enact" and (budget or not works):
            required = self._costs[job.action.operation] - job.action_units
            spent = charge(required, job.action.operation)
            job = replace(job, action_units=job.action_units + spent)
            if spent == required:
                account = inputs[0]
                action_outcome, delta, receipt, witnesses, cause = self._enact(actor, account, job.action, when, event_ref)
                changes.extend(delta); observations.extend((receipt,) + witnesses); causes.add(cause)
                enactment = Enactment(Ref(Kind.EVIDENCE, f"enactment:{key}:{len(job.enactments)}", 1),
                                     actor, account.ref, job.action, receipt.ref, action_outcome)
                extra.append(enactment)
                following, discrepancy = (after_inspection(account, receipt) if job.action.operation == INSPECT
                    else (None, action_outcome == WorkStatus.FAILED))
                job = replace(job, enactments=job.enactments + (enactment.ref,),
                    observations=job.observations + (receipt.ref,), discrepancy=job.discrepancy or discrepancy)
                if following is not None:
                    job = replace(job, action=following, action_units=0)
                    reason = "inspection delivered; conditional transfer awaits its own paid execution"
                else:
                    application = Application(Ref(Kind.EVIDENCE, "application:" + key, 1), actor, account.ref,
                        job.enactments, job.observations, job.discrepancy, action_outcome)
                    extra.append(application)
                    job = replace(job, result=application.ref)
                    outcome, reason = action_outcome, "consequential application finished; experience remains available"
                if action_outcome == WorkStatus.FAILED:
                    works[-1] = replace(works[-1], outcome=WorkStatus.FAILED,
                                        reason="transfer precondition failed after paid work")
        if outcome == WorkStatus.PARTIAL and job.completed_units == 0:
            outcome, reason = WorkStatus.DEFERRED, "no affordable processing unit; specification retained"
        active = route_active(job.plan, job.completed_units)
        terminal = outcome in (WorkStatus.COMPLETED, WorkStatus.FAILED)
        # A paid failed physical attempt has entered IT; failed memory writes
        # preserve the prior perspective and can be retried with a new task.
        crossed = outcome == WorkStatus.COMPLETED or type(payload) is ApplyDraft and terminal
        state = ProcessingState(replace(old_state.ref, revision=old_state.ref.revision + 1), actor, active,
            movement(payload).route.destination if crossed else old_state.perspective,
            None if terminal else cmd.task_id)
        outputs = tuple(r.ref for r in extra) + tuple(m.ref for m in memories)
        history = job.history + tuple(ProcessingStep(len(job.history) + i, w.operation,
            job.basis + job.observations[:-1] if type(payload) is ApplyDraft and observations else job.basis,
            outputs if i == len(works) - 1 else (), w.ref) for i, w in enumerate(works))
        retained = tuple(m.ref for m in memories) + tuple(r.ref for r in extra if type(r) is Capability)
        witness = MovementRecord(Ref(Kind.MOVEMENT, "movement:" + key, job.attempts + 1), actor, None,
            movement(payload), op, (), job.basis, history, outcome, retained, reason)
        extra.extend((state, witness))
        job = replace(job, history=history, attempts=job.attempts + 1, outcome=outcome)
        event = WorldEvent(event_ref, when, (actor,), (inputs[0].item,) if type(payload) is ApplyDraft else (),
            op.key, self.config.context, tuple(changes), tuple(sorted(causes, key=lambda c: (ref_order(c.event), ref_order(c.rule)))),
            tuple(w.ref for w in works), outcome, reason)
        if not observations:
            observations.append(self._observation(actor, event_ref, when,
                (self._prop(event_ref, "outcome", outcome.value, when),),
                "private realized processing receipt", "local process outcome; factual accuracy separate"))
        self._commit(MetabolicTransaction(cmd, event, tuple(works), tuple(observations), (),
                                         tuple(memories), None, tuple(extra), state, job))
        return event

    def _commit(self, tx):
        if type(tx) is not MetabolicTransaction:
            super()._commit(tx)
            self._processing_changes.append((tx.event.ref, ()))
            return
        refs = tuple(x.ref for x in tx.extra)
        if len(set(refs)) != len(refs) or any(r in self._records for r in refs):
            raise ValueError("duplicate processing record")
        super()._commit(tx)
        for record in tx.extra:
            self._records[record.ref] = record
            self._origins[record.ref] = tx.event.ref
            self._known[tx.command.actor].add(record.ref)
        self._processing_states[tx.command.actor] = tx.state
        self._processing_jobs[(tx.command.actor, tx.command.task_id)] = tx.job
        self._processing_changes.append((tx.event.ref, (tx.command.actor,)))

    def checkpoint(self):
        from .codec import dumps
        return dumps(MetabolicCheckpoint("hle-r4-v1", self.config, self.profiles, self.policy, tuple(self._journal)))

    @classmethod
    def restore(cls, text):
        from .codec import loads
        cp = loads(text)
        if type(cp) is not MetabolicCheckpoint or cp.schema != "hle-r4-v1" or not cp.journal:
            raise ValueError("unsupported or empty metabolic checkpoint")
        world = cls(cp.config, cp.profiles, cp.policy)
        if world._journal[0] != cp.journal[0]: raise ValueError("genesis mismatch")
        for entry in cp.journal[1:]:
            if entry.command is None or entry.command.command_id in world._commands:
                raise ValueError("missing or duplicate command")
            world.execute(entry.command)
            if world._journal[-1] != entry: raise ValueError("metabolic replay mismatch")
        return world
