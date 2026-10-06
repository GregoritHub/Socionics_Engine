"""Save continuing source-material lineage and non-clearance witnesses."""
import sys,json,gzip
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from tests_c5.fixtures import *
from hle_unified.crux_shell_audit import audit
from evaluate_c5 import dump

def main(out):
    out.mkdir(parents=True,exist_ok=False);rows=[]
    def save(name,e):
        cp=e.checkpoint();(out/(name+'.json.gz')).write_bytes(gzip.compress(cp.encode(),mtime=0))
        a=audit(e.world.journal(),e.access.checkpoint());assert a['passed']
        rows.append(dict(name=name,audit=a,development=e.development_view(ALICE)))
    e=setup();p=dev.generated(e);dev.supply8(e,'current');r=prepare(e,'Theorize','accumulation')
    e,_=finish(e,r,'initial-gate',phase='after_first_step');save('01-formed-and-active-interruption',e)
    dev.release8(e,'local-other',p,SAW2);r=replace(r,key='recurrence')
    e,_=finish(e,r,'recurrence-gate',phase='after_first_step');save('02-other-target-release-and-recurrence',e)
    e,p=dev.trained8(e);save('03-independent-practice-and-organization',e)
    dev.returned8(e,p);r=replace(r,key='return-movement');e,_=finish(e,r,'return-gate',phase='after_first_step')
    later=downstream(e,r,'Theorize','accumulation');save('04-novel-returns-reownership-and-native-use',e)
    dev.supply8(e,'danger',safe=False);r=replace(r,key='danger-movement');e,_=finish(e,r,'danger-gate');save('05-reowned-does-not-erase-danger',e)
    s=setup();sp=dev.generated(s);dev.supply8(s,'support',approved=True);sr=prepare(s,'Share','expenditure')
    s,_=finish(s,sr,'supported');save('06-supported-success-without-capacity',s)
    dev.supply8(s,'renewed',approved=False);sr=replace(sr,key='renewed-share');s,_=finish(s,sr,'renewed-gate',phase='after_first_step');save('07-support-withdrawal-recurrence',s)
    for effect in ('obligation','salience','forecast','exclude_route'):
        d,c,row=panel_case('Theorize','accumulation',effect=effect,phase='after_first_step')
        save('effect-'+effect+'-deformed',d);save('effect-'+effect+'-control',c)
    (out/'summary.json').write_text(dump(dict(passed=True,witnesses=len(rows),rows=rows,later=later)))
    print('development witnesses',len(rows),flush=True)
if __name__=='__main__':main(Path(sys.argv[1]))
