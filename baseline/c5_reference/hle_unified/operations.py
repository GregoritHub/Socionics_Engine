"""Common paid, resumable operation service over native object revisions.

The service is a trusted simulator boundary. Give policies participant_view(),
never the service, job_status(), material store, or audit. All normal commands
use affected records and indexes; complete history replay occurs only on restore.
"""
from copy import copy
from dataclasses import fields
from hashlib import sha256
from . import codec
from .compact import ValuePool, DependencyCache, seal, unseal
from .records import (ObjectId, ObjectRef, ObjectVersion, Attribute, Role, Material,
    Definition, Procedure, Account, Occurrence, Moment, TimeScope, Proposition,
    Lineage, ChangeKind, Lifecycle)
from .store import next_version, references
from .particulars import AccessLedger, Grant, Selector
from .material import OperationStore, attrs, attributes, material_effect, return_effect, available
from .operation_records import (OperationRequest, WRITER, LAW, EXTENTS,
                                MATERIAL_OPS, SIGNATURES, registry)


def address(namespace, *parts):
    values = [codec.encode(p) for p in parts]
    return ObjectRef(ObjectId(namespace, sha256(codec.canonical(values).encode()).hexdigest()), 1)


def job_address(actor, key):
    return address("u4.operation", actor, key)


def wallet_address(actor):
    return address("u4.wallet", actor)


def record(ref, label, data):
    return ObjectVersion(ref, WRITER, label, (Role.RECORD,), attributes=attributes(data))


def indexed(data, prefix):
    return tuple(data[prefix + str(i)] for i in range(sum(k.startswith(prefix) for k in data)))


class NativeAccess(AccessLedger):
    SCHEMA = "hle-unified-u4-access-v1"
    STORE = OperationStore
    RECEIPT_WRITERS = (WRITER,)

    def preview(self, command, added):
        """Validate a pending receipt without publishing actor-visible changes."""
        class Overlay:
            def __init__(self, world):
                self.world, self.cache = world, DependencyCache()
            def resolve(self, ref):
                return added[ref] if ref in added else self.world.resolve(ref)
        draft = copy(self)
        draft.world = Overlay(self.world)
        draft.pool = ValuePool(registry())
        draft._events = []
        draft._cache_namespace = object()
        draft._states = dict(self._states)
        actor = command[1]
        if actor in self._states:
            state = self._states[actor]
            cloned = copy(state)
            for name, value in vars(state).items():
                setattr(cloned, name, copy(value))
            draft._states[actor] = cloned
        return draft._execute(command)


class OperationEngine:
    SCHEMA = "hle-unified-u4-engine-v1"

    def __init__(self, world, law):
        if type(world) is not OperationStore:
            raise ValueError("U4 native store required")
        definition = world.resolve(law).facet(Definition)
        if definition is None or {a.name: a.value for a in definition.constraints}.get("law") != LAW:
            raise ValueError("explicit finite workshop contract required")
        self.world, self.law = world, law
        self.access = NativeAccess(world)
        self._initial = world.checkpoint()
        self._jobs, self._locks, self._commands = {}, {}, {}
        self._events, self._pool = [], ValuePool(registry())
        self._lock = world._lock
        self._wallets = {}
        for identity in world._heads:
            version = world.head(identity)
            if identity.namespace == "u4.wallet":
                d = attrs(version)
                actor = d.get("actor")
                if (d.get("record_type") != "wallet" or version.ref != wallet_address(actor)
                        or set(d) != {"record_type", "actor", "energy", "time", "initial_energy", "initial_time"}
                        or any(type(d[k]) is not int or d[k] < 0 for k in ("energy", "time", "initial_energy", "initial_time"))
                        or d["energy"] != d["initial_energy"] or d["time"] != d["initial_time"]):
                    raise ValueError("invalid finite initial work wallet")
                self._wallets[actor] = version.ref

    def participant_view(self, actor, *, through=None):
        with self._lock:
            return self.access.view(actor, through=through)

    def job_status(self, actor, key):
        """Simulator inspection only; not a participant access surface."""
        return attrs(self.world.resolve(self._jobs[(actor, key)]))

    def wallet(self, actor):
        return attrs(self.world.resolve(self._wallets[actor]))

    def start(self, command_id, request):
        return self._execute(("start", command_id, request))

    def advance(self, command_id, actor, key, work_limit):
        return self._execute(("advance", command_id, actor, key, work_limit))

    def commit(self, command_id, actor, key):
        return self._execute(("commit", command_id, actor, key))

    def cancel(self, command_id, actor, key):
        return self._execute(("cancel", command_id, actor, key))

    def disclose(self, command_id, actor, source, selectors, subject=None):
        """Simulator-authorized exact disclosure; reading still requires paid work."""
        return self._execute(("disclose", command_id, actor, source, selectors, source if subject is None else subject))

    def deliver_event(self, command_id, event, actor):
        return self._execute(("deliver_event", command_id, event, actor))

    def declare(self, command_id, versions):
        """Harness/actor-draft import. No material, wallets, jobs, or new energy."""
        return self._execute(("declare", command_id, versions))

    def _execute(self, command):
        with self._lock:
            if type(command) is not tuple or len(command) < 2 or type(command[1]) is not str or not command[1].strip():
                raise ValueError("command identity required")
            command_id = command[1]
            if command_id in self._commands:
                prior, result = self._commands[command_id]
                if prior != command:
                    raise ValueError("command identity reused with different content")
                return result
            # The typed registry validates the entire input before mutation.
            ValuePool(registry()).put(command)
            dispatch = {"start": self._start, "advance": self._advance, "commit": self._commit,
                        "cancel": self._cancel, "disclose": self._disclose,
                        "deliver_event": self._deliver_event, "declare": self._declare}
            if command[0] not in dispatch:
                raise ValueError("unsupported native operation command")
            result = dispatch[command[0]](*command[1:])
            self._commands[command_id] = (command, result)
            self._events.append(self._pool.put((command, result)))
            return result

    def _now(self):
        return Moment(len(self.world._journal), 0)

    def _batch(self, cid, actor, versions, *, evidence=(), material=()):
        edges = []
        for value in versions:
            if value.previous is None:
                kind, inputs = ChangeKind.CREATE, ()
            else:
                kind, inputs = ChangeKind.REVISE, (value.previous,)
                old = self.world.resolve(value.previous)
                if old.definition != value.definition or old.facet(Definition) != value.facet(Definition):
                    kind = ChangeKind.DEFINITION
            if value.ref in material:
                kind = ChangeKind.MATERIAL
            edges.append(Lineage(kind, inputs, (value.ref,), evidence, "U4 common operation lifecycle",
                                 self.law if kind == ChangeKind.MATERIAL else None))
        return self.world.commit("u4:" + cid, WRITER, tuple(versions), tuple(edges), actor=actor)

    def _procedure(self, request, view):
        rows = [p for p in view.resolve(request.procedure) if type(p.value) is Procedure]
        if len(rows) != 1:
            raise ValueError("processed exact procedure definition required")
        p = rows[0].value
        matches = [name for name in SIGNATURES if p.executor == "u4." + name + ".v1"]
        if len(matches) != 1 or p.inputs != SIGNATURES[matches[0]] or p.steps or p.preconditions or p.effects:
            raise ValueError("procedure has no supported physical executor/structure")
        return matches[0]

    def _compile(self, r):
        if type(r) is not OperationRequest or r.actor not in self._wallets:
            raise ValueError("known funded actor and exact operation request required")
        if (r.actor, r.key) in self._jobs:
            raise ValueError("operation identity already used")
        if Role.CONTEXT not in self.world.resolve(r.context).roles:
            raise ValueError("context required")
        view = self.access.view(r.actor)
        evidence = tuple(view.detail(a) for a in r.evidence)
        if any(p is None for p in evidence):
            raise ValueError("operation evidence must already be processed by its actor")
        primitive = self._procedure(r, view) if r.kind in ("procedure", "acquire") else r.kind
        if r.kind == "procedure" and not view.can_use(r.procedure, r.context):
            raise ValueError("named procedure needs this actor's acquired use")
        if r.kind == "acquire":
            primitive = "acquire"
        participants = tuple(dict.fromkeys((r.actor,) + r.participants))
        for actor in participants:
            if Role.PERSON not in self.world.resolve(ObjectRef(actor, 1)).roles:
                raise ValueError("known participant required")
        refs = tuple(p for name in ("target", "tool", "stock", "relation", "procedure", "binding", "practice")
                     if (p := getattr(r, name)) is not None)
        if len({p.identity for p in refs}) != len(refs):
            raise ValueError("operation input roles require distinct identities")
        known = self.access._known_refs(r.actor)
        if r.kind != "read" and r.context not in known:
            raise ValueError("processed context required")
        if r.kind in MATERIAL_OPS and r.procedure is not None:
            raise ValueError("invoke a named procedure through the procedure operation")
        if r.kind != "consume" and r.amount != 1:
            raise ValueError("this operation has a fixed extent")
        deps, locks, inputs = [], [], list(refs)
        if primitive in MATERIAL_OPS:
            required = set(SIGNATURES[primitive])
            present = {n for n in ("target", "tool", "stock", "recipient", "relation") if getattr(r, n) is not None}
            if present != required or not evidence or any((r.delivery, r.binding, r.practice)):
                raise ValueError("operation payload does not match the registered affordance")
            if primitive != "consume" and r.amount != 1:
                raise ValueError("workshop care/repair/interaction has a fixed material extent")
            if r.recipient is not None and r.recipient not in participants:
                raise ValueError("transfer recipient must be an explicit participant")
            for name in ("target", "tool", "stock", "relation"):
                ref = getattr(r, name)
                if ref is None:
                    continue
                if ref not in known:
                    raise ValueError("operation input identity/revision is not accessible")
                value = self.world.resolve(ref)
                if name != "relation":
                    if value.facet(Material) is None:
                        raise ValueError("material input role required")
                    # Inspection names an accessible identity and samples current
                    # physical state only at commit, then discloses via observation.
                    if primitive != "inspect":
                        locks.append(ref.identity)
                        deps.extend((ref, value.facet(Material).unit))
                        if value.definition is not None:
                            deps.append(value.definition)
                else:
                    deps.append(ref)
            if r.procedure is not None:
                deps.append(r.procedure)
            deps.append(r.context)
        elif r.kind == "read":
            pending = self.access._state(r.actor).deliveries.get(r.delivery)
            if (pending is None or r.delivery in self.access._state(r.actor).processed
                    or refs or r.recipient is not None or r.evidence):
                raise ValueError("read needs only a pending actor delivery")
            inputs.append(pending.source)
        elif r.kind == "bind":
            if (r.binding is None or set(refs) != {r.binding} or not evidence
                    or r.delivery or r.recipient is not None):
                raise ValueError("bind needs an actor draft and processed evidence")
            value = self.world.resolve(r.binding)
            account = value.facet(Account)
            if value.occurrence != Occurrence.INTERPRETATION or account is None or account.holder != r.actor:
                raise ValueError("actor-owned interpretation draft required")
            deps.append(r.binding)
        elif r.kind == "acquire":
            if (r.procedure is None or r.practice is None or set(refs) != {r.procedure, r.practice}
                    or r.delivery or r.recipient is not None):
                raise ValueError("acquisition needs procedure and executed practice")
            if r.practice not in known:
                raise ValueError("practice outcome must have been delivered and processed")
            practiced = self.world.resolve(r.practice)
            pd = attrs(practiced)
            supported = self._procedure(r, view)
            if (practiced.occurrence != Occurrence.ACTUAL_EVENT or pd.get("outcome") != "succeeded"
                    or pd.get("actor") != r.actor or pd.get("primitive") != supported
                    or pd.get("context") != r.context):
                raise ValueError("acquisition requires matching successful actor-owned practice")
            deps.append(r.procedure)
        else:
            raise ValueError("unsupported processing request")
        deps = tuple(dict.fromkeys((*deps, self.law)))
        inputs = tuple(dict.fromkeys((*inputs, *(p.source for p in evidence), r.context)))
        data = {f.name: getattr(r, f.name) for f in fields(r)
                if f.name not in ("participants", "evidence")}
        data.update(record_type="operation", primitive=primitive, required=1 + EXTENTS[primitive],
                    completed=0, spent=0, status="pending", failure=None, result=None,
                    route_prepare=1, route_execute=EXTENTS[primitive], started_tick=self._now().tick)
        for prefix, values in (("participant.", participants), ("input.", inputs), ("dependency.", deps), ("lock.", tuple(locks))):
            data.update({prefix + str(i): value for i, value in enumerate(values)})
        for i, item in enumerate(r.evidence):
            data["evidence.delivery." + str(i)], data["evidence.key." + str(i)] = item.delivery, item.key
        return data

    def _can_reserve(self, data, ref):
        return all(self._locks.get(identity) in (None, ref.identity) for identity in indexed(data, "lock."))

    def _reserve(self, data, ref):
        for identity in indexed(data, "lock."):
            self._locks[identity] = ref.identity

    def _release(self, data, ref):
        for identity in indexed(data, "lock."):
            if self._locks.get(identity) == ref.identity:
                del self._locks[identity]

    def _start(self, cid, request):
        data = self._compile(request)
        ref = job_address(request.actor, request.key)
        data["status"] = "pending" if self._can_reserve(data, ref) else "waiting"
        value = record(ref, "Paid operation: " + request.kind, data)
        self._batch(cid, request.actor, (value,), evidence=indexed(data, "input."))
        self._jobs[(request.actor, request.key)] = ref
        if data["status"] == "pending":
            self._reserve(data, ref)
        return ref

    def _active(self, actor, key):
        old = self.world.resolve(self._jobs[(actor, key)])
        if attrs(old)["status"] in ("succeeded", "failed", "cancelled"):
            raise ValueError("terminal operation cannot continue")
        return old, attrs(old)

    def _advance(self, cid, actor, key, work_limit):
        if type(work_limit) is not int or work_limit < 1:
            raise ValueError("positive integer work limit required")
        old, data = self._active(actor, key)
        if data["status"] == "ready":
            raise ValueError("completed work awaits effect commit")
        before = self.world.resolve(self._wallets[actor])
        wallet = attrs(before)
        reserve = self._can_reserve(data, old.ref)
        paid = min(work_limit, data["required"] - data["completed"], wallet["energy"], wallet["time"]) if reserve else 0
        data["completed"] += paid
        data["spent"] += paid
        data["status"] = "waiting" if not reserve else ("ready" if data["completed"] == data["required"] else "partial")
        value = next_version(old, attributes=attributes(data))
        versions = [value]
        if paid:
            wallet["energy"] -= paid
            wallet["time"] -= paid
            versions.append(next_version(before, attributes=attributes(wallet)))
        self._batch(cid, actor, versions, evidence=(old.ref,))
        self._jobs[(actor, key)] = value.ref
        if paid:
            self._wallets[actor] = versions[1].ref
        if reserve:
            self._reserve(data, value.ref)
        return value.ref

    def _event(self, cid, job, outcome, changed=()):
        d = attrs(job)
        ref = address("u4.event", cid)
        data = {"actor": d["actor"], "primitive": d["primitive"], "context": d["context"],
                "outcome": outcome, "operation": job.ref, "event": ref}
        data.update({"participant." + str(i): p for i, p in enumerate(indexed(d, "participant."))})
        target = next((v for v in changed if d.get("target") is not None and v.ref.identity == d["target"].identity), None)
        if d["primitive"] == "inspect" and outcome == "succeeded":
            target = self.world.head(d["target"].identity)
        if target is not None:
            m = target.facet(Material)
            data.update(target=target.ref, owner=m.owner, custodian=m.custodian, condition=m.condition)
            if "wear" in attrs(target):
                data["wear"] = attrs(target)["wear"]
            if m.condition == "stock":
                data["available"] = available(target)
        stock = next((v for v in changed if d.get("stock") is not None and v.ref.identity == d["stock"].identity), None)
        if stock is not None:
            data.update(stock=stock.ref, available=available(stock), consumed=attrs(stock)["consumed"])
        relation = next((v for v in changed if d.get("relation") is not None and v.ref.identity == d["relation"].identity), None)
        if relation is not None:
            data.update(relation=relation.ref, relation_status="fulfilled")
        now = self._now()
        subject = target.ref if target is not None else job.ref
        content = tuple(Proposition(subject, k, v, d["context"], TimeScope(now, None))
                        for k, v in data.items() if k in ("outcome", "owner", "custodian", "condition", "wear", "available", "consumed", "relation_status"))
        sources = tuple(dict.fromkeys((job.ref,) + indexed(d, "input.") + (() if target is None else (target.ref,))))
        return ObjectVersion(ref, WRITER, "Operation outcome", (Role.EVENT,),
            (Account(subject, content, now, None, sources),), occurrence=Occurrence.ACTUAL_EVENT, attributes=attributes(data))

    def _processing(self, cid, old):
        d = attrs(old)
        op = d["primitive"]
        if op == "read":
            key = d["delivery"]
            inputs = (self.access._state(d["actor"]).deliveries[key].source,)
            args = (d["actor"], key)
            method = "process"
        elif op == "bind":
            from .particulars import DetailAddress
            addresses = tuple(DetailAddress(delivery, d["evidence.key." + str(i)])
                              for i, delivery in enumerate(indexed(d, "evidence.delivery.")))
            sources = tuple(dict.fromkeys(self.access.view(d["actor"]).detail(a).source for a in addresses))
            key, inputs = d["binding"].identity.key, (d["binding"],) + sources
            args, method = (d["actor"], d["binding"], addresses), "bind"
        else:
            key, inputs = d["key"], (d["procedure"], d["context"])
            args, method = (d["actor"], d["procedure"], d["context"], key), "acquire"
        values = {"actor": d["actor"], "operation": op, "work_key": key,
                  "required": d["required"], "completed": d["completed"], "spent": d["spent"]}
        values.update({"input." + str(i): ref for i, ref in enumerate(inputs)})
        receipt = record(address("u4.receipt", cid), "Executed native processing receipt", values)
        command = (method, *args, receipt.ref)
        self.access.preview(command, {receipt.ref: receipt})
        return receipt, command

    def _commit(self, cid, actor, key):
        old, data = self._active(actor, key)
        if data["status"] != "ready":
            raise ValueError("full paid work is required before effect commitment")
        changed, material_refs, access_command = [], [], None
        failure = None
        # Invalidation stays internal; no participant view is changed here.
        if any(self.world.head(ref.identity).ref != ref for ref in indexed(data, "dependency.")):
            failure = "stale_dependency"
        elif not self._can_reserve(data, old.ref):
            failure = "reservation_unavailable"
        if failure is None:
            try:
                op = data["primitive"]
                if op == "inspect":
                    target = self.world.head(data["target"].identity)
                    if target.facet(Material) is None or target.lifecycle != Lifecycle.ACTIVE:
                        raise ValueError("material is no longer inspectable")
                elif op in MATERIAL_OPS:
                    for name in ("target", "tool", "stock"):
                        if data[name] is not None:
                            value = material_effect(self.world.resolve(data[name]), data)
                            changed.append(value)
                            material_refs.append(value.ref)
                    if op == "return":
                        changed.append(return_effect(self.world.resolve(data["relation"]), changed[0], actor))
                else:
                    receipt, access_command = self._processing(cid, old)
                    changed.append(receipt)
            except (ValueError, KeyError):
                # The operation was paid, but no physical/processing effect commits.
                # Detailed physical preconditions are evaluator-only, never reasons
                # in an undelivered participant view.
                failure = "precondition_unavailable"
                changed, material_refs, access_command = [], [], None
        outcome = "succeeded" if failure is None else "failed"
        event = self._event(cid, old, outcome, changed)
        data.update(status=outcome, failure=failure, result=event.ref, finished_tick=self._now().tick)
        current = next_version(old, attributes=attributes(data))
        self._batch(cid, actor, (current, *changed, event), evidence=(old.ref,), material=tuple(material_refs))
        if access_command is not None:
            self.access._execute(access_command)
        self._jobs[(actor, key)] = current.ref
        self._release(data, old.ref)
        return event.ref

    def _cancel(self, cid, actor, key):
        old, data = self._active(actor, key)
        event = self._event(cid, old, "cancelled")
        data.update(status="cancelled", failure=None, result=event.ref, finished_tick=self._now().tick)
        current = next_version(old, attributes=attributes(data))
        self._batch(cid, actor, (current, event), evidence=(old.ref,))
        self._jobs[(actor, key)] = current.ref
        self._release(data, old.ref)
        return event.ref

    def _disclose(self, cid, actor, source, selectors, subject):
        grant = Grant("grant:" + cid, actor, source, subject, selectors)
        self.access.grant(grant)
        self.access.deliver(actor, cid, grant.key, self._now())
        return cid

    def _deliver_event(self, cid, event_ref, actor):
        event = self.world.resolve(event_ref)
        data = attrs(event)
        if (event.writer != WRITER or event.occurrence != Occurrence.ACTUAL_EVENT
                or actor not in indexed(data, "participant.")):
            raise ValueError("event is not available to this participant")
        ref = address("u4.observation", cid, actor)
        # These are event facts, not current-head facts or diagnostic failure reasons.
        projected = {k: v for k, v in data.items() if not k.startswith("participant.")}
        now = self._now()
        observation = ObjectVersion(ref, WRITER, "Delivered physical outcome", (Role.OBSERVATION,),
            (Account(event.facet(Account).referent, event.facet(Account).content, now, actor, (event_ref,)),),
            occurrence=Occurrence.OBSERVATION, attributes=attributes(projected))
        selectors = tuple(Selector(a.name, "event" if a.name in ("event", "operation") else "detail", ("attributes", str(i), "value"))
                          for i, a in enumerate(observation.attributes))
        self._batch(cid, actor, (observation,), evidence=(event_ref,))
        self.access.grant(Grant("grant:" + cid, actor, ref, event.facet(Account).referent, selectors))
        self.access.deliver(actor, cid, "grant:" + cid, now)
        return ref

    def _declare(self, cid, versions):
        if not versions or any(v.writer != WRITER or v.ref.identity.namespace.startswith("u4.")
                               or v.facet(Material) is not None or v.occurrence == Occurrence.ACTUAL_EVENT
                               for v in versions):
            raise ValueError("declarations cannot supply paid work, resources or actual effects")
        self._batch(cid, None, versions)
        return tuple(v.ref for v in versions)

    def checkpoint(self):
        with self._lock:
            nodes, token = self._pool.export()
            return seal(self.SCHEMA, {"initial": self._initial, "law": codec.encode(self.law),
                "nodes": nodes, "commands": [token(t) for t in self._events],
                "world": self.world.checkpoint(), "access": self.access.checkpoint()})

    @classmethod
    def restore(cls, text):
        data = unseal(text, cls.SCHEMA)
        if type(data) is not dict or set(data) != {"initial", "law", "nodes", "commands", "world", "access"}:
            raise ValueError("invalid operation checkpoint")
        result = cls(OperationStore.restore(data["initial"]), codec.decode(data["law"]))
        raw = ValuePool(registry())
        raw.load_nodes(data["nodes"])
        for token in data["commands"]:
            command, expected = raw.get(raw.import_token(token))
            if result._execute(command) != expected:
                raise ValueError("operation result replay mismatch")
        if result.world.checkpoint() != data["world"] or result.access.checkpoint() != data["access"]:
            raise ValueError("material, work or situated access replay mismatch")
        # Failed/malformed commands never become authoritative retained inputs.
        if codec.canonical(unseal(result.checkpoint(), cls.SCHEMA)) != codec.canonical(data):
            raise ValueError("noncanonical operation command history")
        return result
