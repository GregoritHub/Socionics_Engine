"""Declared material semantics and a paid-effect extension of the compact store.

Stock quantity is lifetime accounted stock, with an irreversible consumed sink.
No source, regeneration, free repair, mind, or arbitrary procedure is implied.
"""
from dataclasses import replace
from .compact import CompactStore
from .records import (Attribute, Definition, Material, Role, Lifecycle, Account,
                      Occurrence, Relation, ChangeKind)
from .store import next_version
from .operation_records import WRITER, LAW


def attrs(version):
    return {a.name: a.value for a in version.attributes}


def attributes(data):
    return tuple(Attribute(k, v) for k, v in sorted(data.items()))


def integer(data, key, low=0):
    value = data.get(key)
    if type(value) is not int or value < low:
        raise ValueError("invalid material integer: " + key)
    return value


def available(version):
    material = version.facet(Material)
    if material is None or material.condition != "stock":
        raise ValueError("consumable stock required")
    used = integer(attrs(version), "consumed")
    if used > material.quantity:
        raise ValueError("stock sink exceeds lifetime quantity")
    return material.quantity - used


def material_effect(before, job):
    """One exact supported change. Raises before any publication on infeasibility."""
    m, data = before.facet(Material), attrs(before)
    if m is None or before.lifecycle != Lifecycle.ACTIVE or before.writer != WRITER:
        raise ValueError("active U4 material required")
    actor, op = job["actor"], job["primitive"]
    if m.custodian != actor:
        raise ValueError("material custody unavailable")
    if before.ref == job.get("stock"):
        if m.owner != actor or op not in ("consume", "repair", "care"):
            raise ValueError("owned consumable required")
        if op != "consume" and data.get("purpose") != op:
            raise ValueError("incompatible consumable")
        amount = integer(job, "amount", 1)
        if available(before) < amount:
            raise ValueError("insufficient stock")
        data["consumed"] += amount
    elif before.ref in (job.get("target"), job.get("tool")):
        wear, maximum = integer(data, "wear"), integer(data, "max_wear", 1)
        if wear > maximum or m.condition not in ("serviceable", "damaged"):
            raise ValueError("invalid tool state")
        if before.ref == job.get("tool") or op == "use":
            if m.condition != "serviceable" or wear >= maximum:
                raise ValueError("tool cannot perform supported use")
            data["wear"] = wear + 1
            m = replace(m, condition="damaged" if data["wear"] == maximum else "serviceable")
        elif op == "repair":
            if m.condition != "damaged":
                raise ValueError("repair needs a damaged target")
            data["wear"] = 0
            m = replace(m, condition="serviceable")
        elif op == "care":
            if m.condition != "serviceable" or wear == 0:
                raise ValueError("care needs a worn serviceable target")
            data["wear"] = wear - 1
        elif op == "damage":
            if m.condition != "serviceable":
                raise ValueError("condition change needs a serviceable target")
            data["wear"] = maximum
            m = replace(m, condition="damaged")
        elif op == "transfer":
            if m.owner != actor or job["recipient"] == actor:
                raise ValueError("ownership transfer unavailable")
            m = replace(m, owner=job["recipient"], custodian=job["recipient"])
        elif op == "return":
            if m.owner == actor:
                raise ValueError("borrowed material required")
            m = replace(m, custodian=m.owner)
        else:
            raise ValueError("unsupported physical affordance")
    else:
        raise ValueError("material is outside operation inputs")
    return next_version(before, facets=tuple(m if type(f) is Material else f for f in before.facets),
                        attributes=attributes(data))


def return_effect(relation, target, actor):
    r = relation.facet(Relation)
    m = target.facet(Material)
    if r is None or r.predicate != "return_due" or Role.COMMITMENT not in relation.roles:
        raise ValueError("return needs an addressable return obligation")
    ends = {e.role: e.target.identity for e in r.endpoints}
    if ends != {"borrower": actor, "owner": m.owner, "item": target.ref.identity}:
        raise ValueError("return obligation does not match physical participants")
    terms = {a.name: a.value for a in r.terms}
    if terms.get("status") != "open":
        raise ValueError("return obligation is not open")
    terms["status"] = "fulfilled"
    changed = replace(r, endpoints=tuple(replace(e, target=target.ref) if e.role == "item" else e for e in r.endpoints),
                      terms=attributes(terms))
    return next_version(relation, facets=tuple(changed if type(f) is Relation else f for f in relation.facets))


class OperationStore(CompactStore):
    SCHEMA = "hle-unified-operation-store-v1"

    def _validate_material_change(self, tx, edge, before, after, pending):
        if tx.writer != WRITER or edge.rule is None or not edge.evidence:
            raise ValueError("material effect needs a paid native operation and law")
        law = self.resolve(edge.rule).facet(Definition)
        if law is None or dict((a.name, a.value) for a in law.constraints).get("law") != LAW:
            raise ValueError("unsupported material world contract")
        old_job = self.resolve(edge.evidence[0])
        data = attrs(old_job)
        if (old_job.writer != WRITER or data.get("record_type") != "operation"
                or data.get("status") != "ready" or data.get("completed") != data.get("required")
                or data.get("spent") != data.get("required") or tx.actor != data.get("actor")):
            raise ValueError("completed actor-owned paid work required")
        new_job = pending.get(next_version(old_job).ref)
        if new_job is None or attrs(new_job).get("status") != "succeeded":
            raise ValueError("material effect must commit with its operation result")
        if after != material_effect(before, data):
            raise ValueError("material output differs from registered affordance")
        # The effect and all other resources must be in this same atomic batch.
        for key in ("target", "tool", "stock"):
            ref = data.get(key)
            if ref is not None:
                expected = material_effect(self.resolve(ref), data)
                if pending.get(expected.ref) != expected:
                    raise ValueError("material operation omitted or changed a required effect")
        if data["primitive"] == "return":
            target = pending[next_version(self.resolve(data["target"])).ref]
            expected = return_effect(self.resolve(data["relation"]), target, tx.actor)
            if pending.get(expected.ref) != expected:
                raise ValueError("physical return must discharge its exact obligation")
        events = [v for v in tx.versions if v.occurrence == Occurrence.ACTUAL_EVENT]
        if len(events) != 1 or old_job.ref not in events[0].facet(Account).sources:
            raise ValueError("effect requires one causally linked actual event")
