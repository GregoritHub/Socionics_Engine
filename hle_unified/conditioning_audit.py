"""CT §8.3 completed paid use observations. No executor import or feedback."""
from hle.model_a import element_at
from .energy_audit import blocks, data, debit, resource_model, validate_profiles
from .axes import AXES, axis_cells, load, tilt, formula_positions

ELEMENTS = ('ne', 'ni', 'se', 'si', 'te', 'ti', 'fe', 'fi')


def completed_use(transactions):
    """Reconstruct all actors from revisions and matching committed wallets.

    A completed hop or seat block counts once even if the enclosing operation
    is subsequently cancelled. Partial blocks, proposals and preparation do not.
    """
    transactions = tuple(transactions)
    model = resource_model(transactions)
    validate_profiles(transactions)
    heads, profiles, counts = {}, {}, {}
    for tx in transactions:
        jobs = [v for v in tx.versions if data(v).get('record_type') == 'operation']
        wallets = [v for v in tx.versions if data(v).get('record_type') == 'wallet' and v.previous]
        if len(jobs) > 1:
            raise ValueError('ambiguous paid operation')
        expected_time = expected_energy = 0
        actor = None
        if jobs:
            v = jobs[0]; d = data(v); actor = d['actor']
            old = heads.get(v.ref.identity)
            previous = {} if old is None else data(old)
            before = previous.get('completed', 0)
            after = d['completed']
            if (type(after) is not int or not 0 <= before <= after <= d['required']
                    or d['spent'] != after):
                raise ValueError('invalid paid completion count')
            expected_time = after-before
            reconstructed = debit(d, previous)  # Also protects immutable routes.
            expected_energy = reconstructed if model == 'grade-v1' else expected_time
            if 'route_count' in d:
                for start, end, _, element in blocks(d):
                    if element is not None and before < end <= after:
                        if actor not in counts or element not in counts[actor]:
                            raise ValueError('completed use without known actor/element')
                        counts[actor][element] += 1
        if bool(expected_time) != bool(wallets) or len(wallets) > 1:
            raise ValueError('completed work lacks exact raw wallet evidence')
        if wallets:
            v = wallets[0]; d = data(v); old = data(heads[v.ref.identity])
            if (d['actor'] != actor or old['energy']-d['energy'] != expected_energy
                    or old['time']-d['time'] != expected_time
                    or min(d['energy'],d['time']) < 0):
                raise ValueError('completed use not paid by actor')
        for v in tx.versions:
            d = data(v)
            if v.ref.identity.namespace == 'u5.profile':
                profiles[d['actor']] = d['tim']
                counts[d['actor']] = dict.fromkeys(ELEMENTS, 0)
            heads[v.ref.identity] = v
    return profiles, counts


def observations(transactions):
    """Fresh derived observations; no state is retained or written."""
    profiles, counts = completed_use(transactions)
    rows = []
    for actor in sorted(profiles):
        tim = profiles[actor]
        field = {p: counts[actor][element_at(tim,p)] for p in range(1,9)}
        loads, tilts, cells = load(field), tilt(field), axis_cells(tim)
        rows.append(dict(actor=actor, tim=tim, counts=counts[actor],
                         axis_loads=loads, axis_tilts=tilts, axis_cells=cells,
                         cells_with_greatest_load=tuple(c for c,n in zip(cells,loads) if n==max(loads)),
                         formula_sums={c:sum(field[p] for p in formula_positions(tim,c)) for c in 'DCNH'},
                         interpretation='cell with the greatest load; ties are ties; not a subtype',
                         source_caveat='2+1 formulas via UMA section 15, not independently checked against Gulenko'))
    return rows
