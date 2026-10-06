"""Exact structural interning and field deltas over the unchanged U2 laws.

This is simulator storage, never a participant API. Hashes index immutable
structure; equality is verified before reuse. No lossy summary is used.
"""
from dataclasses import fields, is_dataclass
from enum import Enum
import hashlib
import json

from . import codec
from .records import ObjectId, ObjectRef, ObjectVersion, Transaction, Checkpoint, Moment
from .store import ObjectStore, references


def seal(schema, payload):
    return codec.canonical({"schema": schema, "payload": payload,
        "sha256": hashlib.sha256(codec.canonical(payload).encode()).hexdigest()})


def unseal(text, schema):
    data = json.loads(text, object_pairs_hook=codec._unique,
        parse_constant=lambda x: (_ for _ in ()).throw(ValueError("nonfinite number")))
    if (type(data) is not dict or set(data) != {"schema", "payload", "sha256"}
            or data["schema"] != schema
            or hashlib.sha256(codec.canonical(data["payload"]).encode()).hexdigest() != data["sha256"]):
        raise ValueError("invalid compact envelope")
    return data["payload"]


def freeze(value):
    if type(value) is list:
        return tuple(freeze(v) for v in value)
    if value is None or type(value) in (str, int, bool):
        return value
    raise ValueError("invalid immutable node")


class ValuePool:
    """Content-addressed immutable DAG. Runtime objects are interned too."""
    def __init__(self, records=None, enums=None):
        self.records = codec.RECORDS if records is None else records
        self.enums = codec.ENUMS if enums is None else enums
        self.nodes = {}
        self._values = {}
        self._loaded_keys = []

    def put(self, value):
        if type(value) in self.enums.values():
            node = ("enum", type(value).__name__, value.value)
        elif is_dataclass(value) and type(value) in self.records.values():
            node = ("record", type(value).__name__,
                    tuple((f.name, self.put(getattr(value, f.name))) for f in fields(value)))
        elif type(value) is tuple:
            node = ("tuple", tuple(self.put(x) for x in value))
        elif value is None or type(value) in (str, int, bool):
            return value
        else:
            raise ValueError("unsupported pooled value")
        digest = hashlib.sha256(codec.canonical(node).encode()).hexdigest()
        if digest in self.nodes and codec.canonical(self.nodes[digest]) != codec.canonical(node):
            raise ValueError("structural hash collision")
        self.nodes[digest] = node
        token = ("@", digest)
        # Decode children through the pool, not the caller's unshared instances.
        self.get(token)
        return token

    def get(self, token, visiting=None):
        if token is None or type(token) in (str, int, bool):
            return token
        if type(token) is not tuple or len(token) != 2 or token[0] != "@" or type(token[1]) is not str:
            raise ValueError("invalid pooled reference")
        key = token[1]
        if key in self._values:
            return self._values[key]
        visiting = set() if visiting is None else visiting
        if key in visiting or key not in self.nodes:
            raise ValueError("cyclic or missing pooled value")
        visiting.add(key)
        node = self.nodes[key]
        if len(node) == 3 and node[0] == "record" and node[1] in self.records:
            cls = self.records[node[1]]
            names = tuple(f.name for f in fields(cls))
            if type(node[2]) is not tuple or any(type(pair) is not tuple or len(pair) != 2 for pair in node[2]):
                raise ValueError("invalid pooled record fields")
            if tuple(pair[0] for pair in node[2]) != names:
                raise ValueError("unexpected pooled record fields")
            value = cls(**{name: self.get(t, visiting) for name, t in node[2]})
        elif len(node) == 3 and node[0] == "enum" and node[1] in self.enums and type(node[2]) is str:
            value = self.enums[node[1]](node[2])
        elif len(node) == 2 and node[0] == "tuple" and type(node[1]) is tuple:
            value = tuple(self.get(t, visiting) for t in node[1])
        else:
            raise ValueError("unknown pooled node")
        visiting.remove(key)
        self._values[key] = value
        return value

    @staticmethod
    def _map_node(node, map_token):
        if len(node) == 3 and node[0] == "enum":
            return node
        if len(node) == 2 and node[0] == "tuple" and type(node[1]) is tuple:
            return ("tuple", tuple(map_token(t) for t in node[1]))
        if len(node) == 3 and node[0] == "record" and type(node[2]) is tuple:
            return ("record", node[1], tuple((name, map_token(t)) for name, t in node[2]))
        raise ValueError("invalid structural node")

    def export(self):
        """Small checkpoint-local indexes; internal identities remain hashes."""
        index = {key: i for i, key in enumerate(self.nodes)}
        def token(t):
            if type(t) is tuple:
                if len(t) != 2 or t[0] != "@" or t[1] not in index:
                    raise ValueError("invalid structural reference")
                return ("@", index[t[1]])
            return t
        nodes = tuple(self._map_node(node, token) for node in self.nodes.values())
        return nodes, token

    def import_token(self, token):
        token = freeze(token) if type(token) is list else token
        if type(token) is tuple:
            if (len(token) != 2 or token[0] != "@" or type(token[1]) is not int
                    or not 0 <= token[1] < len(self._loaded_keys)):
                raise ValueError("invalid or forward structural reference")
            return ("@", self._loaded_keys[token[1]])
        if token is None or type(token) in (str, int, bool):
            return token
        raise ValueError("invalid pooled token")

    def load_nodes(self, data):
        if type(data) is not list or self.nodes:
            raise ValueError("new node table required")
        for raw in data:
            node = self._map_node(freeze(raw), self.import_token)
            key = hashlib.sha256(codec.canonical(node).encode()).hexdigest()
            if key in self.nodes:
                raise ValueError("duplicate structural node")
            self.nodes[key] = node
            self.get(("@", key))  # validates the exact allowlisted structure
            self._loaded_keys.append(key)


class DependencyCache:
    """Internal cache invalidation has no participant-facing event or reason."""
    def __init__(self):
        self.values = {}
        self.dependencies = {}
        self.reverse = {}

    def put(self, key, value, identities):
        self.discard(key)
        self.values[key] = value
        self.dependencies[key] = frozenset(identities)
        for identity in self.dependencies[key]:
            self.reverse.setdefault(identity, set()).add(key)

    def discard(self, key):
        self.values.pop(key, None)
        for identity in self.dependencies.pop(key, ()):
            self.reverse[identity].discard(key)
            if not self.reverse[identity]:
                del self.reverse[identity]

    def invalidate(self, identities):
        keys = {key for identity in identities for key in self.reverse.get(identity, ())}
        for key in keys:
            self.discard(key)
        return len(keys)


class VersionIndex:
    NAMES = tuple(f.name for f in fields(ObjectVersion) if f.name not in ("ref", "previous"))

    def __init__(self, pool):
        self.pool = pool
        self.rows = {}

    def __contains__(self, ref):
        return ref in self.rows

    def __iter__(self):
        return iter(self.rows)

    def __getitem__(self, ref):
        if type(ref) is not ObjectRef:
            raise ValueError("exact revision required")
        values = {}
        cursor = ref
        previous = self.rows[ref][0]
        while cursor is not None:
            base, changes = self.rows[cursor]
            for name, token in changes:
                if name not in values:
                    values[name] = self.pool.get(token)
            cursor = base
        return ObjectVersion(ref=ref, previous=previous, **values)

    def __setitem__(self, ref, version):
        old = None if version.previous is None else self[version.previous]
        changes = tuple((name, self.pool.put(getattr(version, name))) for name in self.NAMES
            if old is None or codec.canonical(codec.encode(getattr(old, name))) != codec.canonical(codec.encode(getattr(version, name))))
        self.rows[ref] = (version.previous, changes)

    def values(self):
        return (self[ref] for ref in self.rows)


class CompactStore(ObjectStore):
    """Same lawful writes as U2; a compact authoritative history, not a mirror."""
    SCHEMA = "hle-unified-compact-store-v1"

    def __init__(self):
        super().__init__()
        self.pool = ValuePool()
        self._versions = VersionIndex(self.pool)
        self.dependencies = {}
        self.cache = DependencyCache()

    def _transaction(self, index):
        key, at, writer, actor, refs, lineage = self.pool.get(self._journal[index])
        return Transaction(key, at, writer, actor, tuple(self.resolve(r) for r in refs), lineage)

    def journal(self):
        with self._lock:
            return tuple(self._transaction(i) for i in range(len(self._journal)))

    def commit(self, key, writer, versions, lineage, *, actor=None):
        with self._lock:
            if key in self._keys:
                prior = self._transaction(self._keys[key])
                if codec.dumps(Transaction(key, prior.at, writer, actor, versions, lineage)) != codec.dumps(prior):
                    raise ValueError("transaction key reused with different content")
                return prior
            tx = Transaction(key, Moment(len(self._journal), 0), writer, actor, versions, lineage)
            self._validate(tx)
            # Every stored value is U2 codec-allowlisted before publishing.
            codec.encode(tx)
            for version in versions:
                self._versions[version.ref] = version
                self._heads[version.ref.identity] = version.ref
                for dependency in references(version):
                    if type(dependency) is ObjectRef and dependency != version.ref:
                        self.dependencies.setdefault(dependency, set()).add(version.ref)
            self._keys[key] = len(self._journal)
            self._journal.append(self.pool.put((key, tx.at, writer, actor, tuple(v.ref for v in versions), lineage)))
            self.cache.invalidate(v.ref.identity for v in versions)
            return tx

    def dependents(self, ref):
        return tuple(sorted(self.dependencies.get(ref, ())))

    def canonical_checkpoint(self):
        return codec.dumps(Checkpoint("hle-unified-object-store-v1", self.journal()))

    def checkpoint(self):
        with self._lock:
            rows = [[self.pool.put(ref), self.pool.put(base), changes]
                    for ref, (base, changes) in self._versions.rows.items()]
            nodes, token = self.pool.export()
            return seal(self.SCHEMA, {"nodes": nodes,
                "versions": [[token(ref), token(base), [(name, token(t)) for name, t in changes]] for ref, base, changes in rows],
                "journal": [token(t) for t in self._journal]})

    @classmethod
    def from_store(cls, source):
        result = cls()
        for tx in source.journal():
            result.commit(tx.key, tx.writer, tx.versions, tx.lineage, actor=tx.actor)
        return result

    @classmethod
    def restore(cls, text):
        data = unseal(text, cls.SCHEMA)
        if type(data) is not dict or set(data) != {"nodes", "versions", "journal"}:
            raise ValueError("invalid compact store fields")
        raw = cls()
        raw.pool.load_nodes(data["nodes"])
        for item in data["versions"]:
            if type(item) is not list or len(item) != 3:
                raise ValueError("invalid version delta")
            ref, base = (raw.pool.get(raw.pool.import_token(t)) for t in item[:2])
            changes = tuple((name, raw.pool.import_token(t)) for name, t in item[2])
            if type(ref) is not ObjectRef or ref in raw._versions.rows:
                raise ValueError("invalid or duplicate exact revision")
            expected = None if ref.revision == 1 else ObjectRef(ref.identity, ref.revision - 1)
            if base != expected or base is not None and base not in raw._versions:
                raise ValueError("missing or out-of-order predecessor")
            names = tuple(name for name, _ in changes)
            if len(set(names)) != len(names) or any(n not in VersionIndex.NAMES for n in names):
                raise ValueError("unknown or duplicate delta field")
            raw._versions.rows[ref] = (base, changes)
        result = cls()
        for token in data["journal"]:
            entry = raw.pool.get(raw.pool.import_token(token))
            if type(entry) is not tuple or len(entry) != 6:
                raise ValueError("invalid journal entry")
            key, at, writer, actor, refs, lineage = entry
            versions = tuple(raw.resolve(r) for r in refs)
            if key in result._keys or at != Moment(len(result._journal), 0):
                raise ValueError("invalid journal order")
            result.commit(key, writer, versions, lineage, actor=actor)
        # Reject extra nodes, stale deltas, unsupported state and noncanonical
        # reconstructions even if the attacker recalculated the outer checksum.
        if codec.canonical(unseal(result.checkpoint(), cls.SCHEMA)) != codec.canonical(data):
            raise ValueError("compact history does not reconstruct exactly")
        return result
