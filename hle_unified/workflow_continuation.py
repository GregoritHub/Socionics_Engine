"""Opt-in bounded continuation of one supplied need through owned results.

No route selection, goal creation, world-head refresh or free access occurs here.
The inherited population still owns scheduling, payment, feedback and stops.
"""
from dataclasses import replace
from .population import Population
from .selection_records import dumps, loads
from .operations import address


class WorkflowContinuation(Population):
    CONTINUATION_SCHEMA = 'hle-c7-workflow-continuation-v1'
    POLICY = 'latest-successful-owned-result-v1'

    def __init__(self, engine, requests, episodes=3, quantum=17, repeat_limit=2):
        requests = tuple(requests)
        if not requests or any(not self._is_workflow(r) for r in requests):
            raise ValueError('owned workflow requests required for continuation')
        super().__init__(engine, requests, episodes, quantum, repeat_limit)
        self.input_history = [[r.accessible] for r in requests]
        self.pending_results = [None] * len(requests)

    def request(self, index):
        r = super().request(index)
        return replace(r, accessible=self.input_history[index][self.counts[index]])

    def step(self):
        before = tuple(self.counts)
        row = super().step()
        if row is None:
            return None
        index = next(i for i, r in enumerate(self.requests) if r.actor == row['actor'])
        r = self.requests[index]
        if row['status'] == 'episode_complete':
            child_key = (r.actor, row['key'] + ':movement')
            child = self.engine.job_status(*child_key) if child_key in self.engine._jobs else None
            result = None
            if child and child['status'] == 'succeeded':
                if self.feedback[index] is not None:
                    result = address('u4.observation', self.feedback[index], r.actor)
                elif child.get('binding'):
                    result = child['binding']
            self.pending_results[index] = result
        if self.counts[index] != before[index]:
            previous = self.input_history[index][-1]
            result = self.pending_results[index]
            if row['status'].startswith('feedback_') and row['status'] != 'feedback_succeeded':
                result = None
            proposed = previous if result is None else (result,)
            # Enforce existing paid, owned and scoped access, never synthesize it.
            self.engine.workflow_selection_view(replace(r, accessible=proposed))
            self.input_history[index].append(proposed)
            self.pending_results[index] = None
        return row

    def checkpoint(self):
        return dumps(dict(schema=self.CONTINUATION_SCHEMA, policy=self.POLICY,
                          population=loads(super().checkpoint()),
                          input_history=self.input_history, pending_results=self.pending_results))

    @classmethod
    def restore(cls, text):
        state = loads(text)
        if (set(state) != {'schema', 'policy', 'population', 'input_history', 'pending_results'}
                or state['schema'] != cls.CONTINUATION_SCHEMA or state['policy'] != cls.POLICY):
            raise ValueError('unsupported continuation checkpoint')
        base = Population.restore(dumps(state['population']))
        obj = cls.__new__(cls)
        obj.__dict__.update(base.__dict__)
        obj.input_history = state['input_history']
        obj.pending_results = state['pending_results']
        from .workflow_continuation_audit import audit_continuation
        audit_continuation(obj.engine.world.journal(), state)
        return obj
