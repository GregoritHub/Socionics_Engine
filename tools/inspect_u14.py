"""Read-only offline inspector. Participant exports never include evaluator truth."""
import argparse
import gzip
import html
import json
from dataclasses import fields,is_dataclass
from enum import Enum
from pathlib import Path
from u14_support import *
from hle_unified import codec


def readable(value):
    """Detached JSON data for every public record shape, including particulars."""
    if isinstance(value,Enum):return value.value
    if isinstance(value,(tuple,list)):return [readable(x) for x in value]
    if isinstance(value,dict):return {str(k):readable(v) for k,v in value.items()}
    if hasattr(value,'identity'):
        return dict(namespace=value.identity.namespace,key=value.identity.key,revision=value.revision)
    if hasattr(value,'namespace'):return dict(namespace=value.namespace,key=value.key)
    if is_dataclass(value):return {f.name:readable(getattr(value,f.name)) for f in fields(value)}
    if value is None or type(value) in (str,int,float,bool):return value
    raise TypeError('unsupported inspector record '+type(value).__name__)


def load_engine(path):
    path=Path(path)
    cp=gzip.decompress(path.read_bytes()).decode() if path.suffix=='.gz' else path.read_text()
    schema=json.loads(cp)['schema']
    from hle_unified.institutions import InstitutionEngine
    from hle_unified.collective import CollectiveEngine
    from hle_unified.grounded_language import LanguageEngine
    from hle_unified.autonomy import AutonomousEngine
    from hle_unified.cognition import CognitiveEngine
    classes=(InstitutionEngine,CollectiveEngine,LanguageEngine,AutonomousEngine,CognitiveEngine)
    engine=next((cls for cls in classes if cls.SCHEMA==schema),None)
    if engine is None:raise ValueError('unsupported engine checkpoint schema')
    return engine.restore(cp)


def participant(engine,actor):
    view=engine.participant_view(actor)
    jobs={}
    for tx in engine.world.journal():
        for v in tx.versions:
            d={a.name:a.value for a in v.attributes}
            if d.get('record_type')=='operation' and d.get('actor')==actor:
                jobs[v.ref.identity]=dict(ref=v.ref,**d)
    return dict(actor=actor.key,scope='Received and processed actor state; historical accounts may be stale.',
        wallet=readable(engine.wallet(actor)),received=readable(view.snapshot.particulars),
        acquired=readable(view.snapshot.acquired),bindings=readable(view.snapshot.bindings),
        pending_deliveries=readable(view.snapshot.pending),own_jobs=readable(list(jobs.values())))


def inspect(engine,actor_name='alice',assess=False,object_name=None,revision=None):
    candidates=[a for a in engine._wallets if a.key==actor_name or f'{a.namespace}:{a.key}'==actor_name]
    if len(candidates)!=1:raise ValueError('actor is absent or ambiguous')
    before=digest(engine.checkpoint())
    result=participant(engine,candidates[0])
    if object_name and not assess:raise ValueError('world-object inspection requires explicit evaluator mode')
    if assess:
        heads={};timeline=[]
        for i,tx in enumerate(engine.world.journal()):
            changed=[]
            for v in tx.versions:
                heads[v.ref.identity]=v
                changed.append(f'{v.ref.identity.namespace}:{v.ref.identity.key}@{v.ref.revision}')
            timeline.append(dict(index=i,key=tx.key,changed=changed))
        result['offline_evaluator']=dict(scope='Simulator history. This is not participant knowledge.',
            accounting=raw_accounting(engine.world.journal()),timeline=timeline,
            objects=[dict(id=f'{k.namespace}:{k.key}',revision=v.ref.revision,label=v.label,roles=readable(v.roles)) for k,v in sorted(heads.items())])
        if object_name:
            matches=[k for k in heads if f'{k.namespace}:{k.key}'==object_name]
            if len(matches)!=1:raise ValueError('unknown object: '+object_name)
            from hle_unified.records import ObjectRef
            key=matches[0]
            versions=[v for tx in engine.world.journal() for v in tx.versions if v.ref.identity==key]
            result['offline_evaluator']['object_history']=readable(versions if revision is None else [engine.world.resolve(ObjectRef(key,revision))])
    if before!=digest(engine.checkpoint()):raise ValueError('inspector mutated checkpoint')
    return result


def write_html(path,data):
    # Escape the script terminator independently of HTML display escaping.
    payload=json.dumps(data,ensure_ascii=True).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    doc='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HLE U14 · Workshop inspector</title><style>
body{margin:0;background:#111b24;color:#e6edf2;font:15px system-ui,sans-serif}main{max-width:1180px;margin:auto;padding:32px}h1{font-size:30px;margin:8px 0}p{color:#b4c9d7;line-height:1.5}nav{display:flex;gap:8px;flex-wrap:wrap;margin:24px 0}button,input{font:inherit;border:1px solid #496375;border-radius:6px;padding:10px 14px;background:#20313e;color:#e6edf2}button[aria-selected=true]{background:#2d6262;border-color:#69cabb}input{width:calc(100% - 30px);margin:0 0 20px}pre{white-space:pre-wrap;overflow-wrap:anywhere;margin:0;background:#182731;padding:20px;border-radius:8px;font:13px ui-monospace,monospace;line-height:1.5}.tag{color:#79d4c7;text-transform:uppercase;letter-spacing:2px;font-size:12px}.note{border-left:3px solid #d5a459;padding:12px;background:#27333b}details{margin:8px 0}summary{padding:12px;cursor:pointer;background:#20313e}footer{margin-top:26px;color:#9cb1be}</style>
<main><div class="tag">Holonic Living Engine / release U14</div><h1>Workshop inspector</h1><p id="intro"></p><div class="note">Actor views contain received accounts and owned work. The evaluator tab shows simulator history. A corrected interpretation does not erase a consequence.</div><nav id="tabs" aria-label="Inspector sections"></nav><input id="query" type="search" aria-label="Filter records" placeholder="Filter by object, actor, operation, or event"><section id="content"></section><footer>Offline, read-only export · Source and full checkpoints accompany the release. Use inspect_u14.py for exact historical object revisions.</footer></main>
<script type="application/json" id="data">PAYLOAD</script><script>
const data=JSON.parse(document.getElementById('data').textContent);let selected='Overview';
const sections={'Overview':{actor:data.actor,wallet:data.wallet,scope:data.scope},'Received accounts':data.received,'Acquired capacity':data.acquired,'Interpretations':data.bindings,'Owned work':data.own_jobs,'Pending deliveries':data.pending_deliveries};if(data.offline_evaluator)sections['Evaluator history']=data.offline_evaluator;
document.getElementById('intro').textContent='Inspecting '+data.actor+' · Paid work, retained capacity, and the history behind the result.';
function render(){const q=document.getElementById('query').value.toLowerCase();let value=sections[selected];const host=document.getElementById('content');host.replaceChildren();const rows=Array.isArray(value)?value:[value];let count=0;rows.forEach((r,i)=>{const raw=JSON.stringify(r,null,2);if(q&&!raw.toLowerCase().includes(q))return;count++;const d=document.createElement('details'),s=document.createElement('summary'),p=document.createElement('pre');s.textContent=(r&&r.label)||('Record '+(i+1));p.textContent=raw;d.open=rows.length<4;d.append(s,p);host.append(d)});if(!count){const p=document.createElement('p');p.textContent='No matching records.';host.append(p)}document.querySelectorAll('nav button').forEach(b=>b.setAttribute('aria-selected',b.textContent===selected))}
Object.keys(sections).forEach(k=>{const b=document.createElement('button');b.textContent=k;b.onclick=()=>{selected=k;render()};document.getElementById('tabs').append(b)});document.getElementById('query').addEventListener('input',render);render();
</script></html>'''.replace('PAYLOAD',payload)
    Path(path).write_text(doc)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('checkpoint',type=Path)
    p.add_argument('--actor',default='alice');p.add_argument('--assess',action='store_true')
    p.add_argument('--object');p.add_argument('--revision',type=int);p.add_argument('--html',type=Path)
    p.add_argument('--out',type=Path)
    a=p.parse_args();e=load_engine(a.checkpoint)
    result=inspect(e,a.actor,a.assess,a.object,a.revision)
    if a.html:write_html(a.html,result)
    if a.out:write_json(a.out,result)
    if not a.html and not a.out:print(json.dumps(result,indent=2))


if __name__=='__main__':main()
