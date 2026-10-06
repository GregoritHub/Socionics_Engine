import itertools
import unittest
from tests_u9.fixtures import *
from hle_unified import composition_language as language
from hle_unified.composition_audit import audit


class ConstructiveTests(unittest.TestCase):
    def test_constructs_absent_complete_answer_and_executes(self):
        e,cap=trained9()
        self.assertEqual(cap["program"],("seq",(("act","repair"),("act","use"),("act","care"))))
        self.assertEqual(e.world.head(ref("train").identity).facet(Material).condition,"serviceable")
        self.assertEqual(attrs(e.world.head(ref("train").identity))["wear"],0)
        self.assertEqual(attrs(e.world.head(ref("train-repair").identity))["consumed"],1)
        self.assertEqual(attrs(e.world.head(ref("train-care").identity))["consumed"],1)
        self.assertIn(Role.PROCEDURE,e.world.resolve(cap["ref"]).roles)
        self.assertIn(Role.CONCEPT,e.world.resolve(cap["ref"]).roles)

    def test_transfer_excluded_from_training(self):
        e,cap=trained9()
        self.assertFalse(any(p.subject.identity==ref("transfer").identity for p in e.participant_view(ALICE).snapshot.particulars))
        d=notice9(e,"transfer");r=run9(e,d,cap,prefix="transfer")
        self.assertEqual(r["status"],"succeeded")
        self.assertEqual(cap["ref"],r["program"])

    def test_failed_generalization_generates_and_revises(self):
        e,d=revised9()
        self.assertEqual(d["failed"]["status"],"failed")
        self.assertEqual({x["reason"] for x in d["repair_demands"]},{"persistent_consequence","failed_generalization"})
        self.assertEqual(d["revised"]["ref"].revision,2)
        self.assertEqual(d["revised"]["split"],("eq",("field","target","max_wear"),1))
        self.assertEqual(e.world.resolve(d["capacity"]["ref"]).ref,d["capacity"]["ref"])
        self.assertEqual(e.world.head(ref("counter").identity).facet(Material).condition,"damaged")

    def test_conditional_preserves_successful_old_branch(self):
        e,d=revised9();demand=notice9(e,"old-return")
        run=run9(e,demand,d["revised"],prefix="old-return")
        self.assertEqual(run["status"],"succeeded")
        self.assertEqual(run["trace"],("repair","use","care"))

    def test_conditional_new_branch_works_on_later_return(self):
        e,d=revised9();demand=notice9(e,"counter",prefix="again-")
        run=run9(e,demand,d["revised"],prefix="again")
        self.assertEqual(run["trace"],("repair","use","repair"))
        self.assertEqual(run["status"],"succeeded")

    def test_persistent_consequence_requires_actual_repair(self):
        e,d=revised9()
        demand=next(x for x in d["repair_demands"] if x["reason"]=="persistent_consequence")
        candidate=find9(e,demand,prefix="consequence-search")
        run=run9(e,demand,candidate,prefix="consequence")
        self.assertEqual(run["status"],"succeeded")
        self.assertEqual(thaw(run["initial"])["progress"]["uses"],1)
        self.assertEqual(thaw(run["state"])["progress"]["uses"],1+run["trace"].count("use"))
        self.assertEqual(e.world.head(ref("counter").identity).facet(Material).condition,"serviceable")

    def test_search_reuses_existing_capacity_first(self):
        e,cap=trained9();d=notice9(e,"transfer")
        candidate=find9(e,d,prefix="reuse")
        self.assertEqual(candidate["program"],("seq",(("call",cap["ref"]),)))
        self.assertEqual(candidate["dependencies"][0],cap["ref"])

    def test_existing_capacity_can_be_extended(self):
        e,cap=trained9();goal=(("ge",("field","progress","uses"),2),*GOAL[1:])
        d=notice9(e,"deep",goal=goal)
        candidate=find9(e,d,prefix="extend")
        self.assertIn(cap["ref"],language.dependencies(candidate["program"]))
        run=run9(e,d,candidate,prefix="extend-run")
        self.assertEqual(run["status"],"succeeded")
        self.assertEqual(thaw(run["state"])["progress"]["uses"],2)

    def test_participant_constructs_ordered_alternatives(self):
        e,cap=trained9();d=notice9(e,"ready-train")
        c=find9(e,d,prefix="ready-search");r=run9(e,d,c,prefix="ready-run")
        other=do9(e,"retain-ready","retain",focus=r["ref"])[0]
        d=notice9(e,"ready-return");c=find9(e,d,prefix="alternative-search")
        self.assertEqual(c["program"],("seq",(("choice",(("call",cap["ref"]),("call",other["ref"]))),)))
        self.assertEqual(run9(e,d,c,prefix="alternative-run")["status"],"succeeded")

    def test_funded_search_extends_beyond_previous_depth(self):
        e=setup9();goal=(("ge",("field","progress","uses"),3),*GOAL[1:]);d=notice9(e,"deep",goal=goal)
        stopped=find9(e,d,depth=2,prefix="shallow")
        self.assertEqual(stopped["status"],"repertoire_exhausted_at_depth")
        self.assertTrue(stopped["deferred"])
        candidate=find9(e,stopped,depth=8,prefix="deeper",tickets=300)
        self.assertEqual(candidate["kind"],"candidate")
        self.assertEqual(len(candidate["program"][1]),7)
        run=run9(e,d,candidate,prefix="deep-run")
        self.assertEqual(run["status"],"succeeded")
        self.assertEqual(thaw(run["state"])["progress"]["uses"],3)

    def test_minimum_plan_matches_independent_small_enumeration(self):
        # Independent state arithmetic, without importing the participant model.
        def advance(s,op):
            broken,wear,uses=s
            if op=="repair" and broken:return False,0,uses
            if op=="use" and not broken:return wear+1==3,wear+1,uses+1
            if op=="care" and not broken and wear:return False,wear-1,uses
            return None
        solutions=[]
        for length in range(1,4):
            for seq in itertools.product(("care","repair","use"),repeat=length):
                s=(True,3,0)
                for op in seq:
                    s=advance(s,op)
                    if s is None:break
                if s is not None and s[0] is False and s[1]==0 and s[2]>=1:solutions.append(seq)
        e=setup9();d=notice9(e);c=find9(e,d)
        self.assertEqual(solutions,[("repair","use","care")])
        self.assertEqual(tuple(p[1] for p in c["program"][1]),solutions[0])

    def test_raw_accounting_and_development_lineage(self):
        e,d=revised9();a=audit(e.world.journal())
        self.assertTrue(a["passed"])
        self.assertEqual(a["conditional_revisions"],1)
        self.assertEqual(a["failed_runs"],1)
        self.assertEqual(a["successful_runs"],3)
        self.assertEqual(a["charged_energy"],a["charged_time"])

    def test_relational_field_comparison_is_grounded(self):
        e=setup9();slots=reveal9(e);s=thaw(snapshot(e.participant_view(ALICE),slots)[0])
        self.assertTrue(language.predicate(("eq",("field","target","owner"),("field","tool","owner")),s))
        self.assertFalse(language.predicate(("ne",("field","target","owner"),("field","target","custodian")),s))

    def test_constructed_procedure_uses_addressable_ownership_relation(self):
        e=setup9();d=loan9(e);c=find9(e,d,prefix="loan-search")
        self.assertEqual(c["program"],("seq",(("act","use"),("act","return"))))
        run=run9(e,d,c,prefix="loan-run")
        self.assertEqual(run["status"],"succeeded")
        self.assertEqual(e.world.head(ref("loan").identity).facet(Material).custodian,BOB)
        self.assertEqual(dict((x.name,x.value) for x in e.world.head(ref("loan-due").identity).facet(Relation).terms)["status"],"fulfilled")
        self.assertTrue(audit(e.world.journal())["passed"])

    def test_later_subprocedure_condition_uses_observed_intermediate_state(self):
        e,d=revised9();goal=(("ge",("field","progress","uses"),2),*GOAL[1:])
        demand=notice9(e,"ready-fragile",goal=goal)
        candidate=find9(e,demand,prefix="conditional-extension")
        self.assertEqual(candidate["program"],("seq",(("act","use"),("call",d["revised"]["ref"]))))
        run=run9(e,demand,candidate,prefix="conditional-extension-run")
        self.assertEqual(run["status"],"succeeded")
        self.assertEqual(run["trace"],("use","repair","use","repair"))
        self.assertTrue(audit(e.world.journal())["passed"])


if __name__=="__main__":unittest.main()
