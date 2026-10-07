"""Bounded authored goals continued through exact paid native results.

This serial participant agenda is opt-in. It does not replace Population or
claim round-robin fairness. Main route choice belongs to the unchanged selector.
"""
from dataclasses import replace
from .workflow_selection_records import WorkflowSelectionRequest, fields_of, dumps, loads
from .workflow_selection_execution import WorkflowFinalSelectionEngine
from .workflow_records import WorkflowRequest
from .operation_records import OperationRequest
from .operations import address
from .particulars import Selector


class WorkflowAgenda:
    SCHEMA = 'hle-c7-owned-workflow-agenda-v1'

    def __init__(self, engine, template, goals, quantum=17):
        if type(template) is not WorkflowSelectionRequest or type(quantum) is not int or quantum < 1:
            raise ValueError('workflow template and finite positive quantum required')
        goals = list(goals)
        if not 1 <= len(goals) <= 8:
            raise ValueError('one to eight supplied goals required')
        for i, goal in enumerate(goals):
            if set(goal) != {'need', 'sources', 'companion', 'own_stance', 'peer_stance'}:
                raise ValueError('goal may name outcomes and sources, never routes')
            if goal['companion'] not in ('none', 'exchange', 'votes') or not 1 <= len(goal['sources']) <= 8:
                raise ValueError('bounded companion and source plan required')
            for slot in goal['sources']:
                if set(slot) not in ({'initial'}, {'result'}):
                    raise ValueError('initial reference or exact earlier result required')
                if 'result' in slot and (type(slot['result']) is not int or not 0 <= slot['result'] < i):
                    raise ValueError('result must precede its consumer')
            # Each goal already belongs to the actor; no goal is formed at runtime.
            engine.workflow_selection_view(replace(template, demand=goal['need']))
        self.engine = engine
        self.template = fields_of(template)
        self.goals = goals
        self.quantum = quantum
        self.stage = self.steps = 0
        self.results = []
        self.main_rows = []
        self.queue = []
        self.active = None
        self.pending_result = None
        self.halted = None
        self.events = []

    @property
    def done(self):
        return self.halted is not None or self.stage == len(self.goals)

    def _request(self, key, actor, recipe, inputs):
        r = self.template
        peer = r['peer'] if actor == r['actor'] else r['actor']
        return WorkflowRequest(key=key, actor=actor, recipe=recipe, context=r['context'], cue=r['cue'],
            target=r['target'], inputs=tuple(inputs),
            evidence=tuple(p.address for p in self.engine.participant_view(actor).resolve(r['target'])),
            group=r['group'], peer=peer)

    def _sources(self, goal):
        values = []
        for slot in goal['sources']:
            ref = slot['initial'] if 'initial' in slot else self.results[slot['result']]
            if ref is None:
                return None
            values.append(ref)
        return tuple(values)

    def _prepare(self):
        g = self.goals[self.stage]; sources = self._sources(g)
        if sources is None:
            self.halted = 'missing_prior_result'; return
        key = 'agenda:' + self.template['key'] + ':' + str(self.stage)
        a = self.template['actor']; peer = self.template['peer']
        inputs = sources
        def aux(suffix, actor, recipe, refs):
            k = key + ':' + suffix
            self.queue.append(dict(kind='aux', key=k, actor=actor, recipe=recipe, inputs=tuple(refs)))
            return address('c7w.message', actor, k)
        def read(ref, actor, suffix):
            self.queue.append(dict(kind='public', key=key + ':' + suffix, actor=actor, ref=ref))
        if g['companion'] == 'exchange':
            if len(sources) != 1 or peer is None:
                raise ValueError('exchange requires one source and a distinct participant')
            r = WorkflowSelectionRequest(**self.template)
            value, _ = self.engine._read_workflow(self.engine.participant_view(a), sources[0], r)
            domain = {'intention':'personal', 'personal':'personal', 'activity':'activity',
                      'shared':'shared', 'system':'system', 'rule':'system'}[value['kind']]
            offer = aux('offer', a, 'workflow-offer-' + domain + '-v1', (sources[0], g['own_stance']))
            read(offer, a, 'own-offer-read'); read(offer, peer, 'peer-offer-read')
            reply = aux('reply', peer, 'workflow-reply-v1', (offer, g['peer_stance']))
            read(reply, a, 'reply-read')
            inputs = (sources[0], offer, reply)
        elif g['companion'] == 'votes':
            if len(sources) != 1 or peer is None:
                raise ValueError('votes require exact draft and two participants')
            read(sources[0], peer, 'peer-draft-read')
            votes = []
            for suffix, actor, stance in (('own-vote', a, g['own_stance']), ('peer-vote', peer, g['peer_stance'])):
                vote = aux(suffix, actor, 'workflow-vote-v1', (sources[0], stance))
                read(vote, a, suffix+'-read'); votes.append(vote)
            inputs = (sources[0], *votes)
        self.queue.append(dict(kind='main', key=key, actor=a, inputs=inputs, need=g['need']))

    def _start(self, action, cid):
        kind = action['kind']; a = action['actor']; key = action['key']
        if kind == 'main':
            r = replace(WorkflowSelectionRequest(**self.template), key=key,
                        demand=action['need'], accessible=action['inputs'])
        elif kind == 'aux':
            r = self._request(key, a, action['recipe'], action['inputs'])
        else:
            delivery = key + ':delivery'
            if kind == 'public':
                source = self.engine.world.resolve(action['ref'])
                selectors = tuple(Selector(v.name, 'detail', ('attributes', str(i), 'value'))
                                  for i, v in enumerate(source.attributes) if v.name == 'payload')
                self.engine.disclose(cid + ':disclose', a, action['ref'], selectors, action['ref'])
                # disclose's command id is its delivery id.
                delivery = cid + ':disclose'
            else:
                delivery = action['delivery']
            r = OperationRequest(key, a, 'read', self.template['context'], delivery=delivery)
        self.engine.start(cid + ':start', r)

    def _finish_main(self, action, cid):
        a = action['actor']; key = action['key']; e = self.engine
        child = e.job_status(a, key + ':movement')
        self.main_rows.append(dict(stage=self.stage, key=key, status=child['status']))
        if child['status'] != 'succeeded':
            self.halted = 'native_' + child['status']; return
        if child.get('public.0'):
            result = child['public.0']
            self.queue.append(dict(kind='public', key=key+':result-read', actor=a, ref=result))
        elif child.get('binding'):
            result = child['binding']
        else:
            delivery = cid + ':own-event'
            result = e.deliver_event(delivery, child['result'], a)
            self.queue.append(dict(kind='event', key=key+':result-read', actor=a, delivery=delivery))
        self.pending_result = result

    def step(self):
        if self.done: return None
        actors = tuple(x for x in (self.template['actor'], self.template['peer']) if x is not None)
        before = [self.engine.wallet(a) for a in actors]
        cid = 'agenda-turn:' + str(self.steps)
        if self.active is None and not self.queue:
            if self.pending_result is not None:
                self.results.append(self.pending_result); self.pending_result = None; self.stage += 1
            elif not self.done:
                self._prepare()
        if self.active is None and self.queue:
            self.active = self.queue.pop(0)
            self._start(self.active, cid)
        elif self.active is not None:
            action = self.active; a = action['actor']; key = action['key']
            comparison = self.engine.job_status(a, key)
            main_child = action['kind'] == 'main' and comparison['status'] == 'succeeded'
            if main_child:
                if (a, key+':movement') not in self.engine._jobs:
                    self.halted = 'no_native_child'; self.active = None
                else: key += ':movement'
            if self.active is not None:
                d = self.engine.job_status(a, key)
                if d['status'] not in ('succeeded', 'failed', 'cancelled'):
                    if min(self.engine.wallet(a)[k] for k in ('energy','time')) == 0:
                        self.halted = 'exhausted'
                    else:
                        if d['status'] != 'ready': self.engine.advance(cid+':work', a, key, self.quantum)
                        if self.engine.job_status(a, key)['status'] == 'ready': self.engine.commit(cid+':commit', a, key)
                d = self.engine.job_status(a, key)
                if d['status'] in ('succeeded','failed','cancelled'):
                    if action['kind'] == 'main' and not main_child and d['status'] == 'succeeded':
                        pass  # Native child is a later bounded turn.
                    else:
                        if main_child: self._finish_main(action, cid)
                        elif d['status'] != 'succeeded': self.halted = 'auxiliary_' + d['status']
                        self.active = None
        charged = tuple((a, before[i]['energy']-self.engine.wallet(a)['energy'],
                         before[i]['time']-self.engine.wallet(a)['time']) for i,a in enumerate(actors))
        row = dict(step=self.steps, charged=charged)
        self.events.append(row); self.steps += 1
        return row

    def run(self, max_steps):
        if type(max_steps) is not int or max_steps < 0: raise ValueError('finite nonnegative step bound required')
        for _ in range(max_steps):
            if self.step() is None: break
        return dict(done=self.done, halted=self.halted, completed=self.stage, steps=self.steps)

    def checkpoint(self):
        state = {k:v for k,v in self.__dict__.items() if k != 'engine'}
        return dumps(dict(schema=self.SCHEMA, engine=self.engine.checkpoint(), state=state))

    @classmethod
    def restore(cls, text):
        raw = loads(text)
        if set(raw) != {'schema','engine','state'} or raw['schema'] != cls.SCHEMA:
            raise ValueError('unknown agenda schema')
        obj = cls.__new__(cls); obj.engine = WorkflowFinalSelectionEngine.restore(raw['engine'])
        if set(raw['state']) != {'template','goals','quantum','stage','steps','results','main_rows','queue','active','pending_result','halted','events'}:
            raise ValueError('unknown agenda state')
        obj.__dict__.update(raw['state'])
        from .workflow_agenda_audit import audit_agenda
        audit_agenda(obj.engine.world.journal(), obj.engine.access.checkpoint(), raw['state'])
        return obj
