"""Declared external R10 opportunities; all terms come from participant operations.

This is an experiment driver, not an autonomous participant policy. No runtime
Truth query, evaluator answer or ready-made Terms is supplied to a participant.
"""
import random
import time
from collections import Counter, defaultdict
from dataclasses import replace

from hle.composition_records import CompositionCommand, FoldDraft, Part, UnfoldDraft
from hle.contracts import ActionRequest, ClaimStatus, Kind, Ref, WorkStatus
from hle.language_records import Act, Interpret, LanguageCommand, Learn, Produce, Speech
from hle.metabolism_records import ProcessingPolicy, Profile
from hle.model_a import TYPES
from hle.organization import OrganizationWorld
from hle.organization_records import (
    Attend, Dispute, Formulate, Join, Leave, OrganizationCommand,
    OrganizationPolicy, Perform, Ratify, ReviewTerms,
)
from hle.socion_records import AgentPolicy, ReceiveCommand
from hle.world_records import (
    Attempt, Credit, Entity, INSPECT, MemoryDraft, Ownership, RETAIN,
    Tick, TRANSFER, Wallet, WorldConfig,
)

DONE = (WorkStatus.COMPLETED, WorkStatus.FAILED)


class ResourceStop(RuntimeError):
    """A valid operation stopped with its unfinished work retained."""


def make_world(population=4, seed=17, resources='ample', objects=1,
               energy=None, time_budget=None, max_members=None):
    rng = random.Random(seed)
    actors = tuple(Ref(Kind.ENTITY, f'p{i:02d}', 1) for i in range(population))
    items = tuple(Ref(Kind.ENTITY, f'item{i:03d}', 1) for i in range(objects))
    context = Ref(Kind.CONTEXT, 'r10-room', 1)
    amount = 1 if resources == 'replenished' else 1000000
    e = amount if energy is None else energy
    t = amount if time_budget is None else time_budget
    types = sorted(TYPES); rng.shuffle(types)
    cfg = WorldConfig(context,
        tuple(Entity(a, a.key, 'actor') for a in actors) +
        tuple(Entity(a, a.key, 'object') for a in items), actors,
        tuple(Ownership(i, actors[0]) for i in items),
        tuple(Wallet(a, e, t) for a in actors), (),
        tuple((a, b) for a in actors for b in actors if a != b))
    w = OrganizationWorld(cfg,
        tuple(Profile(a, types[n % len(types)]) for n, a in enumerate(actors)),
        ProcessingPolicy(), tuple(AgentPolicy(a) for a in actors),
        tuple(OrganizationPolicy(a, max_action_cost=12,
            max_members=max_members or population) for a in actors))
    return w, actors, items


class Driver:
    def __init__(self, world, seed=17, replenish=False, work_limit=64):
        self.w = world
        self.rng = random.Random(seed)
        self.replenish = replenish
        self.work_limit = work_limit
        self.timings = []
        self.by_action = defaultdict(list)
        self.debits = Counter()
        self.credits = Counter()
        self.deferrals = 0
        self.serial = 0

    def emit(self, command):
        begin = time.perf_counter_ns()
        event = self.w.execute(command)
        elapsed = (time.perf_counter_ns() - begin) / 1e6
        tx = self.w._journal[-1]  # Offline instrumentation of the committed receipt.
        self.by_action[event.action].append(elapsed)
        if tx.works and type(command) is not Credit:
            self.timings.append(elapsed)
        for work in tx.works:
            self.debits[work.owner.key] += sum(x.amount for x in work.charged
                if x.unit.key == 'r2.energy_quantum')
        return tx

    def retry_funding(self, actor, key):
        # Only the acting participant's resource state is used for resumption.
        wallet = self.w._wallets[actor]
        if wallet.energy and wallet.time:
            return
        self.deferrals += 1
        if not self.replenish:
            raise ResourceStop(f'{key}: {actor.key} energy={wallet.energy}, time={wallet.time}')
        self.serial += 1
        e = 64 if wallet.energy == 0 else 0
        t = 64 if wallet.time == 0 else 0
        self.emit(Credit(f'external-credit:{self.serial}', actor, e, t,
            'R10 declared external replenishment after unavailable work'))
        self.credits[actor.key] += e

    def operation(self, actor, payload, key, family='organization'):
        command_type, getter = {
            'organization': (OrganizationCommand, self.w.organization_job),
            'language': (LanguageCommand, self.w.language_job),
            'composition': (CompositionCommand, self.w.composition_job),
        }[family]
        for n in range(10000):
            self.emit(command_type(f'{key}:{n}', key, actor, payload, self.work_limit))
            job = getter(actor, key)
            if job.outcome in DONE:
                if job.result is None:
                    raise RuntimeError(f'{key}: semantic operation failed')
                return job.result
            self.retry_funding(actor, key)
        raise RuntimeError(f'{key}: continuation limit exceeded')

    def attempt(self, command):
        for n in range(10000):
            tx = self.emit(command if n == 0 else replace(command,
                command_id=command.command_id + f':retry:{n}'))
            if tx.event.outcome in DONE:
                return tx
            self.retry_funding(command.action.actor, command.task_id)
        raise RuntimeError('physical continuation limit exceeded')

    def physical(self, actor, operation, inputs, key):
        return self.attempt(Attempt(key, key, ActionRequest(actor, operation, inputs, ())))

    def acquire(self, actor, item, key):
        tx = self.physical(actor, INSPECT, (item,), key + ':inspect')
        assert tx.event.outcome == WorkStatus.COMPLETED
        obs = next(o for o in tx.observations if o.observer == actor)
        facts = tuple(p for p in obs.content if p.relation == 'owned_by')
        self.attempt(Attempt(key + ':retain', key + ':retain',
            ActionRequest(actor, RETAIN, (), (obs.ref,)),
            memory=MemoryDraft(key, facts, ClaimStatus.ENDORSED, 'own paid inspection')))
        root = self.operation(actor, FoldDraft(key, (Part('owned evidence',
            self.w.memory_head(actor, key).ref, self.w.config.context),)),
            key + ':fold', 'composition')
        return self.operation(actor, UnfoldDraft(root, self.w.config.context, self.w.now),
            key + ':unfold', 'composition')

    def receive(self, sender, record, actor, key, organization=False):
        factory = self.w.send_organization if organization else self.w.send_language
        tx = self.attempt(factory(sender, record, actor, key))
        if tx.event.outcome != WorkStatus.COMPLETED:
            raise RuntimeError('required declared channel failed')
        obs = next(o.ref for o in tx.observations if o.observer == actor
            and o.source.kind == Kind.MESSAGE)
        for n in range(10000):
            tx = self.emit(ReceiveCommand(f'{key}:receive:{n}', key + ':receive',
                actor, obs, self.work_limit))
            if tx.event.outcome == WorkStatus.COMPLETED:
                return obs
            self.retry_funding(actor, key)
        raise RuntimeError('reception continuation limit exceeded')

    def move(self, actor, recipient, item, key):
        tx = self.physical(actor, TRANSFER, (item, recipient), key)
        assert tx.event.outcome == WorkStatus.COMPLETED

    def learn(self, actor, item, key, teacher=None):
        access = self.acquire(actor, item, key + ':access')
        source = None if teacher is None else self.receive(teacher,
            self.w.lexeme(teacher, 'kept').ref, actor, key + ':definition')
        return self.operation(actor, Learn('kept', access, source), key, 'language')

    def train(self, actor, peer, item, steps, key):
        access = self.acquire(actor, item, key + ':access')
        speech = Speech('request', (self.w.word(peer, 'kept', (item, actor)),),
            tuple(Act(s, item, peer if s == 'transfer' else None) for s in steps))
        said = self.operation(peer, Produce(speech), key + ':say', 'language')
        obs = self.receive(peer, said, actor, key + ':tell')
        plan = self.operation(actor, Interpret(obs, access), key + ':understand', 'language')
        self.actions(actor, plan, organization=False)
        assert self.w.language_outcome(actor, plan) == 'fulfilled'
        self.move(peer, actor, item, key + ':return')

    def actions(self, actor, plan, organization=True):
        factory = self.w.next_organization_action if organization else self.w.next_language_action
        for _ in range(10000):
            command = factory(actor, plan)
            if command is None:
                return
            tx = self.emit(command)
            if tx.event.outcome not in DONE:
                self.retry_funding(actor, command.task_id)
        raise RuntimeError('linked action continuation limit exceeded')

    def propose(self, actor, item, key, identity=None):
        access = self.acquire(actor, item, key + ':access')
        state = None if identity is None else self.w.organization_state(actor, identity).ref
        return self.operation(actor, Formulate(access, state), key)

    def shuffled(self, values):
        values = list(values); self.rng.shuffle(values); return values

    def agree(self, actor, proposal, key, expect=True):
        terms = self.w.organization_record(actor, proposal).terms
        reviews = {}
        for member in self.shuffled(terms.members):
            offer = proposal if member == actor else self.receive(actor, proposal,
                member, key + ':offer:' + member.key, True)
            access = self.acquire(member, terms.item, key + ':evidence:' + member.key)
            reviews[member] = self.operation(member, ReviewTerms(offer, access),
                key + ':review:' + member.key)
        statuses = []
        for member in self.shuffled(terms.members):
            votes = tuple(self.receive(other, reviews[other], member,
                key + ':vote:' + other.key + ':' + member.key, True)
                for other in self.shuffled(terms.members) if other != member)
            result = self.operation(member, Ratify(reviews[member], votes),
                key + ':ratify:' + member.key)
            statuses.append(self.w.organization_record(member, result).status)
        if expect:
            assert set(statuses) == {'active'}, statuses
        return terms.identity, statuses

    def plan(self, actor, item, identity, key):
        access = self.acquire(actor, item, key + ':access')
        return self.operation(actor, Perform(self.w.organization_state(actor, identity).ref,
            access), key + ':plan')

    def rounds(self, holder, item, identity, count, key):
        members = self.w.organization_state(holder, identity).terms.members
        start = members.index(holder)
        order = members[start:] + members[:start]
        outcomes = []
        for n in range(count):
            for actor in order:
                plan = self.plan(actor, item, identity, f'{key}:{n}:{actor.key}')
                self.actions(actor, plan)
                status = self.w.organization_outcome(actor, plan)
                assert status == 'fulfilled', (key, actor.key, status)
                outcomes.append(status)
        return outcomes

    def notify(self, actor, record, peers, identity, key):
        for peer in self.shuffled(peers):
            obs = self.receive(actor, record, peer, key + ':tell:' + peer.key, True)
            self.operation(peer, Attend(self.w.organization_state(peer, identity).ref,
                obs), key + ':attend:' + peer.key)

    def idle(self, key):
        for n in range(self.rng.randrange(3)):
            self.emit(Tick(f'{key}:idle:{n}'))


def snapshot(w):
    """Offline diagnostics: never called by participant selection."""
    job_maps = ('_organization_jobs', '_language_jobs', '_composition_jobs', '_receptions', '_tasks')
    unfinished = {name: sum(getattr(j, 'outcome', None) not in DONE for j in getattr(w, name).values())
        for name in job_maps}
    return {
        'events': len(w._journal), 'records': len(w._records),
        'candidate_summaries': sum(len(v) for v in w._practice.values()),
        'known_references': sum(len(v) for v in w._known.values()),
        'observation_receipts': sum(len(v) for v in w._inboxes.values()),
        'organization_heads': len(w._organization_heads),
        'organization_pending': len(w._organization_pending),
        'socion_notifications': sum(len(v) for v in w._notices.values()),
        'socion_unconsumed_notifications': sum(len(w._notices[a]) - w.agent_state(a).cursor for a in w.config.actors),
        'socion_ready_actors': sum(w.ready(a) for a in w.config.actors),
        'socion_controller_pending': sum(w.agent_state(a).pending is not None for a in w.config.actors),
        'socion_queued_goals': sum(len(w.agent_state(a).goals) for a in w.config.actors),
        'historical_jobs': {name: len(getattr(w, name)) for name in job_maps},
        'unfinished_jobs': unfinished,
        'indexes': {name: len(getattr(w, name)) for name in (
            '_organization_outgoing', '_organization_action_owner', '_language_action_owner',
            '_notice_by_observation', '_completed_reception', '_parents', '_accesses')},
        'dirty_evaluators': {name: len(getattr(w, name)) for name in (
            '_dirty', '_dyad_dirty', '_composition_dirty')},
        'evaluator_visits': {name: getattr(w, name) for name in (
            'assessment_visits', 'dyad_visits', 'composition_visits')},
    }


def run_case(population=4, prefix=0, resources='ample', seed=17, cycles=3,
             initial_rounds=6, revised_rounds=2, successor_rounds=6,
             capture_prefix=True, energy=None, time_budget=None):
    w, actors, (item,) = make_world(population, seed, resources,
        energy=energy, time_budget=time_budget)
    d = Driver(w, seed, resources == 'replenished')
    founder, successor, helper, newcomer = actors[0], actors[1], actors[2], actors[-1]
    cohort = actors[:-1]
    rows = []; continuation = None; blocked = None
    steps = ('inspect',) * prefix + ('transfer',)
    try:
        for actor in cohort:
            d.learn(actor, item, 'initial:learn:' + actor.key)
        for cycle in range(cycles):
            key = f'cycle:{cycle}'
            if cycle:
                d.move(successor, founder, item, key + ':refound')
            for n, peer in enumerate(d.shuffled(cohort[1:])):
                d.train(founder, peer, item, steps, key + ':train:' + str(n))
            proposal = d.propose(founder, item, key + ':proposal')
            original = w.organization_record(founder, proposal).terms
            assert original is not None and original.members == cohort
            identity, _ = d.agree(founder, proposal, key + ':agreement')
            initial = d.rounds(founder, item, identity, initial_rounds, key + ':use')
            d.idle(key + ':initial')
            run = d.plan(founder, item, identity, key + ':intervention')
            d.move(founder, successor, item, key + ':hidden-change')
            d.actions(founder, run)
            failed = w.organization_outcome(founder, run)
            assert failed == ('blocked' if original.steps[0] == 'inspect' else 'failed')
            dispute = d.operation(founder, Dispute(run), key + ':dispute')
            d.notify(founder, dispute, cohort[1:], identity, key + ':dispute-notice')
            without_new = d.propose(successor, item, key + ':existing-alternative', identity)
            alternative_status = w.organization_record(successor, without_new).status
            if alternative_status != 'proposed':
                alternate = ('inspect',) * (prefix + 1) + ('transfer',)
                for n in range(2):
                    d.train(successor, helper, item, alternate, key + ':alternative:' + str(n))
                revised = d.propose(successor, item, key + ':revised-proposal', identity)
            else:
                revised = without_new
            replacement = w.organization_record(successor, revised).terms
            assert replacement is not None and replacement.steps != original.steps
            d.agree(successor, revised, key + ':revised-agreement')
            revised_outcomes = d.rounds(successor, item, identity, revised_rounds, key + ':revised-use')
            d.idle(key + ':revised')
            if cycle == 0:
                d.learn(newcomer, item, key + ':newcomer-learn', teacher=successor)
            access = d.acquire(newcomer, item, key + ':newcomer-access')
            offer = d.receive(successor, w.organization_state(successor, identity).ref,
                newcomer, key + ':newcomer-offer', True)
            join = d.operation(newcomer, Join(offer, access), key + ':join')
            assert w.organization_record(newcomer, join).status == 'accepted'
            d.notify(newcomer, join, cohort, identity, key + ':join-notice')
            departure = d.operation(founder, Leave(w.organization_state(founder, identity).ref,
                'declared founder departure opportunity'), key + ':founder-leave')
            d.notify(founder, departure, cohort[1:], identity, key + ':founder-notice')
            succession = d.propose(successor, item, key + ':succession', identity)
            succession_terms = w.organization_record(successor, succession).terms
            assert succession_terms is not None and succession_terms.members == actors[1:]
            d.agree(successor, succession, key + ':successor-agreement')
            later = d.rounds(successor, item, identity, successor_rounds, key + ':successor-use')
            assert w.organization_state(founder, identity).status == 'withdrawn'
            for peer in d.shuffled(actors[2:]):
                leave = d.operation(peer, Leave(w.organization_state(peer, identity).ref,
                    'declared dissolution opportunity'), key + ':leave:' + peer.key)
                d.notify(peer, leave, (successor,), identity, key + ':exit:' + peer.key)
            assert w.organization_state(successor, identity).status == 'dissolved'
            d.idle(key + ':dissolved')
            diag = snapshot(w)
            assert not diag['organization_pending']
            assert not any(diag['unfinished_jobs'].values()), diag
            rows.append({'cycle': cycle, 'identity': identity,
                'initial_steps': original.steps, 'revised_steps': replacement.steps,
                'initial_members': [a.key for a in original.members],
                'successor_members': [a.key for a in succession_terms.members],
                'generations': [original.generation, replacement.generation, succession_terms.generation],
                'initial_fulfilled': len(initial), 'revised_fulfilled': len(revised_outcomes),
                'successor_fulfilled': len(later), 'intervention_outcome': failed,
                'before_new_training': alternative_status,
                'founder': 'withdrawn', 'survivor': 'dissolved', 'diagnostics': diag})
            if capture_prefix and cycle == cycles - 2:
                continuation = w.checkpoint()
    except ResourceStop as error:
        blocked = str(error)
    return d, {'population': population, 'prefix': prefix, 'resources': resources,
        'seed': seed, 'cycles': rows, 'blocked': blocked,
        'initial_wallets': {x.actor.key: {'energy': x.energy, 'time': x.time} for x in w.config.wallets},
        'profiles': {p.owner.key: p.tim for p in w.profiles},
        'deferrals': d.deferrals, 'credits': dict(d.credits), 'debits': dict(d.debits),
        'diagnostics': snapshot(w)}, continuation


def prepare_candidates(count=1, cohort=3):
    w, actors, items = make_world(max(4, cohort + 1), objects=count)
    d = Driver(w, work_limit=1000000)
    for actor in actors[:cohort]:
        d.learn(actor, items[0], 'profile:learn:' + actor.key)
    for n, item in enumerate(items):
        for peer in actors[1:cohort]:
            d.train(actors[0], peer, item, ('transfer',), f'profile:train:{n}:{peer.key}')
    access = d.acquire(actors[0], items[0], 'profile:fixed-access')
    return d, actors, items, access
