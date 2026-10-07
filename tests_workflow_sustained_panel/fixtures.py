"""Prospectively frozen FB5.5 cell panel and causal controls."""
from tests_workflow_selection.social_fixtures import social_fixture, ALL_NAMES
from tests_c7_workflow.fixtures import *
from hle_unified.workflow_selection_execution import WorkflowFinalSelectionEngine
from hle_unified.workflow_selection_records import WorkflowSelectionRequest
from hle_unified.workflow_agenda_population import NamespacedWorkflowAgenda, FairWorkflowAgendaPopulation
from hle_unified.workflow_records import WORKFLOW_RECIPES
from hle_unified.selection_records import PERSPECTIVES


FACES = ('accumulation', 'expenditure')
cell_fixture = cell
CONSUMERS = {
    'I': ('Theorize', 'ITS', 'none'),
    'IT': ('Embody', 'I', 'none'),
    'WE': ('Identify', 'I', 'stance'),
    'ITS': ('Apply', 'IT', 'none'),
}


def panel_row(cell):
    if type(cell) is not int or not 0 <= cell < 32:
        raise ValueError('one declared workflow cell required')
    name = ALL_NAMES[cell // 2]
    face = FACES[cell % 2]
    owner_type = 'iee' if cell % 2 == 0 else 'sli'
    consumer = ('Educate', 'WE', 'exchange') if name == 'Institutionalize' else None
    return dict(cell=cell, name=name, face=face, owner_type=owner_type, consumer=consumer)


def _need(engine, key, destination, target):
    return seed(engine, key, wf.encode(dict(kind='workflow_need',
        priorities=tuple(10 if x == destination else 0 for x in PERSPECTIVES),
        externalize=False)), relation='c7ws.need', target=target)


def sustained_cell(cell, budget=200000):
    row = panel_row(cell)
    engine = setup_workflow(row['owner_type'], engine_type=WorkflowFinalSelectionEngine, budget=budget)
    base = cell_fixture(engine, row['name'], row['face'], prepare_only=True)
    native = base['request']
    destination = WORKFLOW_RECIPES[native.recipe].destination
    target_need = seed(engine, 'outcome-need', wf.encode(dict(kind='workflow_need',
        priorities=tuple(10 if x == destination else 0 for x in PERSPECTIVES),
        externalize=row['face'] == 'expenditure')), target=native.target, relation='c7ws.need')
    template = WorkflowSelectionRequest('auto', ALICE, ROOM, CUE5, native.target, target_need,
        native.inputs, stock=native.stock, relation=native.relation, peer=native.peer, group=native.group)
    rows = tasks()
    own = authored(engine, 'panel-own-stance', rows, kind='stance')
    peer = authored(engine, 'panel-peer-stance', rows, actor=BOB, kind='stance')
    consumer = row['consumer'] or CONSUMERS[destination]
    first = dict(need=template.demand, sources=[{'initial': ref} for ref in template.accessible],
                 companion='none', own_stance=own, peer_stance=peer)
    sources = [{'result': 0}]
    if consumer[2] == 'stance':
        sources.append({'initial': own})
    second = dict(need=_need(engine, 'panel-consumer-need', consumer[1], template.target),
                  sources=sources, companion='exchange' if consumer[2] == 'exchange' else 'none',
                  own_stance=own, peer_stance=peer)
    agenda = NamespacedWorkflowAgenda('cell-' + str(cell), engine, template, [first, second], 17)
    population = FairWorkflowAgendaPopulation(engine, [agenda], 500)
    row.update(expected_consumer=consumer[0], target_recipe=base['request'].recipe,
               initial=template.accessible)
    return population, row


def run_withheld(population):
    """Stop after matched producer completion, before result handoff."""
    agenda = population.agendas[0]
    for _ in range(population.max_turns):
        if agenda.pending_result is not None and agenda.active is None:
            break
        if population.step() is None:
            break
    if agenda.pending_result is None or agenda.stage != 0:
        raise AssertionError('producer did not reach withheld handoff boundary')
    return dict(done=False, turns=population.turn, pending_result=agenda.pending_result)


def terminal_consequence(population, key='panel-terminal-query'):
    agenda = population.agendas[0]
    if agenda.stage != 2 or len(agenda.results) != 2:
        return None
    engine = population.engine
    template = WorkflowSelectionRequest(**agenda.template)
    source = agenda.results[-1]
    value, _ = engine._read_workflow(engine.participant_view(template.actor), source, template)
    domain = {'personal': 'personal', 'activity': 'activity', 'shared': 'shared',
              'system': 'system', 'rule': 'system'}[value['kind']]
    kw = {}
    if template.group is not None:
        kw = dict(peer=template.peer, group=template.group)
    result = work(engine, request(engine, key, 'use-' + domain, None, (source,),
        actor=template.actor, target=template.target, **kw))
    return data(engine, result, template.actor)


def semantic_value(engine, template, ref):
    value, _ = engine._read_workflow(engine.participant_view(template.actor), ref, template)
    return value


def fair_social_pair():
    """One social vote/reply agenda plus independent SLI-owned work."""
    first = family('institutionalize-educate')
    engine = first.engine
    social = NamespacedWorkflowAgenda('social', engine,
        WorkflowSelectionRequest(**first.template), first.goals, first.quantum)
    rows = tuple((name, primitive, dependencies, earliest, latest, BOB)
                 for name, primitive, dependencies, earliest, latest, _ in tasks())
    source = authored(engine, 'peer-owned-intention', rows, actor=BOB, hypothetical=True)
    need = seed(engine, 'peer-owned-need', wf.encode(dict(kind='workflow_need',
        priorities=(0, 0, 0, 10), externalize=False)), actor=BOB,
        relation='c7ws.need', target=DEVICE)
    current = engine.world.head(DEVICE.identity).ref
    expose(engine, BOB, current)
    template = WorkflowSelectionRequest('peer', BOB, ROOM, CUE5, current, need, (source,))
    stance = authored(engine, 'peer-placeholder-stance', rows, actor=BOB, kind='stance')
    peer_goal = dict(need=need, sources=[{'initial': source}], companion='none',
                     own_stance=stance, peer_stance=stance)
    independent = NamespacedWorkflowAgenda('peer', engine, template, [peer_goal], 17)
    return FairWorkflowAgendaPopulation(engine, [social, independent], 1000)


# Imported only by this prospective fixture, never by production scheduling.
from tests_workflow_families.fixtures import family
