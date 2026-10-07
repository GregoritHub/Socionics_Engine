"""Prospectively fixed FB4.2 parent lifecycle and matched face worlds."""
from dataclasses import replace
from tests_c7_workflow.fixtures import *
from tests_u11.fixtures import work as collective_work
from hle_unified.workflow_nesting_execution import WorkflowNestingEngine
from hle_unified.workflow_nesting_records import WorkflowParentRequest, WorkflowChildEvidence
from hle_unified.store import next_version


def setup_parent(**kwargs):
    return setup_workflow(engine_type=WorkflowNestingEngine, **kwargs)


def expose_operation(e, operation, actor=ALICE):
    version = e.world.resolve(operation)
    selectors = tuple(Selector(a.name, "detail", ("attributes", str(i), "value"))
        for i, a in enumerate(version.attributes) if a.name in ("actor", "context", "status", "spent", "result"))
    if {s.key for s in selectors} <= {p.address.key for p in e.participant_view(actor).resolve(operation)}:
        return
    show(e, actor, operation, key="c7n:" + actor.key + ":" + operation.identity.key,
         selectors=selectors)


def child(e, key, output, actor=ALICE):
    operation = e._jobs[actor, key]
    expose_operation(e, operation, actor)
    return WorkflowChildEvidence(operation, output)


def parent_request(e, children, key="parent", group=None, links=()):
    return WorkflowParentRequest(key, ALICE, "workflow-parent-v1", ROOM, CUE5,
        tuple(children), tuple(p.address for p in e.participant_view(ALICE).resolve(DEVICE)),
        DEVICE, tuple(links), group)


def _normal_children(e):
    first = model(e, "parent-model")
    shared_case = cell(e, "Share", "expenditure", key="parent-social", consumer=False)
    second = shared_case["result"]
    children = (child(e, "parent-model", first), child(e, "parent-social", second))
    return children, shared_case["extra"]["group"]


def _failed_children(e):
    first = model(e, "parent-model")
    intent = authored(e, "parent-failed-intent", hypothetical=True)
    request_ = request(e, "parent-failed", "Theorize", "accumulation", (intent,))
    e.start("failed-start", request_); e.advance("failed-paid", ALICE, request_.key, 100000)
    old = e.world.resolve(intent); account = old.facet(Account); changed = wf.decode(account.content[0].object)
    changed["consent"] = False
    e.declare("failed-source-revision", (next_version(old,
        facets=(replace(account, content=(replace(account.content[0], object=wf.encode(changed)),)),)),))
    event = e.commit("failed-commit", ALICE, request_.key)
    assert e.job_status(ALICE, request_.key)["failure"] == "stale_dependency"
    observation = receive(e, event, ALICE, "parent-failed-result")
    return (child(e, "parent-model", first), child(e, "parent-failed", observation)), None


def parent_world(mode):
    if mode not in ("normal", "failed-child", "membership-change", "participant-withdrawal"):
        raise ValueError(mode)
    e = setup_parent()
    children, group = _failed_children(e) if mode == "failed-child" else _normal_children(e)
    request_ = parent_request(e, children, group=group)
    if mode in ("normal", "failed-child"):
        output = work(e, request_)
    else:
        e.start("parent-start", request_); e.advance("parent-paid", ALICE, request_.key, 100000)
        if mode == "membership-change":
            collective_work(e, "parent-leave", "leave", actor=BOB, focus=group)
        else:
            stance = ref("parent-social-exchange-peer")
            old = e.world.resolve(stance); account = old.facet(Account); value = wf.decode(account.content[0].object)
            value["consent"] = False
            revised = next_version(old, facets=(replace(account,
                content=(replace(account.content[0], object=wf.encode(value)),)),))
            e.declare("parent-withdraw", (revised,))
            perform(e, OperationRequest("parent-retain-withdrawal", BOB, "bind", ROOM,
                binding=revised.ref, evidence=evidence(e, BOB, DEVICE)))
        output = e.commit("parent-finish", ALICE, request_.key)
    return e, dict(mode=mode, output=output, request=request_, children=children, group=group)


def face_pair(route, *, accumulation_tim="iee", expenditure_tim="iee"):
    accumulation = setup_workflow(tim=accumulation_tim)
    expenditure = setup_workflow(tim=expenditure_tim)
    left = cell(accumulation, route, "accumulation")
    right = cell(expenditure, route, "expenditure")
    return accumulation, expenditure, left, right
