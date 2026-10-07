import unittest

from hle_unified.workflow_composition_audit import audit_pair
from tests_workflow_composition.fixtures import FAMILIES, pair


class WorkflowCompositionTests(unittest.TestCase):
    def check_family(self, family):
        witness, ablation, good, cut = pair(family)
        report = audit_pair(witness.world.journal(), witness.access.checkpoint(),
                            ablation.world.journal(), ablation.access.checkpoint(), family)
        self.assertTrue(report["passed"])
        self.assertNotEqual(good["answer"], cut["answer"])
        self.assertEqual(report["exact_generated_handoffs"], len(report["steps"]) - 1)

    def test_theorize_apply_embody(self):
        self.check_family(FAMILIES[0])

    def test_share_commune_identify(self):
        self.check_family(FAMILIES[1])

    def test_coordinate_mobilize(self):
        self.check_family(FAMILIES[2])

    def test_institutionalize_educate(self):
        self.check_family(FAMILIES[3])

    def test_organize_integrate_apply(self):
        self.check_family(FAMILIES[4])

    def test_equal_endpoint_and_unchanged_answer_controls_are_rejected(self):
        witness, _, _, _ = pair(FAMILIES[0])
        with self.assertRaisesRegex(ValueError, "ablation passed ordinary workflow audit"):
            audit_pair(witness.world.journal(), witness.access.checkpoint(),
                       witness.world.journal(), witness.access.checkpoint(), FAMILIES[0])


if __name__ == "__main__":
    unittest.main()
