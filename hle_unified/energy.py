"""Opt-in CT §8 integer energy accounting; no route or selection policy."""
from dataclasses import replace
from hle.model_a import position_of, fields
from .model_g import grade
from .material import OperationStore, attrs, attributes

MODELS = ('legacy-r4', 'grade-v1')


def initial_world(world, resource_model):
    """Build a fresh initial world with versioned wallet identity, before work.

    Keep transaction count/order unchanged so model metadata cannot shift clocks.
    No existing store or historical checkpoint is mutated.
    """
    if resource_model not in MODELS:
        raise ValueError('unknown resource model')
    transactions = world.journal()
    for tx in transactions:
        for v in tx.versions:
            d = attrs(v)
            if d.get('record_type') == 'operation' or 'resource_model' in d:
                raise ValueError('resource model requires a fresh unpriced world')
    if resource_model == 'legacy-r4':
        return world
    result = OperationStore()
    wallets = 0
    for tx in transactions:
        versions = []
        for v in tx.versions:
            d = attrs(v)
            if d.get('record_type') == 'wallet':
                if v.ref.revision != 1 or d['energy'] != d['initial_energy'] or d['time'] != d['initial_time']:
                    raise ValueError('cannot reprice an existing wallet')
                d['resource_model'] = resource_model
                v = replace(v, attributes=attributes(d))
                wallets += 1
            versions.append(v)
        result.commit(tx.key, tx.writer, tuple(versions), tx.lineage, actor=tx.actor)
    if not wallets:
        raise ValueError('experimental world requires initial finite wallets')
    return result


def stages(data):
    """Yield (time, energy) stages; non-Model-A work is paid per quantum."""
    if 'route_count' not in data:
        yield data['required'], None
        return
    yield data['recall_units'], None
    total = data['recall_units']
    for i in range(data['route_count']):
        p = f'route.{i}.'
        j = 0
        while p + 'charges.' + str(j) in data:
            element = data[p + 'path.' + str(j + 1)]
            position = position_of(data['tim'], element)
            duration = 5 - fields(position)['dimensionality']
            yield duration, 4 - grade(position)
            total += duration
            j += 1
        position = position_of(data['tim'], data[p + 'element'])
        unit = 5 - fields(position)['dimensionality']
        duration = data[p + 'content_units']
        if type(duration) is not int or duration < unit or duration % unit:
            raise ValueError('invalid integer seat content size')
        yield duration, (4 - grade(position)) * (duration // unit)
        total += duration
    tail = data['required'] - total
    if tail < 0:
        raise ValueError('route exceeds required work')
    yield tail, None


def payment(data, wallet, work_limit):
    """Largest affordable sequential time prefix, debiting admission once."""
    limit = min(work_limit, data['required'] - data['completed'], wallet['time'])
    left_energy = wallet['energy']
    done = data['completed']
    paid = charged = start = 0
    for duration, energy in stages(data):
        end = start + duration
        if done >= end:
            start = end
            continue
        if paid >= limit:
            break
        available = min(end - max(done, start), limit - paid)
        if energy is None:
            take = min(available, left_energy)
            debit = take
        else:
            debit = energy if done <= start else 0
            if left_energy < debit:
                break
            take = available
        paid += take
        charged += debit
        left_energy -= debit
        if take < available:
            break
        start = end
    return paid, charged
