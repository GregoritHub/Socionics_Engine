"""Finite opportunities and disclosure schedules, never desired rule/vote inputs.

The harness supplies materials, goal, prior blame experiences and opportunities.
U7 generates attributions; U9 generates programs; U12 chooses gates and responses.
"""
from tests_u11.fixtures import *
from tests_u7.fixtures import supply, meet, TRIGGER
from hle_unified.institutions import InstitutionEngine
from hle_unified.institution_records import InstitutionRequest
from hle_unified.shell_records import PatternPolicy
from hle_unified.development_records import DevelopmentRequest
from hle_unified.development_values import attrs as unpack

GOAL=(("ge",("field","progress","uses"),1),
      ("eq",("field","target","condition"),"serviceable"),
      ("eq",("field","target","wear"),0))


def expose12(e,actor,obj):
    if obj.identity.namespace.startswith("u12."):
        v=e.world.resolve(obj)
        selectors=tuple(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(v.attributes) if a.name=="payload")
        if any(p.address.key=="payload" for p in e.participant_view(actor).resolve(obj)):return
        show(e,actor,obj,key="u12:"+actor.key+":"+obj.identity.namespace+":"+obj.identity.key+":"+str(obj.revision),selectors=selectors)
    elif obj.identity.namespace=="u7.encounter":
        v=e.world.resolve(obj)
        if e.participant_view(actor).resolve(obj):return
        show(e,actor,obj,key="encounter:"+actor.key+":"+obj.identity.key,
             selectors=tuple(Selector(a.name,"detail",("attributes",str(i),"value")) for i,a in enumerate(v.attributes)))
    else:expose(e,actor,obj)


def slots12(e,actor,domain="tool"):
    bindings=(("target",ref("u12-"+domain+"-"+actor.key)),
              ("care_stock",ref("u11-care-"+actor.key)),
              ("repair_stock",ref("u11-repair-"+actor.key)),
              ("tool",ref("u11-kit-"+actor.key)))
    result=tuple((k,e.world.head(v.identity).ref) for k,v in bindings)
    for k,v in result:expose12(e,actor,v)
    return result


def encounter12(e,key,actor=ALICE,domain="tool",**facts):
    target=ref("u12-"+domain+"-"+actor.key)
    identity=ref("u12-facts-"+domain+"-"+actor.key).identity
    revision=e.world.head(identity).ref.revision+1 if identity in e.world._heads else 1
    source=supply(e,key,target=target,actor=actor,version=ObjectRef(identity,revision),**facts)
    encounter=meet(e,key,source,target=target,actor=actor,carrier=ObjectRef(BOB if actor==ALICE else ALICE,1),bearer=ObjectRef(actor,1))
    expose12(e,actor,encounter)
    return encounter


def setup12(*,patterns=(ALICE,BOB),train_eve=False,budget=2000000,tim="iee",domain="tool"):
    from hle_unified.compact import unseal
    base=setup11(budget=budget,train_bob=False,tim=tim)
    world=OperationStore.restore(unseal(base.checkpoint(),base.SCHEMA)["initial"])
    materials=tuple(tool(ref("u12-"+domain+"-"+a.key),owner=a,damaged=domain=="pump",
                         maximum=3 if domain=="pump" else 6) for a in (ALICE,BOB,EVE))
    world.create("u12-material-opportunities",WRITER,(*materials,definition(TRIGGER,"Entrusted performance affordance")))
    e=InstitutionEngine(world,LAW_REF)
    for actor in (ALICE,BOB,EVE):
        for obj in (ROOM,CUE5,ObjectRef(ALICE,1),ObjectRef(BOB,1),ObjectRef(EVE,1)):expose12(e,actor,obj)
        if actor!=EVE or train_eve:train(e,actor,("repair","transfer","use","care","consume"))
        e.configure_patterns("patterns-"+actor.key,PatternPolicy(actor))
        expose12(e,actor,TRIGGER)
        slots12(e,actor,domain)
        if actor in patterns:
            # Distinct actual supplied episodes, followed by generated U7 material.
            encounter12(e,"blame-one-"+actor.key,actor,domain,feedback="blame")
            encounter12(e,"blame-two-"+actor.key,actor,domain,feedback="blame")
        encounter12(e,"present-"+actor.key,actor,domain)
    resources=tuple(v.ref for v in materials)
    resources+=tuple(e.world.head(ref("u11-"+n+"-"+a.key).identity).ref for a in (ALICE,BOB,EVE) for n in ("kit","repair","care"))
    # A paid group boundary supplies participants and resources; it contains no rule.
    g=group(e,"voluntary-workshop",resources=resources)
    g=join(e,g)
    for actor in (ALICE,BOB):expose12(e,actor,g["ref"])
    return e,g


def current_encounter(e,actor,domain="tool"):
    return e._last_encounters[actor,ref("u12-"+domain+"-"+actor.key).identity,ROOM,CUE5]


def op12(e,key,purpose,*,actor=ALICE,expect=True,read=True,domain="tool",**kwargs):
    focus=kwargs["focus"]
    if read:
        expose12(e,actor,focus)
        d=e._records11[focus]
        g=focus if d["kind"]=="group" else e._heads11[d["group"].identity]
        expose12(e,actor,g)
        if d.get("institution"):expose12(e,actor,d["institution"])
        if d.get("dispute"):expose12(e,actor,d["dispute"])
        if kwargs.get("support"):expose12(e,actor,kwargs["support"])
    if purpose in ("propose","counter","respond","apply","assent"):
        kwargs.setdefault("encounter",current_encounter(e,actor,domain))
    request=InstitutionRequest(key,actor,purpose,ROOM,CUE5,**kwargs)
    perform(e,request,limit=1000000)
    d=e.job_status(actor,key)
    if expect:assert d["status"]=="succeeded",(key,d.get("diagnostic"),d["failure"])
    return tuple(e._records11[x] for x in indexed(d,"output."))


def propose12(e,g,key="proposal",*,actor=ALICE,intent="establish",domain="tool",**kwargs):
    focus=e._heads11[g["ref"].identity]
    return op12(e,key,"propose",actor=actor,focus=focus,intent=intent,domain=domain,
        slots=slots12(e,actor,domain),**({"goal":GOAL} if intent=="establish" else {}),**kwargs)[0]


def vote12(e,p,key="vote",actors=None,domain="tool"):
    actors=actors or p["electorate"]
    return tuple(op12(e,key+"-"+a.key,"respond",actor=a,focus=p["ref"],domain=domain)[0] for a in actors)


def ratify12(e,p,key="ratify",actor=ALICE):
    for a in p["electorate"]:expose12(e,actor,e._ballots12[p["ref"],a])
    for practice in p.get("practices",()):expose12(e,actor,practice)
    out=op12(e,key,"ratify",actor=actor,focus=p["ref"])
    return next(x for x in out if x["kind"]=="institution")


def establish12(e,g,domain="tool"):
    p=propose12(e,g,domain=domain);vote12(e,p,domain=domain)
    return ratify12(e,p),p


def practice12(e,institution,key,*,actor=ALICE,domain="tool",support=None):
    run=op12(e,key,"apply",actor=actor,focus=institution["ref"],slots=slots12(e,actor,domain),support=support,domain=domain)[0]
    assert run["kind"]=="run",run
    work(e,key+"-consent","accept",actor=actor,focus=run["ref"])
    run=finish(e,run,key+"-work")
    slots12(e,actor,domain)
    practice=op12(e,key+"-record","record",actor=actor,focus=run["ref"])[0]
    return run,practice


def active12(*,domain="tool",**kwargs):
    e,g=setup12(domain=domain,**kwargs)
    institution,p=establish12(e,g,domain)
    practices=[]
    for i in range(2):
        _,pr=practice12(e,institution,"trial-"+str(i),domain=domain)
        practices.append(pr)
        expose12(e,ALICE,pr["ref"])
    maintain=propose12(e,institution,"maintain",intent="maintain",domain=domain)
    vote12(e,maintain,"maintain-vote",domain=domain)
    active=ratify12(e,maintain,"maintained")
    return e,dict(group=g,proposal=p,trial=institution,practices=tuple(practices),institution=active)


def correct12(e,actor,key="correct",domain="tool"):
    target=ref("u12-"+domain+"-"+actor.key)
    pattern=e.pattern_view(actor)[0]
    from hle_unified.shell_policy import facts
    _,sources=facts(e.participant_view(actor),target,ROOM)
    evidence_=tuple(p.address for source in sources for p in e.participant_view(actor).resolve(source))
    request=DevelopmentRequest(key,actor,"release",pattern.ref,ROOM,CUE5,(target,),evidence_)
    perform(e,request,limit=1000000)
    assert e.job_status(actor,key)["status"]=="succeeded"
    encounter12(e,key+"-renewed",actor,domain)
    return e.job_status(actor,key)


def corrected_public12(e,d,domain="tool"):
    institution=d["institution"]
    correct12(e,ALICE,"alice-correct",domain)
    before=propose12(e,institution,"first-revision",intent="review",domain=domain,support=d.get("dispute"))
    votes=vote12(e,before,"first-review",domain=domain)
    for vote in votes:expose12(e,ALICE,vote["ref"])
    op12(e,"unilateral-revision","ratify",focus=before["ref"],expect=False)
    correct12(e,BOB,"bob-correct",domain)
    revised=op12(e,"negotiated-revision","counter",actor=BOB,focus=before["ref"],slots=slots12(e,BOB,domain),domain=domain)[0]
    vote12(e,revised,"revised-vote",domain=domain)
    current=ratify12(e,revised,"collective-correction",actor=BOB)
    return current,before,revised,votes
