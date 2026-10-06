"""Lossless structural adapters and read-only views of authoritative R21B state.

All allowlisted legacy record families are encoded field by field, including
inherited fields. Semantics are added only for named families below; unknown
families keep the generic record role. No mutable mirror or second writer exists.
"""
from dataclasses import fields, is_dataclass
from enum import Enum
import json

from hle import codec as legacy_codec
from hle.contracts import Ref, Kind, WorldEvent, Observation, MemoryRevision, Proposition
from hle.world import World
from hle.world_records import Entity, Transaction as WorldTransaction
from hle.concept_records import ConceptState
from hle.language_records import Interpretation
from hle.organization_records import Terms
from .records import (ObjectId, ObjectRef, ObjectVersion, Role, Occurrence,
    LegacyEnum, LegacyTuple, LegacyField, LegacyRecord, LegacyPayload, Attribute)

_REF_PREFIX = "legacy.ref."


def adapt_ref(ref):
    if type(ref) is not Ref:
        raise ValueError("legacy Ref required")
    return ObjectRef(ObjectId(_REF_PREFIX + ref.kind.value, ref.key), ref.revision)


def recover_ref(ref):
    if type(ref) is not ObjectRef or not ref.identity.namespace.startswith(_REF_PREFIX):
        raise ValueError("not a legacy reference namespace")
    return Ref(Kind(ref.identity.namespace[len(_REF_PREFIX):]), ref.identity.key, ref.revision)


def adapt(value):
    if type(value) is Ref:
        return adapt_ref(value)
    if isinstance(value, Enum) and type(value) in legacy_codec._ENUM_TAGS:
        return LegacyEnum(legacy_codec._ENUM_TAGS[type(value)], value.value)
    if is_dataclass(value) and type(value) in legacy_codec._RECORD_TAGS:
        return LegacyRecord(legacy_codec._RECORD_TAGS[type(value)],
                            tuple(LegacyField(f.name, adapt(getattr(value, f.name))) for f in fields(value)))
    if type(value) is tuple:
        return LegacyTuple(tuple(adapt(v) for v in value))
    if value is None or type(value) in (str, int, bool):
        return value
    raise ValueError("unsupported legacy value")


def recover(value):
    if type(value) is ObjectRef:
        return recover_ref(value)
    if type(value) is LegacyEnum:
        cls = legacy_codec.ENUMS.get(value.tag)
        if cls is None or not any(type(member.value) is type(value.value) and member.value == value.value for member in cls):
            raise ValueError("unknown or malformed legacy enum")
        return cls(value.value)
    if type(value) is LegacyTuple:
        return tuple(recover(v) for v in value.items)
    if type(value) is LegacyRecord:
        cls = legacy_codec.RECORDS.get(value.tag)
        if cls is None or not is_dataclass(cls) or {f.name for f in value.fields} != {f.name for f in fields(cls)}:
            raise ValueError("unknown legacy record or changed field set")
        return cls(**{f.name: recover(f.value) for f in value.fields})
    if value is None or type(value) in (str, int, bool):
        return value
    raise ValueError("unsupported adapted legacy value")


def _roles(value):
    if type(value) is Entity:
        return (Role.PERSON if value.role == "actor" else Role.MATERIAL,), None
    if type(value) is WorldEvent:
        return (Role.EVENT,), Occurrence.ACTUAL_EVENT
    if type(value) is Observation:
        return (Role.OBSERVATION,), Occurrence.OBSERVATION
    if type(value) is MemoryRevision:
        return (Role.CLAIM,), Occurrence.REMEMBERED_CLAIM
    if type(value) is ConceptState:
        return (Role.CONCEPT, Role.INTERPRETATION), Occurrence.INTERPRETATION
    if type(value) is Interpretation:
        return (Role.INTERPRETATION,), Occurrence.INTERPRETATION
    if type(value) is Terms:
        return (Role.COLLECTIVE, Role.COMMITMENT), None
    if type(value) is Proposition:
        return (Role.RELATION,), None
    return (Role.RECORD,), None


def object_view(value, *, address=None):
    """Offline compatibility view; nested legacy data remains exact and typed.

Records without their own Ref require an explicit caller-scoped address. Equal
values never become identity. Previous is a structural revision coordinate;
the original record's causal fields are preserved verbatim in LegacyPayload.
"""
    original = getattr(value, "ref", None)
    if type(original) is Ref:
        expected = adapt_ref(original)
        if address is not None and address != expected:
            raise ValueError("adapter cannot rename a legacy identity")
        address = expected
    if type(address) is not ObjectRef or not address.identity.namespace.startswith("legacy."):
        raise ValueError("unaddressed legacy record needs an explicit legacy namespace address")
    roles, occurrence = _roles(value)
    previous = None if address.revision == 1 else ObjectRef(address.identity, address.revision - 1)
    return ObjectVersion(address, "legacy.r21b", type(value).__name__, roles,
                         (LegacyPayload(adapt(value)),), previous=previous, occurrence=occurrence)


def recover_object(view):
    if type(view) is not ObjectVersion or view.writer != "legacy.r21b" or view.facet(LegacyPayload) is None:
        raise ValueError("legacy compatibility object required")
    result = recover(view.facet(LegacyPayload).value)
    original = getattr(result, "ref", None)
    if type(original) is Ref and adapt_ref(original) != view.ref:
        raise ValueError("legacy identity disagrees with payload")
    roles, occurrence = _roles(result)
    if view.roles != roles or view.occurrence != occurrence:
        raise ValueError("legacy semantic projection disagrees with payload")
    return result


def checkpoint_object(text, key):
    value = legacy_codec.loads(text)
    if not type(value).__name__.endswith("Checkpoint"):
        raise ValueError("legacy checkpoint record required")
    return object_view(value, address=ObjectRef(ObjectId("legacy.checkpoint", key), 1))


def checkpoint_text(view):
    value = recover_object(view)
    if not type(value).__name__.endswith("Checkpoint"):
        raise ValueError("legacy checkpoint record required")
    return legacy_codec.dumps(value)


class LegacyWorldBridge:
    """The owned legacy World is the only writer; common views are detached.

participant_input adapts only the legacy participant view. inspect_object and
ownership_history are explicitly offline inspector APIs, never actor inputs.
The constructor takes a configuration, not a shared externally mutable World.
"""
    def __init__(self, config):
        self.__world = World(config)

    def execute(self, command):
        return object_view(self.__world.execute(command))

    def execute_adapted(self, command):
        return self.execute(recover(command))

    def participant_input(self, actor, after=0):
        view, cursor = self.__world.participant_input(recover_ref(actor), after)
        return adapt(view), cursor

    def inspect_object(self, ref):
        return object_view(self.__world.truth.resolve(recover_ref(ref)))

    def transaction(self, index):
        tx = self.__world.truth.journal()[index]
        address = ObjectRef(ObjectId("legacy.transaction", tx.event.ref.key), 1)
        return object_view(tx, address=address)

    def ownership_history(self, item):
        """Address each actual ownership revision without altering descriptor IDs."""
        item = recover_ref(item)
        revisions = []
        context = self.__world.config.context
        identity = ObjectId("legacy.relation.ownership", json.dumps(
            [item.kind.value, item.key, item.revision, context.kind.value, context.key, context.revision], separators=(",", ":")))
        for tx in self.__world.truth.journal():
            for change in tx.event.changes:
                fact = change.after
                if fact is not None and fact.subject == item and fact.relation == "owned_by" and fact.context == context:
                    ref = ObjectRef(identity, len(revisions) + 1)
                    revisions.append(ObjectVersion(ref, "legacy.r21b", "owned_by", (Role.RELATION,),
                        (LegacyPayload(adapt(fact)),), previous=None if not revisions else revisions[-1].ref,
                        attributes=(Attribute("source_event", adapt_ref(tx.event.ref)),)))
        return tuple(revisions)

    def checkpoint(self):
        return checkpoint_object(self.__world.checkpoint(), "world")

    def legacy_checkpoint(self):
        return self.__world.checkpoint()

    @classmethod
    def restore(cls, view):
        instance = cls.__new__(cls)
        instance.__world = World.restore(checkpoint_text(view))
        return instance
