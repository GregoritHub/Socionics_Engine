import sys
sys.dont_write_bytecode=True
from pathlib import Path
import dataclasses,gzip,hashlib,json
ROOT=Path(__file__).resolve().parent
import os
SOURCE=Path(os.environ.get('SHELL_ENGINE', str(ROOT/'engine')))
sys.path[:0]=[str(SOURCE),str(SOURCE/'baseline/HLE_Rebuild_R21B')]
def serial(v):
    if dataclasses.is_dataclass(v):return {'__type__':type(v).__name__,**{x.name:serial(getattr(v,x.name)) for x in dataclasses.fields(v)}}
    if isinstance(v,dict):return {str(k):serial(x) for k,x in v.items()}
    if isinstance(v,(tuple,list)):return [serial(x) for x in v]
    if isinstance(v,(str,int,float,bool)) or v is None:return v
    if hasattr(v,'value'):return v.value
    raise TypeError(type(v).__name__)
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(serial(v),indent=2,sort_keys=True)+'\n')
def save_checkpoint(path,engine,restore=True):
    cp=engine.checkpoint()
    if restore:assert type(engine).restore(cp).checkpoint()==cp
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('wb') as raw:
        with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as z:z.write(cp.encode())
    return hashlib.sha256(cp.encode()).hexdigest()
