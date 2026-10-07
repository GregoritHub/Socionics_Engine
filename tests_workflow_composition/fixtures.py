"""Prospectively fixed FB4.1 family worlds and defining-step controls."""
from hle_unified.workflow_execution import WorkflowEngine
from hle_unified import workflow_content as wf
from tests_c7_workflow.fixtures import *


FAMILIES = ("theorize-apply-embody", "share-commune-identify",
            "coordinate-mobilize", "institutionalize-educate",
            "organize-integrate-apply")


class CompositionAblatedWorkflow(WorkflowEngine):
    """Equal-price defining-step interventions; ordinary audit must reject."""
    CUTS = {"tae-apply": "material", "cm-mobilize": "material",
            "oia-apply": "material", "sci-commune": "commune",
            "ie-educate": "educate"}

    def _semantic_step(self, name, p, previous):
        result = super()._semantic_step(name, p, previous)
        request_ = p.get("request")
        cut = self.CUTS.get(request_.key) if p.get("c7w") and request_ else None
        if cut is None or not (name.startswith("resolve:") or len(p["recipe"].steps) == 1):
            return result
        kind, target, values = result
        outer = wf.decode(values["payload"])
        resolved = outer["kind"] == "resolved_work"
        value = wf.decode(outer["content"]) if resolved else outer
        if cut == "material":
            value["kind"] = "withheld_command"
            value["permitted"] = False
        elif cut == "commune":
            rows = list(value["tasks"])
            row = rows[0]
            rows[0] = (row[0], "inspect", row[2], row[3], row[4], row[5])
            value["tasks"] = tuple(rows)
        elif cut == "educate":
            value.update(tasks=(), conflicts=(), missing=(), blocked=(), late=(),
                         order=(), slots=(), feasible=False, authorized=False, answer=None)
        if resolved:
            outer["content"] = wf.encode(value)
        else:
            outer = value
        return kind, target, {"payload": wf.encode(outer)}


def _origin_conflict(e, prefix):
    left = authored(e, prefix + "-origin-left")
    rows = list(tasks())
    row = rows[0]
    rows[0] = (row[0], "inspect", row[2], row[3], row[4], row[5])
    right = authored(e, prefix + "-origin-right", tuple(rows))
    return work(e, request(e, prefix + "-origin-conflict", "Contemplate", "expenditure", (left, right)))


def _return_to_origin(e, prefix, conflict):
    return work(e, request(e, prefix + "-origin-return", "use-personal", None,
                           (conflict,), completed=(), clock=0))


def _public(e, key, actor=ALICE):
    ref_ = e.job_status(actor, key)["public.0"]
    for who in (ALICE, BOB):
        expose(e, who, ref_)
    return ref_


def _activity_decision(e, prefix, event):
    observation = receive(e, event, ALICE, prefix + "-result-observation")
    decision = work(e, request(e, prefix + "-decision", "use-activity", None,
                               (observation,), completed=(), clock=0))
    return observation, decision


def run_family(e, family):
    if family not in FAMILIES:
        raise ValueError(family)
    prefix = {name: key for name, key in zip(FAMILIES, ("tae", "sci", "cm", "ie", "oia"))}[family]
    conflict = _origin_conflict(e, prefix)
    outputs = []
    if family == FAMILIES[0]:
        intent = authored(e, "tae-intent", hypothetical=True)
        theory = work(e, request(e, "tae-theory", "Theorize", "accumulation", (intent,)))
        event = work(e, request(e, "tae-apply", "Apply", "expenditure", (theory,),
                                  stock=e.world.head(CARE.identity).ref), allow_failure=True)
        observed = receive(e, event, ALICE, "tae-trial-observation")
        embodied = work(e, request(e, "tae-embody", "Embody", "expenditure", (observed,)))
        decision = work(e, request(e, "tae-decision", "use-personal", None,
                                   (embodied,), completed=(), clock=0))
        outputs = [theory, event, embodied]
    elif family == FAMILIES[1]:
        own = authored(e, "sci-contribution")
        offer, reply, group_ = exchange(e, own, "sci-share-exchange", domain="personal")
        work(e, request(e, "sci-share", "Share", "accumulation", (own, offer, reply),
                        peer=BOB, group=group_))
        shared_ = _public(e, "sci-share")
        offer, reply, _ = exchange(e, shared_, "sci-commune-exchange", domain="shared", g=group_)
        work(e, request(e, "sci-commune", "Commune", "expenditure", (shared_, offer, reply),
                        peer=BOB, group=group_))
        renewed = _public(e, "sci-commune")
        stance = authored(e, "sci-owned-stance", kind="stance")
        identified = work(e, request(e, "sci-identify", "Identify", "expenditure",
                                     (renewed, stance), peer=BOB, group=group_))
        decision = work(e, request(e, "sci-decision", "use-personal", None,
                                   (identified,), completed=("maintain",), clock=1))
        outputs = [shared_, renewed, identified]
    elif family == FAMILIES[2]:
        observed = observe(e, "cm-observed", primitive="inspect")
        offer, reply, group_ = exchange(e, observed, "cm-coordinate-exchange", domain="activity")
        work(e, request(e, "cm-coordinate", "Coordinate", "expenditure",
                        (observed, offer, reply), peer=BOB, group=group_))
        coordinated = _public(e, "cm-coordinate")
        event = work(e, request(e, "cm-mobilize", "Mobilize", "expenditure", (coordinated,),
                                  peer=BOB, group=group_, stock=e.world.head(CARE.identity).ref),
                     allow_failure=True)
        _, decision = _activity_decision(e, "cm", event)
        outputs = [coordinated, event]
    elif family == FAMILIES[3]:
        proposal, group_ = draft(e, "ie-draft")
        ballot = votes(e, proposal, group_, "ie-vote")
        work(e, request(e, "ie-institutionalize", "Institutionalize", "expenditure",
                        (proposal, *ballot), peer=BOB, group=group_))
        rule = _public(e, "ie-institutionalize")
        offer, reply, _ = exchange(e, rule, "ie-educate-exchange", domain="system", g=group_)
        work(e, request(e, "ie-educate", "Educate", "accumulation", (rule, offer, reply),
                        peer=BOB, group=group_))
        taught = _public(e, "ie-educate")
        decision = work(e, request(e, "ie-decision", "use-shared", None, (taught,),
                                   actor=BOB, peer=ALICE, group=group_,
                                   completed=("maintain",), clock=1))
        outputs = [rule, taught]
    else:
        first = observe(e, "oia-care", primitive="care")
        second = observe(e, "oia-use", primitive="use")
        organized = work(e, request(e, "oia-organize", "Organize", "expenditure", (first, second)))
        companion = model(e, "oia-companion")
        integrated = work(e, request(e, "oia-integrate", "Integrate", "expenditure",
                                     (organized, companion)))
        current = e.world.head(DEVICE.identity).ref
        expose(e, ALICE, current)
        event = work(e, request(e, "oia-apply", "Apply", "expenditure", (integrated,),
                                  target=current, stock=e.world.head(CARE.identity).ref), allow_failure=True)
        _, decision = _activity_decision(e, "oia", event)
        outputs = [organized, integrated, event]
    returned = _return_to_origin(e, prefix, conflict)
    return {"family": family, "outputs": tuple(outputs), "decision": decision,
            "answer": data(e, decision, BOB if family == FAMILIES[3] else ALICE),
            "conflict": conflict, "origin_return": returned}


def pair(family):
    witness = setup_workflow()
    ablation = setup_workflow(engine_type=CompositionAblatedWorkflow)
    good = run_family(witness, family)
    cut = run_family(ablation, family)
    return witness, ablation, good, cut
