"""Bounded next-choice probe, separate from history/checkpoint growth."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from hle.individuation_demo import case,make_offer,do,command
from hle.individuation import IndividuationWorld
from hle.world_records import Tick
from hle.concept_demo import fund_command
class NoScan(list):
    def __iter__(self):raise AssertionError('ordinary choice scanned inactive journal')
    def __reversed__(self):raise AssertionError('ordinary choice scanned inactive journal')

def main():
    rows=[]
    for quiet in (0,100,1000):
        w,_=case(renew=False)
        for n in range(quiet):w.execute(Tick('quiet:'+str(n)))
        f=make_offer(w,'inactive:held','si',held=True,all_traps=True);w.execute(f);do(w,f.key,f.partner,'menu')
        c=command(w,f.key,f.learner,'choose');before=w._wallets[f.learner];length=len(w._journal)
        w._journal=NoScan(w._journal);fund_command(w,c);after=w._wallets[f.learner]
        rows.append({'quiet_ticks':quiet,'prior_events':length,'energy':before.energy-after.energy,'time':before.time-after.time,
            'chosen':w._circuit_orders[f.key].chosen,'guard_count':len(w._circuit_orders[f.key].uses),'scan_forbidden':True})
    result={'rows':rows,'passed':len({(r['energy'],r['time'],r['chosen'],r['guard_count']) for r in rows})==1,
        'scope':'next paid choice only; growing checkpoint and full offline replay are excluded'}
    p=ROOT/'evidence/r18/active_work.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
