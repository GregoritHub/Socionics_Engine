"""R16B consequential release-account work in the existing causal journal.

A finite workflow grammar is supplied. Contents and choices come from actual
owned loan terms, practiced concepts, historical supports and paid messages.
The evaluator is never consulted by participant selection.
"""
from dataclasses import replace
import hashlib
from .shell_runtime import ShellAssessmentWorld
from .reconciliation_records import *
from .compensation_records import DEPENDENCY, REQUIRED
from .compensation import RELEASE_SEAL
from .concept_structure import SEAL
from .conceptual import DONE
from .contracts import Moment, ResourceAmount, Cause
from .world_records import Wallet, ENERGY, TIME, Attempt, Tick, Credit
from .world import amounts
from .processing import route_active
from .crux import Perspective as P, Route, FormalMovement, Polarity

ACCOUNT_SEAL = hashlib.sha256(b'r16b-v1:source-separation:component-check:peer-challenge:wrapper-or-scaffold:paid-guard').hexdigest()
INTERNAL = FormalMovement(Route(P.I, P.I), Polarity.ACCUMULATION)
SEPARATE = FormalMovement(Route(P.IT, P.I), Polarity.ACCUMULATION)
SHARE = FormalMovement(Route(P.I, P.WE), Polarity.EXPENDITURE)

class ReconciliationWorld(ShellAssessmentWorld):
    def __init__(self, *args, account_policy=None, **kwargs):
        self.account_policy = account_policy or ReconciliationPolicy()
        self._accounts = {}; self._account_jobs = {}; self._account_active = {}
        self._account_parts = {}; self._account_queue = {}; self._account_replies = {}
        self._account_consumed = set(); self.account_monitor = None
        super().__init__(*args, **kwargs)
        for r in (AUDIT_RULE, AUDIT_WORK):
            self._records[r] = r
            for known in self._known.values(): known.add(r)
        from .reconciliation_runtime import AccountMonitor
        self.account_monitor = AccountMonitor(self.config, self.profiles)
        for tx in self._journal: self.account_monitor.feed(tx)

    def _part(self, s, role):
        return next((self._account_parts[r] for r in reversed(s.parts)
                     if self._account_parts[r].role == role), None)

    def _message(self, actor, source):
        from .codec import loads
        obs = self._owned(actor, source, (Observation,))
        msg = self._records.get(obs.source)
        if type(msg) is not Message or msg.receiver != actor:
            raise ValueError('owned delivered account message required')
        tx = self._journal[msg.at.tick]
        if type(tx) is not AccountTransaction or msg not in tx.messages or tx.event.outcome != WorkStatus.COMPLETED:
            raise ValueError('account message requires authentic paid origin')
        packet = loads(next(p.object for p in obs.content if p.relation == AUDIT_WIRE))
        if type(packet) is not AccountPacket or (actor, source) in self._account_consumed:
            raise ValueError('invalid or consumed account packet')
        return obs, msg, packet

    def _next(self, view, s):
        p = self.account_policy; n = len(view.supports)
        if s is None: return 'hold', 1
        if s.closed: raise ValueError('account already closed')
        if not p.willing: return 'decline', 1
        if not any(x in s.done for x in ('separate', 'summarize')):
            return ('separate', 1 + p.distinction_unit*n) if p.distinction_unit*n <= 1 else ('summarize', 2)
        if 'integrate' not in s.done: return 'integrate', 2
        if 'notify_terms' not in s.done: return 'notify_terms', 1
        if 'notify_policy' not in s.done: return 'notify_policy', 1
        if 'receive' not in s.done:
            if (view.owner, view.loan) not in self._account_replies: raise ValueError('awaiting delivered peer reply')
            return 'receive', 1
        if s.reply is None: raise ValueError('missing reply')
        packet = self._message(view.owner, s.reply)[2]
        if packet.kind != 'challenge': return 'finish', 1
        if not any(x in s.done for x in ('scaffold', 'wrapper')):
            return ('scaffold', 1+p.scaffold_unit*n) if p.scaffold_unit*n <= 1 else ('wrapper', 2)
        if 'apply' not in s.done: return 'apply', 1
        if 'resolve' not in s.done:
            part = self._part(s, 'structure')
            # Correct structures leave no unresolved source conflict.
            if s.permission is None: raise ValueError('structure has not supplied a release permission')
            if s.permission == (not view.required): return 'resolve', 1
            return ('separate_late', 1+p.distinction_unit*n) if p.distinction_unit*n <= p.guard_unit else ('guard', 1+p.guard_unit)
        return 'finish', 1

    def _prepare_account(self, cmd):
        actor = cmd.actor
        if cmd.source is not None:
            obs, msg, packet = self._message(actor, cmd.source)
            if packet.kind != 'policy' or cmd.source not in self._account_queue.get(actor, ()):
                raise ValueError('reply requires a pending policy notice')
            first = self._records.get(packet.first_notice)
            if type(first) is not Message or first.sender != msg.sender or first.receiver != actor:
                raise ValueError('first notice must share sender and recipient')
            operation, extent, view, prior = 'respond', 2, None, None
            basis = (obs.ref, first.ref)
        else:
            view = self.release_view(actor, cmd.item)
            if not (view.clean and view.due and view.owned): raise ValueError('active clean due loan required')
            c = self._concepts.get(actor)
            if c is None or not c.practiced: raise ValueError('source comparison needs practiced capacity')
            s = self._accounts.get((actor, view.loan)); prior = None if s is None else s.ref
            operation, extent = self._next(view, s)
            basis = (view.terms, view.concept) + view.supports + (() if prior is None else (prior,))
            if operation == 'receive': basis += (self._account_replies[actor, view.loan],)
        plan = self._concept_plan(actor, extent)
        movement = SEPARATE if operation in ('separate', 'separate_late', 'scaffold') else SHARE if operation in ('notify_terms', 'notify_policy', 'respond') else INTERNAL
        quote = self._concept_plan(actor, 1+self.account_policy.distinction_unit*(0 if view is None else len(view.supports))).required
        return AccountJob(cmd, operation, plan, (movement,), view, prior, tuple(dict.fromkeys(basis)), quote)

    def _send_account(self, actor, recipient, packet, when, event, basis):
        from .codec import dumps
        if (actor, recipient) not in self.config.message_links: raise ValueError('no permitted account channel')
        msg = Message(Ref(Kind.MESSAGE, 'r16b:message:'+str(when.tick), 1), actor, recipient, event, when,
                      (self._prop(packet.item, AUDIT_WIRE, dumps(packet), when),), basis)
        obs = self._observation(recipient, msg.ref, when, msg.content, 'paid release-account exchange', 'participant statement, not world truth')
        return (msg,), (obs,)

    def _correct(self, actor, evidence):
        c = self._concepts[actor]
        return replace(c, ref=replace(c.ref, revision=c.ref.revision+1), previous=c.ref,
                       relations=tuple(r for r in c.relations if r != DEPENDENCY),
                       tensions=tuple(t for t in c.tensions if t != 'optional_terms_vs_external_prerequisite'), evidence=evidence)

    def _produce_account(self, job, when, event):
        cmd = job.command; actor = cmd.actor; op = job.operation
        if op == 'respond':
            from .codec import loads
            obs, msg, packet = self._message(actor, cmd.source)
            first = self._records[packet.first_notice]
            previous = loads(first.content[0].object)
            if previous.kind != 'terms' or (previous.owner, previous.item, previous.loan) != (packet.owner, packet.item, packet.loan):
                raise ValueError('same loan notices required')
            # The peer compares received statements, never the borrower's mind.
            kind = 'challenge' if packet.complete and previous.requires != packet.requires else 'accepted' if previous.requires == packet.requires else 'pending'
            reply = AccountPacket(kind, packet.owner, packet.item, packet.loan, previous.requires, kind == 'accepted', msg.ref, 2 if kind == 'challenge' else 1)
            messages, observations = self._send_account(actor, msg.sender, reply, when, event, job.basis)
            return None, (), None, messages, observations
        v = job.view; prior = self._accounts.get((actor, v.loan)); concept = None; parts = []; messages = observations = ()
        lineage = Ref(Kind.MEMORY, 'r16b:material:'+actor.key, 1)
        s = prior or AccountState(Ref(Kind.MEMORY, 'r16b:account:'+v.loan.key, 1), actor, v.item, v.loan, v.terms, v.concept, lineage)
        s = replace(s, ref=replace(s.ref, revision=1 if prior is None else s.ref.revision+1), done=s.done+(op,))
        def make(role, value, basis):
            part = AccountPart(Ref(Kind.MEMORY, 'r16b:part:'+str(when.tick)+':'+role, 1), lineage, actor, v.item, v.loan, role, value, tuple(basis))
            parts.append(part); return part
        if op == 'hold':
            if lineage not in self._records:
                parts.append(AccountPart(lineage, lineage, actor, v.item, v.loan, 'origin', v.dependency, (v.concept, v.terms)))
            make('held', v.required or v.dependency, (v.concept, v.terms))
        elif op in ('separate', 'summarize'):
            held = self._part(prior, 'held')
            make('policy', v.required if op == 'separate' else held.requires, (held.ref, v.terms)+v.supports)
            if op == 'separate' and not v.required: concept = self._correct(actor, job.basis)
        elif op == 'integrate':
            policy = self._part(prior, 'policy')
            make('terms_component', v.required, (v.terms,))
            make('policy_component', policy.requires, (policy.ref,)+v.supports)
            s = replace(s, complete=not self.account_policy.cross_check or v.required == policy.requires)
        elif op in ('notify_terms', 'notify_policy'):
            part = self._part(prior, 'terms_component' if op == 'notify_terms' else 'policy_component')
            obs = self._owned(actor, v.terms, (Observation,))
            recipient = next(p.object for p in obs.content if p.subject == v.item and p.relation == 'return_to')
            packet = AccountPacket('terms' if op == 'notify_terms' else 'policy', actor, v.item, v.loan, part.requires, s.complete, s.notice)
            messages, observations = self._send_account(actor, recipient, packet, when, event, (part.ref,)+part.basis)
            s = replace(s, notice=messages[0].ref if op == 'notify_terms' else s.notice,
                        permission=not part.requires if op == 'notify_policy' else s.permission)
        elif op == 'receive':
            s = replace(s, reply=self._account_replies[actor, v.loan])
        elif op in ('wrapper', 'scaffold'):
            policy = self._part(prior, 'policy_component')
            make('structure', policy.requires if op == 'wrapper' else v.required, (s.reply, policy.ref, v.terms))
            if op == 'scaffold' and not v.required: concept = self._correct(actor, job.basis+(s.reply,))
        elif op == 'apply':
            s = replace(s, permission=not self._part(prior, 'structure').requires)
        elif op in ('guard', 'separate_late', 'resolve'):
            # A guard consumes the queued separation opportunity; no source
            # comparison is performed. The competing operation really revises.
            s = replace(s, done=s.done+('resolve',) if op != 'resolve' else s.done)
            if op == 'separate_late':
                concept = self._correct(actor, job.basis); s = replace(s, permission=not v.required)
                make('correction', v.required, (v.terms,)+v.supports)
        elif op in ('finish', 'decline'):
            s = replace(s, closed=True)
        s = replace(s, parts=s.parts+tuple(p.ref for p in parts))
        return s, tuple(parts), concept, messages, observations

    def _account_work(self, cmd):
        actor = cmd.actor
        if actor not in self._actors: raise ValueError('unknown actor')
        old = self._account_jobs.get((actor, cmd.task_id)); processing = self.processing_state(actor)
        if old is not None:
            if old.outcome in DONE or self._account_active.get(actor) != cmd.task_id:
                raise ValueError('terminal or unowned account job')
            if replace(cmd, command_id=old.command.command_id, work_limit=old.command.work_limit) != old.command:
                raise ValueError('changed account continuation')
        elif processing.busy is not None or actor in self._receiving or actor in self._active_turn:
            raise ValueError('personal processing is busy')
        old = old or self._prepare_account(cmd)
        when = Moment(len(self._journal), 0); event_ref = Ref(Kind.EVENT, 'event:'+str(when.tick), 1)
        wallet = self._wallets[actor]
        spent = min(old.plan.required-old.paid, cmd.work_limit, wallet.energy, wallet.time); paid = old.paid+spent
        status = WorkStatus.COMPLETED if paid == old.plan.required else WorkStatus.PARTIAL if spent else WorkStatus.DEFERRED
        if old.view is not None:
            try: fresh = self.release_view(actor, old.view.item)
            except ValueError: fresh = None
            s = self._accounts.get((actor, old.view.loan))
            if fresh != old.view or (None if s is None else s.ref) != old.prior: status = WorkStatus.FAILED
        state = None; parts = (); concept = None; messages = observations = ()
        if status == WorkStatus.COMPLETED:
            state, parts, concept, messages, observations = self._produce_account(old, when, event_ref)
        ps = replace(processing, ref=replace(processing.ref, revision=processing.ref.revision+1),
                     active=route_active(old.plan, paid), busy=None if status in DONE else 'r16b:'+cmd.task_id)
        wr = Ref(Kind.WORK, 'work:'+str(when.tick)+':account', 1)
        work = WorkRecord(wr, actor, AUDIT_WORK, amounts(wallet), (),
            (ResourceAmount(ENERGY, spent), ResourceAmount(TIME, spent)),
            amounts(Wallet(actor, wallet.energy-spent, wallet.time-spent)), old.plan.required-old.paid, spent, status,
            'paid account work; no output before completion' if status != WorkStatus.FAILED else 'owned input changed; no output published')
        event = WorldEvent(event_ref, when, (actor,), () if cmd.item is None else (cmd.item,), 'r16b.'+old.operation,
                self.config.context, (), tuple(dict.fromkeys(Cause(self._origins[r], AUDIT_RULE) for r in old.basis)), (wr,), status, work.reason)
        self._commit(AccountTransaction(cmd, event, (work,), observations, messages, job=replace(old, paid=paid, outcome=status),
                                       processing=ps, state=state, parts=parts, concept=concept))
        return event

    def execute(self, cmd):
        previous = self._commands.get(cmd.command_id)
        if previous is not None:
            if previous.command != cmd: raise ValueError('command identity reused')
            return previous.event
        if type(cmd) is AccountCommand: return self._account_work(cmd)
        actor = cmd.action.actor if type(cmd) is Attempt else getattr(cmd, 'actor', None)
        if actor in self._account_active and type(cmd) not in (Credit, Tick): raise ValueError('unfinished account work owns processing')
        if type(cmd) is Attempt:
            for draft in (cmd.message, cmd.memory):
                if draft is not None and any(p.relation.startswith('r16b.') for p in draft.content):
                    raise ValueError('account packets require authenticated work')
        return super().execute(cmd)

    def _account_due(self, actor):
        view = self._gate(actor)
        if view is None or view.required: return None
        c = self._concepts.get(actor)
        if c is None or not c.practiced: return None
        obs = self._owned(actor, view.terms, (Observation,))
        lender = next(p.object for p in obs.content if p.subject == view.item and p.relation == 'return_to')
        if (actor, lender) not in self.config.message_links or (lender, actor) not in self.config.message_links: return None
        s = self._accounts.get((actor, view.loan))
        return view if s is None or not s.closed else None

    def autonomy_ready(self, actor):
        if min(self._wallets[actor].energy, self._wallets[actor].time) <= 0: return False
        if actor in self._account_active or self._account_queue.get(actor): return True
        v = self._account_due(actor)
        if v is not None:
            s = self._accounts.get((actor, v.loan))
            if s is not None and 'notify_policy' in s.done and 'receive' not in s.done:
                return (actor, v.loan) in self._account_replies
        return super().autonomy_ready(actor)

    def autonomy_step(self, actor):
        if actor in self._account_active:
            j = self._account_jobs[actor, self._account_active[actor]]
            return self.execute(replace(j.command, command_id='r16b:resume:'+str(len(self._journal))))
        if self.processing_state(actor).busy is None and actor not in self._receiving and actor not in self._active_turn:
            key = 'r16b:'+actor.key+':'+str(len(self._journal)); limit = self._autonomy_policies[actor].work_limit
            if self._account_queue.get(actor):
                return self.execute(AccountCommand(key, key, actor, source=self._account_queue[actor][0], work_limit=limit))
            v = self._account_due(actor)
            if v is not None:
                if not self.autonomy_ready(actor): return None
                return self.execute(AccountCommand(key, key, actor, item=v.item, work_limit=limit))
        return super().autonomy_step(actor)

    def _commit(self, tx):
        super()._commit(tx)
        if type(tx) is AccountTransaction:
            actor = tx.command.actor; j = tx.job
            self._account_jobs[actor, tx.command.task_id] = j
            if j.outcome in DONE: self._account_active.pop(actor, None)
            else: self._account_active[actor] = tx.command.task_id
            self._processing_states[actor] = tx.processing
            self._register(tx.processing.ref, tx.processing, actor, tx.event.ref)
            self._processing_changes[-1] = tx.event.ref, (actor,)
            for p in tx.parts:
                self._account_parts[p.ref] = p; self._register(p.ref, p, actor, tx.event.ref)
            if tx.state is not None:
                s = tx.state; self._accounts[actor, s.loan] = s; self._register(s.ref, s, actor, tx.event.ref)
            if tx.concept is not None:
                self._concepts[actor] = tx.concept; self._register(tx.concept.ref, tx.concept, actor, tx.event.ref)
            if j.outcome == WorkStatus.COMPLETED and j.operation == 'respond':
                self._account_consumed.add((actor, tx.command.source)); self._account_queue[actor].remove(tx.command.source)
            from .codec import loads
            for o in tx.observations:
                p = loads(o.content[0].object)
                if p.kind == 'policy': self._account_queue.setdefault(o.observer, []).append(o.ref)
                elif p.kind in ('challenge', 'accepted', 'pending'): self._account_replies[o.observer, p.loan] = o.ref
        if self.account_monitor is not None: self.account_monitor.feed(tx)

    def checkpoint(self):
        from .codec import dumps, loads
        return dumps(ReconciliationCheckpoint('hle-r16b-v1', loads(super().checkpoint()), self.account_policy, ACCOUNT_SEAL))

    @classmethod
    def restore(cls, text):
        from .codec import loads
        cp = loads(text)
        if type(cp) is not ReconciliationCheckpoint or cp.schema != 'hle-r16b-v1' or cp.seal != ACCOUNT_SEAL:
            raise ValueError('unsupported account checkpoint')
        b = cp.base
        if (b.schema != 'hle-r15-v1' or b.base.schema != 'hle-r145-v1' or b.base.base.schema != 'hle-r14-v1'
                or b.base.journal or b.base.base.journal or b.reference_seal != RELEASE_SEAL
                or b.base.reference_seal != SEAL or b.imported_prefix or b.base.migration_prefix):
            raise ValueError('unsupported parent reference or imported history')
        config = b.base.base
        w = cls(config.config, config.profiles, config.policy, config.agents, config.organization_policies,
                config.semantic_policy, config.workshop, config.autonomy, release=b.release, reviewers=b.reviewers, account_policy=cp.account_policy)
        if not b.journal or w._journal[0] != b.journal[0]: raise ValueError('account genesis mismatch')
        for i, tx in enumerate(b.journal[1:], 1):
            if tx.command is None or tx.command.command_id in w._commands: raise ValueError('missing or repeated command')
            w.execute(tx.command)
            if w._journal[-1] != tx: raise ValueError('account replay mismatch at '+str(i))
        return w

    def account_report(self): return self.account_monitor.report()

    def joint_report(self):
        return self.account_report()

    def shell_report(self):
        """Public five-sign report; the inherited placement view stays available."""
        return self.joint_report()

    def placement_report(self):
        return super().shell_report()

    @classmethod
    def import_r15(cls, text, account_policy=None):
        """Verify and retain an R15/R16A journal; only future work uses the new grammar."""
        from .codec import loads, dumps
        from .compensation import CompensationWorld
        source = CompensationWorld.restore(text)
        return cls.restore(dumps(ReconciliationCheckpoint('hle-r16b-v1',loads(source.checkpoint()),
                           account_policy or ReconciliationPolicy(),ACCOUNT_SEAL)))
