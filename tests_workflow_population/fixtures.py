"""Supplied independent workflow demands for FB5.1 population tests."""
from dataclasses import replace

from tests_c7_workflow.fixtures import (
    ALICE, BOB, ROOM, CUE5, DEVICE, CARE, authored, expose, seed,
    setup_workflow, tasks, wf,
)
from tests_workflow_selection.final_fixtures import final_fixture
from hle_unified.population import Population
from hle_unified.selection_records import SelectionRequest
from hle_unified.workflow_selection_execution import WorkflowFinalSelectionEngine
from hle_unified.workflow_selection_records import WorkflowSelectionRequest


def workflow_request(e, actor, key, externalize=False):
    rows = tasks(actor)
    one = authored(e, key + "-one", rows=rows, actor=actor, target=DEVICE)
    two = authored(e, key + "-two", rows=rows, actor=actor, target=DEVICE,
                   hypothetical=externalize)
    demand = seed(e, key + "-need",
                  wf.encode(dict(kind="workflow_need", priorities=(10, 0, 0, 0),
                                 externalize=externalize)),
                  actor=actor, target=DEVICE, relation="c7ws.need")
    return WorkflowSelectionRequest(key, actor, ROOM, CUE5, DEVICE, demand, (one, two))


def workflow_population(count=2, episodes=3, quantum=17, budget=200000,
                        repeat_limit=None):
    e = setup_workflow(engine_type=WorkflowFinalSelectionEngine, budget=budget)
    actors = (ALICE, BOB)[:count]
    requests = tuple(workflow_request(e, actor, "workflow-" + actor.key,
                                      externalize=i % 2 == 1)
                     for i, actor in enumerate(actors))
    return Population(e, requests, episodes, quantum, repeat_limit), requests


def material_population(episodes=1, quantum=16, budget=200000):
    e, r, base = final_fixture("Express", "expenditure",
                               engine_type=WorkflowFinalSelectionEngine)
    return Population(e, (r,), episodes, quantum, None), base


def mixed_population(episodes=1, quantum=32):
    """One workflow demand and one inherited C6 demand on the workflow engine."""
    from tests_c6 import fixtures as old
    e = setup_workflow(engine_type=WorkflowFinalSelectionEngine, budget=200000)
    workflow = workflow_request(e, ALICE, "workflow-alice")
    e.declare("mixed-shell-anchor", (old.definition(old.dev.TRIGGER,
              "Entrusted performance affordance"),))
    for obj in (old.SAW, old.SUPPLY, old.ref("bob-consumables"), old.dev.TRIGGER):
        old.expose(e, BOB, obj)
    e.configure_patterns("patterns-bob", old.PatternPolicy(BOB, generate=False))
    old.dev.supply8(e, "opportunity-bob", actor=BOB, partner=old.ObjectRef(ALICE, 1))
    old.seed_intent(e, "legacy-bob-intent", cap=3, actor=BOB)
    demand = old.need(e, "legacy-bob-need", weights=(10, 0, 0, 10), commit=True,
                      actor=BOB)
    legacy = SelectionRequest("legacy-bob", BOB, old.ROOM, old.CUE5, old.SAW, demand,
                              stock=old.ref("bob-consumables"), peer=ALICE,
                              limit=128, alternatives=16)
    return Population(e, (workflow, legacy), episodes, quantum, None)


def foreign_workflow_request(p):
    return replace(p.requests[0], demand=p.requests[1].demand)
