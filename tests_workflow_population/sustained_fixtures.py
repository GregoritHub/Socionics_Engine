"""Prospectively declared FB5.2 sustained and measurement fixtures."""
import random

from hle_unified.population import Population
from hle_unified.workflow_selection_execution import WorkflowFinalSelectionEngine
from hle_unified.workflow_selection_records import WorkflowSelectionRequest
from tests_c7_workflow.fixtures import ALICE, BOB, ROOM, CUE5, DEVICE, authored, seed, setup_workflow, wf


def task_rows(actor, count):
    if count not in (2, 4, 8):
        raise ValueError("declared task count required")
    return tuple(("task-" + str(i), "care" if i == 0 else "use",
                  () if i == 0 else ("task-" + str(i - 1),), i, i + 2, actor)
                 for i in range(count))


def owned_request(engine, actor, key, count=2, externalize=False):
    rows = task_rows(actor, count)
    one = authored(engine, key + "-one", rows=rows, actor=actor, target=DEVICE)
    two = authored(engine, key + "-two", rows=rows, actor=actor, target=DEVICE,
                   hypothetical=externalize)
    demand = seed(engine, key + "-need",
                  wf.encode(dict(kind="workflow_need", priorities=(10, 0, 0, 0),
                                 externalize=externalize)),
                  actor=actor, target=DEVICE, relation="c7ws.need")
    return WorkflowSelectionRequest(key, actor, ROOM, CUE5, DEVICE, demand, (one, two))


def sustained_population(seed_value=17, episodes=24, quantum=32, repeat_limit=2,
                         budget=200000, inactive=0, shared=False, task_count=2):
    engine = setup_workflow(engine_type=WorkflowFinalSelectionEngine, budget=budget,
                            inactive=inactive, shared=shared)
    requests = [owned_request(engine, actor, "sustained-" + actor.key, task_count,
                              externalize=i == 1)
                for i, actor in enumerate((ALICE, BOB))]
    random.Random(seed_value).shuffle(requests)
    return Population(engine, tuple(requests), episodes, quantum, repeat_limit)
