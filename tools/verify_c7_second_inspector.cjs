/* Structural and functional DOM verification; no pixel-rendering claim. */
const fs=require('fs'),vm=require('vm'),path=require('path');
const html=fs.readFileSync(process.argv[2],'utf8');
const data=html.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const script=html.match(/<\/script><script>([\s\S]*?)<\/script>/)[1];
class Element{constructor(tag){this.tag=tag;this.children=[];this.textContent='';this.value='';this.events={};}append(...xs){this.children.push(...xs)}replaceChildren(...xs){this.children=xs}addEventListener(k,f){this.events[k]=f}}
const nodes={};for(const id of ['data','metrics','route','face','count','cells'])nodes[id]=new Element(id);nodes.data.textContent=data;
vm.runInNewContext(script,{document:{getElementById:id=>nodes[id],createElement:t=>new Element(t)},JSON,Set},{timeout:5000});
if(nodes.cells.children.length!==32||nodes.metrics.children.length!==4)throw Error('missing cells or metrics');
const d=JSON.parse(data);
if(d.manifest.release_complete||d.ledger.some(x=>x.full_release_complete))throw Error('false full release');
if(d.ledger.some(x=>x.settings_gate.established!==2||x.type_cases!==16||!x.control.matched_main_cost||!x.independent_raw_reconstruction))throw Error('incomplete setting evidence');
for(const n of new Set(d.ledger.map(x=>x.name)))for(const f of ['accumulation','expenditure']){
 nodes.route.value=n;nodes.face.value=f;nodes.route.events.change();
 if(nodes.cells.children.length!==1||!nodes.cells.children[0].children.some(x=>x.tag==='pre'&&x.textContent.includes('second_setting_raw')))throw Error('filter or evidence failed');
}
nodes.route.value='';nodes.face.value='';nodes.face.events.change();if(nodes.cells.children.length!==32)throw Error('reset failed');
fs.mkdirSync(process.argv[3],{recursive:true});fs.writeFileSync(path.join(process.argv[3],'summary.json'),JSON.stringify({passed:true,cells:32,types:16,settings:2,filters:true,raw_evidence:true,release_open:true,visual_render_verified:false,mode:'Node VM structural and event harness; no local Chromium executable'},null,2));console.log('PASS: 32 cells, 2 settings, filters, evidence, and explicit release limits');
