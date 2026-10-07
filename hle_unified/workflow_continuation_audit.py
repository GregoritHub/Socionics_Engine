"""Reconstruct continuation provenance without scheduler/selector/executor imports."""
from .material import attrs
from .selection_records import loads
from .population_audit import audit_population
from hashlib import sha256
from . import codec
from .records import ObjectId, ObjectRef

def address(namespace, *parts):
    encoded = codec.canonical([codec.encode(x) for x in parts]).encode()
    return ObjectRef(ObjectId(namespace, sha256(encoded).hexdigest()), 1)


def audit_continuation(transactions, state):
    if (set(state) != {'schema', 'policy', 'population', 'input_history', 'pending_results'}
            or state['schema'] != 'hle-c7-workflow-continuation-v1'
            or state['policy'] != 'latest-successful-owned-result-v1'):
        raise ValueError('unknown continuation contract')
    p = state['population']
    if p['schema'] != 'hle-c7-workflow-population-v3':
        raise ValueError('workflow population required')
    requests = [r['fields'] for r in p['requests']]
    if any(r['request_type'] not in ('WorkflowSelectionRequest', 'WorkflowCapacitySelectionRequest')
           for r in p['requests']):
        raise ValueError('workflow requests only')
    history = [[r['accessible']] for r in requests]
    pending = [None] * len(requests)
    versions = {v.ref: v for tx in transactions for v in tx.versions}
    heads = {v.ref.identity: v for tx in transactions for v in tx.versions}
    snapshots = {ref: loads(attrs(v)['payload']) for ref, v in versions.items()
                 if ref.identity.namespace == 'c7ws.snapshot'}
    actors = [r['actor'] for r in requests]
    links = 0
    for row in p['events']:
        i = actors.index(row['actor']); r = requests[i]; episode = row['episode']
        expected = dict(r, key='c7:' + r['key'] + ':' + str(episode), accessible=history[i][episode])
        if row['key'] != expected['key']:
            raise ValueError('continuation episode key differs')
        ref = address('c7ws.snapshot', r['actor'], row['key'])
        if ref in snapshots and snapshots[ref]['request'] != expected:
            raise ValueError('continuation input provenance differs')
        if row['status'] == 'episode_complete':
            ident = address('u4.operation', r['actor'], row['key'] + ':movement').identity
            child = attrs(heads[ident]) if ident in heads else None
            material = bool(child and child.get('result') and child.get('primitive') in
                            ('inspect', 'consume', 'use', 'repair', 'care', 'damage'))
            result = None
            if child and child['status'] == 'succeeded':
                if material:
                    result = address('u4.observation', 'c7-turn:' + str(row['turn'] - 1) + ':own-event', r['actor'])
                elif child.get('binding'):
                    result = child['binding']
            pending[i] = result
            if not material:
                history[i].append(history[i][-1] if result is None else (result,))
                links += int(result is not None)
                pending[i] = None
        elif row['status'] in ('feedback_succeeded', 'feedback_failed', 'feedback_cancelled'):
            feedback_id = address('u4.operation', r['actor'], row['key'] + ':feedback').identity
            feedback = attrs(heads[feedback_id]) if feedback_id in heads else {}
            if ('feedback_' + feedback.get('status', 'missing') != row['status']
                    or feedback.get('primitive') != 'read'):
                raise ValueError('feedback completion differs from paid read')
            result = pending[i] if row['status'] == 'feedback_succeeded' else None
            if result is not None and result not in versions:
                raise ValueError('missing generated observation')
            history[i].append(history[i][-1] if result is None else (result,))
            links += int(result is not None)
            pending[i] = None
    if history != state['input_history'] or pending != state['pending_results']:
        raise ValueError('continuation history differs from committed results')
    if any(len(h) != c + 1 for h, c in zip(history, p['counts'])):
        raise ValueError('continuation horizon differs')
    return dict(audit_population(transactions, p), retained_handoffs=links,
                policy='latest-successful-owned-result-v1')
