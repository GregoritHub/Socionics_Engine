"""True historical constraints then matched optional release opportunities.

The harness supplies only physical opportunities and genuine accepted terms.
It never supplies a learner answer, treatment, carrier, or defensive sequence.
"""
from dataclasses import replace
from .contracts import Ref, Kind, ActionRequest
from .world_records import WorldConfig, Entity, Ownership, Wallet, Attempt, TRANSFER
from .autonomy_records import WorkshopConfig, AutonomyPolicy, WorkshopCommand
from .socion_records import AgentPolicy
from .metabolism_records import Profile, ProcessingPolicy
from .model_a import ego
from .compensation_records import ReleaseConfig, ReviewPolicy, ReleaseCommand
from .compensation import CompensationWorld
from .concept_demo import fund_command
from .autonomy_demo import run as inherited_run


def run(w, horizon=10000):
    result = inherited_run(w, horizon)
    result['resource_censored'] = result['resource_censored'] or any(
        min(w._wallets[a].energy,w._wallets[a].time)==0 and
        (a in w._release_active or w._request_queue.get(a) or w._response_queue.get(a) or a in w._concept_active)
        for a in w.config.actors)
    return result


def world(history=3, renewals=3, gated_history=True, tim='iee', energy=200000,
          revision_unit=6, work_limit=256, names=('worker', 'lender', 'reviewer'), quotes=(2, 1)):
    actors = tuple(Ref(Kind.ENTITY, n, 1) for n in names)
    worker, lender, reviewer = actors
    count = history + renewals
    tools = tuple(Ref(Kind.ENTITY, 'tool:' + str(i), 1) for i in range(count))
    pieces = tuple(Ref(Kind.ENTITY, 'piece:' + str(i), 1) for i in range(count))
    spares = tuple(Ref(Kind.ENTITY, 'retire:' + str(i), 1) for i in range(count))
    objects = tools + pieces + spares
    config = WorldConfig(Ref(Kind.CONTEXT, 'workshop', 1),
              tuple(Entity(a, a.key, 'actor') for a in actors) + tuple(Entity(i, i.key, 'object') for i in objects),
              actors, tuple(Ownership(i, lender) for i in objects), tuple(Wallet(a, energy, energy) for a in actors), (),
              tuple((a, b) for a in actors for b in actors if a != b))
    profiles = tuple(Profile(a, tim if a == worker else 'iee', ego(tim if a == worker else 'iee')[0]) for a in actors)
    autonomy = (AutonomyPolicy(worker, work_limit=work_limit),
                AutonomyPolicy(lender, intentions=(), work_limit=work_limit),
                AutonomyPolicy(reviewer, intentions=(), work_limit=work_limit))
    workshop = WorkshopConfig(tuple((i, 'dirty') for i in tools) + tuple((i, 'raw') for i in pieces + spares))
    return CompensationWorld(config, profiles, ProcessingPolicy(), tuple(AgentPolicy(a) for a in actors),
               workshop=workshop, autonomy=autonomy,
               release=ReleaseConfig(tools[:history] if gated_history else (), revision_unit),
               reviewers=(ReviewPolicy(worker), ReviewPolicy(lender, review_units=quotes[0]), ReviewPolicy(reviewer, review_units=quotes[1])))


def introduce(w, index):
    worker, lender, _ = w.config.actors
    tool = Ref(Kind.ENTITY, 'tool:' + str(index), 1)
    piece = Ref(Kind.ENTITY, 'piece:' + str(index), 1)
    if index:
        previous = Ref(Kind.ENTITY, 'tool:' + str(index-1), 1)
        spare = Ref(Kind.ENTITY, 'retire:' + str(index), 1)
        fund_command(w, WorkshopCommand('offer:retire:' + str(index), 'offer:retire:' + str(index), lender, 'use', (spare, previous)))
        fund_command(w, WorkshopCommand('offer:old:' + str(index), 'offer:old:' + str(index), worker, 'inspect', (previous,)))
    fund_command(w, WorkshopCommand('offer:clean:' + str(index), 'offer:clean:' + str(index), lender, 'clean', (tool,)))
    w.execute(Attempt('offer:piece:' + str(index), 'offer:piece:' + str(index), ActionRequest(lender, TRANSFER, (piece, worker), ())))
    for obj in (piece, tool):
        key = 'offer:inspect:' + obj.key
        fund_command(w, WorkshopCommand(key, key, worker, 'inspect', (obj,)))


def case(history=3, renewals=3, gated_history=True, refusal=False, **kwargs):
    w = world(history, renewals, gated_history, **kwargs)
    schedules = [run(w, 10000)]; cuts = []
    for i in range(history + renewals):
        if refusal and i == history:
            for actor in w.config.actors[1:]:
                key = 'boundary:' + actor.key
                fund_command(w, ReleaseCommand(key, key, actor, 'boundary', willingness=False, work_limit=256))
        cuts.append(len(w._journal))
        introduce(w, i); schedules.append(run(w, 10000))
    return w, {'history': history, 'renewals': renewals, 'gated_history': gated_history,
               'refusal': refusal, 'cuts': cuts, 'scheduling': schedules}


def main_demo():
    from .compensation_evaluation import evaluate
    w, setup = case()
    return evaluate(w, setup)
