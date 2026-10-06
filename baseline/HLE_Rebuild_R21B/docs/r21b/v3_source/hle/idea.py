"""Exact finite IDEA oracle, separate from the growing-world assessor (S01).

Tables declare X, kappa, f and r before testing. None denotes an unavailable
operation. Closure uses Eq.17 only for a total finite domain exhaustively checked.
This fixture utility does not assert finite closure of the HLE simulation.
"""
from dataclasses import dataclass
from .contracts import EvidenceStatus as E


@dataclass(frozen=True)
class FiniteProtocol:
    name: str
    transform: tuple[int | None, ...]
    return_map: tuple[int | None, ...]


class FiniteIDEA:
    def __init__(self, features, protocols, eligible=None):
        self.features, self.protocols = tuple(features), tuple(protocols)
        self.size = len(self.features)
        self.eligible = tuple(range(self.size)) if eligible is None else tuple(eligible)
        if (not self.size or not self.protocols or len({p.name for p in self.protocols}) != len(self.protocols)
                or any(type(i) is not int or not 0 <= i < self.size for i in self.eligible)):
            raise ValueError("nonempty declared domain and unique protocols required")
        for p in self.protocols:
            for table in (p.transform, p.return_map):
                if len(table) != self.size or any(v is not None and (type(v) is not int or not 0 <= v < self.size) for v in table):
                    raise ValueError("operation leaves declared state space")

    def step(self, state, protocol):
        if type(state) is not int or not 0 <= state < self.size: raise ValueError("invalid state")
        if type(protocol) is not int or not 0 <= protocol < len(self.protocols): raise ValueError("undeclared protocol")
        p = self.protocols[protocol]
        mid = p.transform[state]
        return None if mid is None else p.return_map[mid]

    def sequence(self, state, sequence):
        if type(state) is not int or not 0 <= state < self.size: raise ValueError("invalid state")
        original = state
        trace = [state]
        for index in sequence:
            if type(index) is not int or not 0 <= index < len(self.protocols): raise ValueError("undeclared protocol")
            state = self.step(state, index)
            trace.append(state)
            if state is None: return E.UNASSESSED, tuple(trace)
        if original not in self.eligible: return E.UNASSESSED, tuple(trace)
        return (E.ESTABLISHED if self.features[state] == self.features[original] else E.FAILED), tuple(trace)

    def closure(self, state):
        # Preserve generator failures even when the theorem's premise is absent.
        singles = [self.sequence(state, (i,))[0] for i in range(len(self.protocols))]
        if E.FAILED in singles: return E.FAILED
        if E.UNASSESSED in singles: return E.UNASSESSED
        for i in range(len(self.protocols)):
            targets = [self.step(x, i) for x in range(self.size)]
            if None in targets: return E.UNASSESSED
            for x in range(self.size):
                for y in range(self.size):
                    if self.features[x] == self.features[y] and self.features[targets[x]] != self.features[targets[y]]:
                        return E.UNASSESSED
        return E.ESTABLISHED
