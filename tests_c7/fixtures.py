"""Supplied initial population with independently owned goals and finite wallets."""
import random
from dataclasses import replace
from tests_c6.fixtures import *
from hle_unified.population import Population
from hle_unified.cognition import profile
from hle.model_a import TYPES


def population(seed_value=17, count=3, episodes=24, quantum=32, budget=20000, repeat_limit=None):
    rng=random.Random(seed_value)
    types=rng.sample(list(TYPES),count)
    actors=(ALICE,BOB,EVE)[:count]
    def factory(world,law):
        fresh=OperationStore()
        for tx in world.journal():
            vs=[]
            for v in tx.versions:
                d=attrs(v)
                if d.get('record_type')=='wallet':
                    v=replace(v,attributes=attributes(dict(d,energy=budget,time=budget,initial_energy=budget,initial_time=budget)))
                for actor,tim in zip(actors,types):
                    if v.ref==profile(actor,tim).ref:v=profile(actor,tim)
                vs.append(v)
            fresh.create(tx.key,tx.writer,tuple(vs))
        return SelectionEngine(fresh,law)
    e=setup(generate=False,engine_type=factory,actual='serviceable')
    requests=[]
    for i,actor in enumerate(actors):
        for obj in (SAW,ROOM,CUE5,SUPPLY,ref('bob-consumables'),dev.TRIGGER,*(ObjectRef(a,1) for a in (ALICE,BOB,EVE))):
            expose(e,actor,obj)
        if actor!=ALICE:e.configure_patterns('patterns-'+actor.key,PatternPolicy(actor,generate=False))
        dev.supply8(e,'opportunity-'+actor.key,actor=actor,partner=ObjectRef(actors[(i+1)%count],1))
        own=seed_intent(e,'initial-'+actor.key,cap=2+i,actor=actor)
        # Competing personal/material/system outcomes. Different owned histories
        # cause future rankings; the schedule supplies no route sequence.
        weights=((10,10,0,10),(10,0,0,10),(10,0,0,10))[i]
        d=need(e,'need-'+actor.key,weights=weights,commit=True,actor=actor)
        requests.append(SelectionRequest('owned-'+actor.key,actor,ROOM,CUE5,SAW,d,
            stock=SUPPLY if i==0 else ref('bob-consumables') if i==1 else None,
            peer=actors[(i+1)%count],limit=128,alternatives=16))
    rng.shuffle(requests)
    return Population(e,requests,episodes,quantum,repeat_limit),types
