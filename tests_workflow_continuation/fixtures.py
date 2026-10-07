"""Clearly authored bounded goals; all subsequent meanings are paid outputs."""
from dataclasses import replace
from tests_c7_workflow.fixtures import *
from hle_unified.workflow_selection_execution import WorkflowFinalSelectionEngine
from hle_unified.workflow_selection_records import WorkflowSelectionRequest
from hle_unified.workflow_continuation import WorkflowContinuation


def chain(budget=200000, cls=WorkflowContinuation):
    e = setup_workflow(engine_type=WorkflowFinalSelectionEngine, budget=budget)
    own = authored(e, 'continuation-intent', hypothetical=True)
    demand = seed(e, 'continuation-need', wf.encode(dict(kind='workflow_need',
                  priorities=(10, 8, 0, 9), externalize=True)), relation='c7ws.need', target=DEVICE)
    r = WorkflowSelectionRequest('development', ALICE, ROOM, CUE5, DEVICE, demand,
                                 (own,), stock=e.world.head(CARE.identity).ref)
    return cls(e, (r,), episodes=3, quantum=17, repeat_limit=2)


class WithheldHandoff(WorkflowContinuation):
    """Deliberate control: keep original content, despite claimed ordinary policy."""
    def request(self, index):
        return replace(super().request(index), accessible=self.requests[index].accessible)


def query_personal(p):
    output = p.input_history[0][-1][0]
    return work(p.engine, request(p.engine, 'continuation-query', 'use-personal', None,
                                 (output,), completed=(), clock=0))
