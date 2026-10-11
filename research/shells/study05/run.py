from common import *
import argparse,os
from tests_u8 import fixtures as f
from hle_unified.development_assessment import assess
from hle_unified.development_values import attrs
p=argparse.ArgumentParser();p.add_argument('--type',required=True);p.add_argument('--tag',required=True);a=p.parse_args()
out=ROOT/'attempt_02'/a.tag/a.type;out.mkdir(parents=True,exist_ok=False)
profile={'load':os.environ.get('SHELL_LOAD_RULE','total'),'fresh':os.environ.get('SHELL_FRESH_RULE','historical'),'engine':str(SOURCE)}
write(out/'profile.json',profile)
def load(arm='reowned'):
    e=f.DevelopmentEngine.restore(gzip.open(ROOT.parent/'shell_precision_02/inputs'/f'{a.type}_{arm}.json.gz','rt').read())
    if (profile['load'],profile['fresh']) != ('total','historical'):
        e._execute(('configure_experiment','research-profile-05',profile['load'],profile['fresh']))
    return e
def save(e,name,extra):
    audit=assess(e.world.journal())
    assert audit['accounting']['passed']
    write(out/(name+'.json'),{**extra,'audit':audit,'sha256':save_checkpoint(out/(name+'.json.gz'),e)})
def reown(e,p,key):
    before=e.checkpoint()
    try:
        f.reorganize8(e,key,p,purpose='reown');return {'accepted':True,'unchanged':False}
    except ValueError as exc:
        assert e.checkpoint()==before
        return {'accepted':False,'unchanged':True,'error':str(exc)}
for name,targets in [('mixed',(f.SAW2,f.GROUP,f.MEMORY)),('novel3',(f.MEMORY,f.POSSIBILITY,f.ACTION))]:
    e=load();p=e.pattern_view(f.ALICE)[0];event=f.respond8(e,'test-'+name,p,targets)
    save(e,name,{'response':e._response_results[event]})
for observed in (False,True):
    name='observed' if observed else 'unobserved';e=load();p=e.pattern_view(f.ALICE)[0]
    event=f.respond8(e,'overload',p,(f.MEMORY,f.POSSIBILITY,f.ACTION))
    if observed:f.practice8(e,'retain-overload',p,event)
    attempt=reown(e,p,'old-reown');save(e,name+'-old',attempt)
    # Branch from pre-reownership overloaded checkpoint for fresh-return recovery.
    if observed:
        e=load();p=e.pattern_view(f.ALICE)[0];event=f.respond8(e,'overload',p,(f.MEMORY,f.POSSIBILITY,f.ACTION));f.practice8(e,'retain-overload',p,event)
        for i,targets in enumerate(((f.MEMORY,f.POSSIBILITY),(f.ACTION,f.OBLIGATION))):
            ev=f.respond8(e,'fresh-'+str(i),p,targets,partner=f.ObjectRef(f.EVE,1));f.practice8(e,'retain-fresh-'+str(i),p,ev)
        save(e,'observed-fresh',reown(e,p,'fresh-reown'))
# Existing pattern, no generalized capacity: approval-supported performance.
for required in (False,True):
    e=load('local');p=e.pattern_view(f.ALICE)[0]
    event=f.respond8(e,'supported',p,(f.MEMORY,),approved=True,approval_required=required)
    f.practice8(e,'retain-supported',p,event)
    save(e,'supported-'+str(required),{'response':e._response_results[event]})
print(a.tag,a.type,'complete',flush=True)
