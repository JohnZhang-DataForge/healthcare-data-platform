'use strict';
const test = require('node:test'), assert = require('node:assert/strict');
const fs = require('node:fs'), os = require('node:os'), path = require('node:path'), vm = require('node:vm');
const { install } = require('../install-overlay.cjs');
test('inject before original Web bundle, fail closed for changed template', () => {
  const d = fs.mkdtempSync(path.join(os.tmpdir(), 'portal-web-'));
  try {
    fs.mkdirSync(path.join(d, 'dist'));
    const f = path.join(d, 'dist/index.html');
    fs.writeFileSync(f, '<html><head></head><body><script src="./bundle.js"></script></body></html>');
    for (const asset of ['public-readonly.css','public-datasets.css','public-readonly.js','public-datasets.js']) {
      fs.writeFileSync(path.join(d,'dist',asset), 'asset bytes for '+asset);
    }
    const h = install(d);
    assert.ok(h.indexOf('public-readonly.js') < h.indexOf('./bundle.js'));
    assert.match(h, /public-readonly.css\?v=[0-9a-f]{20}/);
    assert.match(h, /public-readonly.js\?v=[0-9a-f]{20}/);
    assert.match(h, /public-datasets.js\?v=[0-9a-f]{20}/);
    assert.match(h, /public-datasets.css\?v=[0-9a-f]{20}/);
    assert.throws(() => install(d), /Unsupported/);
  } finally { fs.rmSync(d, { recursive: true, force: true }); }
});
test('Delete and Edit Tag disappear, View/Refresh still work, non-GET API rejected', async () => {
  const el = (s) => ({ textContent:s, hidden:false, style:{setProperty(k,v,priority) {this[k]=[v,priority];}}, setAttribute() {}, getAttribute() {return null;} });
  const del=el('Delete'),edit=el('Edit Tag'),fr=el('EFFACER'),es=el('ELIMINAR'),pl=el('USUNĄĆ'),zh=el('删除'),view=el('VIEW'),refresh=el('Refresh'),events=el('');
  const classes = new Set(), field = { disabled:false, tabIndex:0,
    closest:()=>({classList:{contains:(s)=>classes.has(s),add:(s)=>classes.add(s)}}) };
  const doc={readyState:'complete',body:{},querySelectorAll:(q)=>q==='input#dataset-tags'?[field]:[del,edit,fr,es,pl,zh,view,refresh],
    getElementById:(s)=>s==='eventsButton'?events:null};
  const seen=[];
  const win={location:{href:'https://example.org/'},fetch:(...p)=>{seen.push(p);return Promise.resolve('ok');}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../public-readonly.js'),'utf8'),
    {document:doc,window:win,URL,Promise,MutationObserver:class{observe(){}}});
  assert.equal(del.hidden,true);assert.equal(edit.hidden,true);assert.equal(fr.hidden,true);assert.equal(es.hidden,true);assert.equal(pl.hidden,true);assert.equal(zh.hidden,true);assert.equal(events.hidden,true);
  assert.deepEqual(del.style.display,['none','important']);assert.deepEqual(edit.style.display,['none','important']);
  assert.equal(view.hidden,false);assert.equal(refresh.hidden,false);assert.equal(field.disabled,true);
  assert.ok(classes.has('public-readonly-tags'));
  await assert.rejects(win.fetch('/api/v1/jobs',{method:'DELETE'}),/forbids/);
  await assert.rejects(win.fetch('/api/v2beta/search/jobs',{method:'POST'}),/forbids/);
  assert.equal(await win.fetch('/api/v1/lineage',{method:'GET'}),'ok');
  assert.equal(seen.length,1);
});
