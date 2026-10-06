"""Independent positional oracle and offline processing fold; no live routing code."""
from itertools import permutations
import json
from pathlib import Path
from hle.metabolism_records import MetabolicTransaction

STACKS = json.loads((Path(__file__).parent / "stack_fixture.json").read_text())
DIMS = (4, 3, 2, 1, 1, 2, 3, 4)


def leg(stack, first, last):
    a, b = stack.index(first), stack.index(last)
    axes = [1 << i for i in range(3) if (a ^ b) & (1 << i)]
    paths = []
    for ordering in permutations(axes):
        path, node = [first], a
        for axis in ordering:
            node ^= axis; path.append(stack[node])
        paths.append(tuple(path))
    return paths


def route_oracle(tim, active, target, expenditure, size, typed=True, prices=True):
    name = tim if typed else "ile"
    stack = [s.lower() for s in STACKS[name]]
    def price(e): return 5 - DIMS[stack.index(e)] if prices else 1
    possibilities = []
    for seat in ((6, 8) if expenditure else (5, 7)):
        for a in leg(stack, active, stack[seat - 1]):
            for b in leg(stack, stack[seat - 1], target):
                path = a + b[1:]
                costs = tuple(price(e) for e in path[1:])
                possibilities.append((sum(costs), len(path), path, seat, len(a)-1, costs))
    _, _, path, seat, offset, costs = min(possibilities)
    return path, tuple(stack.index(e)+1 for e in path), seat, offset, costs, max(1, size)*price(target)


def processing_fold(profiles, journal):
    states = {p.owner: (p.active, p.perspective, None) for p in profiles}
    jobs, changes = {}, []
    for tx in journal:
        changed = ()
        if type(tx) is MetabolicTransaction:
            state = tx.state
            states[state.owner] = (state.active, state.perspective, state.busy)
            jobs[(tx.command.actor, tx.command.task_id)] = tx.job
            changed = (state.owner,)
        changes.append((tx.event.ref, changed))
    return states, jobs, tuple(changes)
