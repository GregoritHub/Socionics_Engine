"""Evidence-sensitive R5 assessor on the R4 single transaction journal.

Evaluator records never enter participant input. Changes invalidate only reverse
dependencies; assessment work is explicitly drained in bounded batches. Study
aggregates fold one closed trial at a time, without rescanning earlier trials.
"""
from dataclasses import replace
from bisect import insort
from .contracts import (AssessmentResult, Cause, Dimension, EvidenceStatus as E, IdeaCell, IdeaPhase,
    Kind, MemoryRevision, Moment, Observation, Ref, ResourceAmount, WorkRecord,
    WorkStatus, WorldEvent)
from .assessment_records import (ASSESS, MATERIAL, FEATURES, AssessPending,
    AssessmentCheckpoint, AssessmentTransaction, BeginTrial, CarrierUse,
    DeclareStudy, EndTrial, MaterialCommand, MaterialState, Opportunity, PhaseEvidence, Snapshot,
    Study, StudyAggregate, StudyReport, TrialResult, TrialStart)
from .metabolism import MetabolicWorld
from .metabolism_records import (Account, Application, ApplyDraft, Capability,
    Enactment, MetabolicCommand, MetabolicTransaction, OPERATIONS, operation)
from .world import amounts, fact_key, memory_key, ref_order
from .world_records import ENERGY, TIME, INSPECT, Message, Wallet
from .crux import Perspective


def identity(snapshot, features):
    values = {
        "claim_links": tuple((p.subject, p.relation, p.object, p.context) for p in snapshot.claims),
        "claim_scope": tuple(p.scope for p in snapshot.claims),
        "capacity_rules": snapshot.capacity_rules,
        "perspective": snapshot.perspective,
    }
    return tuple(values[f] for f in features)


def factual(snapshot):
    if E.FAILED in snapshot.checks: return E.FAILED
    if not snapshot.checks or E.UNASSESSED in snapshot.checks: return E.UNASSESSED
    return E.ESTABLISHED


def aggregate(study, previous, result, start):
    adequate = start.request.demanded and start.opportunity.affordable
    blocked = previous.blocked_run + 1 if adequate and result.blocked else 0
    reconstruction = previous.reconstruction_run + 1 if result.reconstruction else 0
    candidate = previous.candidate_seen or max(blocked, reconstruction) >= study.recurrence
    # A quiet interval cannot clear a candidate. Require renewed, completed,
    # evidence-correct realization without the persistent path defect.
    corrected = (adequate and result.completed_operations == study.operations
                 and factual(result.end) == E.ESTABLISHED and result.path == E.ESTABLISHED
                 and not result.reconstruction and not result.blocked)
    items = tuple(sorted(set(previous.capacity_items + result.successful_capacity_items), key=ref_order))
    return StudyAggregate(replace(previous.ref, revision=previous.ref.revision + 1), study.ref,
        previous.trials + 1, blocked, reconstruction, candidate,
        previous.corrected_run + 1 if corrected else 0, items, result.ref,
        previous.failed_return or result.identity == E.FAILED)


def shell_label(study, summary, snapshot, result, start):
    if summary.reconstruction_run >= study.recurrence: return "compensation_candidate"
    if summary.blocked_run >= study.recurrence: return "foreclosure_candidate"
    if summary.candidate_seen:
        if (summary.corrected_run >= study.recurrence and study.item in summary.capacity_items
                and len(summary.capacity_items) > 1): return "cleared_in_tested_demands"
        return "candidate_unresolved"
    if result is None: return "unassessed"
    if not start.request.demanded: return "rest_or_stable_error"
    if start.opportunity.required is None: return "opportunity_unassessed"
    if not start.opportunity.affordable: return "resource_limited"
    if not snapshot.claims: return "ignorance"
    return "no_persistent_candidate"


def phases(study, snapshot, return_status, evidence, config):
    """Cumulative Canon cells for the explicitly supported application predicates.

    I: owned retained memory; IT: ownership grammar; ITS: declared executable
    process. WE has no dyadic definition in R5. No growing-world ALIGN proof.
    """
    out=[]
    contrasts={c.perspective:c for c in study.contrasts}
    definitions={Perspective.I: E.ESTABLISHED if snapshot.memory else E.UNASSESSED,
        Perspective.ITS:E.ESTABLISHED, Perspective.WE:E.UNASSESSED}
    # IT structural eligibility is distinct from the owners' factual equality.
    definitions[Perspective.IT]=E.ESTABLISHED if snapshot.claims and all(
        p.subject==study.item and p.relation=="owned_by" and p.context==config.context
        and p.object in config.actors for p in snapshot.claims) else E.UNASSESSED
    for perspective in (Perspective.I,Perspective.WE,Perspective.IT,Perspective.ITS):
        c=contrasts.get(perspective)
        initiated=E.UNASSESSED if c is None else E.ESTABLISHED if (type(c.left),c.left)!=(type(c.right),c.right) else E.FAILED
        defined=definitions[perspective] if initiated==E.ESTABLISHED else initiated
        engaged=return_status if defined==E.ESTABLISHED else defined
        aligned=E.UNASSESSED if engaged==E.ESTABLISHED else engaged
        for phase,status,reason in zip(IdeaPhase,(initiated,defined,engaged,aligned),(
            "declared distinguishable alternatives", "explicit R5 structural predicate; WE not implemented",
            "recorded exact return tests only", "failed engagement retained; successful finite-composition closure remains unassessed")):
            out.append(PhaseEvidence(IdeaCell(phase,perspective),status,evidence,reason))
    return tuple(out)


class AssessedWorld(MetabolicWorld):
    def __init__(self, config, profiles, policy=None):
        from .metabolism_records import ProcessingPolicy
        self._studies, self._starts, self._trial_results, self._aggregates, self._reports = {}, {}, {}, {}, {}
        self._open_studies, self._dirty, self._dependents = set(), set(), {}
        self._actor_events, self._item_events, self._direct_observations = {}, {}, {}
        self._material_heads, self._due = {}, []
        self.assessment_visits = 0
        super().__init__(config, profiles, ProcessingPolicy() if policy is None else policy)
        self._records[ASSESS] = ASSESS
        self._records[MATERIAL] = MATERIAL

    def pending_assessments(self): return tuple(sorted(self._dirty, key=ref_order))

    def report(self, study): return self._reports.get(study)

    def report_is_current(self, report):
        return self._reports.get(report.study) == report and report.study not in self._dirty

    def material(self, actor, ref):
        value = self._records.get(ref)
        if type(value) is not MaterialState or value.owner != actor: raise ValueError("foreign or absent material")
        return value

    def _snapshot(self, study):
        memory = self.memory_head(study.actor, study.memory_key)
        claims = () if memory is None else tuple(p for p in memory.content
            if p.subject == study.item and p.relation == "owned_by")
        caps = () if memory is None else memory.capabilities
        rules = tuple(sorted({self.truth.resolve(c).rule for c in caps if type(self.truth.resolve(c)) is Capability}))
        checks = tuple(self.truth.check(p, self.now) for p in claims)
        state = self.processing_state(study.actor)
        observed = self._direct_observations.get((study.actor, study.item))
        delivery = None
        if observed is not None:
            p = next(p for p in observed.content if p.subject == study.item and p.relation == "owned_by")
            if self.truth.check(p, self.now).status == E.ESTABLISHED: delivery = observed.ref
        return Snapshot(self.now, None if memory is None else memory.ref, claims, caps, rules,
            state.ref, state.perspective.value, tuple(c.status for c in checks),
            tuple(dict.fromkeys(r for c in checks for r in c.evidence)), delivery)

    def _quote(self, study, request, snapshot):
        interpreted, contradiction = False, False
        for ref in request.corrective:
            o = self._owned(study.actor, ref, (Observation,))
            # Testimony alone is not the same as a checked direct observation.
            source = self._records.get(o.source)
            for p in o.content:
                if (type(source) is WorldEvent and p.subject == study.item and p.relation == "owned_by"
                        and p.context == self.config.context and self.truth.check(p, self.now).status == E.ESTABLISHED):
                    interpreted = True
                    contradiction |= any(fact_key(c) == fact_key(p) and c.object != p.object for c in snapshot.claims)
        if request.offer is None:
            return Opportunity(None, False, interpreted, contradiction, "no executable opportunity supplied")
        if request.offer.actor != study.actor: raise ValueError("foreign offered movement")
        if request.offer.command_id in self._commands: raise ValueError("offer was already executed")
        try:
            job, _ = self._validate_processing(request.offer)
        except ValueError:
            return Opportunity(None, False, interpreted, contradiction, "movement is unavailable in current state")
        remaining = job.plan.required - job.completed_units
        if type(request.offer.payload) is ApplyDraft:
            # Conservative quote includes possible inspect + transfer, even if
            # the hidden precondition will make inspection withhold the transfer.
            remaining += 3 - job.action_units
        wallet = self.truth.wallet(study.actor)
        affordable = min(wallet.energy, wallet.time) >= remaining
        return Opportunity(remaining, affordable, interpreted, contradiction,
            "complete offered movement affordable at opening" if affordable else "insufficient energy or time for offered movement")

    def _events_for(self, start, study):
        refs = (self._actor_events.get(study.actor, [])[start.actor_cursor:]
                + self._item_events.get(study.item, [])[start.item_cursor:])
        return tuple(sorted(set(refs), key=lambda r: self.truth.event(r).when))

    def _close(self, start, study):
        end = self._snapshot(study)
        events = self._events_for(start, study)
        works, completed, applications, enacted, uses = [], [], [], [], []
        initiated = False
        rows = [identity(start.snapshot, study.spec.identity_features)]
        last_snapshot = start.snapshot
        rewritten = False
        for ref in events:
            tx = self._journal[self.truth.event(ref).when.tick]
            works.extend(w for w in tx.works if w.owner == study.actor)
            if type(tx) is MetabolicTransaction and tx.command.actor == study.actor:
                offer = start.request.offer
                if offer is not None and tx.command.task_id == offer.task_id and tx.command.payload == offer.payload:
                    initiated |= any(w.completed_units > 0 for w in tx.works)
                if tx.job.outcome == WorkStatus.COMPLETED:
                    completed.append(operation(tx.command.payload))
                applications.extend(r for r in tx.extra if type(r) is Application)
                enacted.extend(r for r in tx.extra if type(r) is Enactment)
                last_snapshot = replace(last_snapshot, perspective=tx.state.perspective.value)
            for m in tx.memories:
                if m.owner == study.actor and m.ref.key == memory_key(study.actor, study.memory_key):
                    claims = tuple(p for p in m.content if p.subject == study.item and p.relation == "owned_by")
                    rules = tuple(sorted({self.truth.resolve(c).rule for c in m.capabilities if type(self.truth.resolve(c)) is Capability}))
                    last_snapshot = replace(last_snapshot, claims=claims, capacity_rules=rules)
                    rewritten = True
            uses.extend(r for r in getattr(tx, "extra", ()) if type(r) is CarrierUse and r.owner == study.actor)
            row = identity(last_snapshot, study.spec.identity_features)
            if row != rows[-1]: rows.append(row)
        final_row = identity(end, study.spec.identity_features)
        if final_row != rows[-1]: rows.append(final_row)
        units = sum(a.amount for w in works for a in w.charged if a.unit == ENERGY)
        exact_protocol = tuple(completed) == study.operations
        domain = (all(s.claims for s in (start.snapshot, end)) if
                  set(study.spec.identity_features) & {"claim_links", "claim_scope"} else True)
        if "capacity_rules" in study.spec.identity_features:
            domain &= bool(start.snapshot.capacity_rules and end.capacity_rules)
        status = (E.ESTABLISHED if rows[0] == final_row else E.FAILED) if exact_protocol and domain else E.UNASSESSED
        discrepancy = any(a.discrepancy for a in applications)
        externalized = any(u.carrier is not None and u.message is not None for u in uses)
        path = E.FAILED if units > study.max_units or externalized or study.forbid_discrepancy and discrepancy else E.ESTABLISHED
        opportunity = start.opportunity
        blocked = (start.request.demanded and opportunity.affordable
                   and opportunity.interpretable and not initiated)
        reconstruction = (start.request.demanded and opportunity.affordable and opportunity.interpretable
            and opportunity.contradiction and rewritten and units > 0 and factual(end) == E.FAILED
            and identity(start.snapshot, ("claim_links",)) == identity(end, ("claim_links",)))
        if reconstruction: path = E.FAILED
        successful = []
        for a in applications:
            account = self.truth.resolve(a.account)
            if account.guard not in start.snapshot.capacities or a.outcome != WorkStatus.COMPLETED: continue
            actions = tuple(self.truth.resolve(r) for r in a.enactments)
            if actions and actions[0].request.operation == INSPECT: successful.append(account.item)
        visible = tuple(f for i, f in enumerate(study.spec.identity_features) if any(a[i] != b[i] for a, b in zip(rows, rows[1:])))
        net = tuple(f for i, f in enumerate(study.spec.identity_features) if rows[0][i] != final_row[i])
        cancelled = tuple(f for f in visible if f not in net)
        recurs = tuple((i, j) for j in range(1, len(rows)) for i in range(j) if rows[i] == rows[j])
        return TrialResult(replace(start.ref, revision=2), start.ref, study.ref, end, events,
            tuple(w.ref for w in works), units, tuple(completed), status, path, initiated,
            blocked, reconstruction, discrepancy, externalized,
            tuple(sorted(set(successful), key=ref_order)), visible, net, cancelled, recurs,
            "exact declared sequence completed" if exact_protocol else "declared sequence incomplete or different; identity unassessed")

    def _make_report(self, study):
        summary = self._aggregates[study.ref]
        result = None if summary.last is None else self._trial_results[summary.last]
        start = None if result is None else self._starts[result.start]
        snapshot = self._snapshot(study)
        scope = study.spec.protocols[0].ref
        evidence = (study.ref, summary.ref) + (() if result is None else (result.ref,)) + snapshot.fact_evidence
        tested = () if result is None or result.completed_operations != study.operations else ((scope,),)
        capacity = (E.ESTABLISHED if study.item in summary.capacity_items and len(summary.capacity_items) > 1
            else E.UNASSESSED)
        statuses = (factual(snapshot), E.UNASSESSED if result is None else result.identity,
                    E.UNASSESSED if result is None else result.path, capacity)
        reasons = ("pointwise Truth agreement; unresolved and empty claims remain unassessed",
            "last exact declared transformation/return sequence only",
            "actual path charges, discrepancies, reconstruction and external carrier use",
            "retained checking procedure used successfully on original and held-out object")
        results = tuple(AssessmentResult(study.ref, scope, dim, status, evidence, tested, reason)
            for dim, status, reason in zip(Dimension, statuses, reasons))
        previous = self._reports.get(study.ref)
        return StudyReport(Ref(Kind.EVIDENCE, "report:" + study.ref.key + ":" + str(study.ref.revision),
            1 if previous is None else previous.ref.revision + 1), study.ref, self.now, snapshot, results,
            sum(s != E.UNASSESSED for s in snapshot.checks), snapshot.checks.count(E.FAILED),
            snapshot.checks.count(E.UNASSESSED), 1, int(snapshot.current_delivery is not None),
            int(bool(snapshot.claims)), shell_label(study, summary, snapshot, result, start),
            study.provenance, summary.ref,
            phases(study, snapshot, E.FAILED if summary.failed_return else statuses[1], evidence, self.config),
            E.FAILED if summary.failed_return else E.UNASSESSED)

    def execute(self, cmd):
        if type(cmd) not in (DeclareStudy, BeginTrial, EndTrial, AssessPending, MaterialCommand):
            return super().execute(cmd)
        text = cmd.command_id
        if not text.strip(): raise ValueError("blank command ID")
        old = self._commands.get(text)
        if old is not None:
            if old.command != cmd: raise ValueError("command ID reused with different input")
            return old.event
        when = Moment(len(self._journal), 0)
        event_ref = Ref(Kind.EVENT, f"event:{when.tick}", 1)
        extra, works, observations, messages, actors, causes = (), (), (), (), (), ()
        outcome = WorkStatus.COMPLETED
        if type(cmd) is DeclareStudy:
            s = cmd.study
            if (s.ref in self._records or s.actor not in self._actors or s.item not in self._items
                    or s.spec.declared_at != self.now or any(op not in OPERATIONS for op in s.operations)
                    or s.spec.protocols[0].transform != s.operations[0]
                    or s.spec.protocols[0].return_policy != s.operations[-1]):
                raise ValueError("invalid/late/duplicate study or unsupported protocol")
            if any(type(value) is Ref and value not in self._records for c in s.contrasts for value in (c.left,c.right)):
                raise ValueError("unknown contrast reference")
            extra = (s, StudyAggregate(Ref(Kind.EVIDENCE, "aggregate:" + s.ref.key + ":" + str(s.ref.revision), 1), s.ref))
        elif type(cmd) is BeginTrial:
            if cmd.study not in self._studies or cmd.study in self._open_studies or not cmd.key.strip():
                raise ValueError("unknown study or already open trial")
            s = self._studies[cmd.study]
            snap = self._snapshot(s)
            ref = Ref(Kind.DEMAND, "trial:" + cmd.key, 1)
            if ref in self._records: raise ValueError("duplicate trial")
            extra = (TrialStart(ref, cmd, snap, self._quote(s, cmd, snap),
                len(self._actor_events.get(s.actor, ())), len(self._item_events.get(s.item, ()))),)
        elif type(cmd) is EndTrial:
            start = self._starts.get(cmd.trial)
            if start is None or replace(cmd.trial, revision=2) in self._records: raise ValueError("unknown or closed trial")
            s = self._studies[start.request.study]
            result = self._close(start, s)
            extra = (result, aggregate(s, self._aggregates[s.ref], result, start))
        elif type(cmd) is AssessPending:
            selected = self.pending_assessments()[:cmd.limit]
            extra = tuple(self._make_report(self._studies[ref]) for ref in selected)
        else:
            extra, works, observations, messages, outcome, causes = self._material_command(cmd, when, event_ref)
            actors = (cmd.actor,)
        event = WorldEvent(event_ref, when, actors, (), "r5." + type(cmd).__name__, self.config.context,
            (), causes, tuple(w.ref for w in works), outcome,
            "explicit paid material operation" if actors else "evaluator-only operation; no participant information delivery")
        self._commit(AssessmentTransaction(cmd, event, works, observations, messages, (), None, extra))
        return event

    def _material_command(self, cmd, when, event_ref):
        if cmd.actor not in self._actors: raise ValueError("unknown material owner")
        local_key = memory_key(cmd.actor, cmd.key)
        head = self._material_heads.get(local_key)
        if cmd.operation == "generate":
            if head is not None: raise ValueError("material already generated")
            source = self._owned(cmd.actor, cmd.source, (Account,))
            draft = MaterialState(Ref(Kind.EVIDENCE, "material:" + local_key, 1), cmd.actor,
                source.ref, "owned", None, None, (source.ref,))
        else:
            source = self.material(cmd.actor, cmd.source)
            if head != source: raise ValueError("material operation requires current revision")
            account = self._owned(cmd.actor, source.account, (Account,))
            if cmd.operation == "externalize":
                if source.treatment != "owned": raise ValueError("material already externalized")
                draft = replace(source, ref=replace(source.ref, revision=source.ref.revision + 1),
                    treatment="unowned", carrier=account.recipient, previous=source.ref, basis=(source.ref, account.ref))
            elif cmd.operation == "reown":
                if source.treatment != "unowned": raise ValueError("material already owned")
                draft = replace(source, ref=replace(source.ref, revision=source.ref.revision + 1),
                    treatment="owned", carrier=None, previous=source.ref, basis=(source.ref,))
            else: draft = None
        before = self.truth.wallet(cmd.actor)
        spent = min(1, before.energy, before.time)
        after = Wallet(cmd.actor, before.energy-spent, before.time-spent)
        status = WorkStatus.COMPLETED if spent else WorkStatus.DEFERRED
        message, output = (), ()
        if spent:
            if draft is not None: output = (draft,)
            else:
                carrier = source.carrier
                if carrier is not None and (cmd.actor, carrier) in self._links:
                    # The implemented action is a real attribution message. It
                    # conveys a modeled claim, never an evaluator's verdict.
                    p = self._prop(source.ref, "attributed_to", carrier, when)
                    message = (Message(Ref(Kind.MESSAGE, f"message:{when.tick}", 1), cmd.actor,
                        carrier, event_ref, when, (p,), (source.ref,)),)
                elif carrier is not None: status = WorkStatus.FAILED
                output = (CarrierUse(Ref(Kind.EVIDENCE, f"carrier-use:{when.tick}", 1), cmd.actor,
                    source.ref, carrier, None if not message else message[0].ref,
                    "withheld_after_reownership" if carrier is None else status.value),)
        work = WorkRecord(Ref(Kind.WORK, f"work:{when.tick}", 1), cmd.actor, MATERIAL,
            amounts(before), (), (ResourceAmount(ENERGY, spent), ResourceAmount(TIME, spent)),
            amounts(after), 1, spent, status, "one explicit treatment/expression unit; no automatic false-belief drain")
        receipt = self._observation(cmd.actor, event_ref, when,
            (self._prop(event_ref, "outcome", status.value, when),), "private material receipt", "local outcome")
        observations = (receipt,) + tuple(self._observation(m.receiver, m.ref, when, m.content,
            "explicit directed attribution", "testimony; no factual authority") for m in message)
        return output, (work,), observations, message, status, (Cause(self._origins[cmd.source], ASSESS),)

    def _watch_time(self, study):
        m = self.memory_head(study.actor, study.memory_key)
        if m is not None:
            for p in m.content:
                for at in (p.scope.start, p.scope.end):
                    if at is not None and at > self.now:
                        insort(self._due, (-at.tick, -at.order, ref_order(study.ref), study.ref))

    def _commit(self, tx):
        extras = tx.extra if type(tx) is AssessmentTransaction else ()
        refs = tuple(r.ref for r in extras)
        if len(set(refs)) != len(refs) or any(ref in self._records for ref in refs):
            raise ValueError("duplicate assessment record")
        super()._commit(tx)
        for record in extras:
            self._records[record.ref], self._origins[record.ref] = record, tx.event.ref
            if type(record) is Study:
                self._studies[record.ref] = record
                for key in (("actor", record.actor), ("item", record.item)):
                    self._dependents.setdefault(key, set()).add(record.ref)
                self._dirty.add(record.ref); self._watch_time(record)
            elif type(record) is TrialStart:
                self._starts[record.ref] = record
                self._open_studies.add(record.request.study)
                self._dirty.add(record.request.study)
            elif type(record) is TrialResult:
                self._trial_results[record.ref] = record
                self._open_studies.remove(record.study)
                self._dirty.add(record.study)
            elif type(record) is StudyAggregate: self._aggregates[record.study] = record
            elif type(record) is StudyReport:
                self._reports[record.study] = record
                self._dirty.discard(record.study)
                self.assessment_visits += 1
            elif type(record) is MaterialState:
                self._material_heads[record.ref.key.removeprefix("material:")] = record
                self._known[record.owner].add(record.ref)
            elif type(record) is CarrierUse: self._known[record.owner].add(record.ref)
        # Evaluator transactions have no participant receipts or actor changes.
        actors = set(tx.event.actors) | {o.observer for o in tx.observations} | {m.owner for m in tx.memories}
        for actor in actors:
            self._actor_events.setdefault(actor, []).append(tx.event.ref)
            self._dirty.update(self._dependents.get(("actor", actor), ()))
        items = {p.subject for c in tx.event.changes for p in (c.before or c.after,)
                 if p.relation == "owned_by"}
        for item in items:
            self._item_events.setdefault(item, []).append(tx.event.ref)
            self._dirty.update(self._dependents.get(("item", item), ()))
        for o in tx.observations:
            if type(self._records.get(o.source)) is WorldEvent:
                for p in o.content:
                    if p.relation == "owned_by": self._direct_observations[(o.observer, p.subject)] = o
        for m in tx.memories:
            for ref in self._dependents.get(("actor", m.owner), ()):
                study = self._studies[ref]
                if m.ref.key == memory_key(m.owner, study.memory_key): self._watch_time(study)
        while self._due and (-self._due[-1][0], -self._due[-1][1]) <= (self.now.tick, self.now.order):
            self._dirty.add(self._due.pop()[3])

    def checkpoint(self):
        from .codec import dumps
        return dumps(AssessmentCheckpoint("hle-r5-v1", self.config, self.profiles, self.policy, tuple(self._journal)))

    @classmethod
    def restore(cls, text):
        from .codec import loads
        cp = loads(text)
        if type(cp) is not AssessmentCheckpoint or cp.schema != "hle-r5-v1" or not cp.journal:
            raise ValueError("unsupported or empty assessment checkpoint")
        w = cls(cp.config, cp.profiles, cp.policy)
        if w._journal[0] != cp.journal[0]: raise ValueError("genesis mismatch")
        for entry in cp.journal[1:]:
            if entry.command is None or entry.command.command_id in w._commands: raise ValueError("missing or duplicate command")
            w.execute(entry.command)
            if w._journal[-1] != entry: raise ValueError("assessment replay mismatch")
        return w
