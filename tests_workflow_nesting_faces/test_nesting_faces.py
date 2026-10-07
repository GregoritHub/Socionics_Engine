import unittest
from dataclasses import replace
from tests_workflow_nesting_faces.fixtures import *
from hle_unified.workflow_nesting_audit import audit_parent, audit_face_pair
from hle_unified.workflow_nesting_records import WorkflowChildEvidence
from hle_unified.material import attrs, attributes


class WorkflowNestingFaceTests(unittest.TestCase):
    def test_four_parent_lifecycle_worlds(self):
        expected = {"normal": ("succeeded", "complete"),
                    "failed-child": ("succeeded", "blocked"),
                    "membership-change": ("failed", None),
                    "participant-withdrawal": ("failed", None)}
        for mode, wanted in expected.items():
            with self.subTest(mode=mode):
                e, out = parent_world(mode); job = e.job_status(ALICE, "parent")
                self.assertEqual(job["status"], wanted[0])
                if job.get("binding"):
                    value = data(e, job["binding"])
                    self.assertEqual(value["status"], wanted[1])
                    self.assertEqual(value["complete"], mode == "normal")
                else:
                    self.assertEqual(job["failure"], "stale_dependency")
                self.assertTrue(audit_parent(e.world.journal(), e.access.checkpoint())["passed"])

    def test_distinct_operation_accounting_and_duplicate_child_rejection(self):
        e, _ = parent_world("normal"); value = data(e, e.job_status(ALICE, "parent")["binding"])
        expected = sum(e.job_status(ALICE, key)["spent"] for key in ("parent-model", "parent-social"))
        self.assertEqual(value["cited_spending"], expected)
        self.assertEqual(len(value["operations"]), 2)
        one = child(e, "parent-model", e.job_status(ALICE, "parent-model")["binding"])
        with self.assertRaisesRegex(ValueError, "distinct child operations"):
            parent_request(e, (one, WorkflowChildEvidence(one.operation, one.output)), key="duplicate")

    def test_parent_summary_grants_no_model_competence_or_authority(self):
        e, _ = parent_world("normal"); parent = e.job_status(ALICE, "parent")["binding"]
        value = data(e, parent)
        self.assertFalse(value["competence"]); self.assertFalse(value["executable"]); self.assertIsNone(value["authority"])
        with self.assertRaisesRegex(ValueError, "workflow child output schema|owned scoped workflow input|typed scoped workflow proposition"):
            e.start("summary-use", request(e, "summary-use", "Theorize", "accumulation", (parent,)))
        audit_parent(e.world.journal(), e.access.checkpoint())

    def test_all_sixteen_matched_route_face_pairs(self):
        reports = []
        for route in PATHS:
            with self.subTest(route=route):
                accumulation, expenditure, _, _ = face_pair(route)
                report = audit_face_pair(accumulation.world.journal(), accumulation.access.checkpoint(),
                    expenditure.world.journal(), expenditure.access.checkpoint(), route)
                self.assertTrue(report["passed"]); reports.append(report)
        self.assertEqual(len(reports), 16)
        self.assertTrue(any(r["converged_final_answer"] for r in reports))
        self.assertTrue(any(not r["converged_final_answer"] for r in reports))

    def test_face_pair_requires_the_same_fresh_start(self):
        accumulation, expenditure, _, _ = face_pair("Express", expenditure_tim="eii")
        with self.assertRaisesRegex(ValueError, "fresh starting world"):
            audit_face_pair(accumulation.world.journal(), accumulation.access.checkpoint(),
                expenditure.world.journal(), expenditure.access.checkpoint(), "Express")

    def test_raw_parent_capacity_mutation_is_rejected(self):
        e, _ = parent_world("normal"); changed = False; transactions = []
        for tx in e.world.journal():
            versions = []
            for version in tx.versions:
                if not changed and version.ref.identity.namespace == "c7n.output":
                    account = version.facet(Account); proposition = account.content[0]
                    value = wf.decode(proposition.object); value["competence"] = True
                    version = replace(version, facets=(replace(account,
                        content=(replace(proposition, object=wf.encode(value)),)),))
                    changed = True
                versions.append(version)
            transactions.append(replace(tx, versions=tuple(versions)))
        self.assertTrue(changed)
        with self.assertRaisesRegex(ValueError, "unjustified workflow parent output|retained binding differs from raw paid content"):
            audit_parent(transactions, e.access.checkpoint())


if __name__ == "__main__": unittest.main()
