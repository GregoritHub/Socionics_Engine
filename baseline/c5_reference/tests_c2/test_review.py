"""Additional controls from the C2 audit/dependency review."""
import unittest
from dataclasses import replace
from tests_c2.fixtures import *
from tests_c2.test_self_routes import NAMES,FACES,make
from hle_unified.self_audit import audit
from hle_unified.self_records import SELF_RECIPES
from tests_u11.fixtures import work as collective_work


class ReviewTests(unittest.TestCase):
    def test_transitive_stance_revision_invalidates_old_exchange(self):
        e=setup_c2(); out=cell(e,"Commune","expenditure",prepare_only=True); r=out["request"]
        e.start("begin",r); e.advance("paid",ALICE,r.key,10000)
        stance=data(e,r.inputs[1])["stance"]
        e.declare("retract-stance",(next_version(e.world.resolve(stance),label="Withdrawn stance"),))
        e.commit("finish",ALICE,r.key)
        self.assertEqual(e.job_status(ALICE,r.key)["failure"],"stale_dependency")
        self.assertIsNone(e.job_status(ALICE,r.key)["binding"])
        audit(e.world.journal(),e.access.checkpoint())

    def test_changed_source_system_blocks_later_coupled_dispatch(self):
        e=setup_c2(); out=cell(e,"Integrate","expenditure",consumer=False)
        expose(e,ALICE,SAW)
        decision=consume(e,out["result"],tool=KIT,stock=STOCK)
        e.declare("model-revised",(next_version(e.world.resolve(out["inputs"][0]),label="Revised system"),))
        with self.assertRaisesRegex(ValueError,"dependencies"):
            e.enact("stale-dispatch",ALICE,"cannot",decision)
        self.assertEqual(e.world.head(SAW.identity).ref,SAW)
        audit(e.world.journal(),e.access.checkpoint())

    def test_alternative_attitudes_preserve_content_for_eight_cells(self):
        for name in NAMES:
            for face in FACES:
                with self.subTest(name=name,face=face):
                    e=make(name,face); twin=make(name,face)
                    r=cell(e,name,face,prepare_only=True)["request"]
                    other=cell(twin,name,face,prepare_only=True)["request"]
                    primary=SELF_RECIPES[r.recipe].elements
                    alternative=tuple(x[0]+("e" if x[1]=="i" else "i") for x in primary)
                    first=work(e,r); second=work(twin,replace(other,elements=alternative))
                    if name!="Act": self.assertEqual(data(e,first),data(twin,second))
                    else: self.assertEqual(e.world.head(SAW.identity).facet(Material),twin.world.head(SAW.identity).facet(Material))
                    audit(twin.world.journal(),twin.access.checkpoint())

    def test_node_budget_does_not_silently_drop_work(self):
        e=setup_c2()
        a=seed_data(e,"first",dict(kind="system",nodes=(("repair",("damaged",),("serviceable",),"repair",ALICE),)))
        b=seed_data(e,"second",dict(kind="system",nodes=tuple((str(i),("serviceable",),("used",),"use",ALICE) for i in range(16))))
        before=e.checkpoint()
        with self.assertRaisesRegex(ValueError,"node budget"):
            e.start("too-large",req(e,"too-large","integrate-accumulation-v1",(a,b)))
        self.assertEqual(e.checkpoint(),before)

if __name__=="__main__":unittest.main()
