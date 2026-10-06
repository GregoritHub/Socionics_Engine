"""One authoritative native writer per identity and an atomic immutable journal.

This is a simulator/service boundary, not an authorization sandbox for hostile
Python. Native material commands are structural bookkeeping, not paid U4 work.
Legacy compatibility views are never accepted as independently writable state.
"""
from dataclasses import fields, is_dataclass, replace
from threading import RLock

from . import codec
from .records import (ObjectId, ObjectRef, ObjectVersion, Definition, Material,
    Composition, Relation, Proposition, LegacyPayload, Occurrence, Role, Lifecycle, ChangeKind, Lineage,
    Transaction, Checkpoint, Moment)

CONSERVATION_LAW = "u2.conserve-owned-quanta-v1"


def references(value):
    """Finite leaf references, never follow a referent while traversing a record."""
    if type(value) in (ObjectId, ObjectRef):
        yield value
    elif type(value) is tuple:
        for item in value:
            yield from references(item)
    elif is_dataclass(value):
        for field in fields(value):
            yield from references(getattr(value, field.name))


def contextual_records(value):
    if type(value) in (Relation, Proposition):
        yield value
    if type(value) is tuple:
        for item in value:
            yield from contextual_records(item)
    elif is_dataclass(value):
        for field in fields(value):
            yield from contextual_records(getattr(value, field.name))


def next_version(old, **changes):
    if {"ref", "previous", "writer"}.intersection(changes):
        raise ValueError("identity, writer and predecessor follow the existing revision")
    return replace(old, ref=ObjectRef(old.ref.identity, old.ref.revision + 1), previous=old.ref, **changes)


class ObjectStore:
    def __init__(self):
        self._versions = {}
        self._heads = {}
        self._journal = []
        self._keys = {}
        self._lock = RLock()

    def resolve(self, ref):
        if type(ref) is not ObjectRef:
            raise ValueError("exact revision required")
        with self._lock:
            return self._versions[ref]

    def head(self, identity):
        """Explicit current-state lookup; historical resolution never calls this."""
        if type(identity) is not ObjectId:
            raise ValueError("ObjectId required")
        with self._lock:
            return self.resolve(self._heads[identity])

    def journal(self):
        with self._lock:
            return tuple(self._journal)

    def actual_events(self):
        with self._lock:
            return tuple(v for v in self._versions.values() if v.occurrence == Occurrence.ACTUAL_EVENT)

    def create(self, key, writer, versions, *, actor=None, evidence=(), reason="declared creation"):
        edge = Lineage(ChangeKind.CREATE, (), tuple(v.ref for v in versions), evidence, reason)
        return self.commit(key, writer, versions, (edge,), actor=actor)

    def revise(self, key, writer, version, *, actor=None, evidence=(), reason="explicit revision"):
        old = self.resolve(version.previous)
        kind = ChangeKind.REVISE
        if old.definition != version.definition or old.facet(Definition) != version.facet(Definition):
            kind = ChangeKind.DEFINITION
        elif old.facet(Composition) != version.facet(Composition):
            kind = ChangeKind.MEMBERSHIP
        edge = Lineage(kind, (old.ref,), (version.ref,), evidence, reason)
        return self.commit(key, writer, (version,), (edge,), actor=actor)

    def transfer(self, key, writer, expected, recipient, *, actor, evidence=()):
        old = self.resolve(expected)
        material = old.facet(Material)
        if material is None:
            raise ValueError("not a material object")
        updated = replace(material, owner=recipient, custodian=recipient)
        new = next_version(old, facets=tuple(updated if type(f) is Material else f for f in old.facets))
        edge = Lineage(ChangeKind.TRANSFER, (old.ref,), (new.ref,), evidence, "ownership and custody transfer")
        return self.commit(key, writer, (new,), (edge,), actor=actor)

    def restructure(self, key, writer, inputs, outputs, *, actor, rule, reason, evidence=()):
        if len(inputs) == 1 and len(outputs) > 1:
            kind = ChangeKind.DIVIDE
        elif len(inputs) > 1 and len(outputs) == 1:
            kind = ChangeKind.COMBINE
        elif len(inputs) == 1 and len(outputs) == 1:
            kind = ChangeKind.REPLACE
        else:
            raise ValueError("declare one split, merge or replacement per structural operation")
        retired = tuple(next_version(self.resolve(ref), lifecycle=Lifecycle.RETIRED) for ref in inputs)
        edge = Lineage(kind, inputs, tuple(v.ref for v in outputs), evidence, reason, rule)
        return self.commit(key, writer, retired + outputs, (edge,), actor=actor)

    def commit(self, key, writer, versions, lineage, *, actor=None):
        with self._lock:
            prior = self._keys.get(key)
            if prior is not None:
                retry = Transaction(key, prior.at, writer, actor, versions, lineage)
                if retry != prior:
                    raise ValueError("transaction key reused with different content")
                return prior
            tx = Transaction(key, Moment(len(self._journal), 0), writer, actor, versions, lineage)
            self._validate(tx)
            # No changes are published until the complete transaction validates.
            for version in tx.versions:
                self._versions[version.ref] = version
                self._heads[version.ref.identity] = version.ref
            self._journal.append(tx)
            self._keys[key] = tx
            return tx

    def _validate(self, tx):
        pending = {v.ref: v for v in tx.versions}
        ids = {v.ref.identity for v in tx.versions}
        if len(pending) != len(tx.versions) or len(ids) != len(tx.versions):
            raise ValueError("one write per identity per transaction")
        known_ids = set(self._heads) | ids

        def resolve(ref):
            if ref in pending:
                return pending[ref]
            return self.resolve(ref)

        for v in tx.versions:
            if v.writer != tx.writer or v.facet(LegacyPayload) is not None or v.ref.identity.namespace.startswith("legacy."):
                raise ValueError("wrong authoritative writer or read-only legacy view")
            old_ref = self._heads.get(v.ref.identity)
            if v.previous != old_ref or v.ref in self._versions:
                raise ValueError("stale, skipped or duplicate revision")
            if old_ref is None:
                if v.ref.revision != 1 or v.lifecycle != Lifecycle.ACTIVE:
                    raise ValueError("creation requires active first revision")
            else:
                old = self.resolve(old_ref)
                if old.writer != v.writer:
                    raise ValueError("identity already belongs to another writer")
                if old.lifecycle == Lifecycle.RETIRED or old.occurrence == Occurrence.ACTUAL_EVENT:
                    raise ValueError("retired state and actual event history cannot be rewritten")
                if old.occurrence != v.occurrence:
                    raise ValueError("occurrence category cannot be promoted by revision")
                if (old.facet(Material) is None) != (v.facet(Material) is None):
                    raise ValueError("material capability cannot appear or disappear through revision")
            for ref in references(v):
                if type(ref) is ObjectRef and ref not in self._versions and ref not in pending:
                    raise ValueError(f"unresolved exact revision: {ref}")
                if type(ref) is ObjectId and ref not in known_ids:
                    raise ValueError(f"unknown instance: {ref}")
            if v.definition is not None and resolve(v.definition).facet(Definition) is None:
                raise ValueError("definition binding must address a definition revision")
            for contextual in contextual_records(v.facets):
                if Role.CONTEXT not in resolve(contextual.context).roles:
                    raise ValueError("relation or proposition context requires the context role")
            material = v.facet(Material)
            if material and resolve(material.unit).facet(Definition) is None:
                raise ValueError("material unit must be a versioned definition")
        if tx.actor is not None and tx.actor not in known_ids:
            raise ValueError("unknown acting instance")

        covered = set()
        for edge in tx.lineage:
            for ref in edge.evidence + (() if edge.rule is None else (edge.rule,)):
                if ref not in self._versions:
                    raise ValueError("causal basis and law must exist before this transaction")
            if any(ref not in pending for ref in edge.outputs):
                raise ValueError("lineage output not written in this transaction")
            if any(ref not in self._versions or self._heads[ref.identity] != ref for ref in edge.inputs):
                raise ValueError("lineage input must pin current state")
            owned = set(edge.outputs)
            if edge.kind == ChangeKind.CREATE:
                if edge.inputs or any(pending[ref].previous is not None for ref in edge.outputs):
                    raise ValueError("creation cannot overwrite an instance")
            elif edge.kind in (ChangeKind.DIVIDE, ChangeKind.COMBINE, ChangeKind.REPLACE):
                owned.update(self._validate_material_transform(tx, edge, pending))
            else:
                if len(edge.inputs) != 1 or len(edge.outputs) != 1:
                    raise ValueError("revision lineage is one-to-one")
                before, after = self.resolve(edge.inputs[0]), pending[edge.outputs[0]]
                if after.previous != before.ref or after.lifecycle != before.lifecycle:
                    raise ValueError("revision cannot replace or retire an identity")
                definition_changed = before.definition != after.definition or before.facet(Definition) != after.facet(Definition)
                membership_changed = before.facet(Composition) != after.facet(Composition)
                if definition_changed != (edge.kind == ChangeKind.DEFINITION):
                    raise ValueError("changed definitions require explicit definition lineage")
                if membership_changed and edge.kind != ChangeKind.MEMBERSHIP:
                    raise ValueError("changed composition requires membership lineage")
                if edge.kind == ChangeKind.MEMBERSHIP and not membership_changed:
                    raise ValueError("membership lineage requires changed composition")
                bm, am = before.facet(Material), after.facet(Material)
                if edge.kind == ChangeKind.TRANSFER:
                    if bm is None or tx.actor != bm.owner or tx.actor != bm.custodian:
                        raise ValueError("actor must own and hold the transferred material")
                    if am.owner != am.custodian or am.owner == bm.owner or replace(am, owner=bm.owner, custodian=bm.custodian) != bm:
                        raise ValueError("transfer changes only ownership and custody")
                    if replace(after, ref=before.ref, previous=before.previous, facets=before.facets) != before:
                        raise ValueError("transfer cannot hide other object changes")
                elif edge.kind == ChangeKind.MATERIAL:
                    self._validate_material_change(tx, edge, before, after, pending)
                elif bm != am:
                    raise ValueError("material state change requires a supported material operation")
            if covered.intersection(owned):
                raise ValueError("a write cannot have conflicting lineage")
            covered.update(owned)
        if covered != set(pending):
            raise ValueError("every version must have explicit lineage")

    def _validate_material_change(self, tx, edge, before, after, pending):
        # U2 and U3 retain their original, deliberately restricted material laws.
        raise ValueError("paid material effects require the U4 operation store")

    def _validate_material_transform(self, tx, edge, pending):
        sizes = (len(edge.inputs), len(edge.outputs))
        valid = {ChangeKind.DIVIDE: sizes[0] == 1 and sizes[1] > 1,
                 ChangeKind.COMBINE: sizes[0] > 1 and sizes[1] == 1,
                 ChangeKind.REPLACE: sizes == (1, 1)}
        if not valid[edge.kind] or edge.rule is None:
            raise ValueError("wrong material transformation shape or missing law")
        definition = self.resolve(edge.rule).facet(Definition)
        if definition is None or not any(p.name == "law" and p.value == CONSERVATION_LAW for p in definition.constraints):
            raise ValueError("unsupported conservation law")
        sources = [self.resolve(ref) for ref in edge.inputs]
        targets = [pending[ref] for ref in edge.outputs]
        if any(v.facet(Material) is None or v.lifecycle != Lifecycle.ACTIVE for v in sources + targets):
            raise ValueError("material transformation requires active material")
        if any(v.previous is not None for v in targets):
            raise ValueError("transformation outputs require fresh identities")
        materials = [v.facet(Material) for v in sources + targets]
        first = materials[0]
        if tx.actor != first.owner or tx.actor != first.custodian:
            raise ValueError("actor must own and hold the consumed material")
        if any((m.owner, m.custodian, m.unit, m.condition) != (first.owner, first.custodian, first.unit, first.condition) for m in materials):
            raise ValueError("cannot mix ownership, custody, units or material condition")
        if sum(v.facet(Material).quantity for v in sources) != sum(v.facet(Material).quantity for v in targets):
            raise ValueError("resource conservation failed")
        retired_refs = set()
        for v in sources:
            expected = next_version(v, lifecycle=Lifecycle.RETIRED)
            if pending.get(expected.ref) != expected:
                raise ValueError("source must be retired exactly once in the same transaction")
            retired_refs.add(expected.ref)
        return retired_refs

    def checkpoint(self):
        with self._lock:
            return codec.dumps(Checkpoint("hle-unified-object-store-v1", tuple(self._journal)))

    @classmethod
    def restore(cls, text):
        cp = codec.loads(text)
        if type(cp) is not Checkpoint or cp.schema != "hle-unified-object-store-v1":
            raise ValueError("unsupported native checkpoint")
        store = cls()
        for tx in cp.journal:
            if tx.key in store._keys or tx.at != Moment(len(store._journal), 0):
                raise ValueError("repeated transaction or wrong journal order")
            if store.commit(tx.key, tx.writer, tx.versions, tx.lineage, actor=tx.actor) != tx:
                raise ValueError("journal replay mismatch")
        return store
