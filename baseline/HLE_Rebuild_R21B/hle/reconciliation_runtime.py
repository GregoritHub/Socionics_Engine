"""Incremental journal adapter for consequential R16B account operations."""
from .reconciliation_records import AccountTransaction, AccountPart, AUDIT_WIRE
from .contracts import Ref, Kind, WorkStatus
from .world_records import ENERGY, TIME
from .autonomy_records import WorkshopCommand
from .compensation_records import REQUIRED, ReleaseTransaction, DEPENDENCY, WIRE
from .shell_records import Claim, LocalEvidence, ContentPart, TraceOperation, OpportunityEvidence, DemandIncrease, EngagementTrace
from .shell_assessment import JointShellAssessment, json_value, assess_engagement
from .crux import Perspective as P, Route, FormalMovement, Polarity

CHANNELS = ('premature_translation', 'forced_placement', 'new_defensive_structure', 'residual_fragmentation', 'foreclosure')

class AccountMonitor:
    def __init__(self, config, profiles):
        self.config = config; self.profiles = {p.owner:p for p in profiles}
        self.records = {}; self.created = {}; self.demands = {}; self.builders = {}; self.active = {}
        self.work = {}; self.traces = []; self.groups = {}; self.last_tick = -1; self.partial_jobs = {}
        self.completed_visits = 0; self.close_visits = 0; self.errors = []

    def _claim(self, b, value):
        return Claim(b['item'], 'release_requires_external_confirmation', 'true' if value else 'false', self.config.context, b['loan'])

    def feed(self, tx):
        tick = tx.event.when.tick
        if tick != self.last_tick+1: raise ValueError('account monitor needs contiguous journal')
        self.last_tick = tick
        for r in (tx.event,)+tx.observations+tx.messages+tx.works+tx.memories:
            self.records[r.ref] = r
        for attr in ('state','concept','decision','material','treatment'):
            r = getattr(tx,attr,None)
            if r is not None and hasattr(r,'ref'):
                self.records[r.ref] = r; self.created.setdefault(r.ref,tick)
        for p in getattr(tx,'parts',()): self.records[p.ref] = p
        for d in getattr(tx,'demands',()):
            if d.specification.family == 'return_commitment': self.demands[d.owner,d.item] = d
        if tx.command is not None and hasattr(tx.command,'task_id') and hasattr(tx.command,'actor'):
            key = tx.command.actor,tx.command.task_id
            self.work.setdefault(key,[]).extend(tx.works)
        if type(tx) is AccountTransaction:
            if tx.event.outcome in (WorkStatus.PARTIAL,WorkStatus.DEFERRED):
                self.partial_jobs[key] = {'event':json_value(tx.event.ref),'operation':tx.job.operation,'paid':tx.job.paid,'required':tx.job.plan.required}
            else: self.partial_jobs.pop(key,None)
            if tx.event.outcome == WorkStatus.COMPLETED and tx.state is not None:
                self.completed_visits += 1; self._account(tx,self.work[key])
        if type(tx) is ReleaseTransaction and tx.event.outcome == WorkStatus.COMPLETED:
            self._release(tx,self.work[key])
        cmd = tx.command
        if type(cmd) is WorkshopCommand and cmd.operation == 'return' and tx.event.outcome == WorkStatus.COMPLETED:
            key = self.active.pop((cmd.actor,cmd.inputs[0]),None)
            if key is not None:
                b = self.builders.pop(key)
                # Successful original workshop return establishes physical endpoint.
                b['end'] = tick; b['endpoint'] = 'correct'; b['closed'] = True
                work = self.work[cmd.actor,cmd.task_id]
                b['ops'].append(TraceOperation(tx.event.ref,tick,'return',(),(),(),tuple(w.ref for w in work),
                    sum(w.completed_units for w in work),(FormalMovement(Route(P.I,P.IT),Polarity.EXPENDITURE),),(P.IT,)))
                trace = self._trace(b); self.traces.append(trace)
                self.groups.setdefault(trace.scope,JointShellAssessment()).append(trace)
                self.close_visits += len(trace.operations)

    def _release(self,tx,work):
        from .codec import loads
        cmd = tx.command; d = tx.decision
        if d is None and cmd.operator == 'enact': d = self.records.get(cmd.source)
        if d is None and cmd.operator in ('review','assimilate'):
            obs = self.records[cmd.source]
            packet = loads(next(p.object for p in obs.content if p.relation == WIRE))
            d = self.records[packet.decision]
        if d is None: return
        b = self.builders.get((d.owner,d.view.loan))
        if b is None: return
        v = d.view; tick = tx.event.when.tick; name = 'consider'; inputs = outputs = (); domains = (P.I,); claims = ()
        def add(concept,value,created):
            if concept is None: return None
            b['parts'].setdefault(concept.ref,ContentPart(concept.ref,b['lineage'],created,(self._claim(b,value),)))
            return concept.ref
        # Both chains originate in the same actor-owned conceptual account,
        # current item and loan. The original R15 material/treatment identities
        # remain in the journal; this is a scoped observational lineage bridge.
        c = self.records.get(v.concept)
        source = add(c,v.required or v.dependency,self.created[c.ref]) if c is not None else None
        if source is not None: inputs = (source,)
        if cmd.operator == 'consider': claims = (self._claim(b,v.required or v.dependency),)
        elif cmd.operator == 'enact' and d.selection.mode == 'confirm':
            name = 'place'; domains = (P.I,P.WE)
            out = add(tx.concept or c,v.required or v.dependency,tick)
            if out is not None: outputs = (out,); b['placement'] = out
            claims = (self._claim(b,v.required or v.dependency),)
        elif cmd.operator == 'enact':
            name = 'revise'; inputs = ();out = add(tx.concept,v.required,tick)
            outputs = () if out is None else (out,);claims = (self._claim(b,v.required),)
        elif cmd.operator == 'review':
            name = 'review'; domains = (P.IT,P.WE); inputs = () if not b.get('placement') else (b['placement'],)
        elif cmd.operator == 'assimilate':
            current = self.records.get(tx.job.view.concept)
            kept = current is not None and DEPENDENCY in current.relations
            name = 'maintain' if kept else 'revise';claims = (self._claim(b,v.required or kept),)
            inputs = () if not b.get('placement') else (b['placement'],)
        b['ops'].append(TraceOperation(tx.event.ref,tick,name,inputs,outputs,claims,tuple(w.ref for w in work),
            sum(w.completed_units for w in work),tx.job.movements,domains))
        b['end'] = tick

    def _account(self,tx,work):
        s = tx.state; v = tx.job.view; actor = s.owner; key = actor,s.loan
        op = tx.job.operation; tick = tx.event.when.tick
        if op == 'hold':
            obs = self.records[v.terms]; d = self.demands.get((actor,v.item))
            facts = {p.relation:p.object for p in obs.content if p.subject == v.item}
            if obs.observer != actor or facts.get(REQUIRED) != v.required:
                self.errors.append('unowned or mismatched account terms'); return
            current = FormalMovement(Route(P.I,P.I),Polarity.ACCUMULATION)
            required = FormalMovement(Route(P.IT,P.I),Polarity.ACCUMULATION)
            wallet = {r.unit:r.amount for r in work[-1].after}
            concept = self.records[v.concept]
            b = {'actor':actor,'item':v.item,'loan':v.loan,'lineage':s.lineage,'start':tick,'end':tick,
                 'parts':{},'ops':[],'evidence':[],'increase':None,'closed':False,'endpoint':'unassessed',
                 'opportunity':OpportunityEvidence(None if d is None else d.specification.ref,
                    'differentiate_sources',('differentiate_sources',) if concept.practiced else (),
                    (concept.ref,) if concept.practiced else (), tx.job.correction_quote,
                    wallet[ENERGY],wallet[TIME],True,(),tick if d is None else d.specification.duration.start.tick,
                    current,required,tick)}
            b['evidence'].append(LocalEvidence(obs.ref,actor,obs.delivered_at.tick,tick,tx.event.ref,(self._claim(b,v.required),)))
            self.builders[key] = b; self.active[actor,v.item] = key
        b = self.builders.get(key)
        if b is None: return
        b['end'] = tick
        for p in tx.parts: b['parts'][p.ref] = ContentPart(p.ref,s.lineage,tick,(self._claim(b,p.requires),))
        outputs = tuple(p.ref for p in tx.parts if p.role != 'origin'); inputs = (); claims = (); target = ''
        name = op; domains = (P.I,)
        def part(role):
            return next((self.records[r] for r in reversed(s.parts) if self.records[r].role == role),None)
        if op == 'hold': pass
        elif op in ('summarize','separate'):
            inputs = (part('held').ref,); claims = (self._claim(b,part('policy').requires),)
            name = 'translate' if op == 'summarize' else 'differentiate_sources'
            domains = (P.I,) if op == 'summarize' else (P.IT,P.I)
        elif op == 'integrate':
            inputs = (part('policy').ref,); name = 'integrate_closed' if s.complete else 'integrate_open'
        elif op in ('notify_terms','notify_policy'):
            inputs = tuple(r for r in tx.messages[0].based_on if r in b['parts'])
            p = part('terms_component' if op == 'notify_terms' else 'policy_component')
            claims = (self._claim(b,p.requires),); name = 'act'; domains = (P.I,P.WE)
        elif op == 'receive':
            from .codec import loads
            obs = self.records[s.reply]; packet = loads(obs.content[0].object)
            if packet.kind == 'challenge':
                scope = str((actor,s.loan,self.config.context))
                b['increase'] = DemandIncrease(tx.event.ref,tick,(('source_obligations',1),),(('source_obligations',packet.obligations),),scope,scope)
        elif op in ('wrapper','scaffold'):
            name = 'construct'; inputs = (part('policy_component').ref,)
            claims = (self._claim(b,part('structure').requires),)
            if op == 'scaffold': domains = (P.IT,P.I)
        elif op == 'apply':
            name = 'use'; inputs = (part('structure').ref,); claims = (self._claim(b,not s.permission),)
        elif op == 'guard':
            name = 'block'; inputs = (part('structure').ref,); claims = (self._claim(b,part('structure').requires),); target = 'differentiate_sources'
        elif op == 'separate_late':
            name = 'start'; target = 'differentiate_sources'; inputs = (part('structure').ref,)
            claims = (self._claim(b,v.required),); domains = (P.IT,P.I)
        elif op == 'decline':
            from dataclasses import replace
            b['opportunity'] = replace(b['opportunity'],refusal_evidence=(tx.event.ref,))
        if op in ('guard','separate_late'):
            from dataclasses import replace
            wallet = {r.unit:r.amount for r in work[0].before}
            b['opportunity'] = replace(b['opportunity'],required_units=tx.job.correction_quote,
                energy=wallet[ENERGY],time=wallet[TIME],engaged_at=tick)
        b['ops'].append(TraceOperation(tx.event.ref,tick,name,inputs,outputs,claims,tuple(w.ref for w in work),
                            sum(w.completed_units for w in work),tx.job.movements,domains,target))

    def _trace(self,b):
        return EngagementTrace(b['loan'],b['actor'],b['lineage'],self.config.context,self.profiles[b['actor']].tim,
            'runtime',b['start'],b['end'],b['opportunity'],tuple(b['evidence']),tuple(b['parts'].values()),tuple(b['ops']),
            CHANNELS,prerequisites=('differentiate_sources',),increase=b['increase'],closed=b['closed'],endpoint=b['endpoint'])

    def report(self):
        return {'schema':'r16b-runtime-assessment-v1','groups':[g.report() for g in self.groups.values()],
                'open_engagements':[assess_engagement(self._trace(b)) for b in self.builders.values()],
                'incomplete_jobs':json_value(list(self.partial_jobs.values())),
                'events_consumed':self.last_tick+1,'completed_visits':self.completed_visits,
                'closed_operation_visits':self.close_visits,'errors':list(self.errors),'runtime_coverage':list(CHANNELS)}
