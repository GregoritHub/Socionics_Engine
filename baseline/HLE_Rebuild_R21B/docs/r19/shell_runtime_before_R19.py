"""R16A live read-only monitor of the existing R15 causal journal.

Only forced placement has sufficient runtime semantics in this adapter. The
other four channels deliberately remain unassessed. No verdict enters policy.
All indexes are derived from transactions and rebuilt by ordinary R15 replay.
"""
from dataclasses import replace
from .compensation import CompensationWorld
from .compensation_records import ReleaseTransaction, ReleasePacket, DEPENDENCY, REQUIRED, WIRE
from .concept_records import ConceptState
from .contracts import Ref, Kind, WorkStatus
from .world_records import ENERGY, TIME
from .autonomy_records import WorkshopCommand
from .crux import Perspective as P, FormalMovement, Route, Polarity
from .concept_structure import conceptual_path
from .processing import _route_geometry
from .shell_records import (Claim, LocalEvidence, ContentPart, TraceOperation,
                            OpportunityEvidence, EngagementTrace)
from .shell_assessment import JointShellAssessment, reftext


def revision_quote(tim, active, extent, positional_prices):
    """Structural tariff only; no participant selection or world lookup."""
    total = 0
    for edge in conceptual_path(tim):
        path, seats, support, at, hops, price = _route_geometry(
            tim, active, edge.element, Polarity.ACCUMULATION, positional_prices)
        total += sum(hops) + max(1, extent) * price; active = path[-1]
    return total


class ShellJournalMonitor:
    def __init__(self, config, profiles, policy, release):
        self.config = config; self.profiles = {p.owner: p for p in profiles}
        self.policy = policy; self.release = release
        self.records = {}; self.facts = {}; self.demands = {}; self.builders = {}; self.active_items = {}
        self.decisions = {}; self.groups = {}; self.traces = []
        self.job_work = {}; self.partial_jobs = {}; self.last_tick = -1
        self.feed_count = 0; self.release_visits = 0; self.closed_visits = 0
        self.errors = []

    def _claim(self, actor, item, loan, needed):
        return Claim(item, 'release_requires_external_confirmation', 'true' if needed else 'false',
                     self.config.context, loan)

    def _append(self, builder, tx, name, claims=(), inputs=(), outputs=(), domains=(P.I,)):
        cmd = tx.command; work = self.job_work.get((cmd.actor, cmd.task_id), tx.works)
        moves = tx.job.movements if type(tx) is ReleaseTransaction else (
            FormalMovement(Route(P.I, P.IT), Polarity.EXPENDITURE),)
        builder['ops'].append(TraceOperation(tx.event.ref, tx.event.when.tick, name,
            tuple(inputs), tuple(outputs), tuple(claims), tuple(w.ref for w in work),
            sum(w.completed_units for w in work), tuple(moves), tuple(domains)))

    def _open(self, tx):
        d = tx.decision; v = d.view; actor = d.owner; key = actor, v.loan
        self.decisions[d.ref] = key
        if key in self.builders:
            b = self.builders[key]
            claim = self._claim(actor, v.item, v.loan, v.required or v.dependency)
            if v.concept not in b['parts']:
                b['parts'][v.concept] = ContentPart(v.concept, b['lineage'], tx.event.when.tick, (claim,))
            self._append(b, tx, 'consider', (claim,), (v.concept,))
            return
        obs = self.records.get(v.terms); concept = self.records.get(v.concept)
        if obs is None or obs.observer != actor or obs.delivered_at.tick > tx.event.when.tick:
            self.errors.append('missing owned terms at ' + reftext(tx.event.ref)); return
        f = {p.relation: p.object for p in obs.content if p.subject == v.item and p.context == self.config.context}
        if f.get(REQUIRED) is not v.required:
            self.errors.append('terms/view mismatch at ' + reftext(tx.event.ref)); return
        dependency = concept is not None and DEPENDENCY in concept.relations
        if dependency != v.dependency:
            self.errors.append('concept/view mismatch at ' + reftext(tx.event.ref)); return
        # With no tension yet, the exact first conceptual revision is a control
        # lineage. It is never pooled with subsequently generated material.
        lineage = d.material or (None if concept is None else Ref(Kind.MEMORY, concept.ref.key, 1))
        if lineage is None or lineage not in self.records:
            self.errors.append('missing addressable lineage'); return
        demand = self.demands.get((actor, v.item))
        eligible_facts = (f.get('condition') == 'clean' and f.get('loan_active') is True
                          and f.get('return_due') is True and f.get('owned_by') == actor)
        before = {a.unit: a.amount for a in tx.works[-1].after}
        tim = tx.job.plan.routing_type
        extent = 1 + self.release.revision_unit * len(v.supports)
        quote = revision_quote(tim, tx.processing.active, extent, self.policy.positional_prices)
        current = tx.job.movements[-1] if tx.job.movements else None
        evidence_claim = self._claim(actor, v.item, v.loan, v.required)
        local = LocalEvidence(obs.ref, actor, obs.delivered_at.tick, tx.event.when.tick,
                              tx.event.ref, (evidence_claim,))
        cap = () if concept is None or not concept.practiced else (concept.ref,)
        opp = OpportunityEvidence(None if demand is None or demand.status != 'active' else demand.specification.ref,
                   'reconcile', ('reconcile',) if eligible_facts and cap else (), cap, quote,
                   before[ENERGY], before[TIME], True, (),
                   tx.event.when.tick if demand is None else demand.specification.duration.start.tick,
                   current, None, tx.event.when.tick)
        part_claim = self._claim(actor, v.item, v.loan, v.required or dependency)
        parts = {} if concept is None else {concept.ref: ContentPart(concept.ref, lineage, 0, (part_claim,))}
        b = {'actor': actor, 'item': v.item, 'loan': v.loan, 'lineage': lineage,
             'tim': self.profiles[actor].tim, 'start': tx.event.when.tick, 'opportunity': opp,
             'evidence': [local], 'parts': parts, 'ops': [], 'placement': None, 'endpoint': 'unassessed'}
        self.builders[key] = b
        self.active_items[actor, v.item] = key
        self._append(b, tx, 'consider', (part_claim,), () if concept is None else (concept.ref,))

    def _release(self, tx):
        self.release_visits += 1; cmd = tx.command
        if tx.decision is not None: self._open(tx); return
        d = None; packet = None
        if cmd.operator == 'enact': d = self.records.get(cmd.source)
        elif cmd.operator in ('review', 'assimilate'):
            obs = self.records.get(cmd.source)
            if obs is not None:
                from .codec import loads
                packet = loads(next(p.object for p in obs.content if p.relation == WIRE))
                d = self.records.get(packet.decision)
        if d is None: return
        b = self.builders.get((d.owner, d.view.loan))
        if b is None: return
        v = d.view; claim = self._claim(d.owner, v.item, v.loan, v.required or v.dependency)
        if cmd.operator == 'enact':
            if d.selection.mode == 'confirm':
                source = tx.concept or self.records.get(v.concept)
                if source is None: return
                b['parts'].setdefault(source.ref, ContentPart(source.ref, b['lineage'], tx.event.when.tick, (claim,)))
                b['placement'] = source.ref
                self._append(b, tx, 'place', (claim,), (v.concept,), (source.ref,), (P.I, P.WE))
            elif d.selection.mode == 'reconcile':
                corrected = self._claim(d.owner, v.item, v.loan, v.required)
                c = tx.concept
                if c is not None:
                    b['parts'][c.ref] = ContentPart(c.ref, b['lineage'], tx.event.when.tick, (corrected,))
                    self._append(b, tx, 'revise', (corrected,), (), (c.ref,))
        elif cmd.operator == 'review':
            # Actual paid peer inspection and response; no new ITS organization.
            inputs = () if b['placement'] is None else (b['placement'],)
            self._append(b, tx, 'review', (), inputs, domains=(P.IT, P.WE))
        elif cmd.operator == 'assimilate':
            obs = self.records[cmd.source]
            b['evidence'].append(LocalEvidence(obs.ref, d.owner, obs.delivered_at.tick,
                tx.event.when.tick, tx.event.ref, (self._claim(d.owner, v.item, v.loan, packet.required),)))
            if b['placement'] is not None:
                # The completed response assimilation retains the dependency.
                current = self.records.get(tx.job.view.concept)
                kept = current is not None and DEPENDENCY in current.relations
                actual = self._claim(d.owner, v.item, v.loan, v.required or kept)
                self._append(b, tx, 'maintain' if kept else 'revise', (actual,), (b['placement'],))

    def _close(self, tx):
        cmd = tx.command
        key = self.active_items.pop((cmd.actor, cmd.inputs[0]), None)
        if key is None: return
        b = self.builders.pop(key)
        f = {r: self.facts[b['item'], r, self.config.context].object
             for r in ('condition', 'loan_active', 'owned_by', 'return_to')
             if (b['item'], r, self.config.context) in self.facts}
        good = f.get('condition') == 'clean' and f.get('loan_active') is False and f.get('owned_by') == f.get('return_to')
        b['endpoint'] = 'correct' if good else 'failed'
        self._append(b, tx, 'return', (), domains=(P.IT,))
        trace = self._trace(b, tx.event.when.tick, True)
        self.traces.append(trace)
        group = self.groups.setdefault(trace.scope, JointShellAssessment())
        group.append(trace); self.closed_visits += len(trace.operations)

    def _trace(self, b, end, closed):
        return EngagementTrace(b['loan'], b['actor'], b['lineage'], self.config.context, b['tim'],
                   'runtime', b['start'], end, b['opportunity'], tuple(b['evidence']),
                   tuple(b['parts'].values()), tuple(b['ops']), ('forced_placement',),
                   closed=closed, endpoint=b['endpoint'])

    def feed(self, tx):
        tick = tx.event.when.tick
        if tick != self.last_tick + 1: raise ValueError('monitor requires one committed journal prefix')
        self.last_tick = tick; self.feed_count += 1
        for change in tx.event.changes:
            p = change.after or change.before; key = p.subject, p.relation, p.context
            if self.facts.get(key) != change.before: self.errors.append('fact history mismatch')
            if change.after is None: self.facts.pop(key, None)
            else: self.facts[key] = change.after
        for record in (tx.event,) + tx.works + tx.observations + tx.messages + tx.memories:
            self.records[record.ref] = record
        for name in ('concept', 'material', 'treatment', 'decision'):
            record = getattr(tx, name, None)
            if record is not None: self.records[record.ref] = record
        for demand in getattr(tx, 'demands', ()):
            if demand.specification.family == 'return_commitment': self.demands[(demand.owner, demand.item)] = demand
        cmd = tx.command
        if cmd is not None and hasattr(cmd, 'task_id') and hasattr(cmd, 'actor'):
            key = cmd.actor, cmd.task_id
            self.job_work.setdefault(key, []).extend(tx.works)
        if type(tx) is ReleaseTransaction:
            key = cmd.actor, cmd.task_id
            if tx.event.outcome in (WorkStatus.PARTIAL, WorkStatus.DEFERRED):
                self.partial_jobs[key] = (tx.event.ref, tx.job.paid, tx.job.plan.required)
            else: self.partial_jobs.pop(key, None)
            if tx.event.outcome == WorkStatus.COMPLETED: self._release(tx)
        elif type(cmd) is WorkshopCommand and cmd.operation == 'return' and tx.event.outcome == WorkStatus.COMPLETED:
            self._close(tx)

    def report(self):
        from .shell_assessment import assess_engagement
        return {'schema': 'r16a-runtime-assessment-v1', 'groups': [x.report() for x in self.groups.values()],
                'open_engagements': [assess_engagement(self._trace(b, self.last_tick, False)) for b in self.builders.values()],
                'incomplete_release_jobs': [{'event': reftext(e), 'paid': paid, 'required': required}
                                            for e, paid, required in self.partial_jobs.values()],
                'events_consumed': self.feed_count, 'completed_release_visits': self.release_visits,
                'closed_operation_visits': self.closed_visits, 'errors': list(self.errors),
                'runtime_coverage': ['forced_placement'],
                'parent_R16': 'open: four runtime channels and the demand-increase gate remain unevidenced'}


class ShellAssessmentWorld(CompensationWorld):
    """Existing behavior and checkpoint bytes, with a disposable derived monitor."""
    def __init__(self, *args, **kwargs):
        self.shell_monitor = None
        super().__init__(*args, **kwargs)
        self.shell_monitor = ShellJournalMonitor(self.config, self.profiles, self.policy, self.release)
        for tx in self._journal: self.shell_monitor.feed(tx)

    def _commit(self, tx):
        super()._commit(tx)
        if self.shell_monitor is not None: self.shell_monitor.feed(self._journal[-1])

    def shell_report(self): return self.shell_monitor.report()
