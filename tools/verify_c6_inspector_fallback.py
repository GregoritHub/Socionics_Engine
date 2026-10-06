"""Static HTML and real inline-script smoke check; explicitly not a visual render."""
import json,sys,os,subprocess
from pathlib import Path
from html.parser import HTMLParser
class Document(HTMLParser):
    def __init__(self):super().__init__();self.cells=[];self.ids=[];self.scripts=[];self.in_script=False
    def handle_starttag(self,tag,attributes):
        a=dict(attributes)
        if 'id' in a:self.ids.append(a['id'])
        if tag=='details' and a.get('class')=='cell':self.cells.append(a['data-search'])
        if tag=='script':
            assert 'src' not in a,'inspector must be self-contained';self.in_script=True
    def handle_endtag(self,tag):
        if tag=='script':self.in_script=False
    def handle_data(self,data):
        if self.in_script:self.scripts.append(data)
p=Document();p.feed(Path(sys.argv[1]).read_text());assert len(p.cells)==32 and len(set(p.ids))==len(p.ids) and {'filter','count'}<=set(p.ids)
checks=[('',32),('Embody',2),('accumulation',16),('does-not-exist',0),('',32)]
program='''const vm=require('vm');const input={value:'',addEventListener:(event,fn)=>{if(event!=='input')throw Error(event);input.listener=fn}};const count={textContent:''};const cells=CELLS.map(search=>({hidden:false,dataset:{search}}));const document={getElementById:id=>{if(id==='filter')return input;if(id==='count')return count;throw Error(id)},querySelectorAll:q=>{if(q!=='.cell')throw Error(q);return cells}};vm.runInNewContext(SCRIPT,{document});for(const [query,expected] of CHECKS){input.value=query;input.listener();const visible=cells.filter(x=>!x.hidden).length;if(visible!==expected||count.textContent!==expected+' cells shown')throw Error('filter mismatch '+query)}console.log('inline filter passed');'''
program=program.replace('CELLS',json.dumps(p.cells)).replace('SCRIPT',json.dumps(''.join(p.scripts))).replace('CHECKS',json.dumps(checks))
result=subprocess.run([os.environ.get('CODEX_PRIMARY_RUNTIME_NODE','node'),'-e',program],capture_output=True,text=True,check=True)
out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
(out/'summary.json').write_text(json.dumps(dict(passed=True,cells=32,filter_cases=checks,validation='HTML structure and actual inline JavaScript using a minimal DOM interface',visual_rendered=False,reason='Chromium binary unavailable; no visual-render claim',stdout=result.stdout),indent=2))
print(result.stdout,end='')
