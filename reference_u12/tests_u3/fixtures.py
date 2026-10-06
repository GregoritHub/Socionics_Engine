"""Declared histories and imported work evidence, not a native paid executor."""
from hle.contracts import ClaimStatus
from hle_unified.records import (ObjectVersion, Role, Material, Procedure, Definition,
    SourceStatus, Attribute, Account, Proposition, TimeScope, Moment, Occurrence)
from hle_unified.compact import CompactStore
from hle_unified.particulars import AccessLedger, Grant, Selector, DetailAddress, RECEIPT_WRITER
from tests_u2.fixtures import (base, ref, ident, WRITER, ALICE, BOB, ROOM, UNIT, FORM, RULE)

SAW, CUE, REPAIR = ref("saw"), ref("cue-assistance"), ref("repair-procedure")


def setup():
    world = CompactStore.from_store(base())
    world.create("workshop", WRITER, (
        ObjectVersion(SAW, WRITER, "Workshop saw", (Role.MATERIAL,),
            (Material(ALICE.identity, ALICE.identity, 1, UNIT, "intact"),), definition=FORM),
        ObjectVersion(CUE, WRITER, "Assistance cue", (Role.DEFINITION,),
            (Definition("Contextual assistance anchor; no automatic tension or competence.", SourceStatus.ENGINEERING),)),
        ObjectVersion(REPAIR, WRITER, "Inspect and repair", (Role.PROCEDURE,),
            (Procedure(("tool",), (), (), (), None),)),
    ))
    return world, AccessLedger(world)


def receipt(world, key, actor, operation, work_key, inputs, completed=2, required=2, spent=None):
    attrs = [Attribute("actor", actor), Attribute("operation", operation), Attribute("work_key", work_key),
        Attribute("required", required), Attribute("completed", completed), Attribute("spent", completed if spent is None else spent)]
    attrs += [Attribute("input." + str(i), r) for i, r in enumerate(inputs)]
    value = ObjectVersion(ref(key), RECEIPT_WRITER, "Imported processing evidence", (Role.RECORD,), attributes=tuple(attrs))
    world.create("work-" + key, RECEIPT_WRITER, (value,), actor=actor,
        reason="Declared fixture imports cumulative work from a trusted processor; no U4 executor claimed.")
    return value.ref


def disclose(ledger, actor, key, source, selectors, *, subject=None, completed=2):
    ledger.grant(Grant("grant-" + key, actor, source, source if subject is None else subject, selectors))
    ledger.deliver(actor, key, "grant-" + key, Moment(5, 0))
    work = receipt(ledger.world, actor.key + "-read-" + key, actor, "read", key, (source,), completed=completed)
    ledger.process(actor, key, work)
    return work


def basics(ledger, actor):
    disclose(ledger, actor, "tool", SAW, (
        Selector("name", "name", ("label",)),
        Selector("owner", "ownership", ("facets", "0", "owner")),
        Selector("form", "definition", ("definition",)),
    ))
    disclose(ledger, actor, "context", ROOM, (Selector("name", "name", ("label",)),))
    disclose(ledger, actor, "cue", CUE, (Selector("meaning", "definition", ("facets", "0")),))


def show_procedure(ledger, actor):
    disclose(ledger, actor, "procedure", REPAIR, (Selector("procedure", "definition", ("facets", "0")),))


def interpretation(world, key, actor, source_refs=(SAW,), *, meaning="Help entails control.", confidence=80, links=(), previous=None):
    exact = ref(key) if previous is None else ref(key, previous.revision + 1)
    attrs = (Attribute("cue", CUE), Attribute("context", ROOM), Attribute("meaning", meaning),
        Attribute("endorsement", ClaimStatus.ENDORSED.value), Attribute("confidence", confidence))
    attrs += tuple(Attribute("link." + str(i), r) for i, r in enumerate(links))
    value = ObjectVersion(exact, "u3.actor." + actor.key, key, (Role.INTERPRETATION,),
        (Account(SAW, (), Moment(5, 0), actor, source_refs),), previous=previous,
        occurrence=Occurrence.INTERPRETATION, attributes=attrs)
    if previous is None:
        world.create("interpret-" + key, value.writer, (value,), actor=actor)
    else:
        world.revise("interpret-" + key + "-" + str(exact.revision), value.writer, value, actor=actor)
    return exact


def bind(ledger, actor, key, *, addresses=(DetailAddress("tool", "owner"),), **kwargs):
    sources = tuple(dict.fromkeys(ledger.view(actor).detail(a).source for a in addresses))
    binding = interpretation(ledger.world, key, actor, sources, **kwargs)
    work = receipt(ledger.world, actor.key + "-bind-" + key + "-" + str(binding.revision),
        actor, "bind", key, (binding,) + sources)
    ledger.bind(actor, binding, addresses, work)
    return binding


def choose(view):
    """A declared pure policy probe; it proposes a request, never executes repair."""
    owners = view.lookup(key="owner", subject=SAW.identity)
    if not owners:
        return {"choice": "ask-for-owner", "reasons": []}
    owner = owners[-1]
    return {"choice": "request-use" if owner.value != view.snapshot.actor else "consider-own-tool",
            "owner": owner.value.key, "reasons": [owner.source.identity.key, owner.source.revision],
            "acquired_repair": view.can_use(REPAIR, ROOM)}
