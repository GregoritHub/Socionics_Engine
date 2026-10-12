"""Independent raw CT §8 audit helpers; never import execution or pricing."""
from hle.model_a import position_of

# Literal prospective CT Table 13, independently of model_g/executor arithmetic.
TIME = (1, 2, 3, 4, 4, 3, 2, 1)
ENERGY = (1, 1, 3, 3, 2, 4, 4, 2)


def data(version):
    return {a.name: a.value for a in version.attributes}


def blocks(d):
    """(start, end, energy or None, element) from committed work records."""
    if 'route_count' not in d:
        return [(0, d['required'], None, None)]
    at = d['recall_units']
    result = [(0, at, None, None)]
    for i in range(d['route_count']):
        prefix = f'route.{i}.'
        paths = sorted((int(k[len(prefix+'path.'):]), v) for k, v in d.items()
                       if k.startswith(prefix+'path.'))
        if [n for n, _ in paths] != list(range(len(paths))):
            raise ValueError('noncontiguous raw path')
        for n, element in paths[1:]:
            seat = position_of(d['tim'], element) - 1
            duration = TIME[seat]
            if d[prefix+'charges.'+str(n-1)] != duration:
                raise ValueError('raw hop time differs from CT table')
            result.append((at, at+duration, ENERGY[seat], element))
            at += duration
        element = d[prefix+'element']
        seat = position_of(d['tim'], element)-1
        duration = d[prefix+'content_units']
        if type(duration) is not int or duration < TIME[seat] or duration % TIME[seat]:
            raise ValueError('raw seat-content extent differs')
        result.append((at, at+duration, ENERGY[seat]*(duration//TIME[seat]), element))
        at += duration
    if at > d['required']:
        raise ValueError('raw route work exceeds job')
    result.append((at, d['required'], None, None))
    return result


def cumulative_energy(d, completed):
    total = 0
    for start, end, energy, _ in blocks(d):
        if completed <= start:
            break
        total += min(completed, end)-start if energy is None else energy
    return total


def debit(d, previous):
    """Once-only energy difference; source shape cannot change mid-job."""
    before = previous.get('completed', 0)
    if previous:
        for key in set(previous) | set(d):
            if key.startswith('route.') or key in ('tim','route_count','required','recall_units'):
                if previous.get(key) != d.get(key):
                    raise ValueError('changed raw accounting contract within job')
    return cumulative_energy(d, d['completed']) - cumulative_energy(d, before)


def resource_model(transactions):
    models = set()
    for tx in transactions:
        for version in tx.versions:
            d = data(version)
            if d.get('record_type') == 'wallet':
                model = d.get('resource_model', 'legacy-r4')
                if model not in ('legacy-r4','grade-v1') or ('resource_model' in d and model != 'grade-v1'):
                    raise ValueError('invalid raw resource model')
                models.add(model)
    if len(models) > 1:
        raise ValueError('resource model switched or mixed')
    return next(iter(models), 'legacy-r4')


def validate_profiles(transactions):
    profiles = {}
    for tx in transactions:
        for v in tx.versions:
            d = data(v)
            if v.ref.identity.namespace == 'u5.profile':
                if v.ref.revision != 1 or d['actor'] in profiles:
                    raise ValueError('mutable raw type profile')
                profiles[d['actor']] = d['tim']
            if d.get('record_type') == 'operation' and 'route_count' in d:
                if profiles.get(d['actor']) != d['tim']:
                    raise ValueError('job type differs from committed profile')


def cannot_pay(d, wallet):
    """Independent next-unit admission predicate, for raw stop audits."""
    if d and d['completed'] == d['required']:
        return False
    if wallet['time'] == 0:
        return True
    if not d:
        return wallet['energy'] == 0
    next_cost = cumulative_energy(d, d['completed']+1)-cumulative_energy(d, d['completed'])
    return wallet['energy'] < next_cost


def validate_agenda_exhaustion(transactions, state):
    if state.get('halted') != 'exhausted' or resource_model(transactions) != 'grade-v1':
        return
    heads = {v.ref.identity: v for tx in transactions for v in tx.versions}
    action = state.get('active')
    if action is None:
        raise ValueError('exhausted agenda lacks active work')
    actor, key = action['actor'], action['key']
    jobs = {data(v).get('key'): data(v) for v in heads.values()
            if data(v).get('record_type') == 'operation' and data(v).get('actor') == actor}
    d = jobs.get(key)
    if action['kind'] == 'main' and d and d['status'] == 'succeeded':
        d = jobs.get(key+':movement')
    wallets = [data(v) for v in heads.values() if data(v).get('record_type') == 'wallet'
               and data(v).get('actor') == actor]
    if d is None or len(wallets) != 1 or not cannot_pay(d, wallets[0]):
        raise ValueError('false experimental agenda exhaustion')
