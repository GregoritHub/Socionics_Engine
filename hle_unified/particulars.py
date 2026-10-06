"""Situated access over exact U2 revisions.

AccessLedger is a trusted observation/processing adapter, like ObjectStore's
simulator boundary. Policies receive only ParticipantView. Delivery alone does
not confer processed content; complete actor-owned receipts are required.
The receipt authority is an explicit import boundary until U4 supplies execution.
"""
from dataclasses import dataclass, fields, is_dataclass
from types import MappingProxyType

from hle.contracts import Record, ClaimStatus
from . import codec
from .compact import CompactStore, ValuePool, seal, unseal, freeze
from .records import (ObjectId, ObjectRef, Moment, TimeScope, Definition, Procedure,
    Proposition, Occurrence, Role, Account, Attitude, Memory, Agency, text_required)
from .store import references
from .efficiency import field_names

Value = ObjectRef | ObjectId | str | int | bool | None | Moment | TimeScope | Definition | Procedure
CATEGORIES = ("name", "date", "ownership", "event", "receipt", "definition", "detail")
RECEIPT_WRITER = "u3.processing"
_ANY = object()


def typed_key(value):
    """Exact type-sensitive query key; no JSON allocation or digest needed."""
    t = type(value)
    if value is None or t in (str, int, bool) or t in codec.ENUMS.values():
        return t, value
    if t is tuple:
        return t, tuple(typed_key(x) for x in value)
    if t in codec.RECORDS.values():
        return t, tuple(typed_key(getattr(value, n)) for n in field_names(t))
    raise ValueError('unsupported U2 query value')


@dataclass(frozen=True)
class Selector(Record):
    key: str
    category: str
    path: tuple[str, ...]

    def __post_init__(self):
        super().__post_init__()
        text_required(self.key)
        if self.category not in CATEGORIES or not self.path or any(not p for p in self.path):
            raise ValueError("invalid particular selector")


@dataclass(frozen=True)
class Grant(Record):
    key: str
    actor: ObjectId
    source: ObjectRef
    subject: ObjectRef
    selectors: tuple[Selector, ...]

    def __post_init__(self):
        super().__post_init__()
        text_required(self.key)
        if not self.selectors or len({s.key for s in self.selectors}) != len(self.selectors):
            raise ValueError("unique nonempty particular keys required")


@dataclass(frozen=True)
class DetailAddress(Record):
    delivery: str
    key: str

    def __post_init__(self):
        super().__post_init__()
        text_required(self.delivery)
        text_required(self.key)


@dataclass(frozen=True)
class Particular(Record):
    address: DetailAddress
    category: str
    source: ObjectRef
    subject: ObjectRef
    path: tuple[str, ...]
    value: Value
    occurrence: Occurrence | None


@dataclass(frozen=True)
class Delivery(Record):
    key: str
    actor: ObjectId
    at: Moment
    source: ObjectRef
    particulars: tuple[Particular, ...]


@dataclass(frozen=True)
class Receipt(Record):
    ref: ObjectRef
    actor: ObjectId
    operation: str
    work_key: str
    inputs: tuple[ObjectRef, ...]
    required: int
    completed: int
    spent: int

    def __post_init__(self):
        super().__post_init__()
        if self.operation not in ("read", "bind", "acquire"):
            raise ValueError("unsupported processing receipt")
        text_required(self.work_key)
        if not 0 <= self.completed <= self.required or self.required < 1 or self.spent < self.completed:
            raise ValueError("invalid recorded work")

    @property
    def complete(self):
        return self.completed == self.required


@dataclass(frozen=True)
class BindingView(Record):
    ref: ObjectRef
    actor: ObjectId
    target: ObjectRef
    cue: ObjectRef
    context: ObjectRef
    meaning: str
    content: tuple[Proposition, ...]
    endorsement: ClaimStatus
    confidence: int | None
    particulars: tuple[DetailAddress, ...]
    links: tuple[ObjectRef, ...]
    receipt: ObjectRef


@dataclass(frozen=True)
class AcquiredUse(Record):
    key: str
    procedure: ObjectRef
    context: ObjectRef
    receipt: ObjectRef


@dataclass(frozen=True)
class Pending(Record):
    key: str
    at: Moment


@dataclass(frozen=True)
class ActorEvent(Record):
    sequence: int
    kind: str
    key: str
    refs: tuple[ObjectRef, ...]


@dataclass(frozen=True)
class ViewSnapshot(Record):
    actor: ObjectId
    particulars: tuple[Particular, ...]
    pending: tuple[Pending, ...]
    receipts: tuple[Receipt, ...]
    bindings: tuple[BindingView, ...]
    acquired: tuple[AcquiredUse, ...]
    history: tuple[ActorEvent, ...]


@dataclass(frozen=True)
class Traversal(Record):
    visited: tuple[ObjectRef, ...]
    bindings: tuple[BindingView, ...]
    particulars: tuple[Particular, ...]
    truncated: bool


def record_registry():
    return {**codec.RECORDS, **{cls.__name__: cls for cls in globals().values()
        if isinstance(cls, type) and issubclass(cls, Record) and cls.__module__ == __name__}}


def packed(value):
    """Deterministic actor-visible bytes: no cache, global time or pool counters."""
    pool = ValuePool(record_registry())
    token = pool.put(value)
    nodes, encode_token = pool.export()
    return seal("hle-unified-participant-value-v1", {"root": encode_token(token), "nodes": nodes})


def read_path(version, path, actor):
    value = version
    for part in path:
        if type(value) in (Memory, Agency) and value.owner != actor:
            raise ValueError("another participant's private capability state")
        if is_dataclass(value) and part in {f.name for f in fields(value)}:
            value = getattr(value, part)
        elif type(value) is tuple and part.isascii() and part.isdecimal() and str(int(part)) == part and int(part) < len(value):
            value = value[int(part)]
        else:
            raise ValueError("invalid disclosed field path")
    return value


def _attrs(version):
    return {a.name: a.value for a in version.attributes}


class ParticipantView:
    """Detached read-only query surface. No resolver, writer or world handle."""
    __slots__ = ("snapshot", "_keys", "_categories", "_subjects", "_addresses", "_sources", "_values", "_receipts", "_work", "_bindings", "_heads")

    def __init__(self, snapshot):
        object.__setattr__(self, "snapshot", snapshot)
        indexes = {name: {} for name in ("_keys", "_categories", "_subjects", "_sources", "_values")}
        for detail in snapshot.particulars:
            for name, key in (("_keys", detail.address.key), ("_categories", detail.category),
                              ("_subjects", detail.subject.identity), ("_sources", detail.source), ("_values", typed_key(detail.value))):
                indexes[name].setdefault(key, []).append(detail)
        for name, index in indexes.items():
            object.__setattr__(self, name, MappingProxyType({k: tuple(v) for k, v in index.items()}))
        object.__setattr__(self, "_addresses", MappingProxyType({p.address: p for p in snapshot.particulars}))
        object.__setattr__(self, "_bindings", MappingProxyType({b.ref: b for b in snapshot.bindings}))
        object.__setattr__(self, "_heads", MappingProxyType({b.ref.identity: b for b in snapshot.bindings}))
        object.__setattr__(self, "_receipts", MappingProxyType({r.ref: r for r in snapshot.receipts}))
        work = {}
        for receipt in snapshot.receipts:
            work.setdefault((receipt.operation, receipt.work_key), []).append(receipt)
        object.__setattr__(self, "_work", MappingProxyType({k: tuple(v) for k, v in work.items()}))

    def __setattr__(self, name, value):
        raise AttributeError("participant views are immutable")

    def bytes(self):
        return packed(self.snapshot)

    def lookup(self, *, key=None, category=None, subject=None, value=_ANY):
        """Index-only detail lookup; never invokes conceptual traversal."""
        candidates = []
        for constraint, index in ((key, self._keys), (category, self._categories), (subject, self._subjects)):
            if constraint is not None:
                candidates.append(index.get(constraint, ()))
        # Exact typed values keep False distinct from integer zero.
        value_key = None if value is _ANY else typed_key(value)
        if value_key is not None:
            candidates.append(self._values.get(value_key, ()))
        selected = min(candidates, key=len) if candidates else self.snapshot.particulars
        return tuple(p for p in selected if (key is None or p.address.key == key)
            and (category is None or p.category == category)
            and (subject is None or p.subject.identity == subject)
            and (value_key is None or typed_key(p.value) == value_key))

    def receipt(self, ref):
        return self._receipts.get(ref)

    def work_receipts(self, operation, key):
        return self._work.get((operation, key), ())

    def resolve(self, ref):
        """Only explicitly processed fields. Unknown and inaccessible are alike."""
        return self._sources.get(ref, ())

    def detail(self, address):
        return self._addresses.get(address)

    def can_use(self, procedure, context):
        """Retained acquisition evidence only; U4 must check actual execution."""
        return any(u.procedure == procedure and u.context == context for u in self.snapshot.acquired)

    def traverse(self, cue, context, *, visit_limit=32):
        """Bounded contextual binding walk, not U5 Model A realization."""
        if type(visit_limit) is not int or visit_limit < 1:
            raise ValueError("positive traversal limit required")
        queue = [b.ref for b in self._heads.values() if b.cue == cue and b.context == context]
        seen, found, selected = set(), [], {}
        cursor = 0
        while cursor < len(queue) and len(found) < visit_limit:
            ref = queue[cursor]
            cursor += 1
            binding = self._bindings.get(ref)
            if ref in seen or binding is None or binding.context != context:
                continue
            seen.add(ref)
            found.append(binding)
            for address in binding.particulars:
                if address in self._addresses:
                    selected.setdefault(address, self._addresses[address])
            queue.extend(binding.links)
        truncated = any(r not in seen and r in self._bindings and self._bindings[r].context == context for r in queue[cursor:])
        return Traversal(tuple(b.ref for b in found), tuple(found), tuple(selected.values()), truncated)


class _ActorState:
    def __init__(self):
        self.deliveries = {}
        self.processed = set()
        self.receipts = {}
        self.bindings = {}
        self.acquired = {}
        self.history = []


class AccessLedger:
    SCHEMA = "hle-unified-situated-access-v1"
    STORE = CompactStore
    RECEIPT_WRITERS = (RECEIPT_WRITER,)

    def __init__(self, world):
        if not isinstance(world, self.STORE):
            raise ValueError("situated access requires the compact native store")
        self.world = world
        self.pool = ValuePool(record_registry())
        self._grants = {}
        self._revoked = set()
        self._states = {}
        self._events = []
        self._cache_namespace = object()

    def _state(self, actor):
        if type(actor) is not ObjectId:
            raise ValueError("actor identity required")
        return self._states.setdefault(actor, _ActorState())

    def _append(self, command, result=()):
        self._events.append(self.pool.put((command, result)))

    def _visible_event(self, actor, kind, key, refs=()):
        state = self._state(actor)
        state.history.append(ActorEvent(len(state.history) + 1, kind, key, refs))
        self.world.cache.discard((self._cache_namespace, actor))

    def grant(self, grant):
        if type(grant) is not Grant or (grant.actor, grant.key) in self._grants:
            raise ValueError("new exact grant required")
        if Role.PERSON not in self.world.resolve(ObjectRef(grant.actor, 1)).roles:
            raise ValueError("participant role required")
        source = self.world.resolve(grant.source)
        self.world.resolve(grant.subject)
        if Role.ASSESSMENT in source.roles:
            raise ValueError("evaluator records cannot enter participant access")
        account, attitude = source.facet(Account), source.facet(Attitude)
        if ((account is not None and account.holder is not None and account.holder != grant.actor)
                or (attitude is not None and attitude.holder != grant.actor)):
            raise ValueError("private account requires an explicit recipient observation")
        # Validate the entire projection before storing a right. References in a
        # permitted value are identifiers, never transitive reading permissions.
        self._project(grant, "validation", Moment(0, 0))
        grant = self.pool.get(self.pool.put(grant))
        self._grants[(grant.actor, grant.key)] = grant
        self._append(("grant", grant))

    def revoke(self, actor, key):
        if (actor, key) not in self._grants or (actor, key) in self._revoked:
            raise ValueError("active grant required")
        self._revoked.add((actor, key))
        self._append(("revoke", actor, key))

    def _project(self, grant, key, at):
        source = self.world.resolve(grant.source)
        details = tuple(Particular(DetailAddress(key, s.key), s.category, grant.source, grant.subject,
            s.path, read_path(source, s.path, grant.actor), source.occurrence) for s in grant.selectors)
        return Delivery(key, grant.actor, at, grant.source, details)

    def deliver(self, actor, key, grant_key, at):
        text_required(key)
        state = self._state(actor)
        grant = self._grants.get((actor, grant_key))
        if key in state.deliveries or grant is None or (actor, grant_key) in self._revoked:
            raise ValueError("new delivery and active exact grant required")
        if state.deliveries and at < next(reversed(state.deliveries.values())).at:
            raise ValueError("actor delivery time cannot run backwards")
        delivery = self._project(grant, key, at)
        delivery = self.pool.get(self.pool.put(delivery))
        state.deliveries[key] = delivery
        self._visible_event(actor, "delivery", key)
        self._append(("deliver", actor, key, grant_key, at), delivery)
        return Pending(key, at)

    def _receipt(self, ref, actor, operation, work_key, inputs):
        version = self.world.resolve(ref)
        data = _attrs(version)
        base = {"actor", "operation", "work_key", "required", "completed", "spent"}
        extras = tuple(k for k in data if k not in base)
        expected = tuple("input." + str(i) for i in range(len(inputs)))
        if version.writer not in self.RECEIPT_WRITERS or version.roles != (Role.RECORD,) or set(extras) != set(expected) or not base.issubset(data):
            raise ValueError("recognized actor processing evidence required")
        receipt = Receipt(ref, data["actor"], data["operation"], data["work_key"],
            tuple(data[k] for k in expected), data["required"], data["completed"], data["spent"])
        if (receipt.actor, receipt.operation, receipt.work_key, receipt.inputs) != (actor, operation, work_key, inputs):
            raise ValueError("receipt actor, work or exact dependencies do not match")
        if ref in self._state(actor).receipts:
            raise ValueError("processing receipt already consumed")
        return receipt

    def process(self, actor, delivery_key, receipt_ref):
        state = self._state(actor)
        delivery = state.deliveries.get(delivery_key)
        if delivery is None or delivery_key in state.processed:
            raise ValueError("pending delivered input required")
        receipt = self._receipt(receipt_ref, actor, "read", delivery_key, (delivery.source,))
        previous = [r for r in state.receipts.values() if r.operation == "read" and r.work_key == delivery_key]
        if previous and (receipt.required != previous[-1].required or receipt.completed < previous[-1].completed or receipt.spent < previous[-1].spent):
            raise ValueError("processing continuation cannot erase recorded work")
        state.receipts[receipt.ref] = receipt
        if receipt.complete:
            state.processed.add(delivery_key)
        self._visible_event(actor, "processed" if receipt.complete else "partial", delivery_key, (receipt.ref,))
        self._append(("process", actor, delivery_key, receipt_ref), receipt)
        return receipt

    def _known_refs(self, actor):
        result = set()
        for p in self.view(actor).snapshot.particulars:
            result.update(r for r in references(p) if type(r) is ObjectRef)
        return result

    def bind(self, actor, binding_ref, addresses, receipt_ref):
        state = self._state(actor)
        view = self.view(actor)
        version = self.world.resolve(binding_ref)
        account, data = version.facet(Account), _attrs(version)
        if version.occurrence != Occurrence.INTERPRETATION or account is None or account.holder != actor:
            raise ValueError("actor-owned interpretation required")
        if len(set(addresses)) != len(addresses) or not addresses or any(view.detail(a) is None for a in addresses):
            raise ValueError("binding needs processed particular evidence")
        source_refs = tuple(dict.fromkeys(view.detail(a).source for a in addresses))
        if any(r not in account.sources for r in source_refs) or set(account.sources) != set(source_refs):
            raise ValueError("interpretation evidence must equal accessible particular sources")
        base = {"cue", "context", "meaning", "endorsement", "confidence"}
        link_keys = tuple("link." + str(i) for i in range(len(data) - len(base)))
        if set(data) != base | set(link_keys):
            raise ValueError("invalid binding attributes")
        known = self._known_refs(actor)
        if any(r not in known for r in (account.referent, data["cue"], data["context"])):
            raise ValueError("binding anchors must be accessible exact references")
        if any(r not in known for r in references(account.content) if type(r) is ObjectRef):
            raise ValueError("interpretation content contains inaccessible references")
        links = tuple(data[k] for k in link_keys)
        if any(r != binding_ref and r not in state.bindings for r in links):
            raise ValueError("links must identify retained actor bindings")
        prior = next((b for b in reversed(tuple(state.bindings.values())) if b.ref.identity == binding_ref.identity), None)
        if version.previous != (None if prior is None else prior.ref):
            raise ValueError("binding revision must follow retained history")
        confidence = data["confidence"]
        if confidence is not None and (type(confidence) is not int or not 0 <= confidence <= 100):
            raise ValueError("confidence must be 0..100 or unspecified")
        receipt = self._receipt(receipt_ref, actor, "bind", binding_ref.identity.key, (binding_ref,) + source_refs)
        if not receipt.complete:
            raise ValueError("completed binding work required")
        binding = BindingView(binding_ref, actor, account.referent, data["cue"], data["context"],
            data["meaning"], account.content, ClaimStatus(data["endorsement"]), confidence, addresses, links, receipt_ref)
        text_required(binding.meaning)
        binding = self.pool.get(self.pool.put(binding))
        state.bindings[binding_ref] = binding
        state.receipts[receipt.ref] = receipt
        self._visible_event(actor, "binding", binding_ref.identity.key, (binding_ref, receipt_ref))
        self._append(("bind", actor, binding_ref, addresses, receipt_ref), (binding, receipt))
        return binding

    def acquire(self, actor, procedure, context, key, receipt_ref):
        state = self._state(actor)
        view = self.view(actor)
        if key in state.acquired or context not in self._known_refs(actor):
            raise ValueError("new contextual acquired use required")
        if not any(type(p.value) is Procedure and p.source == procedure for p in view.snapshot.particulars):
            raise ValueError("processed exact procedure structure required")
        receipt = self._receipt(receipt_ref, actor, "acquire", key, (procedure, context))
        if not receipt.complete:
            raise ValueError("completed acquisition evidence required")
        acquired = AcquiredUse(key, procedure, context, receipt_ref)
        state.acquired[key] = acquired
        state.receipts[receipt.ref] = receipt
        self._visible_event(actor, "acquired", key, (procedure, context, receipt_ref))
        self._append(("acquire", actor, procedure, context, key, receipt_ref), (acquired, receipt))
        return acquired

    def view(self, actor, *, through=None):
        state = self._state(actor)
        if through is not None:
            if type(through) is not int or not 0 <= through <= len(state.history):
                raise ValueError("actor-local history position required")
            replay = type(self)(self.world)
            if through:
                for token in self._events:
                    command, result = self.pool.get(token)
                    replay._execute(command)
                    if len(replay._state(actor).history) == through:
                        break
            historical = replay.view(actor)
            for key in tuple(self.world.cache.values):
                if type(key) is tuple and key[0] is replay._cache_namespace:
                    self.world.cache.discard(key)
            return historical
        cache_key = (self._cache_namespace, actor)
        if cache_key in self.world.cache.values:
            return self.world.cache.values[cache_key]
        details = tuple(p for key, d in state.deliveries.items() if key in state.processed for p in d.particulars)
        snapshot = ViewSnapshot(actor, details,
            tuple(Pending(key, d.at) for key, d in state.deliveries.items() if key not in state.processed),
            tuple(state.receipts.values()), tuple(state.bindings.values()), tuple(state.acquired.values()), tuple(state.history))
        view = ParticipantView(snapshot)
        deps = {r.identity if type(r) is ObjectRef else r for r in references(snapshot)}
        self.world.cache.put(cache_key, view, deps)
        return view

    def _execute(self, command):
        allowed = {"grant": self.grant, "revoke": self.revoke, "deliver": self.deliver,
            "process": self.process, "bind": self.bind, "acquire": self.acquire}
        if type(command) is not tuple or not command or command[0] not in allowed:
            raise ValueError("unsupported access command")
        return allowed[command[0]](*command[1:])

    def checkpoint(self):
        nodes, token = self.pool.export()
        return seal(self.SCHEMA, {"world": self.world.checkpoint(), "nodes": nodes, "events": [token(t) for t in self._events]})

    @classmethod
    def restore(cls, text):
        data = unseal(text, cls.SCHEMA)
        if type(data) is not dict or set(data) != {"world", "nodes", "events"}:
            raise ValueError("invalid access checkpoint fields")
        result = cls(cls.STORE.restore(data["world"]))
        raw = ValuePool(record_registry())
        raw.load_nodes(data["nodes"])
        for token in data["events"]:
            command, expected = raw.get(raw.import_token(token))
            result._execute(command)
            # Compare the full rederived event with typed structural bytes.
            if packed(result.pool.get(result._events[-1])) != packed((command, expected)):
                raise ValueError("access projection or processing replay mismatch")
        if codec.canonical(unseal(result.checkpoint(), cls.SCHEMA)) != codec.canonical(data):
            raise ValueError("noncanonical access history")
        return result
