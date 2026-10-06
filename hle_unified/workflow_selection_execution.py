"""Paid workflow comparison and admission; native movement remains authoritative."""
from .workflow_execution import WorkflowEngine
from .workflow_records import WorkflowRequest
from .workflow_selection_records import WorkflowSelectionRequest, registry, demand_value, fields_of, dumps
from .workflow_selection_policy import proposals, choose
from .workflow_content import decode
from .operation_records import OperationRequest
from .operations import OperationEngine, record, address, job_address
from .particulars import DetailAddress
from .material import attrs, attributes
from .store import next_version

class WorkflowSelectionEngine(WorkflowEngine):
    SCHEMA = 'hle-full-crux-c7-workflow-selection-v1'

    @staticmethod
    def _registry(): return registry()

    def __init__(self, world, law):
        super().__init__(world, law)
        self._workflow_selections = {}

    def _declare(self, cid, versions):
        if any(v.ref.identity.namespace.startswith('c7ws.') for v in versions):
            raise ValueError('selection records cannot be authored')
        return super()._declare(cid, versions)

    def _disclose(self, cid, actor, source, selectors, subject):
        if source.identity.namespace.startswith('c7ws.'):
            raise ValueError('audit records are not participant knowledge')
        return super()._disclose(cid, actor, source, selectors, subject)

    def workflow_selection_view(self, r):
        view = self.participant_view(r.actor); b = view._bindings.get(r.demand)
        if (b is None or (b.actor, b.context, b.cue, b.target.identity) != (r.actor, r.context, r.cue, r.target.identity)
            or b.endorsement.value in ('retracted', 'disputed') or len(b.content) != 1
            or b.content[0].relation != 'c7ws.need' or b.content[0].subject != b.target or b.content[0].context != r.context):
            raise ValueError('owned paid workflow demand required')
        need = demand_value(decode(b.content[0].object))
        known = self.access._known_refs(r.actor)
        if any(x not in known for x in (r.context, r.cue, r.target)) or r.cue not in self._references:
            raise ValueError('paid context, cue and target required')
        items = []
        for ref in sorted(r.accessible, key=dumps):
            value, paid = self._read_workflow(view, ref, r)
            binding = view._bindings.get(ref)
            if binding is not None and binding.endorsement.value in ('retracted', 'disputed'):
                raise ValueError('withdrawn content cannot be selected')
            items.append(dict(ref=ref, data=value, evidence=tuple((x.delivery, x.key) for x in paid)))
        def visible(ref):
            if ref is None: return {}
            ps = view.resolve(ref)
            if not ps: raise ValueError('unread material or group reference')
            return {p.address.key:p.value for p in ps}
        group = visible(r.group).get('payload')
        profile = self._profiles[r.actor]
        return dict(request=fields_of(r), need=need, items=items, target=visible(r.target), stock=visible(r.stock),
            relation=visible(r.relation), group=decode(group) if group else None,
            profile=profile, tim=attrs(self.world.resolve(profile))['tim'], cursor=self._cursors[r.actor],
            wallet=(self.wallet(r.actor)['energy'], self.wallet(r.actor)['time']),
            evidence=tuple((p.address.delivery,p.address.key) for p in view.resolve(r.target)))

    def _workflow_policy(self, s):
        rows = proposals(s)
        return rows, choose(rows)

    def _start(self, cid, r):
        if type(r) is not WorkflowSelectionRequest: return super()._start(cid, r)
        if r.actor not in self._profiles or r.actor in self._locks or (r.actor,r.key) in self._jobs:
            raise ValueError('free typed participant and unused selection key required')
        s = self.workflow_selection_view(r); rows, selected = self._workflow_policy(s)
        required = 1 + len(s['items']) + len(rows) + sum(x['examined'] for x in rows)
        snapshot = record(address('c7ws.snapshot',r.actor,r.key),'Paid accessible selection inputs',dict(payload=dumps(s)))
        ballot = record(address('c7ws.candidates',r.actor,r.key),'Bounded workflow proposals',dict(payload=dumps(rows)))
        d = fields_of(OperationRequest(r.key,r.actor,'bind',r.context)); d.pop('participants'); d.pop('evidence')
        d.update(record_type='operation',c7ws=True,required=required,completed=0,spent=0,status='pending',failure=None,result=None,
            primitive='bind',route_prepare=required,route_execute=0,started_tick=self._now().tick,
            snapshot=snapshot.ref,candidates=ballot.ref,scanned=len(s['items']),candidate_count=len(rows),
            evaluated=sum(x['examined'] for x in rows),policy='c7-workflow-selection-v1',
            **{'participant.0':r.actor,'lock.0':r.actor,'input.0':r.demand,'dependency.0':self.law})
        job = record(job_address(r.actor,r.key),'Paid workflow candidate comparison',d)
        self._batch(cid,r.actor,(snapshot,ballot,job),evidence=(r.demand,*r.accessible))
        self._jobs[r.actor,r.key]=job.ref; self._reserve(d,job.ref)
        self._workflow_selections[r.actor,r.key]=(r,s,rows,selected)
        return job.ref

    def _advance(self,cid,actor,key,work_limit):
        if (actor,key) in self._workflow_selections: return OperationEngine._advance(self,cid,actor,key,work_limit)
        return super()._advance(cid,actor,key,work_limit)

    def _workflow_child(self,s,row):
        r=s['request']
        return WorkflowRequest(key=r['key']+':movement',actor=r['actor'],recipe=row['recipe'],context=r['context'],cue=r['cue'],
            target=r['target'],inputs=row['inputs'],evidence=tuple(DetailAddress(*a) for a in s['evidence']),
            stock=r['stock'],relation=r['relation'],peer=r['peer'],group=r['group'])

    def _launch_workflow(self,cid,s,row):
        return super()._start(cid,self._workflow_child(s,row))

    def _commit(self,cid,actor,key):
        if (actor,key) not in self._workflow_selections: return super()._commit(cid,actor,key)
        old,d=self._active(actor,key)
        if d['status']!='ready': raise ValueError('comparison must be fully paid')
        r,s,rows,selected=self._workflow_selections[actor,key]
        now=self.workflow_selection_view(r)
        failure='changed_participant_inputs' if any(now[k]!=s[k] for k in s if k!='wallet') else None
        event=self._event(cid,old,'failed' if failure else 'succeeded')
        d.update(status='failed' if failure else 'succeeded',failure=failure,result=event.ref,finished_tick=self._now().tick)
        current=next_version(old,attributes=attributes(d))
        receipt=() if failure else (record(address('u4.receipt',cid),'Paid workflow comparison',dict(actor=actor,operation='bind',
            work_key=key,required=d['required'],completed=d['completed'],spent=d['spent'],**{'input.0':r.demand})),)
        self._batch(cid,actor,(current,*receipt,event),evidence=(old.ref,));self._jobs[actor,key]=current.ref;self._release(d,old.ref)
        child=None
        if failure is None and selected is not None:
            try: child=self._launch_workflow(cid+':native',s,selected)
            except ValueError as exc: failure='native_validation: '+str(exc)
        admission=record(address('c7ws.admission',actor,key),'Native validation after paid comparison',
            dict(operation=current.ref,child=child,failure=failure,completion_claim=False))
        decision=record(address('c7ws.decision',actor,key),'Workflow selection distinct from completion',dict(operation=current.ref,
            snapshot=d['snapshot'],candidates=d['candidates'],selected=None if selected is None else selected['cell'],
            recipe=None if selected is None else selected['recipe'],admission=admission.ref,child=child,failure=failure,
            spent=d['spent'],status='deferred' if selected is None else 'launched' if child else 'rejected',completion_claim=False))
        self._batch(cid+':decision',actor,(admission,decision),evidence=(current.ref,))
        return event.ref
