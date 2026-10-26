const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');

class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.textContent = ''; this.listeners = {}; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; }
  addEventListener(name, fn) { this.listeners[name] = fn; }
  set innerHTML(value) { throw new Error('Unsafe HTML insertion is forbidden in Module 2.'); }
}

async function main() {
  const handlers = {};
  const nodes = { '#tracking-result': new Element('div'), '#registration-result': new Element('div') };
  let response;
  const context = vm.createContext({
    $: selector => nodes[selector],
    bindForm: (selector, fn) => { handlers[selector] = fn; },
    api: async () => response,
    document: { createElement: tag => new Element(tag), createTextNode: value => value },
    toast() {}, Date, Object, encodeURIComponent,
    navigator: { clipboard: { writeText: async () => {} } }
  });
  vm.runInContext(fs.readFileSync('static/js/module2.js', 'utf8'), context);
  const attack = '<script>alert(1)</script>';
  response = { history: [{ status: attack, created: '2026-10-26T00:00:00Z' }] };
  await handlers['#track-form']({}, new Map([['number','KC-'+'A'.repeat(32)]]));
  const status = nodes['#tracking-result'].children[0].children[0].children[0];
  assert.equal(status.textContent, attack);
  assert.equal(status.tag, 'strong');
  response = { tracking: attack, id: 12 };
  await handlers['#parcel-form']({ reset() {} }, new Map());
  const panel = nodes['#registration-result'].children[0];
  assert.equal(panel.children[1].textContent, attack);
  assert.equal(panel.children[4].href, '/parcels/12');
  console.log('PASS: Module 2 registration and tracking use safe DOM text, preserve details link, and never insert HTML.');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
