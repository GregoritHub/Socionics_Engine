from dataclasses import replace
from tests_c3.fixtures import *
from tests_c2 import fixtures as c2
from tests_c3 import fixtures as c3
from tests_u8 import fixtures as dev
from hle_unified.crux_shell_execution import CruxShellEngine
from hle_unified.crux_composition_execution import CruxCompositionEngine
from hle_unified.crux_shell_records import ShellMovementRequest
from hle_unified.shell_records import PatternPolicy,Effect,PatternSeed
from hle_unified.records import Composition
from hle_unified.operations import address
from hle_unified.crux_composition_audit import audit as content_audit
from hle_unified.shell_audit import audit as shell_audit
from hle_unified.development_audit import audit as development_audit

NAMES=('Contemplate','Express','Share','Theorize','Embody','Act','Coordinate','Organize','Identify','Mobilize','Commune','Institutionalize','Understand','Apply','Educate','Integrate')
FACES=('accumulation','expenditure')
SELF=('Contemplate','Act','Commune','Integrate')

def setup(tim='iee',inactive=0,shared=False,generate=True,engine_type=CruxShellEngine,actual='damaged'):
    def factory(world,law):
        if actual=='serviceable':
            fresh=OperationStore()
            for tx in world.journal():
                vs=tuple(replace(v,facets=(replace(v.facet(Material),condition='serviceable'),),attributes=attributes({**attrs(v),'wear':0})) if v.ref==SAW else v for v in tx.versions)
                fresh.create(tx.key,tx.writer,vs)
            world=fresh
        return engine_type(world,law)
    e=setup_c3(tim,engine_type=factory,inactive=inactive,shared=shared)
    objects=(definition(dev.TRIGGER,'Entrusted performance affordance'),definition(dev.OTHER_TRIGGER,'Other affordance'),
        ObjectVersion(dev.GROUP,WRITER,'Group',(Role.COLLECTIVE,),(Composition((ALICE,BOB),'workshop'),)),
        ObjectVersion(dev.MEMORY,WRITER,'Memory',(Role.CLAIM,),(Account(SAW,(),Moment(0,0),ALICE),),occurrence=Occurrence.REMEMBERED_CLAIM),
        ObjectVersion(dev.POSSIBILITY,WRITER,'Possibility',(Role.CLAIM,),(Account(SAW,(),Moment(0,0),ALICE),),occurrence=Occurrence.HYPOTHETICAL),
        ObjectVersion(dev.ACTION,WRITER,'Plan',(Role.PROCEDURE,),(Procedure(('target',),(),(),()),)))
    e.declare('c5-anchors',objects)
    for r in (*dev.TARGETS.values(),dev.TRIGGER,dev.OTHER_TRIGGER,ObjectRef(EVE,1),SAW2):
        if r not in e.access._known_refs(ALICE): show(e,ALICE,r)
    e.configure_patterns('c5-policy',PatternPolicy(ALICE,generate=generate))
    return e

def prepare(e,name,face,key='case'):
    f=c2.cell if name in SELF else c3.cell
    return f(e,name,face,prepare_only=True,**({'prefix':key} if name in SELF else {'key':key}))['request']

def gate(e,r,key='gate',**kwargs):
    return ShellMovementRequest(key,r,ObjectRef(BOB,1),ObjectRef(EVE,1),dev.evidence8(e,(r.target,)),**kwargs)

def finish(e,r,key='gate',interrupt=False,phase='admission'):
    q=gate(e,r,key,phase=phase)
    e.start(key+':start',q)
    if interrupt:
        e.advance(key+':partial',r.actor,key,1)
        e=type(e).restore(e.checkpoint())
    e.advance(key+':advance',r.actor,key,1000000)
    e.commit(key+':commit',r.actor,key)
    receipt=attrs(e.world.resolve(address('c5.admission',r.actor,key)))
    if receipt['child']:
        e.advance(key+':child-advance',r.actor,r.key,1000000)
        if e.job_status(r.actor,r.key)['status']=='ready': e.commit(key+':child-commit',r.actor,r.key)
    return e,receipt

def downstream(e,r,name,face):
    d=e.job_status(r.actor,r.key); result=d.get('binding') or d['result']; key=r.key
    if name in SELF:
        if name=='Act':
            t=e.world.head(r.target.identity).ref; c2.expose(e,ALICE,t)
            result=perform(e,OperationRequest(key+'-later',ALICE,'use' if face=='accumulation' else 'care',ROOM,
                target=t,stock=CARE if face=='expenditure' else None,evidence=evidence(e,ALICE,t)),limit=10000)
            return dict(kind='event',outcome=attrs(e.world.resolve(result))['outcome'],ref=result)
        if name=='Commune':
            result=d['public.0']; c2.expose(e,BOB,result);c2.expose(e,BOB,ref('bob-consumables'))
            decision=c2.consume(e,result,key+'-later',actor=BOB,group=r.group,demand=4,stock=ref('bob-consumables'))
            actor=BOB
        else:
            c2.expose(e,ALICE,r.target)
            decision=c2.consume(e,result,key+'-later',tool=KIT,stock=STOCK);actor=ALICE
        out=c2.data(e,decision,actor)
    else:
        destination=PATHS[name][1]; actor=ALICE; peer=BOB if r.group else None
        if destination=='IT':
            source=receive(e,result,ALICE,key+'-received')
            if face=='expenditure' or name=='Apply': source=inspect(e,key+'-remaining')
            domain='observation'; demand=20
        elif destination=='WE':
            source=d['public.0'];actor=BOB;peer=ALICE;expose(e,actor,source);domain='shared';demand=5
        else: source=result;domain='personal' if destination=='I' else 'system';demand=5
        current=e.world.head((SUPPLY if actor==ALICE else ref('bob-consumables')).identity).ref;expose(e,actor,current)
        decision=work(e,req(e,key+'-later','use-'+domain+'-v1',(source,),actor=actor,stock=current,group=r.group,peer=peer,demand=demand))
        out=data(e,decision,actor)
    event=None
    if (name not in SELF and out['action']=='consume') or (name=='Contemplate' or name=='Integrate' and face=='expenditure' or name=='Commune' and face=='expenditure') and out['action']!='none':
        event=enact(e,decision,key+'-enact',actor=actor)
    return dict(kind='decision',ref=decision,action=out['action'],amount=out.get('amount'),event=event)

def panel_case(name,face,tim='iee',effect='approval',interrupt=False,phase='admission'):
    actual='serviceable' if name=='Act' and face=='expenditure' else 'damaged'
    base=setup(tim,actual=actual)
    # Both arms retain exactly the same history and pattern. The control uses
    # an explicit, paid, target-local release, not erased labels or history.
    if effect=='approval': p=dev.generated(base)
    else:
        dev.supply8(base,'fixture-opportunity')
        pref=dev.inject(base,Effect(effect,name.lower()+'-'+face+'-v1',-1 if effect=='salience' else 1))
        p=base._patterns[pref]
    dev.supply8(base,'current-neutral')
    r=prepare(base,name,face)
    cp=base.checkpoint(); deformed=CruxShellEngine.restore(cp)
    deformed,dr=finish(deformed,r,interrupt=interrupt,phase=phase)
    control=CruxShellEngine.restore(cp)
    if effect=='approval': dev.release8(control,'local-release',p)
    else:
        # For non-authorization operators the control is a separate pre-pattern
        # run; C5 does not invent correction rules for these effect kinds.
        control=setup(tim,generate=False,actual=actual);dev.supply8(control,'current-neutral');r=prepare(control,name,face)
    control,cr=finish(control,r,interrupt=interrupt,phase=phase)
    later=downstream(control,r,name,face)
    return deformed,control,dict(name=name,face=face,effect=effect,phase=phase,deformed=dr,control=cr,later=later)
