"""Supplied development opportunities. Generated patterns are runtime outputs."""
from dataclasses import replace
from tests_u6.fixtures import *
from hle_unified.records import Composition, Concept
from hle_unified.shell import ShellEngine
from hle_unified.shell_records import PatternPolicy, PatternSeed, Effect, EncounterRequest
from hle_unified.shell_policy import FACT_SCHEMA
from hle_unified.operations import address, indexed

TRIGGER, OTHER_TRIGGER = ref("entrusted-affordance"), ref("unrelated-affordance")
GROUP, MEMORY, POSSIBILITY, ACTION = (ref(k) for k in ("group", "memory", "possibility", "action"))
TARGETS = {"tool": SAW, "person": ObjectRef(BOB, 1), "group": GROUP, "rule": RULE,
           "memory": MEMORY, "possibility": POSSIBILITY, "action": ACTION, "relation": OBLIGATION}


def setup7(*, generate=True, budget=6000, actor=ALICE, **kwargs):
    e = ShellEngine.adopt(setup6(budget=budget, **kwargs))
    objects = (
        definition(TRIGGER, "Entrusted performance affordance"),
        definition(OTHER_TRIGGER, "Unrelated affordance"),
        ObjectVersion(GROUP, WRITER, "Work group", (Role.COLLECTIVE,), (Composition((ALICE, BOB), "workshop"),)),
        ObjectVersion(MEMORY, WRITER, "Memory of prior work", (Role.CLAIM,),
            (Account(SAW, (), Moment(0, 0), ALICE),), occurrence=Occurrence.REMEMBERED_CLAIM),
        ObjectVersion(POSSIBILITY, WRITER, "Possible shared task", (Role.CLAIM,),
            (Account(SAW, (), Moment(0, 0), ALICE),), occurrence=Occurrence.HYPOTHETICAL),
        ObjectVersion(ACTION, WRITER, "An addressable action plan", (Role.PROCEDURE,),
            (Procedure(("target",), (), (), ()),)))
    e.declare("u7-opportunity-objects", objects)
    for r in (*TARGETS.values(), TRIGGER, OTHER_TRIGGER, ObjectRef(EVE, 1)):
        if r not in e.access._known_refs(ALICE):
            show(e, ALICE, r)
    e.configure_patterns("patterns-alice", PatternPolicy(ALICE, generate=generate))
    return e


def supply(e, key, *, target=SAW, actor=ALICE, context=ROOM, trigger=TRIGGER,
           deliver=True, read=True, version=None, **overrides):
    r = version or ref("facts:"+key)
    values = {"schema": FACT_SCHEMA, "target": target, "context": context, "receiver": actor,
        "trigger": trigger, "available": True, "safe": True, "requires_partner": False,
        "willing": True, "approval_required": False, "approved": False, "feedback": "neutral",
        "recommended": "engage", **overrides}
    v = ObjectVersion(r, WRITER, "Declared encounter facts", (Role.RECORD,),
        previous=None if r.revision == 1 else ObjectRef(r.identity, r.revision-1), attributes=attributes(values))
    e.declare("facts:"+key, (v,))
    if deliver:
        selectors = tuple(Selector(a.name, "detail", ("attributes", str(i), "value")) for i, a in enumerate(v.attributes))
        e.disclose("facts-delivery:"+key, actor, r, selectors, target)
        if read:
            perform(e, OperationRequest("facts-read:"+key, actor, "read", context, delivery="facts-delivery:"+key))
    return r


def request7(e, key, source=None, *, target=SAW, actor=ALICE, context=ROOM, cue=CUE5,
             carrier=ObjectRef(BOB, 1), bearer=ObjectRef(EVE, 1), **kwargs):
    evidence_ = () if source is None else tuple(p.address for p in e.participant_view(actor).resolve(source))
    return EncounterRequest(key, actor, target, context, cue, carrier, bearer, evidence_, **kwargs)


def meet(e, key, source=None, **kwargs):
    r = request7(e, key, source, **kwargs)
    perform(e, r, limit=1000)
    return e.job_status(r.actor, r.key)["encounter"]


def generated(e):
    a = supply(e, "learning-1", target=SAW, feedback="blame")
    meet(e, "learning-1", a)
    b = supply(e, "learning-2", target=SAW2, feedback="blame")
    meet(e, "learning-2", b, target=SAW2)
    return e.pattern_view(ALICE)[0]


def inject(e, effect, *, actor=ALICE, cue=CUE5, context=ROOM, key="fixture"):
    origin = SAW
    return e.inject_pattern_fixture(key, PatternSeed(actor, context, cue, TRIGGER,
        origin, (effect,), evidence(e, actor, origin)))


def cross_target(e):
    rows = {}
    for label, target in TARGETS.items():
        source = supply(e, "transfer:"+label, target=target)
        eref = meet(e, "transfer:"+label, source, target=target)
        rows[label] = attrs(e.world.resolve(eref))
    return rows
