"""Independent reconstruction for namespaced agenda populations.

This module imports no scheduler, selector, executor or fixture builder.  Native
selection semantics are delegated to the existing independent selection audit.
"""
import re
from hashlib import sha256

from . import codec
from .records import ObjectId, ObjectRef, Account
from .material import attrs
from .selection_records import loads
from .workflow_selection_audit import audit as native_audit
from .workflow_reference import decode
from .crux_audit import _access


def address(namespace, *parts):
    value = sha256(codec.canonical([codec.encode(x) for x in parts]).encode()).hexdigest()
    return ObjectRef(ObjectId(namespace, value), 1)


def _turn_of(key, namespace):
    patterns = (
        r'^u4:sustain-turn:(\d+):agenda:' + re.escape(namespace) + r':',
        r'^u4:agenda2:' + re.escape(namespace) + r':turn:(\d+):',
    )
    for pattern in patterns:
        match = re.match(pattern, key)
        if match:
            return int(match[1])
    return None


def _validate_goals(state):
    if (type(state['quantum']) is not int or state['quantum'] < 1
            or not 1 <= len(state['goals']) <= 8
            or not 0 <= state['stage'] <= len(state['goals'])):
        raise ValueError('invalid finite namespaced agenda bounds')
    if type(state['namespace']) is not str or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', state['namespace']):
        raise ValueError('invalid agenda namespace')
    for i, goal in enumerate(state['goals']):
        if (set(goal) != {'need', 'sources', 'companion', 'own_stance', 'peer_stance'}
                or goal['companion'] not in ('none', 'exchange', 'votes')
                or not 1 <= len(goal['sources']) <= 8):
            raise ValueError('invalid supplied namespaced goal')
        for slot in goal['sources']:
            if (set(slot) not in ({'initial'}, {'result'}) or ('result' in slot
                    and (type(slot['result']) is not int or not 0 <= slot['result'] < i))):
                raise ValueError('invalid prior-result slot')


def audit_namespaced_agenda(transactions, access, state):
    _validate_goals(state)
    namespace = state['namespace']
    native = native_audit(transactions, access)
    versions = {}
    heads = {}
    charges = {}
    agenda_turns = []
    for tx in transactions:
        turn = _turn_of(tx.key, namespace)
        if turn is not None and turn not in agenda_turns:
            agenda_turns.append(turn)
        for version in tx.versions:
            value = attrs(version)
            if turn is not None and value.get('record_type') == 'wallet':
                old = attrs(versions[version.previous])
                key = (turn, value['actor'])
                delta = tuple(old[k] - value[k] for k in ('energy', 'time'))
                if any(n < 0 for n in delta):
                    raise ValueError('agenda replenishment')
                charges[key] = tuple(a + b for a, b in zip(charges.get(key, (0, 0)), delta))
            versions[version.ref] = version
            heads[version.ref.identity] = version
    if len(state['events']) != state['steps']:
        raise ValueError('agenda step count differs')
    total = 0
    for index, row in enumerate(state['events']):
        if row['step'] != index or row['stage_before'] > row['stage_after']:
            raise ValueError('agenda event order differs')
        if not row['key'].startswith('agenda:' + namespace + ':'):
            raise ValueError('agenda event escaped namespace')
        charged_actor = None
        for actor, energy, time in row['charged']:
            turn = agenda_turns[index] if index < len(agenda_turns) else None
            if (energy, time) != charges.pop((turn, actor), (0, 0)):
                raise ValueError('agenda charge differs from committed wallet')
            if energy or time:
                charged_actor = actor
            total += energy
        if charged_actor is not None and charged_actor != row['actor']:
            raise ValueError('agenda charge payer differs')
    if charges:
        raise ValueError('unreported agenda charges')
    template = state['template']
    actor = template['actor']
    actual_results = []
    for index, goal in enumerate(state['goals']):
        key = 'agenda:' + namespace + ':' + template['key'] + ':' + str(index)
        snapshot = address('c7ws.snapshot', actor, key)
        if snapshot not in versions:
            break
        source_refs = []
        for slot in goal['sources']:
            if 'initial' in slot:
                source_refs.append(slot['initial'])
            elif slot['result'] < len(actual_results):
                source_refs.append(actual_results[slot['result']])
            else:
                raise ValueError('selection preceded generated source')
        inputs = tuple(source_refs)
        if goal['companion'] == 'exchange':
            inputs = (source_refs[0], address('c7w.message', actor, key + ':offer'),
                      address('c7w.message', template['peer'], key + ':reply'))
        elif goal['companion'] == 'votes':
            inputs = (source_refs[0], address('c7w.message', actor, key + ':own-vote'),
                      address('c7w.message', template['peer'], key + ':peer-vote'))
        expected = dict(template, key=key, demand=goal['need'], accessible=inputs)
        request = loads(attrs(versions[snapshot])['payload'])['request']
        if request != expected:
            raise ValueError('agenda input or supplied need differs')
        child_id = address('u4.operation', actor, key + ':movement').identity
        child = attrs(heads[child_id]) if child_id in heads else None
        if not child or child['status'] != 'succeeded':
            break
        result = child.get('public.0') or child.get('binding')
        if result is None:
            observations = [v for v in versions.values() if v.ref.identity.namespace == 'u4.observation'
                            and v.facet(Account).sources == (child['result'],)]
            if len(observations) != 1:
                raise ValueError('exact material observation missing')
            result = observations[0].ref
        actual_results.append(result)
    if state['stage'] != len(state['results']) or state['results'] != actual_results[:state['stage']]:
        raise ValueError('agenda retained result provenance differs')
    if state['pending_result'] is not None and (state['stage'] >= len(actual_results)
            or state['pending_result'] != actual_results[state['stage']]):
        raise ValueError('agenda pending result differs')
    times = {v.ref: tx.at.tick for tx in transactions for v in tx.versions}
    details, bindings = _access(access, versions, times)
    for result in state['results']:
        if result.identity.namespace == 'c7w.output':
            if result not in bindings or bindings[result][0].actor != actor:
                raise ValueError('unpaid owned agenda result')
        else:
            read = {p.address.key for (owner, _), (p, _) in details.items()
                    if owner == actor and p.source == result}
            required = ({'payload'} if result.identity.namespace == 'c7w.message' else
                        {'event', 'outcome', 'context', 'primitive', 'actor', 'workflow_tick',
                         'condition', 'wear', 'custodian'})
            if not required <= read:
                raise ValueError('agenda result advanced before paid reading')
    _validate_pending(state, versions)
    return dict(passed=True, namespace=namespace, completed_goals=state['stage'],
                modeled_energy=total, main_selections=native['workflow_selections'], native=native)


def _validate_pending(state, versions):
    actions = list(state['queue']) + ([] if state['active'] is None else [state['active']])
    if not actions:
        return
    if state['stage'] >= len(state['goals']):
        raise ValueError('commands beyond agenda horizon')
    goal = state['goals'][state['stage']]
    template = state['template']
    actor = template['actor']
    peer = template['peer']
    key = 'agenda:' + state['namespace'] + ':' + template['key'] + ':' + str(state['stage'])
    sources = tuple(slot['initial'] if 'initial' in slot else state['results'][slot['result']]
                    for slot in goal['sources'])
    offer = address('c7w.message', actor, key + ':offer')
    reply = address('c7w.message', peer, key + ':reply') if peer else None
    votes = ((address('c7w.message', actor, key + ':own-vote'),
              address('c7w.message', peer, key + ':peer-vote')) if peer else ())
    inputs = ((sources[0], offer, reply) if goal['companion'] == 'exchange' else
              (sources[0], *votes) if goal['companion'] == 'votes' else sources)
    for action in actions:
        kind = action['kind']
        suffix = action['key'][len(key):]
        if not action['key'].startswith(key) or action['actor'] not in (actor, peer):
            raise ValueError('pending command leaves supplied goal')
        if kind == 'main':
            expected = dict(kind='main', key=key, actor=actor, inputs=inputs, need=goal['need'])
        elif kind == 'aux':
            if suffix == ':offer' and goal['companion'] == 'exchange':
                version = versions[sources[0]]
                if sources[0].identity.namespace == 'u4.observation':
                    source_kind = 'activity'
                elif sources[0].identity.namespace == 'c7w.message':
                    source_kind = decode(attrs(version)['payload'])['kind']
                else:
                    source_kind = decode(version.facet(Account).content[0].object)['kind']
                domain = {'intention': 'personal', 'personal': 'personal', 'activity': 'activity',
                          'shared': 'shared', 'system': 'system', 'rule': 'system'}[source_kind]
                expected = dict(kind='aux', key=key + suffix, actor=actor,
                                recipe='workflow-offer-' + domain + '-v1',
                                inputs=(sources[0], goal['own_stance']))
            elif suffix == ':reply' and goal['companion'] == 'exchange':
                expected = dict(kind='aux', key=key + suffix, actor=peer,
                                recipe='workflow-reply-v1', inputs=(offer, goal['peer_stance']))
            elif suffix in (':own-vote', ':peer-vote') and goal['companion'] == 'votes':
                own = suffix == ':own-vote'
                expected = dict(kind='aux', key=key + suffix, actor=actor if own else peer,
                                recipe='workflow-vote-v1',
                                inputs=(sources[0], goal['own_stance' if own else 'peer_stance']))
            else:
                raise ValueError('unsupported pending auxiliary')
        elif kind == 'public':
            choices = ({':own-offer-read': (actor, offer), ':peer-offer-read': (peer, offer),
                        ':reply-read': (actor, reply)} if goal['companion'] == 'exchange' else {})
            if goal['companion'] == 'votes':
                choices = {':peer-draft-read': (peer, sources[0]), ':own-vote-read': (actor, votes[0]),
                           ':peer-vote-read': (actor, votes[1])}
            if state['pending_result'] is not None:
                choices[':result-read'] = (actor, state['pending_result'])
            if suffix not in choices:
                raise ValueError('unsupported pending public read')
            expected_actor, ref = choices[suffix]
            expected = dict(kind='public', key=key + suffix, actor=expected_actor, ref=ref)
        elif kind == 'event':
            if suffix != ':result-read' or state['pending_result'] is None:
                raise ValueError('unscoped pending event read')
            if address('u4.observation', action['delivery'], actor) != state['pending_result']:
                raise ValueError('pending event delivery differs')
            expected = dict(kind='event', key=key + suffix, actor=actor, delivery=action['delivery'])
        else:
            raise ValueError('unknown pending command kind')
        if action != expected:
            raise ValueError('pending command differs from supplied goal')


def audit_agenda_population(transactions, access, state):
    if state.get('schema') != 'hle-c7-fair-workflow-agenda-population-v1':
        raise ValueError('unsupported fair agenda population schema')
    agendas = state['agendas']
    if (not agendas or len({a['namespace'] for a in agendas}) != len(agendas)
            or type(state['max_turns']) is not int or state['max_turns'] < 1
            or state['turn'] != len(state['events']) or state['turn'] > state['max_turns']):
        raise ValueError('invalid fair agenda population bounds')
    reports = [audit_namespaced_agenda(transactions, access, agenda) for agenda in agendas]
    versions = {}
    charges = {}
    for tx in transactions:
        match = re.match(r'^u4:sustain-turn:(\d+):agenda:([a-z0-9-]+):', tx.key)
        turn = int(match[1]) if match else None
        for version in tx.versions:
            value = attrs(version)
            if turn is not None and value.get('record_type') == 'wallet':
                old = attrs(versions[version.previous])
                key = (turn, value['actor'])
                delta = tuple(old[k] - value[k] for k in ('energy', 'time'))
                if any(n < 0 for n in delta):
                    raise ValueError('population replenishment')
                charges[key] = tuple(a + b for a, b in zip(charges.get(key, (0, 0)), delta))
            versions[version.ref] = version
    actors = state['actors']
    if not actors or len(state['agenda_cursors']) != len(actors):
        raise ValueError('invalid fair actor registry')
    actor_cursor = 0
    agenda_cursors = [0] * len(actors)
    agenda_steps = [0] * len(agendas)
    total = 0
    peer_turns = 0
    for number, row in enumerate(state['events']):
        if row['turn'] != number or row['agenda_index'] >= len(agendas):
            raise ValueError('population turn order differs')
        runnable = list(row['runnable'])
        if not runnable or any(i >= len(agendas) or actor not in actors for i, actor in runnable):
            raise ValueError('invalid runnable owner set')
        actor_index = next((actor_cursor + i) % len(actors) for i in range(len(actors))
                           if any(actor == actors[(actor_cursor + i) % len(actors)] for _, actor in runnable))
        actor = actors[actor_index]
        candidates = [i for i, a in runnable if a == actor]
        cursor = agenda_cursors[actor_index]
        agenda_index = next((cursor + i) % len(agendas) for i in range(len(agendas))
                            if (cursor + i) % len(agendas) in candidates)
        if (row['actor'], row['agenda_index'], row['agenda']) != (
                actor, agenda_index, agendas[agenda_index]['namespace']):
            raise ValueError('fair payer or agenda choice differs')
        local = agenda_steps[agenda_index]
        if local >= len(agendas[agenda_index]['events']):
            raise ValueError('population invented agenda step')
        detail = agendas[agenda_index]['events'][local]
        if (detail['actor'], detail['action'], detail['key']) != (row['actor'], row['action'], row['key']):
            raise ValueError('population action differs from agenda transition')
        agenda_steps[agenda_index] += 1
        charged = charges.pop((number, actor), (0, 0))
        if charged != row['charged']:
            raise ValueError('population charge differs from committed wallet')
        if any(key[0] == number for key in charges):
            raise ValueError('population turn charged unscheduled actor')
        total += charged[0]
        peer_turns += int(actor != agendas[agenda_index]['template']['actor'])
        actor_cursor = (actor_index + 1) % len(actors)
        agenda_cursors[actor_index] = (agenda_index + 1) % len(agendas)
    if charges:
        raise ValueError('unreported population charges')
    if (agenda_steps != [len(a['events']) for a in agendas]
            or actor_cursor != state['actor_cursor'] or agenda_cursors != state['agenda_cursors']):
        raise ValueError('population continuation counters differ')
    return dict(passed=True, turns=state['turn'], modeled_energy=total, peer_turns=peer_turns,
                completed=tuple(a['stage'] for a in agendas), agendas=reports)
