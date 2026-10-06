"""Declared R5 controls. Goals, opportunities and fixture choices are supplied.

Participant content and checking capacity are derived by inherited R4 operators.
Detector fixtures deliberately choose a rejection or material treatment policy;
these are never represented as autonomously generated psychological defenses.
"""
from dataclasses import replace
from .contracts import (AssessmentSpec, ClaimStatus, Kind, ProtocolSpec, Ref)
from .assessment import AssessedWorld
from .assessment_records import (AssessPending, BeginTrial, Contrast, DeclareStudy,
    EndTrial, MaterialCommand, Study)
from .cards import card
from .demo import ALICE, BOB, BOX, TOOL, ROOM, config, request
from .memory_records import MemoryCommand, WriteDraft
from .metabolism_demo import (CUE, LESSON, associate, finish, remember_initial, retrieve)
from .metabolism_records import (APPLY, EMBODY, THEORIZE, UNDERSTAND, ApplyDraft,
    EmbodyDraft, MetabolicCommand, ProcessingPolicy, Profile, TheorizeDraft, UnderstandDraft)
from .world_records import Attempt, Credit, INSPECT, TRANSFER
from .crux import Perspective


def world(energy=4000, time=4000, tim="iee", policy=ProcessingPolicy()):
    return AssessedWorld(config(energy, time), (Profile(ALICE, "lse"), Profile(BOB, tim)), policy)


def declare(w, key="study", memory="box", item=BOX, features=("claim_links",),
            operations=(THEORIZE, APPLY, EMBODY), fixture=False, strict=False, max_units=1000):
    protocol = ProtocolSpec(Ref(Kind.PROTOCOL, "r5.protocol:" + key, 1), operations[0], operations[-1],
        "R4 ownership/checking grammar; named memory and relevant feature must exist",
        "actual energy and time; complete next offered movement quoted at trial opening",
        ("bounded paid work", "no paid contradicted reconstruction", "no external attribution action")
        + (("no prediction discrepancy",) if strict else ()))
    spec = AssessmentSpec(Ref(Kind.ASSESSMENT, key, 1), w.now, "r5.ownership_agent.v1",
        Ref(Kind.IDENTITY, "r5.selected_features", 1), features, (protocol,),
        Ref(Kind.RULE, "r5.exact", 1), "declared trials; direct observations; supplied demand scheduling",
        "only recorded sequences; general finite-composition closure unassessed")
    study = Study(spec, BOB, memory, item, operations, max_units, strict, 2,
        "injected_detector_fixture" if fixture else "controlled_execution",
        (Contrast(Perspective.I,ALICE,BOB), Contrast(Perspective.IT,ALICE,BOB),
         Contrast(Perspective.ITS,INSPECT,TRANSFER)))
    w.execute(DeclareStudy("declare:" + key, study))
    return study


def begin(w, s, key, payload=None, demanded=True, corrective=()):
    offer = None if payload is None else MetabolicCommand("offer:"+key, "offer:"+key, s.actor, payload)
    w.execute(BeginTrial("begin:"+key, key, s.ref, demanded, offer, corrective))
    return Ref(Kind.DEMAND, "trial:"+key, 1), offer


def end(w, trial):
    w.execute(EndTrial("end:"+trial.key, trial))
    return w._trial_results[replace(trial, revision=2)]


def drain(w, key="assess", limit=1):
    i=0
    while w.pending_assessments():
        w.execute(AssessPending(f"{key}:{i}", limit)); i+=1
    return i


def execute_offer(w, offer):
    w.execute(offer)
    j = w.processing_job(offer.actor, offer.task_id)
    i=0
    while j.result is None and min(w.truth.wallet(offer.actor).energy, w.truth.wallet(offer.actor).time):
        i+=1
        w.execute(replace(offer, command_id=offer.command_id+f":resume:{i}"))
        j=w.processing_job(offer.actor,offer.task_id)
    return j


def false_account_fixture(w, key="box"):
    old=remember_initial(w,key)
    w.execute(Attempt("hidden-transfer","hidden-transfer",request(ALICE,TRANSFER,(BOX,BOB))))
    r=retrieve(w,"recall-false")
    a=finish(w,TheorizeDraft(r,BOX,ALICE),"theory-before-opportunity")
    # Direct inspect supplies usable evidence. It does not force attention or retention.
    event=w.execute(Attempt("corrective-inspection","corrective-inspection",request(BOB,INSPECT,(BOX,))))
    observation=next(o for o in w._journal[event.when.tick].observations if o.observer==BOB)
    return old,w.processing_record(BOB,a.result),observation


def detector_case(mode="foreclosure", energy=4000):
    w=world(energy=4000 if energy == 4000 else 100,
            time=4000 if energy == 4000 else 100)
    old,a,observation=false_account_fixture(w)
    s=declare(w,fixture=True,operations=(APPLY,EMBODY))
    if energy != 4000:
        # Consume the actual wallet via paid attempted work, not mutation or a refund.
        from .world_records import Tick
        for i in range(w.truth.wallet(BOB).energy-energy):
            w.execute(Attempt(f"spend:{i}",f"spend:{i}",request(BOB,INSPECT,(BOX,))))
    from .world_records import Tick
    for i in range(2):
        trial,offer=begin(w,s,f"detector:{i}",ApplyDraft(a.ref),mode!="rest",(observation.ref,))
        if mode=="compensation":
            m=w.memory_head(BOB,"box")
            w.execute(MemoryCommand(f"reconstruct:{i}",f"reconstruct:{i}",BOB,
                WriteDraft("box",old.content,(),ClaimStatus.ENDORSED,m.ref,
                    "explicit detector-fixture policy reasserts old account despite direct evidence"),(m.ref,observation.ref)))
        else: w.execute(Tick(f"quiet:{i}"))
        end(w,trial)
    drain(w)
    return w,s


def run_assessment_demo():
    w=world()
    original=remember_initial(w)
    s=declare(w,features=("claim_links","perspective"),strict=True)
    w.execute(Attempt("hidden-transfer","hidden-transfer",request(ALICE,TRANSFER,(BOX,BOB))))
    r=retrieve(w,"old")
    trial,offer=begin(w,s,"learn",TheorizeDraft(r,BOX,ALICE))
    a=execute_offer(w,offer)
    app=finish(w,ApplyDraft(a.result),"learn-apply",work_limit=3)
    finish(w,EmbodyDraft(app.result,"box",original.ref),"learn-embody")
    first=end(w,trial)
    lesson=w.memory_head(BOB,"box")
    associate(w,lesson,"lesson",LESSON)
    # Retained organization, tracked as capacity, faces renewed and held-out demands.
    capacity=declare(w,"capacity",features=("capacity_rules",))
    for index,item in enumerate((BOX,TOOL)):
        cue=CUE if item==BOX else card("arcana:3").ref
        if item==TOOL: remember_initial(w,"tool",TOOL,cue)
        # Old box prediction says Alice; after hidden transfer Bob owns it again.
        if item==BOX:
            w.execute(Attempt("renew-box","renew-box",request(ALICE,TRANSFER,(BOX,BOB))))
        rr=retrieve(w,f"retained:{index}",(cue,LESSON))
        t,o=begin(w,capacity,f"retained:{index}",TheorizeDraft(rr,item,ALICE))
        aa=execute_offer(w,o)
        ap=finish(w,ApplyDraft(aa.result),f"retained-apply:{index}")
        # Preserve the generic lesson in its own memory; output can concern either object.
        finish(w,EmbodyDraft(ap.result,f"experience:{index}"),f"retained-embody:{index}")
        end(w,t)
    drain(w)
    return w, {"milestone":"R5","events":len(w._journal),
        "initial_identity_return":first.identity.value,"initial_path":first.path.value,
        "initial_discrepancy":first.discrepancy,"initial_units":first.units,
        "retained_capacity":w.report(capacity.ref).results[3].status.value,
        "capacity_items":[r.key for r in w._aggregates[capacity.ref].capacity_items],
        "assessment_visits":w.assessment_visits,
        "scope":"bounded IDEA assessment; detector fixtures separately identified; no growing-world closure proof",
        "next":"R6: Socion exchanges among independently adapting holons"}


def clearance_case():
    w,s=detector_case("foreclosure")
    labels=[w.report(s.ref).shell]
    account=next(r for r in w._records.values() if type(r).__name__=="Account")
    for index,item in enumerate((BOX,BOX,TOOL)):
        if index:
            lesson=w.memory_head(BOB,"box")
            if index==1:associate(w,lesson,"corrected-cue",LESSON)
            if item==TOOL:remember_initial(w,"tool",TOOL,card("arcana:3").ref)
            cues=(LESSON,) if item==BOX else (LESSON,card("arcana:3").ref)
            rr=retrieve(w,f"renew:{index}",cues)
            a=finish(w,TheorizeDraft(rr,item,ALICE),f"renew-think:{index}")
            account=w.processing_record(BOB,a.result)
        t,o=begin(w,s,f"clear:{index}",ApplyDraft(account.ref))
        app=execute_offer(w,o)
        if item==BOX:
            old=w.memory_head(BOB,"box")
            finish(w,EmbodyDraft(app.result,"box",old.ref),f"clear-return:{index}")
        else:finish(w,EmbodyDraft(app.result,"new-object"),f"clear-return:{index}")
        end(w,t);drain(w,f"clear-report:{index}");labels.append(w.report(s.ref).shell)
    return w,s,labels


def capacity_controls():
    """Same history and wallet; change only which equal-content lesson is recalled."""
    from .memory import observed_revision
    rows=[]
    for item in (BOX,TOOL):
        for enabled in (False,True):
            w,_=run_assessment_demo()
            lesson=w.memory_head(BOB,"box")
            # Both demo objects now belong to Alice. Supply the same new episode.
            w.execute(Attempt("give-self","give-self",request(ALICE,TRANSFER,(item,BOB))))
            e=w.execute(Attempt("see-self","see-self",request(BOB,INSPECT,(item,))))
            obs=next(o for o in w._journal[e.when.tick].observations if o.observer==BOB)
            view,_=w.select_input(BOB)
            draft,basis=observed_revision(view,obs.ref,item,"owned_by","stale-self")
            w.execute(MemoryCommand("stale-self","stale-self",BOB,draft,basis))
            associate(w,w.memory_head(BOB,"stale-self"),"stale-cue",card("arcana:5").ref)
            w.execute(Attempt("give-away","give-away",request(BOB,TRANSFER,(item,ALICE))))
            w.execute(MemoryCommand("no-cap","no-cap",BOB,
                WriteDraft("no-cap",lesson.content,(),ClaimStatus.ENDORSED,None,"matched capacity ablation"),(lesson.ref,)))
            associate(w,w.memory_head(BOB,"no-cap"),"no-cap-cue",card("arcana:4").ref)
            balance=w.truth.wallet(BOB)
            rr=retrieve(w,"control-recall",(card("arcana:5").ref,LESSON if enabled else card("arcana:4").ref))
            a=finish(w,TheorizeDraft(rr,item,ALICE),"control-think")
            account=w.processing_record(BOB,a.result)
            app=finish(w,ApplyDraft(a.result),"control-apply")
            application=w.processing_record(BOB,app.result)
            first=w.processing_record(BOB,application.enactments[0])
            rows.append({"item":item.key,"capacity_recalled":enabled,
                "resources_before_recall":{"energy":balance.energy,"time":balance.time},
                "prediction":account.claim.object.key,"first_action":first.request.operation.key,
                "outcome":app.outcome.value,"application":application.ref.key,
                "discrepancy":application.discrepancy})
    return rows
