"""R15 generated accommodation and material treatment in the R14.5 journal.

The finite model deliberately permits a locally inexpensive, self-confirming
generalization. Its conceptual distortion is assessable independently of the
truthful particular records and successful physical endpoint. R16 assessment
and R17 developmental conversion are not implemented by this module.
"""
from dataclasses import replace
import hashlib
import json

from .conceptual import ConceptualWorld, DONE
from .concept_records import ConceptTransaction, ConceptCheckpoint
from .concept_structure import SEAL, conceptual_path
from .compensation_records import *
from .compensation_policy import select_release
from .contracts import (Moment, ResourceAmount, Cause, Change, ActionRequest)
from .crux import FormalMovement, Polarity
from .processing import route_active
from .development_contracts import MaterialTreatment, Treatment, validate_material_transition
from .autonomy_records import WorkshopCommand, WorkshopJob, AutonomousTransaction, AutonomousCheckpoint
from .world_records import Wallet, ENERGY, TIME, Attempt, Tick, Credit
from .world import amounts

REFERENCE = {
    'version': 'r15.release.v1',
    'parent_reference': SEAL,
    'invariant': 'accepted item-specific conditions determine whether peer confirmation is necessary',
    'learning': 'successful confirmed returns induce and support a generalized external prerequisite',
    'selection': 'minimize current work; revision reprocesses retained supports; confirmation accommodates the present conflict',
    'status': 'finite implementation hypotheses; no additional canonical rank semantics',
}
RELEASE_SEAL = hashlib.sha256(json.dumps(REFERENCE, sort_keys=True).encode()).hexdigest()


class CompensationWorld(ConceptualWorld):
    def __init__(self, *args, release=None, reviewers=None, legacy_genesis=False, **kwargs):
        self.release = release or ReleaseConfig()
        config = args[0] if args else kwargs['config']
        self.reviewers = tuple(reviewers) if reviewers is not None else tuple(ReviewPolicy(a) for a in config.actors)
        if {p.owner for p in self.reviewers} != set(config.actors) or len(self.reviewers) != len(config.actors):
            raise ValueError('one review policy per actor required')
        if any(i not in {o.item for o in config.ownership} for i in self.release.required_items):
            raise ValueError('required review needs declared items')
        self._review_policies = {p.owner: p for p in self.reviewers}
        self._willing = {p.owner: p.may_review for p in self.reviewers}
        self._release_jobs = {}; self._release_active = {}; self._release_flows = {}
        self._release_terms = {}; self._offers = {}; self._local_loans = {}; self._world_loans = {}
        self._release_supports = {}; self._refused = {}; self._grants = {}; self._release_pass = {}
        self._request_queue = {}; self._response_queue = {}; self._release_consumed = set()
        self._tensions = {}; self._treatments = {}; self._release_decisions = {}
        self._r15_enabled = not legacy_genesis; self._imported_prefix = 0
        self._announced = set() if legacy_genesis else set(config.actors)
        super().__init__(*args, **kwargs)
        for r in (RELEASE_RULE, RELEASE_WORK):
            self._records[r] = r
            for known in self._known.values(): known.add(r)

    def material_state(self, actor):
        if actor not in self._actors: raise ValueError('unknown actor')
        return self._tensions.get(actor), self._treatments.get(actor)

    def _snapshot(self, item, when):
        props = super()._snapshot(item, when)
        if not self._r15_enabled: return props
        if any(p.relation == 'workshop_kind' and p.object == 'tool' for p in props):
            borrower = next((p.object for p in props if p.relation == 'borrower'), None)
            loan = self._world_loans.get(item)
            confirmed = (borrower, item, loan) in self._grants
            props += (self._prop(item, REQUIRED, item in self.release.required_items, when),
                      self._prop(item, CONFIRMED, confirmed, when))
        return props

    def release_view(self, actor, item):
        """Direct owned particulars plus conceptual references; never Truth."""
        if actor not in self._actors: raise ValueError('unknown actor')
        terms = self._release_terms.get((actor, item))
        loan = self._local_loans.get((actor, item))
        if terms is None or loan is None: raise ValueError('no owned current loan terms')
        obs = self._owned(actor, terms, (Observation,))
        facts = {p.relation: p.object for p in obs.content if p.subject == item}
        concept = self._concepts.get(actor)
        carriers = []
        for (owner, peer), ref in self._offers.items():
            if owner != actor or peer == actor: continue
            own = self._owned(actor, ref, (Observation,))
            units = next(p.object for p in own.content if p.subject == peer and p.relation == QUOTE)
            carriers.append(CarrierOption(peer, (ref,), units))
        treatment = self._treatments.get(actor)
        return ReleaseView(actor, item, loan, terms, facts[REQUIRED], facts.get('condition') == 'clean',
                           facts.get('loan_active') is True and facts.get('return_due') is True,
                           facts.get('owned_by') == actor,
                           None if concept is None else concept.ref,
                           concept is not None and DEPENDENCY in concept.relations,
                           tuple(self._release_supports.get(actor, ())),
                           tuple(sorted(carriers, key=lambda c: c.actor.key)),
                           tuple(self._refused.get((actor, loan), ())),
                           None if treatment is None else treatment.ref)

    @staticmethod
    def _basis(view):
        return tuple(dict.fromkeys((view.terms,) + (() if view.concept is None else (view.concept,))
                    + view.supports + tuple(r for c in view.carriers for r in c.evidence)
                    + (() if view.prior_treatment is None else (view.prior_treatment,))))

    def _packet(self, actor, ref, kind):
        from .codec import loads
        obs = self._owned(actor, ref, (Observation,))
        msg = self._records.get(obs.source)
        if type(msg) is not Message or msg.receiver != actor:
            raise ValueError('recipient-owned delivered message required')
        tx = self._journal[msg.at.tick]
        if (type(tx) is not ReleaseTransaction or msg not in tx.messages
                or tx.event.outcome != WorkStatus.COMPLETED):
            raise ValueError('release packet must have an authenticated paid origin')
        props = [p for p in obs.content if p.relation == WIRE]
        if len(props) != 1: raise ValueError('one exact release packet required')
        packet = loads(props[0].object)
        if type(packet) is not ReleasePacket or packet.kind != kind:
            raise ValueError('wrong release packet kind')
        if (actor, ref) in self._release_consumed: raise ValueError('packet already processed')
        return obs, msg, packet

    def _decision(self, actor, ref):
        d = self._records.get(ref)
        if type(d) is not ReleaseDecision or d.owner != actor:
            raise ValueError('owned release decision required')
        if self._release_decisions.get((actor, d.view.loan)) != d.ref:
            raise ValueError('superseded release decision')
        return d

    def _prepare_release(self, cmd):
        actor = cmd.actor; view = selection = None
        prior = self._treatments.get(actor)
        if cmd.operator == 'consider':
            view = self.release_view(actor, cmd.item)
            flow = self._release_flows.get((actor,view.loan))
            if flow is not None and flow[0] != 'retry':
                raise ValueError('this loan already has a selected, pending or completed release decision')
            selection = select_release(view, self.release.revision_unit)
            basis = self._basis(view)
            extent = 1 + len(view.carriers) + len(view.supports) + int(view.dependency)
        elif cmd.operator == 'enact':
            d = self._decision(actor, cmd.source); view = self.release_view(actor, d.view.item)
            if self._release_flows.get((actor, d.view.loan)) != ('selected', d.ref):
                raise ValueError('release decision was already enacted or is no longer selected')
            if replace(view, prior_treatment=d.view.prior_treatment) != d.view:
                raise ValueError('release decision inputs changed')
            if d.treatment != (None if prior is None else prior.ref):
                raise ValueError('material treatment changed before enactment')
            selection = d.selection
            if selection.mode not in ('confirm', 'reconcile'): raise ValueError('no enactable alternative')
            basis = (d.ref,) + self._basis(view); extent = selection.extent
        elif cmd.operator == 'review':
            obs, msg, packet = self._packet(actor, cmd.source, 'request')
            basis = (obs.ref,); extent = self._review_policies[actor].review_units
        elif cmd.operator == 'assimilate':
            obs, msg, packet = self._packet(actor, cmd.source, 'response')
            d = self._decision(actor, packet.decision)
            request = self._records.get(packet.request)
            if (type(request) is not Message or request.sender != actor or request.receiver != msg.sender
                    or d.selection.carrier != msg.sender or d.view.loan != packet.loan or d.view.item != packet.item):
                raise ValueError('response does not match the selected carrier and exact request')
            flow = self._release_flows.get((actor, packet.loan))
            if flow != ('await', request.ref): raise ValueError('response is not for the pending request')
            view = self.release_view(actor, packet.item)
            basis = (obs.ref, d.ref) + self._basis(view); extent = 2
        else:
            basis = (); extent = 1
        tim = self._profiles[actor].tim if self.policy.typed_routing else 'ile'
        return ReleaseJob(cmd, self._concept_plan(actor, extent),
                          tuple(FormalMovement(e.route, Polarity.ACCUMULATION) for e in conceptual_path(tim)),
                          view, selection, tuple(dict.fromkeys(basis)), None if prior is None else prior.ref)

    def _treatment(self, actor, kind, carrier, evidence, work, event, previous=None, consequences=()):
        material = self._tensions.get(actor)
        old = previous if previous is not None else self._treatments.get(actor)
        lineage = material.ref if material is not None else Ref(Kind.MEMORY, 'r15:material:' + actor.key, 1)
        ref = Ref(Kind.MEMORY, 'r15:treatment:' + actor.key, 1 if old is None else old.ref.revision + 1)
        result = MaterialTreatment(ref, lineage, actor, (event,) if old is None else old.source_events,
                    actor, kind, carrier, None if old is None else old.ref,
                    tuple(dict.fromkeys(evidence)), (work,), tuple(dict.fromkeys(consequences)))
        if old is not None: validate_material_transition(old, result)
        return result

    def _send_release(self, actor, peer, packet, event, when, basis):
        from .codec import dumps
        if (actor, peer) not in self.config.message_links: raise ValueError('no directed release channel')
        msg = Message(Ref(Kind.MESSAGE, 'r15:message:' + str(when.tick), 1), actor, peer, event, when,
                      (self._prop(actor, WIRE, dumps(packet), when),), basis)
        obs = self._observation(peer, msg.ref, when, msg.content, 'permitted directed release message',
                                'request expresses a personal prerequisite, not a world truth')
        return (msg,), (obs,)

    def _release_work(self, cmd):
        actor = cmd.actor
        if actor not in self._actors: raise ValueError('unknown actor')
        old = self._release_jobs.get((actor, cmd.task_id)); processing = self.processing_state(actor)
        if old is not None:
            if old.outcome in DONE or self._release_active.get(actor) != cmd.task_id:
                raise ValueError('terminal or unowned release work')
            if replace(cmd, command_id=old.command.command_id, work_limit=old.command.work_limit) != old.command:
                raise ValueError('changed release continuation')
        elif (processing.busy is not None or actor in self._receiving or actor in self._active_turn
              or actor in self._concept_active or actor in self._release_active):
            raise ValueError('personal processing already owned')
        old = old or self._prepare_release(cmd)
        when = Moment(len(self._journal), 0); event_ref = Ref(Kind.EVENT, 'event:' + str(when.tick), 1)
        wallet = self._wallets[actor]
        spent = min(old.plan.required - old.paid, cmd.work_limit, wallet.energy, wallet.time)
        paid = old.paid + spent
        status = WorkStatus.COMPLETED if paid == old.plan.required else WorkStatus.PARTIAL if paid else WorkStatus.DEFERRED
        reason = 'paid local release processing; outputs require complete funding'
        if old.view is not None:
            try: fresh = self.release_view(actor, old.view.item)
            except ValueError: fresh = None
            if fresh != old.view:
                status = WorkStatus.FAILED; reason = 'owned terms, concept or material changed during work; no result published'
        material = treatment = decision = concept = None; messages = observations = ()
        work_ref = Ref(Kind.WORK, 'work:' + str(when.tick) + ':release', 1)
        if status == WorkStatus.COMPLETED:
            view = old.view
            if cmd.operator == 'consider':
                gap = view.dependency and not view.required and view.clean and view.owned and view.due
                previous = self._treatments.get(actor)
                if gap:
                    c = self._concepts[actor]
                    if actor not in self._tensions:
                        material = TensionMaterial(Ref(Kind.MEMORY, 'r15:material:' + actor.key, 1), actor,
                                    c.reference, c.address, DEPENDENCY, event_ref, c.ref, (view.terms,))
                    treatment = self._treatment(actor, Treatment.HOLD, actor, (view.terms, c.ref), work_ref, event_ref)
                    previous = treatment
                root = material or self._tensions.get(actor)
                decision = ReleaseDecision(Ref(Kind.MEMORY, 'r15:decision:' + str(when.tick), 1), actor,
                             view, old.selection, None if root is None else root.ref,
                             None if previous is None else previous.ref)
            elif cmd.operator == 'enact':
                d = self._decision(actor, cmd.source); selection = d.selection
                gap = view.dependency and not view.required
                if selection.mode == 'confirm':
                    if gap:
                        candidate = next(c for c in view.carriers if c.actor == selection.carrier)
                        treatment = self._treatment(actor, Treatment.EXTERNALIZE, selection.carrier,
                                        (view.terms, view.concept) + candidate.evidence, work_ref, event_ref)
                        c = self._concepts[actor]
                        concept = replace(c, ref=replace(c.ref, revision=c.ref.revision + 1), previous=c.ref,
                                  tensions=tuple(sorted(set(c.tensions) | {'optional_terms_vs_external_prerequisite'})),
                                  evidence=(view.terms, treatment.ref))
                    packet = ReleasePacket('request', view.item, view.loan, d.ref,
                               required=view.required, material=d.material,
                               reason='I need your confirmation before I can release this entrusted tool')
                    messages, observations = self._send_release(actor, selection.carrier, packet, event_ref, when,
                                                (d.ref,) + (() if treatment is None else (treatment.ref,)))
                else:
                    c = self._concepts[actor]
                    treatment = self._treatment(actor, Treatment.REOWN, actor,
                                    (view.terms, c.ref) + view.supports, work_ref, event_ref)
                    concept = replace(c, ref=replace(c.ref, revision=c.ref.revision + 1), previous=c.ref,
                              relations=tuple(r for r in c.relations if r != DEPENDENCY),
                              tensions=tuple(t for t in c.tensions if t != 'optional_terms_vs_external_prerequisite'),
                              evidence=(view.terms, treatment.ref))
            elif cmd.operator == 'review':
                obs, msg, request = self._packet(actor, cmd.source, 'request')
                # This is a paid physical inspection boundary, not participant access to Truth.
                facts = {p.relation: p.object for p in self._snapshot(request.item, when)}
                valid = (self._world_loans.get(request.item) == request.loan
                         and facts.get('owned_by') == msg.sender and facts.get('condition') == 'clean'
                         and facts.get('loan_active') is True)
                own_need = any(d.status == 'active' and d.specification.family == 'production'
                               for d in self.own_demands(actor))
                approved = (self._willing[actor] and 'inspect' in self._autonomy_policies[actor].primitives
                            and not own_need and valid)
                packet = ReleasePacket('response', request.item, request.loan, request.decision, msg.ref,
                            approved, facts.get(REQUIRED, False), request.material,
                            'confirmed; current terms require review' if approved and facts.get(REQUIRED) else
                            'confirmed; current terms explicitly permit independent release' if approved else
                            'review declined by own boundary, own need, unavailable inspection or changed physical conditions')
                messages, observations = self._send_release(actor, msg.sender, packet, event_ref, when, (obs.ref,))
            elif cmd.operator == 'assimilate':
                obs, msg, response = self._packet(actor, cmd.source, 'response')
                if response.loan != view.loan or response.required != view.required:
                    status = WorkStatus.FAILED; reason = 'response belongs to superseded loan conditions'
                elif actor in self._tensions and view.dependency and not view.required:
                    treatment = self._treatment(actor, Treatment.EXTERNALIZE, msg.sender,
                                    (obs.ref, view.terms, view.concept), work_ref, event_ref,
                                    consequences=(msg.event,))
            elif cmd.operator == 'announce':
                if actor in self._announced:
                    status = WorkStatus.FAILED; reason = 'review terms have already been announced'
                else:
                    quote = self._prop(actor, QUOTE, self._review_policies[actor].review_units, when)
                    recipients = sorted({actor} | {b for a, b in self.config.message_links if a == actor}, key=lambda r: r.key)
                    observations = tuple(self._observation(b, event_ref, when, (quote,),
                                         'paid public review offer', 'offer is not a guarantee of future willingness') for b in recipients)
        state = replace(processing, ref=replace(processing.ref, revision=processing.ref.revision + 1),
                        active=route_active(old.plan, paid), busy=None if status in DONE else 'r15:' + cmd.task_id)
        work = WorkRecord(work_ref, actor, RELEASE_WORK, amounts(wallet), (),
                          (ResourceAmount(ENERGY, spent), ResourceAmount(TIME, spent)),
                          amounts(Wallet(actor, wallet.energy - spent, wallet.time - spent)),
                          old.plan.required - old.paid, spent, status, reason)
        causes = tuple(dict.fromkeys(Cause(self._origins[r], RELEASE_RULE) for r in old.basis))
        event = WorldEvent(event_ref, when, (actor,), () if cmd.item is None else (cmd.item,),
                           'r15.' + cmd.operator, self.config.context, (), causes, (work_ref,), status, reason)
        self._commit(ReleaseTransaction(cmd, event, (work,), observations, messages, job=replace(old, paid=paid, outcome=status),
                                       processing=state, material=material, treatment=treatment, decision=decision, concept=concept))
        return event

    def execute(self, cmd):
        previous = self._commands.get(cmd.command_id)
        if previous is not None:
            if previous.command != cmd: raise ValueError('command identity reused')
            return previous.event
        if type(cmd) is ReleaseCommand: return self._release_work(cmd)
        actor = cmd.action.actor if type(cmd) is Attempt else getattr(cmd, 'actor', None)
        if actor in self._release_active and type(cmd) not in (Credit, Tick):
            raise ValueError('unfinished release work owns personal processing')
        if type(cmd) is Attempt:
            for draft in (cmd.message, cmd.memory):
                if draft is not None and any(p.relation.startswith('r15.') for p in draft.content):
                    raise ValueError('release evidence requires authenticated paid operations')
        return super().execute(cmd)

    def _integrated(self, cmd, prior, sources, when):
        result = super()._integrated(cmd, prior, sources, when)
        if not self._r15_enabled: return result
        relations = set(result.relations)
        for o in sources:
            tx = self._journal[o.source_time.tick]; c = tx.command
            if (type(c) is WorkshopCommand and c.actor == cmd.actor and c.operation == 'return'
                    and tx.event.outcome == WorkStatus.COMPLETED and tx.event.ref == o.source):
                f = {p.relation: p.object for p in o.content if p.subject == c.inputs[0]}
                if f.get(CONFIRMED) is True: relations.add(DEPENDENCY)
        tensions = set(result.tensions)
        if DEPENDENCY in relations and prior is not None:
            tensions.update(t for t in prior.tensions if t == 'optional_terms_vs_external_prerequisite')
        return replace(result, relations=tuple(sorted(relations)), tensions=tuple(sorted(tensions)))

    def _gate(self, actor):
        s = self.autonomy_state(actor); cmd = s.pending
        if (not self._r15_enabled or type(cmd) is not WorkshopCommand or cmd.operation != 'return'
                or self._pending_status(actor, cmd) in DONE): return None
        try: view = self.release_view(actor, cmd.inputs[0])
        except ValueError: return None
        return view

    def autonomy_ready(self, actor):
        if min(self._wallets[actor].energy, self._wallets[actor].time) <= 0: return False
        if self._r15_enabled and actor not in self._announced: return True
        if actor in self._release_active or self._request_queue.get(actor) or self._response_queue.get(actor): return True
        view = self._gate(actor)
        if view is not None:
            flow = self._release_flows.get((actor, view.loan))
            if flow is not None and flow[0] in ('await', 'wait'): return False
        return super().autonomy_ready(actor)

    def autonomy_step(self, actor):
        if actor in self._release_active:
            job = self._release_jobs[(actor, self._release_active[actor])]
            return self.execute(replace(job.command, command_id='r15:resume:' + actor.key + ':' + str(len(self._journal))))
        available = (self.processing_state(actor).busy is None and actor not in self._receiving
                     and actor not in self._active_turn and actor not in self._concept_active)
        if available:
            key = 'r15:' + actor.key + ':' + str(len(self._journal))
            limit = self._autonomy_policies[actor].work_limit
            if self._r15_enabled and actor not in self._announced:
                return self.execute(ReleaseCommand(key, key, actor, 'announce', work_limit=limit))
            for queue, operator in ((self._response_queue, 'assimilate'), (self._request_queue, 'review')):
                if queue.get(actor):
                    return self.execute(ReleaseCommand(key, key, actor, operator, source=queue[actor][0], work_limit=limit))
            view = self._gate(actor)
            if view is not None:
                flow = self._release_flows.get((actor, view.loan))
                if flow is None or flow[0] == 'retry':
                    return self.execute(ReleaseCommand(key, key, actor, 'consider', view.item, work_limit=limit))
                if flow[0] == 'selected':
                    return self.execute(ReleaseCommand(key, key, actor, 'enact', source=flow[1], work_limit=limit))
                if flow[0] in ('await', 'wait'): return None
        return super().autonomy_step(actor)

    def _workshop(self, cmd):
        # A real physical rule during training, independent of learned beliefs.
        if (self._r15_enabled and cmd.operation == 'return' and len(cmd.inputs) == 1
                and cmd.inputs[0] in self.release.required_items
                and (cmd.actor, cmd.inputs[0], self._world_loans.get(cmd.inputs[0])) not in self._grants):
            if cmd.actor not in self._actors or self.processing_state(cmd.actor).busy is not None:
                raise ValueError('invalid or busy return actor')
            for ref in cmd.based_on: self._owned(cmd.actor, ref, (Observation, MemoryRevision))
            old = self._workshop_jobs.get((cmd.actor, cmd.task_id))
            if old is not None and (old.outcome in DONE or replace(cmd, command_id=old.command.command_id, work_limit=old.command.work_limit) != old.command):
                raise ValueError('changed or terminal return continuation')
            old = old or WorkshopJob(cmd, 2)
            when = Moment(len(self._journal), 0); event_ref = Ref(Kind.EVENT, 'event:' + str(when.tick), 1)
            wallet = self._wallets[cmd.actor]; spent = min(2-old.paid, cmd.work_limit, wallet.energy, wallet.time)
            paid = old.paid + spent
            status = WorkStatus.FAILED if paid == 2 else WorkStatus.PARTIAL if paid else WorkStatus.DEFERRED
            work = WorkRecord(Ref(Kind.WORK, 'work:' + str(when.tick) + ':workshop', 1), cmd.actor,
                       Ref(Kind.PROCEDURE, 'r14.return', 1), amounts(wallet), (),
                       (ResourceAmount(ENERGY, spent), ResourceAmount(TIME, spent)),
                       amounts(Wallet(cmd.actor, wallet.energy-spent, wallet.time-spent)), 2-old.paid, spent, status,
                       'this accepted loan actually requires a current peer confirmation')
            event = WorldEvent(event_ref, when, (cmd.actor,), cmd.inputs, 'r14.return', self.config.context, (),
                       tuple(dict.fromkeys(Cause(self._origins[r], RELEASE_RULE) for r in cmd.based_on)),
                       (work.ref,), status, work.reason)
            observations = () if status not in DONE else (self._observation(cmd.actor, event_ref, when,
                       self._snapshot(cmd.inputs[0], when), 'own paid failed return', 'current exact accepted conditions'),)
            self._commit(AutonomousTransaction(cmd, event, (work,), observations, workshop_job=replace(old, paid=paid, outcome=status)))
            return event
        return super()._workshop(cmd)

    def _commit(self, tx):
        if tx.event.action == 'genesis' and self._r15_enabled:
            extra = tuple(Change(None, self._prop(item, REQUIRED, item in self.release.required_items, tx.event.when))
                          for item, condition in self.workshop.conditions if condition in ('clean', 'dirty'))
            quotes = tuple(self._prop(p.owner, QUOTE, p.review_units, tx.event.when) for p in self.reviewers)
            tx = replace(tx, event=replace(tx.event, changes=tx.event.changes + extra),
                         observations=tuple(replace(o, content=o.content + tuple(c.after for c in extra) + quotes) for o in tx.observations))
        super()._commit(tx)
        c = tx.command
        if type(c) is WorkshopCommand and tx.event.outcome == WorkStatus.COMPLETED and c.operation == 'lend':
            self._world_loans[c.inputs[0]] = tx.event.ref
            for o in tx.observations:
                if o.observer == c.inputs[1]: self._local_loans[(o.observer, c.inputs[0])] = tx.event.ref
        if not self._r15_enabled: return
        if type(tx) is ReleaseTransaction:
            actor = tx.command.actor; cmd = tx.command; j = tx.job
            self._release_jobs[(actor, cmd.task_id)] = j
            if j.outcome in DONE: self._release_active.pop(actor, None)
            else: self._release_active[actor] = cmd.task_id
            self._processing_states[actor] = tx.processing
            self._register(tx.processing.ref, tx.processing, actor, tx.event.ref)
            self._processing_changes[-1] = (tx.event.ref, (actor,))
            for attr, target in (('material', self._tensions), ('treatment', self._treatments), ('concept', self._concepts)):
                record = getattr(tx, attr)
                if record is not None:
                    target[actor] = record; self._register(record.ref, record, actor, tx.event.ref)
            if tx.decision is not None:
                d = tx.decision; self._register(d.ref, d, actor, tx.event.ref)
                self._release_decisions[(actor, d.view.loan)] = d.ref
                mode = d.selection.mode
                self._release_flows[(actor, d.view.loan)] = ('ready' if mode == 'direct' else 'wait' if mode == 'wait' else 'selected', d.ref)
            if j.outcome == WorkStatus.COMPLETED:
                if cmd.operator == 'enact':
                    d = self._records[cmd.source]
                    self._release_flows[(actor, d.view.loan)] = ('await', tx.messages[0].ref) if tx.messages else ('ready', d.ref)
                elif cmd.operator == 'review':
                    self._release_consumed.add((actor, cmd.source)); self._request_queue[actor].remove(cmd.source)
                elif cmd.operator == 'assimilate':
                    from .codec import loads
                    obs = self._records[cmd.source]; msg = self._records[obs.source]
                    packet = loads(obs.content[0].object)
                    self._release_consumed.add((actor, cmd.source)); self._response_queue[actor].remove(cmd.source)
                    if packet.approved:
                        self._grants[(actor, packet.item, packet.loan)] = obs.ref
                        self._release_flows[(actor, packet.loan)] = ('ready', packet.decision)
                    else:
                        self._refused.setdefault((actor, packet.loan), []).append(msg.sender)
                        self._release_flows[(actor, packet.loan)] = ('retry', packet.decision)
                elif cmd.operator == 'boundary': self._willing[actor] = cmd.willingness
                elif cmd.operator == 'announce': self._announced.add(actor)
            elif j.outcome == WorkStatus.FAILED and j.view is not None:
                self._release_flows[(actor, j.view.loan)] = ('retry', None)
                if cmd.operator == 'assimilate':
                    self._response_queue[actor].remove(cmd.source); self._release_consumed.add((actor, cmd.source))
        for o in tx.observations:
            # Only authentic world observations update particulars and offers.
            if o.source.kind != Kind.MESSAGE:
                for p in o.content:
                    if p.relation == REQUIRED: self._release_terms[(o.observer, p.subject)] = o.ref
                    if p.relation == QUOTE and (o.observer, p.subject) in self.config.message_links and (p.subject, o.observer) in self.config.message_links:
                        self._offers[(o.observer, p.subject)] = o.ref
                if type(c) is WorkshopCommand and tx.event.outcome == WorkStatus.COMPLETED:
                    if c.operation == 'return' and c.actor == o.observer:
                        confirmed = any(p.subject == c.inputs[0] and p.relation == CONFIRMED and p.object is True for p in o.content)
                        if confirmed: self._release_supports.setdefault(o.observer, []).append(o.ref)
            if type(tx) is ReleaseTransaction and o.source.kind == Kind.MESSAGE:
                from .codec import loads
                packet = loads(o.content[0].object)
                queue = self._request_queue if packet.kind == 'request' else self._response_queue
                queue.setdefault(o.observer, []).append(o.ref)

    def checkpoint(self):
        from .codec import dumps
        base = AutonomousCheckpoint('hle-r14-v1', self.config, self.profiles, self.policy, self.agents,
                    self.organization_policies, self.semantic_policy, self.workshop, self.autonomy, ())
        parent = ConceptCheckpoint('hle-r145-v1', base, (), self._migration_prefix, SEAL)
        return dumps(CompensationCheckpoint('hle-r15-v1', parent, self.release, self.reviewers,
                                            tuple(self._journal), RELEASE_SEAL, self._imported_prefix))

    @classmethod
    def restore(cls, text):
        from .codec import loads
        cp = loads(text)
        if (type(cp) is not CompensationCheckpoint or cp.schema != 'hle-r15-v1'
                or cp.reference_seal != RELEASE_SEAL or cp.base.reference_seal != SEAL or not cp.journal
                or cp.base.schema != 'hle-r145-v1' or cp.base.base.schema != 'hle-r14-v1'
                or cp.base.journal or cp.base.base.journal or not 0 <= cp.imported_prefix <= len(cp.journal)
                or not 0 <= cp.base.migration_prefix <= cp.imported_prefix):
            raise ValueError('unsupported compensation checkpoint or reference version')
        b = cp.base.base
        w = cls(b.config, b.profiles, b.policy, b.agents, b.organization_policies, b.semantic_policy,
                b.workshop, b.autonomy, release=cp.release, reviewers=cp.reviewers, legacy_genesis=bool(cp.imported_prefix))
        w._migration_prefix = cp.base.migration_prefix; w._imported_prefix = cp.imported_prefix
        if w._journal[0] != cp.journal[0]: raise ValueError('R15 genesis mismatch')
        for i, tx in enumerate(cp.journal[1:], 1):
            w._legacy_replay = i < w._migration_prefix
            w._r15_enabled = i >= cp.imported_prefix
            if tx.command is None or tx.command.command_id in w._commands: raise ValueError('missing or repeated command')
            w.execute(tx.command)
            if w._journal[-1] != tx: raise ValueError('R15 replay mismatch at ' + str(i))
        w._r15_enabled = True; w._legacy_replay = False
        return w

    @classmethod
    def import_r145(cls, text):
        """Validate and preserve old paid history; announce new services afterward.

        Old work receives no R15 prerequisite, support, treatment or cost credit.
        Subsequent actual observations make new loan terms locally available.
        """
        from .codec import loads
        source = ConceptualWorld.restore(text); cp = loads(text); b = cp.base
        w = cls(b.config, b.profiles, b.policy, b.agents, b.organization_policies, b.semantic_policy,
                b.workshop, b.autonomy, legacy_genesis=True)
        w._migration_prefix = cp.migration_prefix
        for i, tx in enumerate(source._journal[1:], 1):
            w._legacy_replay = i < w._migration_prefix
            w.execute(tx.command)
            if w._journal[-1] != tx: raise ValueError('R14.5 import changed an old transaction')
        w._imported_prefix = len(w._journal); w._r15_enabled = True; w._legacy_replay = False
        return w
