/* Structural/functional DOM harness; explicitly not a rendered-browser test. */
const fs=require('fs'),vm=require('vm'),path=require('path');
const file=process.argv[2],out=process.argv[3],html=fs.readFileSync(file,'utf8');
const data=html.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const script=html.match(/<\/script><script>([\s\S]*?)<\/script>/)[1];
class Element{constructor(tag){this.tag=tag;this.children=[];this.textContent='';this.value='';this.events={};}append(...xs){this.children.push(...xs)}replaceChildren(...xs){this.children=xs}addEventListener(k,f){this.events[k]=f}}
const nodes={};for(const id of ['data','metrics','worlds','route','face','count','cells'])nodes[id]=new Element(id);
nodes.data.textContent=data;
const document={getElementById:id=>nodes[id],createElement:t=>new Element(t)};
vm.runInNewContext(script,{document,JSON,Set},{timeout:5000});
if(nodes.cells.children.length!==32)throw Error('matrix incomplete');
if(nodes.worlds.children.length!==6)throw Error('world panel incomplete');
if(nodes.metrics.children.length!==4)throw Error('metrics incomplete');
nodes.route.value='Educate';nodes.face.value='expenditure';nodes.route.events.change();
if(nodes.cells.children.length!==1)throw Error('filter mismatch');
if(!nodes.cells.children[0].children.some(x=>x.tag==='pre'&&x.textContent.includes('settings_gate')))throw Error('missing raw evidence');
nodes.route.value='';nodes.face.value='';nodes.face.events.change();if(nodes.cells.children.length!==32)throw Error('reset failed');
const d=JSON.parse(data);if(d.manifest.release_complete||d.ledger.some(x=>x.full_release_complete))throw Error('false release');
fs.mkdirSync(out,{recursive:true});fs.writeFileSync(path.join(out,'summary.json'),JSON.stringify({passed:true,mode:'Node VM structural and DOM-event harness',cells:32,worlds:6,filters:true,raw_evidence:true,release_open:true,visual_render_verified:false,reason:'Local Playwright Chromium executable unavailable; this is not a browser or pixel-rendering claim'},null,2));console.log('PASS structural inspector checks; visual render unverified');
