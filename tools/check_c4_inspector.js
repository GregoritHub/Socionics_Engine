/* Standalone view-logic smoke check. This is not browser layout verification. */
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const file = path.join(root, 'docs/HLE_Full_Crux_C4_Inspector_v1.html');
const html = fs.readFileSync(file, 'utf8');
const json = html.match(/<script id="evidence" type="application\/json">([\s\S]*?)<\/script>/)[1];
const code = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const data = JSON.parse(json);
class Element {
  constructor() {
    this.innerHTML = ''; this.textContent = ''; this.selected = null;
    this.classes = new Set();
    this.classList = {toggle: (name, on) => on ? this.classes.add(name) : this.classes.delete(name)};
  }
  get value() { return this.selected ?? this.innerHTML.match(/<option>(.*?)<\/option>/)?.[1] ?? ''; }
  set value(x) { this.selected = x; }
}
const elements = new Map();
for (const match of html.matchAll(/\bid="([^"]+)"/g)) elements.set(match[1], new Element());
elements.get('evidence').textContent = json;
const sandbox = vm.createContext({document: {getElementById: id => {
  assert(elements.has(id), `Missing element ${id}`); return elements.get(id);
}}});
vm.runInContext(code, sandbox, {timeout: 3000});
const cases = [...new Set(data.witnesses.rows.map(r => r.name))];
let branches = 0;
for (const name of cases) {
  elements.get('case').value = name;
  elements.get('case').onchange();
  for (const control of [false, true]) {
    elements.get(control ? 'bad' : 'good').onclick();
    const row = data.witnesses.rows.find(r => r.name === name && r.control === control);
    const output = elements.get('detail').innerHTML;
    assert(output.includes(name));
    assert(output.includes(row.checkpoint_sha256));
    assert(output.includes(control ? 'Intervention rejected by semantic audit' : 'Independent audit passed'));
    assert(output.includes(`<strong>${row.focus_spent}</strong>`));
    assert(!output.includes('undefined'));
    assert(!output.includes('[object Object]'));
    assert.equal(elements.get('bad').classes.has('active'), control);
    assert.equal(elements.get('good').classes.has('active'), !control);
    branches++;
  }
}
assert.equal(elements.get('tests').textContent, 554);
assert(elements.get('blocked').textContent.includes('later permitted amount: 0'));
assert(elements.get('measure').innerHTML.includes('36 isolated workers'));
assert(html.includes('interrupted frozen-source run with recorded continuations'));
assert(!/(?:src|href)\s*=\s*["']https?:\/\//i.test(html));
assert(!html.includes('__DATA__'));
console.log(JSON.stringify({passed: true, evidence_cases: cases.length, branches_checked: branches,
  self_contained: true, displayed_tests: data.tests.tests, displayed_workers: data.measurements.workers,
  method: 'Node VM executes the actual inspector script with element state and event callbacks',
  limit: 'View logic and data checked; no browser engine was available for visual layout measurement'}, null, 2));
