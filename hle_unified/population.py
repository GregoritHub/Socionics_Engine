"""Bounded fair continuation of independently owned C6 demands.

Engineering policy, not spontaneous goal formation. This scheduler chooses only
whose paid turn runs. C6 chooses the content movement. No truth is used to pick
a route, no energy is replenished, and an exhausted partial job is retained.
"""
from dataclasses import replace
from .selection_execution import SelectionEngine
from .selection_records import SelectionRequest, fields_of, dumps, loads
from .operation_records import OperationRequest
from .operations import address
from .material import attrs


class Population:
    LEGACY_SCHEMA = 'hle-c7-population-v2'
    SCHEMA = 'hle-c7-workflow-population-v3'

    def __init__(self, engine, requests, episodes=24, quantum=32, repeat_limit=2):
        from .workflow_selection_records import WorkflowSelectionRequest, WorkflowCapacitySelectionRequest
        requests = tuple(requests)
        allowed = (SelectionRequest, WorkflowSelectionRequest, WorkflowCapacitySelectionRequest)
        if not requests or any(type(r) not in allowed for r in requests):
            raise ValueError('owned legacy or workflow selection requests required')
        if len({r.actor for r in requests}) != len(requests):
            raise ValueError('one independent demand per actor')
        if any(type(x) is not int or x < 1 for x in (episodes, quantum)):
            raise ValueError('positive finite episode and work budgets required')
        if repeat_limit is not None and (type(repeat_limit) is not int or repeat_limit < 1):
            raise ValueError('positive repeat limit or explicit None required')
        self.repeat_limit = repeat_limit
        self.signatures = [None] * len(requests)
        self.repeats = [0] * len(requests)
        self.engine = engine
        self.requests = requests
        self.episodes, self.quantum = episodes, quantum
        self.cursor = self.turn = 0
        self.counts = [0] * len(requests)
        self.stopped = [None] * len(requests)
        self.feedback = [None] * len(requests)
        self.events = []
        # Reject foreign or malformed goals before starting any work.
        for r in requests:
            self._selection_view(r)

    @staticmethod
    def _is_workflow(r):
        from .workflow_selection_records import WorkflowSelectionRequest, WorkflowCapacitySelectionRequest
        return type(r) in (WorkflowSelectionRequest, WorkflowCapacitySelectionRequest)

    def _selection_view(self, r):
        return self.engine.workflow_selection_view(r) if self._is_workflow(r) else self.engine.selection_view(r)

    @staticmethod
    def _keys(r):
        if Population._is_workflow(r):
            return (r.key, r.key + ':movement', r.key + ':feedback')
        return (r.key, r.key + ':admission', r.key + ':movement', r.key + ':feedback')

    def _participate(self, cid, r):
        if not self._is_workflow(r):
            return self.engine.participate(cid, r, self.quantum)
        if (r.actor, r.key) not in self.engine._jobs:
            self.engine.start(cid + ':start', r)
        for key in (r.key, r.key + ':movement'):
            if (r.actor, key) not in self.engine._jobs:
                continue
            d = self.engine.job_status(r.actor, key)
            if d['status'] in ('cancelled', 'succeeded', 'failed'):
                continue
            if d['status'] != 'ready':
                self.engine.advance(cid + ':work:' + key, r.actor, key, self.quantum)
            if self.engine.job_status(r.actor, key)['status'] == 'ready':
                self.engine.commit(cid + ':commit:' + key, r.actor, key)
            return self.engine.job_status(r.actor, key)
        return None

    def request(self, index):
        r = self.requests[index]
        return replace(r, key='c7:' + r.key + ':' + str(self.counts[index]))

    @property
    def done(self):
        return all(s is not None or c >= self.episodes for s, c in zip(self.stopped, self.counts))

    def step(self):
        if self.done:
            return None
        n = len(self.requests)
        i = next((self.cursor + j) % n for j in range(n)
                 if self.stopped[(self.cursor + j) % n] is None
                 and self.counts[(self.cursor + j) % n] < self.episodes)
        self.cursor = (i + 1) % n
        r = self.request(i)
        cid = 'c7-turn:' + str(self.turn)
        self.turn += 1
        before = self.engine.wallet(r.actor)
        row = dict(turn=self.turn, actor=r.actor, episode=self.counts[i], key=r.key)
        if min(before[k] for k in ('energy', 'time')) == 0:
            self.stopped[i] = 'exhausted'
            row['status'] = 'exhausted'
        elif r.actor in self.engine._locks and not any(
                (r.actor, key) in self.engine._jobs and
                self.engine.job_status(r.actor, key)['status'] not in ('succeeded', 'failed', 'cancelled')
                for key in self._keys(r)):
            row['status'] = 'blocked_by_other_work'
        elif self.feedback[i] is not None:
            key = r.key + ':feedback'
            if (r.actor, key) not in self.engine._jobs:
                self.engine.start(cid + ':start', OperationRequest(key, r.actor, 'read', r.context,
                                                                  delivery=self.feedback[i]))
            d = self.engine.job_status(r.actor, key)
            if d['status'] not in ('succeeded', 'failed', 'cancelled'):
                if d['status'] != 'ready':
                    self.engine.advance(cid + ':read', r.actor, key, self.quantum)
                if self.engine.job_status(r.actor, key)['status'] == 'ready':
                    self.engine.commit(cid + ':commit', r.actor, key)
            d = self.engine.job_status(r.actor, key)
            row.update(status='feedback_' + d['status'])
            if d['status'] in ('succeeded', 'failed', 'cancelled'):
                self.feedback[i] = None
                self.counts[i] += 1
        else:
            outcome = self._participate(cid, r)
            row['status'] = 'working' if outcome is not None else 'episode_complete'
            if outcome is not None:
                row.update(job_status=outcome['status'], spent=outcome['spent'])
            else:
                ref = address('c7ws.decision' if self._is_workflow(r) else 'c6.decision', r.actor, r.key)
                decision = attrs(self.engine.world.resolve(ref))
                row.update(decision=ref, recipe=decision['recipe'], failure=decision['failure'])
                key = r.key + ':movement'
                child = self.engine.job_status(r.actor, key) if (r.actor, key) in self.engine._jobs else None
                if child:
                    row.update(native_status=child['status'], output=child.get('binding') or child.get('result'))
                # Only one's own actual material event is delivered. Paid reading
                # is a separate future turn. No global stock refresh is performed.
                if child and child.get('result') and child.get('primitive') in ('inspect', 'consume', 'use', 'repair', 'care', 'damage'):
                    delivery = cid + ':own-event'
                    self.engine.deliver_event(delivery, child['result'], r.actor)
                    self.feedback[i] = delivery
                else:
                    self.counts[i] += 1
                    # A paid duplicate can be a stable but wrong account. Stop
                    # this supplied demand; do not call it development or truth.
                    if child and child['status']=='succeeded' and child.get('binding') and not any(k.startswith('public.') for k in child):
                        binding=self.engine.participant_view(r.actor)._bindings[child['binding']]
                        signature=(binding.actor,binding.context,binding.target,tuple((p.relation,p.object) for p in binding.content))
                        self.repeats[i] = self.repeats[i]+1 if signature==self.signatures[i] else 1
                        self.signatures[i] = signature
                        if self.repeat_limit is not None and self.repeats[i]>=self.repeat_limit:
                            self.stopped[i]='unchanged_retained_result'
                            row['stop']='unchanged_retained_result'
        after = self.engine.wallet(r.actor)
        row['charged'] = tuple(before[k] - after[k] for k in ('energy', 'time'))
        self.events.append(row)
        return row

    def run(self, max_turns):
        if type(max_turns) is not int or max_turns < 0:
            raise ValueError('nonnegative turn bound required')
        for _ in range(max_turns):
            if self.step() is None:
                break
        return dict(done=self.done, turns=self.turn, counts=tuple(self.counts),
                    stops=tuple(self.stopped), pending=not self.done)

    def checkpoint(self):
        workflow = any(self._is_workflow(r) for r in self.requests)
        requests = ([dict(request_type=type(r).__name__, fields=fields_of(r)) for r in self.requests]
                    if workflow else [fields_of(r) for r in self.requests])
        return dumps(dict(schema=self.SCHEMA if workflow else self.LEGACY_SCHEMA,
                          engine=self.engine.checkpoint(), requests=requests, episodes=self.episodes,
                          quantum=self.quantum, repeat_limit=self.repeat_limit, signatures=self.signatures, repeats=self.repeats, cursor=self.cursor, turn=self.turn,
                          counts=self.counts, stopped=self.stopped, feedback=self.feedback, events=self.events))

    @classmethod
    def restore(cls, text):
        d = loads(text)
        schema = d.pop('schema')
        if schema == cls.LEGACY_SCHEMA:
            e = SelectionEngine.restore(d.pop('engine'))
            requests = [SelectionRequest(**r) for r in d.pop('requests')]
        elif schema == cls.SCHEMA:
            from .workflow_selection_execution import WorkflowFinalSelectionEngine
            from .workflow_selection_records import WorkflowSelectionRequest, WorkflowCapacitySelectionRequest
            types = dict(SelectionRequest=SelectionRequest,
                         WorkflowSelectionRequest=WorkflowSelectionRequest,
                         WorkflowCapacitySelectionRequest=WorkflowCapacitySelectionRequest)
            e = WorkflowFinalSelectionEngine.restore(d.pop('engine'))
            encoded = d.pop('requests'); requests = []
            for row in encoded:
                if set(row) != {'request_type', 'fields'} or row['request_type'] not in types:
                    raise ValueError('unsupported population request type')
                requests.append(types[row['request_type']](**row['fields']))
            if not any(cls._is_workflow(r) for r in requests):
                raise ValueError('workflow population schema requires workflow demand')
        else:
            raise ValueError('unsupported population schema')
        obj = cls(e, requests, d.pop('episodes'), d.pop('quantum'), d.pop('repeat_limit'))
        for k, v in d.items():
            if k not in ('cursor', 'turn', 'counts', 'stopped', 'feedback', 'events', 'signatures', 'repeats'):
                raise ValueError('unknown scheduler field')
            setattr(obj, k, v)
        n = len(obj.requests)
        if not 0 <= obj.cursor < n or obj.turn != len(obj.events) or any(len(x) != n for x in (obj.counts, obj.stopped, obj.feedback, obj.signatures, obj.repeats)):
            raise ValueError('inconsistent scheduler continuation')
        if any(type(c) is not int or not 0 <= c <= obj.episodes for c in obj.counts):
            raise ValueError('invalid episode count')
        return obj
