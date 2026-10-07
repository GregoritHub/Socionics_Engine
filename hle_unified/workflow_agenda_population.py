"""Fair bounded scheduling for opt-in generated-content workflow agendas.

The scheduler chooses only an actual pending payer.  Supplied agenda goals and
the unchanged workflow selector continue to determine content and native work.
"""
import re
from dataclasses import replace

from .workflow_agenda import WorkflowAgenda
from .workflow_selection_records import WorkflowSelectionRequest, dumps, loads
from .workflow_selection_execution import WorkflowFinalSelectionEngine


class NamespacedWorkflowAgenda(WorkflowAgenda):
    """WorkflowAgenda v2 with collision-free commands and shared-engine state."""

    SCHEMA = 'hle-c7-namespaced-workflow-agenda-v2'

    def __init__(self, namespace, engine, template, goals, quantum=17):
        if type(namespace) is not str or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', namespace):
            raise ValueError('bounded deterministic agenda namespace required')
        self.namespace = namespace
        super().__init__(engine, template, goals, quantum)

    def _goal_key(self):
        return 'agenda:' + self.namespace + ':' + self.template['key'] + ':' + str(self.stage)

    def _prepare(self):
        g = self.goals[self.stage]
        sources = self._sources(g)
        if sources is None:
            self.halted = 'missing_prior_result'
            return
        key = self._goal_key()
        a = self.template['actor']
        peer = self.template['peer']
        inputs = sources

        def aux(suffix, actor, recipe, refs):
            k = key + ':' + suffix
            self.queue.append(dict(kind='aux', key=k, actor=actor, recipe=recipe, inputs=tuple(refs)))
            from .operations import address
            return address('c7w.message', actor, k)

        def read(ref, actor, suffix):
            self.queue.append(dict(kind='public', key=key + ':' + suffix, actor=actor, ref=ref))

        if g['companion'] == 'exchange':
            if len(sources) != 1 or peer is None:
                raise ValueError('exchange requires one source and a distinct participant')
            r = WorkflowSelectionRequest(**self.template)
            value, _ = self.engine._read_workflow(self.engine.participant_view(a), sources[0], r)
            domain = {'intention': 'personal', 'personal': 'personal', 'activity': 'activity',
                      'shared': 'shared', 'system': 'system', 'rule': 'system'}[value['kind']]
            offer = aux('offer', a, 'workflow-offer-' + domain + '-v1', (sources[0], g['own_stance']))
            read(offer, a, 'own-offer-read')
            read(offer, peer, 'peer-offer-read')
            reply = aux('reply', peer, 'workflow-reply-v1', (offer, g['peer_stance']))
            read(reply, a, 'reply-read')
            inputs = (sources[0], offer, reply)
        elif g['companion'] == 'votes':
            if len(sources) != 1 or peer is None:
                raise ValueError('votes require exact draft and two participants')
            read(sources[0], peer, 'peer-draft-read')
            votes = []
            for suffix, actor, stance in (('own-vote', a, g['own_stance']),
                                           ('peer-vote', peer, g['peer_stance'])):
                vote = aux(suffix, actor, 'workflow-vote-v1', (sources[0], stance))
                read(vote, a, suffix + '-read')
                votes.append(vote)
            inputs = (sources[0], *votes)
        self.queue.append(dict(kind='main', key=key, actor=a, inputs=inputs, need=g['need']))

    def prepare(self):
        """Advance free bookkeeping and return the actual next payer."""
        if self.done:
            return None
        if self.active is None and not self.queue:
            if self.pending_result is not None:
                self.results.append(self.pending_result)
                self.pending_result = None
                self.stage += 1
            if not self.done and self.active is None and not self.queue:
                self._prepare()
        if self.done:
            return None
        action = self.active if self.active is not None else self.queue[0]
        return action['actor']

    def _active_job_key(self):
        if self.active is None:
            return None
        key = self.active['key']
        if self.active['kind'] == 'main' and (self.active['actor'], key) in self.engine._jobs:
            d = self.engine.job_status(self.active['actor'], key)
            if d['status'] == 'succeeded' and (self.active['actor'], key + ':movement') in self.engine._jobs:
                return key + ':movement'
        return key

    def runnable(self):
        actor = self.prepare()
        if actor is None:
            return False
        if actor not in self.engine._locks:
            return True
        key = self._active_job_key()
        return key is not None and (actor, key) in self.engine._jobs and self.engine.job_status(actor, key)['status'] not in (
            'succeeded', 'failed', 'cancelled')

    def step(self, command_prefix=None):
        if self.prepare() is None:
            return None
        actors = tuple(x for x in (self.template['actor'], self.template['peer']) if x is not None)
        before = [self.engine.wallet(a) for a in actors]
        payer = self.active['actor'] if self.active is not None else self.queue[0]['actor']
        cid = command_prefix or ('agenda2:' + self.namespace + ':turn:' + str(self.steps))
        stage_before = self.stage
        action_before = self.active if self.active is not None else self.queue[0]
        if self.active is None and self.queue:
            self.active = self.queue.pop(0)
            self._start(self.active, cid)
        elif self.active is not None:
            action = self.active
            a = action['actor']
            key = action['key']
            comparison = self.engine.job_status(a, key)
            main_child = action['kind'] == 'main' and comparison['status'] == 'succeeded'
            if main_child:
                if (a, key + ':movement') not in self.engine._jobs:
                    self.halted = 'no_native_child'
                    self.active = None
                else:
                    key += ':movement'
            if self.active is not None:
                d = self.engine.job_status(a, key)
                if d['status'] not in ('succeeded', 'failed', 'cancelled'):
                    if min(self.engine.wallet(a)[k] for k in ('energy', 'time')) == 0:
                        self.halted = 'exhausted'
                    else:
                        if d['status'] != 'ready':
                            self.engine.advance(cid + ':work', a, key, self.quantum)
                        if self.engine.job_status(a, key)['status'] == 'ready':
                            self.engine.commit(cid + ':commit', a, key)
                d = self.engine.job_status(a, key)
                if d['status'] in ('succeeded', 'failed', 'cancelled'):
                    if action['kind'] == 'main' and not main_child and d['status'] == 'succeeded':
                        pass
                    else:
                        if main_child:
                            self._finish_main(action, cid)
                        elif d['status'] != 'succeeded':
                            self.halted = 'auxiliary_' + d['status']
                        self.active = None
        charged = tuple((a, before[i]['energy'] - self.engine.wallet(a)['energy'],
                         before[i]['time'] - self.engine.wallet(a)['time']) for i, a in enumerate(actors))
        if any(a != payer and (energy or time) for a, energy, time in charged):
            raise ValueError('agenda charged an actor other than the scheduled payer')
        row = dict(step=self.steps, actor=payer, action=action_before['kind'], key=action_before['key'],
                   stage_before=stage_before, stage_after=self.stage, charged=charged)
        self.events.append(row)
        self.steps += 1
        return row

    def state(self):
        return {k: v for k, v in self.__dict__.items() if k != 'engine'}

    @classmethod
    def from_state(cls, engine, state):
        required = {'namespace', 'template', 'goals', 'quantum', 'stage', 'steps', 'results', 'main_rows',
                    'queue', 'active', 'pending_result', 'halted', 'events'}
        if set(state) != required:
            raise ValueError('unknown namespaced agenda state')
        obj = cls.__new__(cls)
        obj.engine = engine
        obj.__dict__.update(state)
        if type(obj.namespace) is not str or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', obj.namespace):
            raise ValueError('invalid restored agenda namespace')
        return obj

    def checkpoint(self):
        return dumps(dict(schema=self.SCHEMA, engine=self.engine.checkpoint(), state=self.state()))

    @classmethod
    def restore(cls, text):
        raw = loads(text)
        if set(raw) != {'schema', 'engine', 'state'} or raw['schema'] != cls.SCHEMA:
            raise ValueError('unknown namespaced agenda schema')
        engine = WorkflowFinalSelectionEngine.restore(raw['engine'])
        obj = cls.from_state(engine, raw['state'])
        from .workflow_agenda_population_audit import audit_namespaced_agenda
        audit_namespaced_agenda(engine.world.journal(), engine.access.checkpoint(), obj.state())
        return obj


class FairWorkflowAgendaPopulation:
    """Actor-fair turn scheduling across agendas sharing one engine."""

    SCHEMA = 'hle-c7-fair-workflow-agenda-population-v1'

    def __init__(self, engine, agendas, max_turns=2000):
        agendas = tuple(agendas)
        if not agendas or any(type(a) is not NamespacedWorkflowAgenda or a.engine is not engine for a in agendas):
            raise ValueError('one shared-engine namespaced agenda population required')
        if len({a.namespace for a in agendas}) != len(agendas):
            raise ValueError('distinct agenda namespaces required')
        if type(max_turns) is not int or max_turns < 1:
            raise ValueError('positive finite turn horizon required')
        actors = []
        for agenda in agendas:
            for actor in (agenda.template['actor'], agenda.template['peer']):
                if actor is not None and actor not in actors:
                    actors.append(actor)
        self.engine = engine
        self.agendas = agendas
        self.max_turns = max_turns
        self.actors = tuple(actors)
        self.actor_cursor = 0
        self.agenda_cursors = [0] * len(self.actors)
        self.turn = 0
        self.events = []

    @property
    def done(self):
        return all(a.done for a in self.agendas)

    def _runnable(self):
        rows = []
        for index, agenda in enumerate(self.agendas):
            actor = agenda.prepare()
            if actor is not None and agenda.runnable():
                rows.append((index, actor))
        return rows

    def step(self):
        if self.done or self.turn >= self.max_turns:
            return None
        runnable = self._runnable()
        if self.done:
            return None
        if not runnable:
            raise ValueError('unfinished agenda population has no runnable payer')
        actor_index = next((self.actor_cursor + i) % len(self.actors) for i in range(len(self.actors))
                           if any(actor == self.actors[(self.actor_cursor + i) % len(self.actors)]
                                  for _, actor in runnable))
        actor = self.actors[actor_index]
        candidates = [i for i, a in runnable if a == actor]
        cursor = self.agenda_cursors[actor_index]
        agenda_index = next((cursor + i) % len(self.agendas) for i in range(len(self.agendas))
                            if (cursor + i) % len(self.agendas) in candidates)
        self.actor_cursor = (actor_index + 1) % len(self.actors)
        self.agenda_cursors[actor_index] = (agenda_index + 1) % len(self.agendas)
        before = self.engine.wallet(actor)
        prefix = 'sustain-turn:' + str(self.turn) + ':agenda:' + self.agendas[agenda_index].namespace
        detail = self.agendas[agenda_index].step(prefix)
        after = self.engine.wallet(actor)
        row = dict(turn=self.turn, actor=actor, agenda=self.agendas[agenda_index].namespace,
                   agenda_index=agenda_index, runnable=tuple((i, a) for i, a in runnable),
                   action=detail['action'], key=detail['key'],
                   charged=(before['energy'] - after['energy'], before['time'] - after['time']))
        self.events.append(row)
        self.turn += 1
        return row

    def run(self, turns=None):
        limit = self.max_turns - self.turn if turns is None else turns
        if type(limit) is not int or limit < 0:
            raise ValueError('finite nonnegative run bound required')
        for _ in range(limit):
            if self.step() is None:
                break
        return dict(done=self.done, turns=self.turn, pending=not self.done,
                    completed=tuple(a.stage for a in self.agendas), halted=tuple(a.halted for a in self.agendas))

    def checkpoint(self):
        return dumps(dict(schema=self.SCHEMA, engine=self.engine.checkpoint(), max_turns=self.max_turns,
                          actors=self.actors, actor_cursor=self.actor_cursor,
                          agenda_cursors=self.agenda_cursors, turn=self.turn, events=self.events,
                          agendas=[a.state() for a in self.agendas]))

    @classmethod
    def restore(cls, text):
        raw = loads(text)
        if raw.pop('schema', None) != cls.SCHEMA:
            raise ValueError('unknown fair agenda population schema')
        engine = WorkflowFinalSelectionEngine.restore(raw.pop('engine'))
        states = raw.pop('agendas')
        agendas = tuple(NamespacedWorkflowAgenda.from_state(engine, s) for s in states)
        obj = cls(engine, agendas, raw.pop('max_turns'))
        allowed = {'actors', 'actor_cursor', 'agenda_cursors', 'turn', 'events'}
        if set(raw) != allowed:
            raise ValueError('unknown fair scheduler field')
        obj.__dict__.update(raw)
        if (obj.actors != tuple(obj.actors) or obj.turn != len(obj.events)
                or len(obj.agenda_cursors) != len(obj.actors)
                or not 0 <= obj.actor_cursor < len(obj.actors)):
            raise ValueError('inconsistent fair scheduler continuation')
        from .workflow_agenda_population_audit import audit_agenda_population
        audit_agenda_population(engine.world.journal(), engine.access.checkpoint(), loads(obj.checkpoint()))
        return obj
