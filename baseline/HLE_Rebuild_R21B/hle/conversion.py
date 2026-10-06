"""R17 conversion extends the same paid reconciliation/workshop journal.

The finite learner compares constant versus source-conditional prerequisites.
It may release, obtain context, form a provisional organization, practice,
pause, fail, revise, retain and recall. Evidence, not a phase counter, licenses
retention. The harness offers opportunities; it cannot supply a learned answer.
"""
from dataclasses import replace
import hashlib
from .conversion_records import *
from .reconciliation import ReconciliationWorld, ACCOUNT_SEAL, INTERNAL, SEPARATE
from .reconciliation_records import AccountPart
from .compensation_records import DEPENDENCY, REQUIRED, CONFIRMED
from .compensation import RELEASE_SEAL
from .concept_structure import SEAL
from .conceptual import DONE
from .contracts import Moment, ResourceAmount, Cause
from .world_records import Wallet, ENERGY, TIME, Attempt, Tick, Credit
from .world import amounts
from .autonomy_records import WorkshopCommand
from .development_contracts import Treatment
from .development_structure import portage, lap
from .model_a import element_at, position_of
from .processing import _route_geometry, route_active
from .crux import Perspective as P, Route, FormalMovement, Polarity

CONVERSION_SEAL = hashlib.sha256(b'r17-v1:preserved-material:source-context:finite-table:own-two-branch-practice:failed-return-inspection:paid-current-recall:independent-account').hexdigest()

def infer_table(observations):
    """Interpret only explicit accepted conditions, not confirmation occurrence.

    A finite two-input grammar is supplied. Contrasting required and optional
    conditions eliminate both constant hypotheses. No evaluator is consulted.
    """
    values = {p.object for o in observations for p in o.content if p.relation == REQUIRED}
    hypotheses = (((False, False), (True, False)),
                  ((False, True), (True, True)),
                  ((False, False), (True, True)))
    compatible = [h for h in hypotheses if all(dict(h)[v] == v for v in values)]
    return compatible[0] if len(compatible) == 1 else None

class ConversionWorld(ReconciliationWorld):
    def __init__(self, *args, conversion_policy=None, **kwargs):
        self.conversion_policy = conversion_policy or ConversionPolicy()
        self._studies = {}; self._candidates = {}; self._capacities = {}
        self._conversion_jobs = {}; self._conversion_active = {}; self._conversion_uses = {}
        self._practice_pending = {}; self._practice_results = {}; self._conversion_access = {}
        self._conversion_work_refs = {}; self._conversion_started = set()
        self._conversion_checks = {}
        super().__init__(*args, **kwargs)
        for ref in (CONVERSION_RULE, CONVERSION_WORK):
            self._records[ref] = ref
            for known in self._known.values(): known.add(ref)

    def _accessible(self, actor):
        if not self._conversion_access.get(actor, self.conversion_policy.material_access): return False
        s = self._studies.get(actor)
        return s is None or all(r in self._records and r in self._known[actor]
                               for r in (s.material, s.concept_origin, s.account_material))

    def _base_view(self, actor, item):
        return super().release_view(actor, item)

    def _gate(self, actor):
        view = super()._gate(actor)
        if view is None and actor in self._practice_pending:
            view = self.release_view(actor, self._practice_pending[actor].item)
        # A stale scheduled return must encounter its real physical failure
        # and replan. Account/release work cannot claim a usable opportunity.
        return view if view is not None and view.clean and view.owned and view.due else None

    def _recovery_view(self, actor):
        s = self._studies.get(actor)
        if s is None or s.candidate is None: return None
        r = self._candidates[s.candidate]
        if not r.failures: return None
        o = self._owned(actor, r.failures[-1], (Observation,))
        items = {p.subject for p in o.content if p.relation == REQUIRED}
        if len(items) != 1: return None
        v = self._base_view(actor, next(iter(items)))
        return v if v.owned and v.due else None

    def _trial_view(self, actor):
        return self._gate(actor) or self._recovery_view(actor)

    def _valid_use(self, actor, view):
        use = self._conversion_uses.get((actor, view.loan))
        if use is None or not self._accessible(actor) or use.terms != view.terms: return None
        rule = self._candidates.get(use.rule)
        if rule is None or rule.context != self.config.context: return None
        if use.capacity is None:
            study = self._studies.get(actor)
            if study is None or not study.active or study.paused or study.candidate != use.rule: return None
        else:
            cap = self._capacities.get(actor)
            if cap is None or not cap.current or cap.ref != use.capacity or cap.rule != use.rule: return None
        return use

    def release_view(self, actor, item):
        v = self._base_view(actor, item)
        study = self._studies.get(actor)
        if study is None: return v
        use = self._valid_use(actor, v)
        # An executable conditional organization requires paid, current access.
        # Without it, the earlier practiced habit remains the available fallback.
        original = self._records[study.concept_origin]
        dependency = DEPENDENCY in original.relations if use is None else use.required
        return replace(v, dependency=dependency)

    def _account_due(self, actor):
        view = self._gate(actor)
        if view is not None and self._valid_use(actor, view) is not None:
            # The paid owned procedure supplies the source distinction. Asking
            # a peer to accept it again would preserve the external prerequisite.
            return None
        return super()._account_due(actor)

    def _conversion_plan(self, actor, op, extent):
        tim = self._profiles[actor].tim if self.policy.typed_routing else 'ile'
        # Re-aim n(1)=3 -> cp(1)=5 preserves directive. Producing work then
        # targets E(5)=6; a portage never manufactures that directive change.
        accepting = portage(1, 'cp')
        producing = lap(accepting)
        target_seat = accepting if op in ('release', 'context', 'reflect') else producing
        polarity = Polarity.ACCUMULATION if target_seat == accepting else Polarity.EXPENDITURE
        active = self.processing_state(actor).active
        path, seats, support, offset, units, price = _route_geometry(
            tim, active, element_at(tim, target_seat), polarity, self.policy.positional_prices)
        return RoutePlan(self._profiles[actor].tim, tim, path, seats, support, offset, units, max(1, extent)*price)

    def _context_sources(self, actor, study):
        material = self._records[study.material]
        sources = material.evidence_at_origin + tuple(self._release_supports.get(actor, ()))
        # Particulars stay in owned observations; the study only indexes them.
        sources += tuple(r for (a, _), r in self._release_terms.items() if a == actor)
        return tuple(dict.fromkeys(sources))

    def _operation(self, actor):
        s = self._studies.get(actor)
        if s is None or not s.active or s.paused or not self._accessible(actor): return None
        if not s.context_sources: return 'context'
        if s.candidate is None:
            return 'reorganize' if infer_table(tuple(self._owned(actor, r, (Observation,)) for r in s.context_sources)) is not None else None
        if actor in self._practice_results: return 'reflect'
        candidate = self._candidates[s.candidate]
        if set(candidate.covered) == {False, True}:
            return 'retain' if self.conversion_policy.retention else 'archive'
        if not self.conversion_policy.practice or actor in self._practice_pending: return None
        recovery = self._recovery_view(actor)
        if recovery is not None and 'return' not in self._autonomy_policies[actor].primitives: return None
        if recovery is not None and not recovery.clean:
            return 'repair' if 'clean' in self._autonomy_policies[actor].primitives else None
        view = self._trial_view(actor)
        if view is not None and view.clean and view.owned and view.due and self._valid_use(actor, view) is None:
            # No overriding an already enacted carrier decision or account.
            if recovery is not None or ((actor, view.loan) not in self._release_flows and (actor, view.loan) not in self._accounts):
                if self._needs_check(actor, view, candidate):
                    return 'recheck' if 'inspect' in self._autonomy_policies[actor].primitives else None
                return 'try'
        return None

    def _needs_check(self, actor, view, rule):
        return ('fresh_own_inspection' in rule.preconditions
                and self._conversion_checks.get((actor, view.item)) != view.terms)

    def _prepare_conversion(self, cmd):
        actor = cmd.actor; s = self._studies.get(actor); cap = self._capacities.get(actor)
        op = cmd.operator; view = None; result = None; basis = (); extent = 1
        if op == 'release':
            if actor in self._conversion_started: raise ValueError('release already attempted; resume the existing material')
            if actor not in self._tensions: raise ValueError('generated owned material required')
            if not self._accessible(actor): op = 'unavailable'
            else:
                m = self._tensions[actor]; c = self._records[m.concept_at_origin]
                ar = Ref(Kind.MEMORY, 'r16b:material:'+actor.key, 1)
                if type(self._records.get(ar)) is not AccountPart: raise ValueError('held reconciliation lineage required')
                if DEPENDENCY not in c.relations: raise ValueError('no historical compensatory account to convert')
                basis = (m.ref, c.ref, ar, self._treatments[actor].ref)
        elif op == 'advance':
            op = self._operation(actor)
            if op is None: raise ValueError('no available conversion work')
            if op in ('recheck', 'repair'): raise ValueError('candidate requires real paid physical work')
            basis = (s.ref, s.material)
            if op == 'context':
                basis += self._context_sources(actor, s); extent = len(basis)
            elif op == 'reorganize':
                basis += s.context_sources; extent = 3 + len(s.context_sources)
            elif op == 'try':
                view = self._base_view(actor, self._trial_view(actor).item)
                basis += (s.candidate, view.terms); extent = 3
            elif op == 'reflect':
                result = self._practice_results[actor]
                use = self._practice_pending[actor]
                basis += (s.candidate, use.ref, result); extent = 3
            else:
                r = self._candidates[s.candidate]
                basis += (r.ref,) + r.practice; extent = 1 + len(r.practice)
        elif op == 'recall':
            if cap is None or not cap.current or not self._accessible(actor): raise ValueError('no accessible current retained capacity')
            view = self._base_view(actor, cmd.item)
            if not (view.clean and view.owned and view.due): raise ValueError('no usable current loan')
            if self._valid_use(actor, view) is not None: raise ValueError('current use already available')
            if (actor, view.loan) in self._release_flows or (actor, view.loan) in self._accounts:
                raise ValueError('recall must precede this loan decision')
            if self._needs_check(actor, view, self._candidates[cap.rule]):
                raise ValueError('retained procedure requires fresh own inspection')
            basis = (cap.ref, cap.rule, cap.material, view.terms); extent = 3
        elif op in ('pause', 'resume'):
            if s is None or not s.active: raise ValueError('active study required')
            if s.paused == (op == 'pause'): raise ValueError('study already in requested state')
            basis = (s.ref,)
        elif op == 'withdraw':
            if cap is None or not cap.current: raise ValueError('current capacity required')
            basis = (cap.ref,)
        elif op in ('restrict', 'restore_access'):
            if s is None: raise ValueError('owned released material required')
            if self._accessible(actor) == (op == 'restore_access'): raise ValueError('access already in requested state')
            basis = (s.ref, s.material)
        plan = self._conversion_plan(actor, op, extent)
        movement = SEPARATE if op in ('context', 'reflect') else INTERNAL
        return ConversionJob(cmd, op, plan, (movement,), tuple(dict.fromkeys(basis)),
            None if s is None else s.ref, None if cap is None else cap.ref, self._accessible(actor), view, result)

    def _produce_conversion(self, j, when, event, work):
        actor = j.command.actor; op = j.operation
        s = self._studies.get(actor); candidate = capacity = use = treatment = concept = None
        state = None
        def revised(**kw):
            return replace(s, ref=replace(s.ref, revision=s.ref.revision+1), **kw)
        if op == 'release':
            m = self._tensions[actor]
            state = ConversionStudy(Ref(Kind.MEMORY, 'r17:study:'+actor.key, 1), actor, m.ref,
                m.concept_at_origin, Ref(Kind.MEMORY, 'r16b:material:'+actor.key, 1))
            treatment = self._treatment(actor, Treatment.HOLD, actor, j.basis, work, event)
        elif op == 'context': state = revised(context_sources=j.basis[2:])
        elif op == 'reorganize':
            table = infer_table(tuple(self._owned(actor, r, (Observation,)) for r in s.context_sources))
            if table is None: raise ValueError('context does not distinguish the alternatives')
            candidate = ScopeCandidate(Ref(Kind.MEMORY, 'r17:candidate:'+actor.key, 1), actor, s.material,
                self.config.context, table, s.context_sources)
            state = revised(candidate=candidate.ref)
            treatment = self._treatment(actor, Treatment.REVISE, actor, (s.ref,)+s.context_sources, work, event)
        elif op in ('try', 'recall'):
            cap = self._capacities.get(actor) if op == 'recall' else None
            r = self._candidates[cap.rule if cap else s.candidate]
            if r.context != self.config.context: raise ValueError('capacity context differs')
            use = ConversionUse(Ref(Kind.MEMORY, 'r17:use:'+str(when.tick), 1), actor, r.material, r.ref,
                None if cap is None else cap.ref, j.view.item, j.view.loan, j.view.terms, dict(r.table)[j.view.required], event)
        elif op == 'reflect':
            r = self._candidates[s.candidate]; trial = self._practice_pending[actor]
            obs = self._owned(actor, j.result, (Observation,))
            tx = self._journal[obs.source_time.tick]; c = tx.command
            facts = {p.relation:p.object for p in obs.content if p.subject == trial.item}
            authentic = (type(c) is WorkshopCommand and c.actor == actor and c.operation == 'return'
                         and c.inputs == (trial.item,) and tx.event.ref == obs.source)
            if not authentic: raise ValueError('practice needs its own physical consequence')
            success = (tx.event.outcome == WorkStatus.COMPLETED and facts.get('loan_active') is False
                and facts.get('owned_by') == facts.get('return_to') and facts.get('condition') == 'clean'
                and (not trial.required or facts.get(CONFIRMED) is True)
                and (trial.required or facts.get(CONFIRMED) is False))
            candidate = replace(r, ref=replace(r.ref, revision=r.ref.revision+1), previous=r.ref,
                practice=r.practice+(obs.ref,) if success else r.practice,
                failures=r.failures if success else r.failures+(obs.ref,),
                covered=tuple(sorted(set(r.covered) | ({trial.required} if success else set()))),
                preconditions=r.preconditions if success else tuple(sorted(set(r.preconditions) | {'fresh_own_inspection'})))
            state = revised(candidate=candidate.ref)
            treatment = self._treatment(actor, Treatment.REVISE, actor, (r.ref, trial.ref, obs.ref), work, event,
                consequences=(tx.event.ref,))
        elif op in ('retain', 'archive'):
            r = self._candidates[s.candidate]
            if set(r.covered) != {False, True} or len(r.practice) < 2: raise ValueError('both consequential branches required')
            state = revised(active=False)
            if op == 'retain':
                capacity = ConversionCapacity(Ref(Kind.MEMORY, 'r17:capacity:'+actor.key, 1), actor,
                    s.material, r.ref, tuple(self._conversion_work_refs.get(actor, ()))+(work,), r.practice)
                treatment = self._treatment(actor, Treatment.REOWN, actor, (r.ref,)+r.practice, work, event,
                    consequences=tuple(self._records[o].source for o in r.practice))
                c = self._concepts[actor]
                concept = replace(c, ref=replace(c.ref, revision=c.ref.revision+1), previous=c.ref,
                    relations=tuple(x for x in c.relations if x != DEPENDENCY)+(SCOPED,),
                    tensions=tuple(x for x in c.tensions if x != 'optional_terms_vs_external_prerequisite'),
                    evidence=(r.ref, capacity.ref, treatment.ref))
        elif op == 'withdraw':
            c = self._capacities[actor]
            capacity = replace(c, ref=replace(c.ref, revision=c.ref.revision+1), current=False, previous=c.ref)
        elif op in ('pause', 'resume'): state = revised(paused=op == 'pause')
        elif op in ('restrict', 'restore_access'):
            treatment = self._treatment(actor, Treatment.RESTRICT_ACCESS if op == 'restrict' else Treatment.HOLD,
                actor, (s.ref, s.material), work, event)
        return state, candidate, capacity, use, treatment, concept

    def _conversion_work(self, cmd):
        actor = cmd.actor
        if actor not in self._actors: raise ValueError('unknown actor')
        old = self._conversion_jobs.get((actor, cmd.task_id)); processing = self.processing_state(actor)
        if old is not None:
            if old.outcome in DONE or self._conversion_active.get(actor) != cmd.task_id: raise ValueError('terminal or unowned conversion job')
            if replace(cmd, command_id=old.command.command_id, work_limit=old.command.work_limit) != old.command:
                raise ValueError('changed conversion continuation')
        elif processing.busy is not None or actor in self._receiving or actor in self._active_turn:
            raise ValueError('personal processing already owned')
        old = old or self._prepare_conversion(cmd)
        when = Moment(len(self._journal), 0); event_ref = Ref(Kind.EVENT, 'event:'+str(when.tick), 1)
        wallet = self._wallets[actor]
        spent = min(old.plan.required-old.paid, cmd.work_limit, wallet.energy, wallet.time); paid = old.paid+spent
        status = WorkStatus.COMPLETED if paid == old.plan.required else WorkStatus.PARTIAL if spent else WorkStatus.DEFERRED
        s = self._studies.get(actor); c = self._capacities.get(actor)
        stale = ((None if s is None else s.ref) != old.study or (None if c is None else c.ref) != old.capacity
                 or self._accessible(actor) != old.accessible)
        if old.view is not None:
            stale |= self._base_view(actor, old.view.item) != old.view
        if old.result is not None: stale |= self._practice_results.get(actor) != old.result
        if old.operation == 'context': stale |= self._context_sources(actor, s) != old.basis[2:]
        if stale: status = WorkStatus.FAILED
        wr = Ref(Kind.WORK, 'work:'+str(when.tick)+':conversion', 1)
        outputs = (None,)*6 if status != WorkStatus.COMPLETED else self._produce_conversion(old, when, event_ref, wr)
        ps = replace(processing, ref=replace(processing.ref, revision=processing.ref.revision+1),
            active=route_active(old.plan, paid), busy=None if status in DONE else 'r17:'+cmd.task_id)
        reason = 'owned input changed; no publication' if stale else 'paid conversion; access, practice and retention remain distinct'
        work = WorkRecord(wr, actor, CONVERSION_WORK, amounts(wallet), (),
            (ResourceAmount(ENERGY, spent), ResourceAmount(TIME, spent)),
            amounts(Wallet(actor, wallet.energy-spent, wallet.time-spent)), old.plan.required-old.paid, spent, status, reason)
        event = WorldEvent(event_ref, when, (actor,), () if old.view is None else (old.view.item,), 'r17.'+old.operation,
            self.config.context, (), tuple(dict.fromkeys(Cause(self._origins[r], CONVERSION_RULE) for r in old.basis)), (wr,), status, reason)
        self._commit(ConversionTransaction(cmd, event, (work,), job=replace(old, paid=paid, outcome=status), processing=ps,
            study=outputs[0], candidate=outputs[1], capacity=outputs[2], use=outputs[3], treatment=outputs[4], concept=outputs[5]))
        return event

    def execute(self, cmd):
        old = self._commands.get(cmd.command_id)
        if old is not None:
            if old.command != cmd: raise ValueError('command identity reused')
            return old.event
        if type(cmd) is ConversionCommand: return self._conversion_work(cmd)
        actor = cmd.action.actor if type(cmd) is Attempt else getattr(cmd, 'actor', None)
        if actor in self._conversion_active and type(cmd) not in (Tick, Credit): raise ValueError('unfinished conversion owns processing')
        return super().execute(cmd)

    def _recall_due(self, actor):
        cap = self._capacities.get(actor)
        if cap is None or not cap.current or not self._accessible(actor): return None
        v = self._gate(actor)
        if v is None or not (v.clean and v.owned and v.due) or self._valid_use(actor, v) is not None: return None
        if self._needs_check(actor, v, self._candidates[cap.rule]) and 'inspect' not in self._autonomy_policies[actor].primitives: return None
        if (actor, v.loan) in self._accounts or (actor, v.loan) in self._release_flows: return None
        return v

    def autonomy_ready(self, actor):
        if min(self._wallets[actor].energy, self._wallets[actor].time) <= 0: return False
        return actor in self._conversion_active or self._operation(actor) is not None or self._recall_due(actor) is not None or super().autonomy_ready(actor)

    def autonomy_step(self, actor):
        if actor in self._conversion_active:
            j = self._conversion_jobs[actor, self._conversion_active[actor]]
            return self.execute(replace(j.command, command_id='r17:resume:'+str(len(self._journal))))
        if self.processing_state(actor).busy is None and actor not in self._receiving and actor not in self._active_turn:
            op = self._operation(actor); v = self._recall_due(actor)
            if op is not None or v is not None:
                key = 'r17:'+actor.key+':'+str(len(self._journal))
                check_view = self._trial_view(actor) if op in ('recheck', 'repair') else v
                if op in ('recheck', 'repair') or (op is None and v is not None
                        and self._needs_check(actor, v, self._candidates[self._capacities[actor].rule])):
                    return self.execute(WorkshopCommand(key, key, actor, 'clean' if op == 'repair' else 'inspect', (check_view.item,),
                        based_on=(check_view.terms,),
                        work_limit=self._autonomy_policies[actor].work_limit))
                return self.execute(ConversionCommand(key, key, actor, 'advance' if op else 'recall',
                    None if op else v.item, self._autonomy_policies[actor].work_limit))
            u = self._practice_pending.get(actor)
            if u is not None and self._release_flows.get((actor, u.loan), (None,))[0] == 'ready':
                pending = self.autonomy_state(actor).pending
                if pending is None or self._pending_status(actor, pending) in DONE:
                    key = 'r17:retry-return:'+str(len(self._journal))
                    return self.execute(WorkshopCommand(key, key, actor, 'return', (u.item,), based_on=(u.terms,),
                        work_limit=self._autonomy_policies[actor].work_limit))
        return super().autonomy_step(actor)

    def _integrated(self, cmd, prior, sources, when):
        c = super()._integrated(cmd, prior, sources, when)
        if prior is not None and SCOPED in prior.relations:
            c = replace(c, relations=tuple(r for r in c.relations if r != DEPENDENCY))
        return c

    def _commit(self, tx):
        super()._commit(tx)
        if type(tx) is ConversionTransaction:
            actor = tx.command.actor; j = tx.job
            self._conversion_jobs[actor, tx.command.task_id] = j
            self._conversion_work_refs.setdefault(actor, []).extend(w.ref for w in tx.works)
            if j.outcome in DONE: self._conversion_active.pop(actor, None)
            else: self._conversion_active[actor] = tx.command.task_id
            self._processing_states[actor] = tx.processing
            self._register(tx.processing.ref, tx.processing, actor, tx.event.ref)
            self._processing_changes[-1] = tx.event.ref, (actor,)
            for attr, target in (('study', self._studies), ('capacity', self._capacities),
                                 ('treatment', self._treatments), ('concept', self._concepts)):
                value = getattr(tx, attr)
                if value is not None:
                    target[actor] = value; self._register(value.ref, value, actor, tx.event.ref)
            if tx.candidate is not None:
                self._candidates[tx.candidate.ref] = tx.candidate
                self._register(tx.candidate.ref, tx.candidate, actor, tx.event.ref)
            if tx.use is not None:
                u = tx.use; self._conversion_uses[actor, u.loan] = u
                self._register(u.ref, u, actor, tx.event.ref)
                if j.operation == 'try': self._practice_pending[actor] = u
            if j.outcome == WorkStatus.COMPLETED:
                if j.operation in ('release', 'unavailable'): self._conversion_started.add(actor)
                if j.operation == 'reflect':
                    u = self._practice_pending.pop(actor); self._practice_results.pop(actor)
                    self._conversion_uses.pop((actor, u.loan), None)
                if j.operation in ('restrict', 'restore_access'):
                    self._conversion_access[actor] = j.operation == 'restore_access'
        cmd = tx.command
        if type(cmd) is WorkshopCommand and cmd.operation == 'inspect' and tx.event.outcome == WorkStatus.COMPLETED:
            obs = next((o for o in tx.observations if o.observer == cmd.actor and o.source == tx.event.ref), None)
            if obs is not None: self._conversion_checks[cmd.actor, cmd.inputs[0]] = obs.ref
        if type(cmd) is WorkshopCommand and cmd.operation == 'return' and tx.event.outcome in DONE:
            u = self._practice_pending.get(cmd.actor)
            if u is not None and cmd.inputs == (u.item,):
                obs = next((o for o in tx.observations if o.observer == cmd.actor and o.source == tx.event.ref), None)
                if obs is not None: self._practice_results[cmd.actor] = obs.ref

    def checkpoint(self):
        from .codec import dumps, loads
        return dumps(ConversionCheckpoint('hle-r17-v1', loads(super().checkpoint()), self.conversion_policy, CONVERSION_SEAL))

    @classmethod
    def restore(cls, text):
        from .codec import loads
        cp = loads(text)
        if type(cp) is not ConversionCheckpoint or cp.schema != 'hle-r17-v1' or cp.seal != CONVERSION_SEAL:
            raise ValueError('unsupported conversion checkpoint')
        r = cp.base; b = r.base
        if (r.schema != 'hle-r16b-v1' or r.seal != ACCOUNT_SEAL or b.schema != 'hle-r15-v1'
            or b.base.schema != 'hle-r145-v1' or b.base.base.schema != 'hle-r14-v1'
            or b.reference_seal != RELEASE_SEAL or b.base.reference_seal != SEAL
            or b.base.journal or b.base.base.journal or b.imported_prefix or b.base.migration_prefix):
            raise ValueError('unsupported conversion parent')
        c = b.base.base
        w = cls(c.config, c.profiles, c.policy, c.agents, c.organization_policies, c.semantic_policy,
            c.workshop, c.autonomy, release=b.release, reviewers=b.reviewers,
            account_policy=r.account_policy, conversion_policy=cp.policy)
        if not b.journal or w._journal[0] != b.journal[0]: raise ValueError('conversion genesis mismatch')
        for i, tx in enumerate(b.journal[1:], 1):
            if tx.command is None or tx.command.command_id in w._commands: raise ValueError('missing or repeated command')
            w.execute(tx.command)
            if w._journal[-1] != tx: raise ValueError('conversion replay mismatch at '+str(i))
        return w

    @classmethod
    def import_r16(cls, text, conversion_policy=None):
        from .codec import loads, dumps
        source = ReconciliationWorld.restore(text)
        return cls.restore(dumps(ConversionCheckpoint('hle-r17-v1', loads(source.checkpoint()),
            conversion_policy or ConversionPolicy(), CONVERSION_SEAL)))
