from hle_unified.records import (
    ObjectId, ObjectRef, ObjectVersion, Role, Definition, SourceStatus, Attribute,
    Material, Moment, TimeScope, Account, Occurrence)
from hle_unified.store import ObjectStore, CONSERVATION_LAW

WRITER = "u2.world"


def ident(key):
    return ObjectId("workshop", key)


def ref(key, revision=1):
    return ObjectRef(ident(key), revision)


ALICE, BOB, ROOM = ref("alice"), ref("bob"), ref("room")
UNIT, FORM, LAW, RULE = ref("unit"), ref("bowl-form"), ref("law"), ref("return-rule")


def definition(key, meaning, constraints=()):
    return ObjectVersion(ref(key), WRITER, key, (Role.DEFINITION,),
        (Definition(meaning, SourceStatus.ENGINEERING, constraints),))


def base():
    store = ObjectStore()
    store.create("genesis", WRITER, (
        ObjectVersion(ALICE, WRITER, "Alice", (Role.PERSON,)),
        ObjectVersion(BOB, WRITER, "Bob", (Role.PERSON,)),
        ObjectVersion(ROOM, WRITER, "Workshop", (Role.CONTEXT,)),
        definition("unit", "One declared material quantum."),
        definition("bowl-form", "A reusable bowl form; instances remain distinct."),
        definition("law", "Conserve owned material quanta; no sources or sinks during transformation.",
                   (Attribute("law", CONSERVATION_LAW),)),
        definition("return-rule", "Return the borrowed bowl before tick 9."),
    ))
    return store


def bowl(key, quantity=1, owner=ALICE, label="White bowl"):
    return ObjectVersion(ref(key), WRITER, label, (Role.MATERIAL,),
        (Material(owner.identity, owner.identity, quantity, UNIT, "intact"),), definition=FORM)


def event(key, at=1, referent=None, content=()):
    return ObjectVersion(ref(key), WRITER, key, (Role.EVENT,),
        (Account(referent, content, Moment(at, 0)),), occurrence=Occurrence.ACTUAL_EVENT)


def active_quantities(store):
    """Independent history fold: last write wins by ID; sum material by owner."""
    heads = {}
    for tx in store.journal():
        for version in tx.versions:
            heads[version.ref.identity] = version
    totals = {}
    for version in heads.values():
        material = version.facet(Material)
        if material is not None and version.lifecycle.value == "active":
            key = (material.owner, material.unit)
            totals[key] = totals.get(key, 0) + material.quantity
    return totals
