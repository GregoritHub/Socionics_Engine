"""Explicit workshop setup, never a generated-development claim."""
from hle_unified.records import (ObjectId, ObjectRef, ObjectVersion, Role, Material,
    Definition, SourceStatus, Procedure, Relation, Endpoint, TimeScope, Moment,
    Attribute, Account, Occurrence, ClaimStatus)
from hle_unified.operation_records import OperationRequest, WRITER, LAW, SIGNATURES
from hle_unified.operations import OperationEngine, wallet_address, record
from hle_unified.material import OperationStore, attrs, attributes
from hle_unified.particulars import Selector, DetailAddress
from hle_unified.store import next_version


def ref(key, revision=1):
    return ObjectRef(ObjectId("workshop", key), revision)


ALICE, BOB, EVE = (ref(k).identity for k in ("alice", "bob", "eve"))
ROOM, UNIT, LAW_REF, FORM, CUE = (ref(k) for k in ("room", "unit", "law", "tool-form", "cue"))
SAW, SAW2, KIT, STOCK, CARE, BORROWED, OBLIGATION, REPAIR = (
    ref(k) for k in ("saw", "saw2", "kit", "stock", "care", "borrowed", "return-obligation", "repair-procedure"))


def definition(ref_, text, constraints=()):
    return ObjectVersion(ref_, WRITER, text, (Role.DEFINITION,),
                         (Definition(text, SourceStatus.ENGINEERING, constraints),))


def tool(ref_, *, owner=ALICE, holder=None, damaged=False, wear=0, maximum=3):
    return ObjectVersion(ref_, WRITER, ref_.identity.key, (Role.MATERIAL,),
        (Material(owner, owner if holder is None else holder, 1, UNIT, "damaged" if damaged else "serviceable"),),
        definition=FORM, attributes=attributes({"wear": maximum if damaged else wear, "max_wear": maximum}))


def stock(ref_, purpose, quantity, owner=ALICE):
    return ObjectVersion(ref_, WRITER, ref_.identity.key, (Role.MATERIAL,),
        (Material(owner, owner, quantity, UNIT, "stock"),),
        attributes=attributes({"consumed": 0, "purpose": purpose}))


def setup(budget=200, quantity=2, *, prepare=True, time_budget=None):
    world = OperationStore()
    people = tuple(ObjectVersion(ObjectRef(a, 1), WRITER, a.key, (Role.PERSON,)) for a in (ALICE, BOB, EVE))
    time_budget = budget if time_budget is None else time_budget
    wallets = tuple(record(wallet_address(a), "Finite work wallet", {"record_type": "wallet", "actor": a,
        "energy": budget, "time": time_budget, "initial_energy": budget, "initial_time": time_budget}) for a in (ALICE, BOB, EVE))
    obligation = ObjectVersion(OBLIGATION, WRITER, "Return borrowed tool", (Role.COMMITMENT,),
        (Relation("return_due", (Endpoint("borrower", ObjectRef(BOB, 1)), Endpoint("owner", ObjectRef(ALICE, 1)),
            Endpoint("item", BORROWED)), True, ROOM, TimeScope(Moment(0, 0), None), (Attribute("status", "open"),)),))
    world.create("genesis", WRITER, (*people, *wallets,
        ObjectVersion(ROOM, WRITER, "Workshop", (Role.CONTEXT,)),
        definition(UNIT, "One finite material quantum"), definition(FORM, "Workshop tool"),
        definition(CUE, "Assistance cue"), definition(LAW_REF, "Finite native workshop", (Attribute("law", LAW),)),
        tool(SAW, damaged=True), tool(SAW2, damaged=True), tool(KIT, maximum=10),
        tool(BORROWED, holder=BOB, wear=1), stock(STOCK, "repair", quantity), stock(CARE, "care", 2), obligation,
        ObjectVersion(REPAIR, WRITER, "Repair a tool", (Role.PROCEDURE,),
            (Procedure(SIGNATURES["repair"], (), (), (), "u4.repair.v1"),))))
    engine = OperationEngine(world, LAW_REF)
    if prepare:
        basics(engine, ALICE)
    return engine


def perform(engine, request, limit=100):
    engine.start("start:" + request.actor.key + ":" + request.key, request)
    engine.advance("work:" + request.actor.key + ":" + request.key, request.actor, request.key, limit)
    return engine.commit("commit:" + request.actor.key + ":" + request.key, request.actor, request.key)


def show(engine, actor, source, key=None, selectors=None, subject=None):
    key = key or actor.key + ":" + source.identity.key + ":" + str(source.revision)
    selectors = selectors or (Selector("name", "name", ("label",)),)
    engine.disclose("show:" + key, actor, source, selectors, subject)
    perform(engine, OperationRequest("read:" + key, actor, "read", ROOM, delivery="show:" + key))
    return DetailAddress("show:" + key, selectors[0].key)


def basics(engine, actor):
    for source in (ROOM, CUE, SAW, SAW2, KIT, STOCK, CARE, BORROWED, OBLIGATION):
        show(engine, actor, source)
    show(engine, actor, REPAIR, selectors=(Selector("procedure", "definition", ("facets", "0")),))


def evidence(engine, actor, source):
    values = engine.participant_view(actor).lookup(subject=source.identity)
    return (values[-1].address,)


def repair(engine, key="repair", target=SAW, actor=ALICE, **kwargs):
    return OperationRequest(key, actor, "repair", ROOM, participants=(BOB,),
        evidence=evidence(engine, actor, target), target=target, tool=engine.world.head(KIT.identity).ref,
        stock=engine.world.head(STOCK.identity).ref, **kwargs)


def receive(engine, event, actor, key):
    observation = engine.deliver_event("deliver:" + key, event, actor)
    perform(engine, OperationRequest("read-event:" + key, actor, "read", ROOM, delivery="deliver:" + key))
    return observation


def binding(engine, key, actor, observation, *, meaning="Repair is possible with help.", previous=None):
    viewed = engine.participant_view(actor)
    details = viewed.resolve(observation)
    target = next(p.value for p in details if p.address.key == "target")
    r = ref(key) if previous is None else ObjectRef(previous.identity, previous.revision + 1)
    value = ObjectVersion(r, WRITER, "Actor interpretation draft", (Role.INTERPRETATION,),
        (Account(target, (), Moment(0, 0), actor, (observation,)),), previous=previous,
        occurrence=Occurrence.INTERPRETATION,
        attributes=attributes({"cue": CUE, "context": ROOM, "meaning": meaning,
                               "endorsement": ClaimStatus.ENDORSED.value, "confidence": 70}))
    engine.declare("draft:" + key + ":" + str(r.revision), (value,))
    return OperationRequest("bind:" + key + ":" + str(r.revision), actor, "bind", ROOM,
        binding=r, evidence=(details[0].address,))
