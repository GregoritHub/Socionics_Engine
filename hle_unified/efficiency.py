"""U13 physical optimizations; no participant policies or prices live here.

The legacy adapter is explicitly enabled by callers. Validation still checks
every field, including strict bool/int types; only the schema is compiled once.
"""
from dataclasses import fields, is_dataclass
from functools import lru_cache
from types import UnionType, MappingProxyType
from typing import get_args, get_origin
from enum import Enum


@lru_cache(maxsize=None)
def field_names(cls):
    return tuple(f.name for f in fields(cls))


def exact_equal(a, b):
    if type(a) is not type(b):
        return False
    if a is b:
        return True
    if type(a) is tuple:
        return len(a) == len(b) and all(exact_equal(x, y) for x, y in zip(a, b))
    if is_dataclass(a):
        return all(exact_equal(getattr(a, n), getattr(b, n)) for n in field_names(type(a)))
    return a == b


@lru_cache(maxsize=None)
def validator(hint):
    origin, args = get_origin(hint), get_args(hint)
    if origin is UnionType:
        checks = tuple(validator(part) for part in args)
        return lambda v: any(check(v) for check in checks)
    if origin is tuple:
        if len(args) == 2 and args[1] is Ellipsis:
            check = validator(args[0])
            return lambda v: type(v) is tuple and all(check(x) for x in v)
        checks = tuple(validator(part) for part in args)
        return lambda v: (type(v) is tuple and len(v) == len(checks)
                          and all(check(x) for check, x in zip(checks, v)))
    return lambda v: type(v) is hint


@lru_cache(maxsize=None)
def record_schema(cls):
    from hle.contracts import _hints
    hints = _hints(cls)
    return tuple((f.name, validator(hints[f.name])) for f in fields(cls))


def validate_record(self):
    for name, check in record_schema(type(self)):
        if not check(getattr(self, name)):
            raise ValueError(f"{type(self).__name__}.{name}: wrong type or mutable value")


def install_validators():
    from hle.contracts import Record
    Record.__post_init__ = validate_record


def share_validated_graph(root):
    """Coalesce equal immutable values in an already validated restored graph.

    The table is local and released afterwards. Mutable containers retain their
    identity. Frozen records keep their exact type and every field; different
    referents, revisions and actor-owned histories never compare equal.
    This is not a deserializer or a way around checkpoint validation.
    """
    memo, atoms, intern = {}, {}, {}

    def visit(value):
        t = type(value)
        if value is None or t in (int, bool, str) or isinstance(value, Enum):
            return atoms.setdefault((t, value), value)
        identity = id(value)
        if identity in memo:
            return memo[identity]
        # All typed boundary values are immutable and acyclic. Mutable world
        # objects can be cyclic and are marked before descending.
        memo[identity] = value
        if t is tuple:
            parts = tuple(visit(x) for x in value)
            key = (tuple, tuple(id(x) for x in parts))
            result = intern.setdefault(key, parts)
        elif is_dataclass(value) and getattr(t, '__dataclass_params__').frozen:
            parts = tuple(visit(getattr(value, f.name)) for f in fields(value))
            key = (t, tuple(id(x) for x in parts))
            result = intern.get(key)
            if result is None:
                # These children are exactly equal to the already checked
                # children; change physical sharing only, without revalidation.
                for f, part in zip(fields(value), parts):
                    object.__setattr__(value, f.name, part)
                result = intern[key] = value
        elif t is dict:
            items = [(visit(k), visit(v)) for k, v in value.items()]
            value.clear(); value.update(items); result = value
        elif t is list:
            value[:] = [visit(x) for x in value]; result = value
        elif t is set:
            parts = [visit(x) for x in value]
            value.clear(); value.update(parts); result = value
        elif t is frozenset:
            result = frozenset(visit(x) for x in value)
        elif t is MappingProxyType:
            result = MappingProxyType({visit(k): visit(v) for k, v in value.items()})
        elif hasattr(value, '__dict__') and t.__module__.startswith('hle.'):
            for k, v in tuple(vars(value).items()):
                setattr(value, k, visit(v))
            result = value
        else:
            result = value
        memo[identity] = result
        return result
    return visit(root)


def install_legacy_optimizations():
    """Opt-in R21B execution adapter, leaving every frozen source byte intact."""
    install_validators()
    from hle.closure import ClosureWorld
    if getattr(ClosureWorld, '_u13_restore_installed', False):
        return
    original = ClosureWorld.restore.__func__

    @classmethod
    def restore(cls, text):
        return share_validated_graph(original(cls, text))

    ClosureWorld.restore = restore
    install_command_query_cache(ClosureWorld)
    ClosureWorld._u13_restore_installed = True


def install_command_query_cache(world_cls):
    """Reuse actor-specific read checks inside one atomic circuit command.

    The cache is disabled throughout publication, and erased on success, error
    or nested execution. It never persists into a later command or checkpoint.
    Material actions, paid work, offers and decisions are not cached.
    """
    if getattr(world_cls, '_u13_queries_installed', False):
        return
    missing = object()
    attr = '_u13_command_queries'
    original_step = world_cls._circuit_work_step
    original_commit = world_cls._commit

    def restore_scope(self, previous):
        if previous is missing:
            self.__dict__.pop(attr, None)
        elif previous is None:
            setattr(self, attr, None)
        else:
            previous.clear()
            setattr(self, attr, previous)

    def step(self, command):
        previous = self.__dict__.get(attr, missing)
        setattr(self, attr, {})
        try:
            return original_step(self, command)
        finally:
            restore_scope(self, previous)

    def commit(self, transaction):
        previous = self.__dict__.get(attr, missing)
        setattr(self, attr, None)
        try:
            return original_commit(self, transaction)
        finally:
            restore_scope(self, previous)

    def wrap(name, original):
        mapping = name == '_current_aspects'
        def query(self, actor):
            cache = self.__dict__.get(attr)
            if cache is None:
                return original(self, actor)
            key = (name, actor)
            if key not in cache:
                result = original(self, actor)
                cache[key] = tuple(result.items()) if mapping else result
            value = cache[key]
            return dict(value) if mapping else value
        return query

    for name in ('_root_available', '_current_aspects', '_signature'):
        setattr(world_cls, name, wrap(name, getattr(world_cls, name)))
    world_cls._circuit_work_step = step
    world_cls._commit = commit
    world_cls._u13_queries_installed = True
