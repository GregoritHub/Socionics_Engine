from functools import wraps
from hle.contracts import *


def rules(*ids):
    def decorate(function):
        function.rule_ids = ids
        return function
    return decorate


def ref(kind, key, revision=1):
    return Ref(kind, key, revision)


ALICE = ref(Kind.ENTITY, "alice")
BOB = ref(Kind.ENTITY, "bob")
BOX = ref(Kind.ENTITY, "box")
CONTEXT = ref(Kind.CONTEXT, "warehouse")
TIME = Moment(1, 0)
SCOPE = TimeScope(TIME, None)
OWNERSHIP = Proposition(BOX, "owned_by", ALICE, CONTEXT, SCOPE)
PROC = ref(Kind.PROCEDURE, "inspect")
UNIT = ref(Kind.RULE, "energy_quantum")


def memory(key="m", owner=ALICE, content=(OWNERSHIP,), **overrides):
    args = dict(ref=ref(Kind.MEMORY, key), owner=owner, retained_at=TIME,
                content=content, links=(), observations=(), derived_from=(),
                claim_status=ClaimStatus.TENTATIVE, capabilities=(), replaces=None,
                reason="fixture interpretation; no accuracy claim")
    args.update(overrides)
    return MemoryRevision(**args)


def work(**overrides):
    args = dict(ref=ref(Kind.WORK, "attempt"), owner=ALICE, operation=PROC,
                before=(ResourceAmount(UNIT, 5),), credited=(),
                charged=(ResourceAmount(UNIT, 2),), after=(ResourceAmount(UNIT, 3),),
                required_units=4, completed_units=2, outcome=WorkStatus.PARTIAL,
                reason="partial work retained and charged")
    args.update(overrides)
    return WorkRecord(**args)
