import unittest
from dataclasses import FrozenInstanceError, replace
from hle.contracts import *
from hle.crux import *
from .support import *


class BoundaryContracts(unittest.TestCase):
    @rules("E02")
    def test_historical_references_distinguish_versions_kinds_and_people(self):
        self.assertNotEqual(ref(Kind.MEMORY,"x",1),ref(Kind.MEMORY,"x",2))
        self.assertNotEqual(ref(Kind.MEMORY,"x"),ref(Kind.EVENT,"x"))
        self.assertNotEqual(OWNERSHIP,replace(OWNERSHIP,object=BOB))
        self.assertNotEqual(OWNERSHIP,replace(OWNERSHIP,context=ref(Kind.CONTEXT,"elsewhere")))
        self.assertNotEqual(OWNERSHIP,replace(OWNERSHIP,scope=TimeScope(Moment(2,0),None)))
        for args in ((Kind.EVENT,"x",0),(Kind.EVENT,"",1),(Kind.EVENT,"x",True),("event","x",1)):
            with self.assertRaises(ValueError):Ref(*args)

    @rules("E02", "E03")
    def test_records_cannot_hide_mutable_nested_payloads(self):
        m=memory()
        with self.assertRaises(FrozenInstanceError):m.reason="changed"
        with self.assertRaises(ValueError):replace(m,content=[OWNERSHIP])
        with self.assertRaises(ValueError):replace(OWNERSHIP,object={"owner":"alice"})
        with self.assertRaises(ValueError):replace(m,observations=(ref(Kind.EVENT,"e"),))
        with self.assertRaises(ValueError):Moment(True,0)

    @rules("E02", "E03")
    def test_revision_keeps_old_content_and_pins_exact_predecessor(self):
        old=memory()
        new=replace(old,ref=ref(Kind.MEMORY,"m",2),replaces=old.ref,
                    content=(replace(OWNERSHIP,object=BOB),),reason="corrected by evidence")
        self.assertEqual(old.content[0].object,ALICE)
        self.assertEqual(new.content[0].object,BOB)
        with self.assertRaises(ValueError):replace(new,replaces=None)
        with self.assertRaises(ValueError):replace(new,replaces=ref(Kind.MEMORY,"other"))
        with self.assertRaises(ValueError):replace(new,ref=ref(Kind.MEMORY,"m",3))

    @rules("E03", "U01")
    def test_variable_memory_graphs_do_not_require_three_vertices(self):
        for n in (0,1,2,4,17):
            m=memory(content=tuple(replace(OWNERSHIP,relation=f"r{i}") for i in range(n)),
                     links=tuple(ref(Kind.MEMORY,f"link{i}") for i in range(n)))
            self.assertEqual(len(m.content),n)
            self.assertFalse(hasattr(m,"replay_order"))
        self.assertFalse(hasattr(memory(),"rank"))

    @rules("E03", "U01")
    def test_many_memories_share_one_cue_and_many_cues_share_one_memory(self):
        cue=CueDescriptor(ref(Kind.CUE,"magician"),"Magician","major_arcana",None,1,1,"Super-Ego")
        bindings=tuple(CueBinding(ref(Kind.BINDING,f"b{i}"),ALICE,cue.ref,CONTEXT,
                                 memory(f"m{i}").ref,SCOPE,()) for i in range(721))
        self.assertEqual(len({b.target for b in bindings}),721)
        second=replace(bindings[0],ref=ref(Kind.BINDING,"other"),cue=ref(Kind.CUE,"sun"))
        self.assertEqual(second.target,bindings[0].target)
        alternate=replace(bindings[0],context=ref(Kind.CONTEXT,"childhood"))
        self.assertNotEqual(alternate,bindings[0])

    @rules("E03", "U01", "O01")
    def test_rank_fold_content_and_cursor_competence_are_independent(self):
        ace=CueDescriptor(ref(Kind.CUE,"ace"),"Ace","minor","Wand",1,1,"Super-Ego")
        ten=replace(ace,ref=ref(Kind.CUE,"ten"),symbol="Ten",rank=10)
        sun=replace(ace,ref=ref(Kind.CUE,"sun"),symbol="Sun",rank=19,layer_label="Identity")
        self.assertEqual({c.folded_location for c in (ace,ten,sun)},{1})
        self.assertEqual({c.rank for c in (ace,ten,sun)},{1,10,19})
        cursor=CursorState(ref(Kind.CURSOR,"cursor"),ALICE,(),None,())
        m=memory()
        self.assertEqual(cursor.policy,None)
        self.assertTrue(m.content)
        self.assertFalse(hasattr(cursor,"identity_cycle"))
        self.assertEqual(replace(ace,symbol="Fool",rank=0,folded_location=None).folded_location,None)

    @rules("E04", "E08")
    def test_belief_existence_uses_shared_vocabulary_without_truth_flag(self):
        belief=memory(claim_status=ClaimStatus.ENDORSED)
        existence=Proposition(ALICE,"holds_belief",belief.ref,CONTEXT,SCOPE)
        event=WorldEvent(ref(Kind.EVENT,"learned"),TIME,(ALICE,),(),"retain",CONTEXT,
                         (Change(None,existence),),(),(),WorkStatus.COMPLETED,"retained a belief")
        self.assertEqual(event.changes[0].after.object,belief.ref)
        self.assertFalse(hasattr(belief,"is_true"))
        self.assertNotEqual(existence,belief.content[0])

    @rules("E04")
    def test_event_corrections_and_causes_require_explicit_references(self):
        event=WorldEvent(ref(Kind.EVENT,"e"),TIME,(ALICE,),(BOX,),"inspect",CONTEXT,
                         (),(),(),WorkStatus.FAILED,"object unavailable")
        corrected=replace(event,ref=ref(Kind.EVENT,"correction"),corrects=event.ref)
        self.assertEqual(corrected.corrects,event.ref)
        with self.assertRaises(ValueError):replace(event,corrects=event.ref)
        with self.assertRaises(ValueError):replace(event,causes=(Cause(event.ref,ref(Kind.RULE,"r")),))
        with self.assertRaises(ValueError):Cause(ref(Kind.MEMORY,"m"),ref(Kind.RULE,"r"))
        with self.assertRaises(ValueError):Change(None,None)

    @rules("E06")
    def test_observation_delivery_and_memory_owner_boundaries(self):
        obs=Observation(ref(Kind.OBSERVATION,"seen"),ALICE,ref(Kind.EVENT,"e"),TIME,TIME,
                        (OWNERSHIP,),ref(Kind.RULE,"sight"),"only visible properties","no noise")
        view=ParticipantInput(ALICE,TIME,(obs,),(memory(),),(),())
        self.assertEqual(view.observations,(obs,))
        for changes in (dict(observer=BOB),dict(delivered_at=Moment(2,0))):
            with self.assertRaises(ValueError):replace(view,observations=(replace(obs,**changes),))
        with self.assertRaises(ValueError):replace(obs,delivered_at=Moment(0,0))
        with self.assertRaises(ValueError):replace(view,own_memories=(memory(owner=BOB),))
        with self.assertRaises(ValueError):replace(view,own_memories=(memory(retained_at=Moment(2,0)),))
        with self.assertRaises(ValueError):replace(view,observations=(ref(Kind.EVENT,"secret"),))
        with self.assertRaises(ValueError):ActionRequest(ALICE,PROC,(),(ref(Kind.ASSESSMENT,"secret"),))

    @rules("E05")
    def test_partial_failed_and_deferred_work_keep_charges(self):
        partial=work()
        self.assertEqual(partial.charged[0].amount,2)
        failed=replace(partial,outcome=WorkStatus.FAILED,reason="processing failed after two units")
        self.assertEqual(failed.after,partial.after)
        deferred=work(completed_units=0,outcome=WorkStatus.DEFERRED,
                      reason="attempt cost charged; task deferred")
        self.assertEqual(deferred.charged[0].amount,2)
        complete=work(completed_units=4,outcome=WorkStatus.COMPLETED)
        self.assertEqual(complete.completed_units,4)
        failed_at_end=work(completed_units=4,outcome=WorkStatus.FAILED,
                           reason="all processing performed; final operation failed")
        self.assertEqual(failed_at_end.completed_units,4)
        self.assertEqual(failed_at_end.charged,partial.charged)

    @rules("E05")
    def test_invalid_balances_and_completion_status_rejected(self):
        for changes in (dict(after=(ResourceAmount(UNIT,4),)),dict(completed_units=5),
                        dict(outcome=WorkStatus.COMPLETED),dict(outcome=WorkStatus.DEFERRED),
                        dict(before=(ResourceAmount(UNIT,5),ResourceAmount(UNIT,5))),
                        dict(after=()),dict(completed_units=0),dict(required_units=0)):
            with self.assertRaises(ValueError):work(**changes)
        with self.assertRaises(ValueError):ResourceAmount(UNIT,-1)
        with self.assertRaises(ValueError):ResourceAmount(UNIT,2.0)
        with self.assertRaises(ValueError):ResourceAmount(UNIT,True)

    @rules("E05", "E09", "C04")
    def test_realized_movement_requires_processing_and_cost_witness(self):
        formal=FormalMovement(Route(Perspective.I,Perspective.ITS),Polarity.ACCUMULATION)
        step=ProcessingStep(0,PROC,(memory().ref,),(),work().ref)
        record=MovementRecord(ref(Kind.MOVEMENT,"move"),ALICE,ref(Kind.DEMAND,"d"),formal,PROC,
                               (),(),(step,),WorkStatus.PARTIAL,(),"more processing needed")
        self.assertEqual(record.history[0].work,work().ref)
        with self.assertRaises(ValueError):replace(record,history=())
        with self.assertRaises(ValueError):replace(record,history=(replace(step,order=1),))
        pending=replace(record,history=(),outcome=WorkStatus.PENDING)
        self.assertEqual(pending.outcome,WorkStatus.PENDING)

    @rules("E07")
    def test_assessment_requires_predeclared_identity_and_protocols(self):
        protocol=ProtocolSpec(ref(Kind.PROTOCOL,"return"),PROC,ref(Kind.PROCEDURE,"restore"),
                              "declared states","five available quanta",("record every charge",))
        spec=AssessmentSpec(ref(Kind.ASSESSMENT,"s"),Moment(0,0),"two-actor resource world",
                            ref(Kind.IDENTITY,"ownership_check"),("can check ownership",),(protocol,),
                            ref(Kind.RULE,"exact_features"),"one case","only sequences explicitly tested")
        with self.assertRaises(ValueError):replace(spec,identity_features=())
        with self.assertRaises(ValueError):replace(spec,protocols=())
        with self.assertRaises(ValueError):replace(spec,protocols=(protocol,protocol))
        with self.assertRaises(FrozenInstanceError):spec.scope="all worlds"

    @rules("E07", "E08")
    def test_stability_accuracy_path_and_capacity_have_separate_results(self):
        base=AssessmentResult(ref(Kind.ASSESSMENT,"s"),ref(Kind.PROTOCOL,"p"),
                              Dimension.IDENTITY_RETURN,EvidenceStatus.ESTABLISHED,
                              (ref(Kind.EVIDENCE,"trace"),),((ref(Kind.PROTOCOL,"p"),),),
                              "fixture records successful declared feature return")
        factual=replace(base,dimension=Dimension.FACTUAL_AGREEMENT,status=EvidenceStatus.FAILED,
                        reason="same stable account disagrees with declared world")
        path=replace(factual,dimension=Dimension.PATH_CONDITIONS,reason="compensatory work recorded")
        capacity=replace(base,dimension=Dimension.RETAINED_CAPACITY,status=EvidenceStatus.UNASSESSED,
                         evidence=(),tested_sequences=(),reason="renewed demand not run")
        self.assertEqual(len({x.dimension for x in (base,factual,path,capacity)}),4)
        self.assertEqual(capacity.status,EvidenceStatus.UNASSESSED)
        with self.assertRaises(ValueError):replace(base,evidence=())
        with self.assertRaises(ValueError):replace(base,tested_sequences=((),))

    @rules("E01", "E04")
    def test_logical_time_is_ordered_and_scope_is_explicit(self):
        self.assertLess(Moment(1,0),Moment(1,1))
        self.assertLess(Moment(1,100),Moment(2,0))
        with self.assertRaises(ValueError):TimeScope(Moment(2,0),Moment(1,0))
        with self.assertRaises(ValueError):TimeScope(TIME,TIME)
        with self.assertRaises(ValueError):Moment(-1,0)
