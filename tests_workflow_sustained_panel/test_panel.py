import copy
import unittest

from hle_unified.material import attrs
from hle_unified.operations import address
from hle_unified.selection_records import loads, dumps
from hle_unified.workflow_agenda_population import FairWorkflowAgendaPopulation
from hle_unified.workflow_agenda_population_audit import audit_agenda_population
from tests_workflow_sustained_panel.fixtures import *


class SustainedPanelTests(unittest.TestCase):
    def test_all_32_declared_cells_have_generated_consumer_and_consequence(self):
        seen = set()
        for cell in range(32):
            population, row = sustained_cell(cell)
            result = population.run()
            self.assertTrue(result['done'], row)
            agenda = population.agendas[0]
            self.assertEqual((agenda.stage, agenda.halted, len(agenda.results)), (2, None, 2), row)
            target_key = 'agenda:cell-' + str(cell) + ':auto:0'
            consumer_key = 'agenda:cell-' + str(cell) + ':auto:1'
            actor = agenda.template['actor']
            target = attrs(population.engine.world.resolve(address('c7ws.decision', actor, target_key)))
            consumer = attrs(population.engine.world.resolve(address('c7ws.decision', actor, consumer_key)))
            self.assertEqual(target['recipe'], row['target_recipe'])
            self.assertEqual(consumer['recipe'], 'workflow-' + row['expected_consumer'].lower() + '-accumulation-v1')
            template = WorkflowSelectionRequest(**agenda.template)
            output = semantic_value(population.engine, template, agenda.results[0])
            inputs = [semantic_value(population.engine, template, ref) for ref in row['initial']]
            self.assertNotIn(output, inputs, row)
            self.assertIsNotNone(terminal_consequence(population), row)
            report = audit_agenda_population(population.engine.world.journal(),
                                              population.engine.access.checkpoint(),
                                              loads(population.checkpoint()))
            self.assertTrue(report['passed'])
            seen.add((row['name'], row['face'], row['owner_type']))
        self.assertEqual(len(seen), 32)

    def test_32_matched_controls_preserve_exact_target_and_cost(self):
        for cell in range(32):
            witness, row = sustained_cell(cell)
            witness.run()
            control, _ = sustained_cell(cell)
            run_withheld(control)
            wa = witness.agendas[0]
            ca = control.agendas[0]
            key = 'agenda:cell-' + str(cell) + ':auto:0:movement'
            actor = wa.template['actor']
            wjob = witness.engine.job_status(actor, key)
            cjob = control.engine.job_status(actor, key)
            self.assertEqual((wjob['status'], wjob['spent']), (cjob['status'], cjob['spent']), row)
            self.assertEqual(wa.results[0], ca.pending_result, row)
            self.assertEqual(ca.stage, 0)
            self.assertFalse(any(x['key'].endswith(':auto:1') for x in ca.main_rows))
            self.assertTrue(audit_agenda_population(control.engine.world.journal(),
                control.engine.access.checkpoint(), loads(control.checkpoint()))['passed'])

    def test_public_result_is_hidden_until_paid_read(self):
        control, _ = sustained_cell(28)
        run_withheld(control)
        agenda = control.agendas[0]
        template = WorkflowSelectionRequest(**agenda.template)
        with self.assertRaises(ValueError):
            control.engine._read_workflow(control.engine.participant_view(template.actor),
                                          agenda.pending_result, template)
        witness, _ = sustained_cell(28)
        witness.run()
        self.assertEqual(semantic_value(witness.engine, WorkflowSelectionRequest(**witness.agendas[0].template),
                                        witness.agendas[0].results[0])['kind'], 'rule')

    def test_interrupted_restore_is_exact(self):
        uninterrupted, _ = sustained_cell(29)
        uninterrupted.run()
        interrupted, _ = sustained_cell(29)
        interrupted.run(13)
        restored = FairWorkflowAgendaPopulation.restore(interrupted.checkpoint())
        restored.run()
        self.assertEqual(restored.checkpoint(), uninterrupted.checkpoint())

    def test_actual_payer_fairness_includes_peer_vote_and_reply(self):
        population = fair_social_pair()
        self.assertTrue(population.run()['done'])
        actors = {row['actor'].key for row in population.events}
        self.assertEqual(actors, {'alice', 'bob'})
        peer = [row for row in population.events
                if row['actor'] != population.agendas[row['agenda_index']].template['actor']]
        self.assertTrue(any('vote' in row['key'] for row in peer))
        self.assertTrue(any('reply' in row['key'] for row in peer))
        report = audit_agenda_population(population.engine.world.journal(),
            population.engine.access.checkpoint(), loads(population.checkpoint()))
        self.assertGreater(report['peer_turns'], 0)

    def test_finite_turn_pending_and_tamper_rejection(self):
        population, _ = sustained_cell(0)
        population.max_turns = 1
        result = population.run()
        self.assertFalse(result['done'])
        state = loads(population.checkpoint())
        self.assertTrue(audit_agenda_population(population.engine.world.journal(),
            population.engine.access.checkpoint(), state)['passed'])
        forged = copy.deepcopy(state)
        forged['events'][0]['charged'] = (1, 1)
        with self.assertRaises(ValueError):
            audit_agenda_population(population.engine.world.journal(),
                                    population.engine.access.checkpoint(), forged)

    def test_namespace_and_goal_tampering_rejected(self):
        population, _ = sustained_cell(0)
        population.run()
        state = loads(population.checkpoint())
        forged = copy.deepcopy(state)
        forged['events'][0]['agenda'] = 'other'
        with self.assertRaises(ValueError):
            audit_agenda_population(population.engine.world.journal(),
                                    population.engine.access.checkpoint(), forged)
        forged = copy.deepcopy(state)
        forged['agendas'][0]['goals'][1]['sources'] = [{'initial': forged['agendas'][0]['results'][0]}]
        with self.assertRaises(ValueError):
            audit_agenda_population(population.engine.world.journal(),
                                    population.engine.access.checkpoint(), forged)


if __name__ == '__main__':
    unittest.main()
