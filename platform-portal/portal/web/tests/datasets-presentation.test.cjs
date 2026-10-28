'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const src=fs.readFileSync(path.join(__dirname,'../public-datasets.js'),'utf8');
const encounter='source=synthea/source_version=v3.3.0/ingest_date=2026-10-25/batch_id=synthea-new-only-gh-40208104106/entity=encounter/run_id=task004-encounter-20261025T154424Z-9/work/normalized/data';
const patient=encounter.replace('entity=encounter/run_id=task004-encounter','entity=patient/run_id=task004-person');
const landingPrefix='source=synthea/source_version=v3.3.0/ingest_date=2026-10-25/batch_id=synthea-new-only-gh-40208104106';
const landingNames=['manifest.json','encounters.csv','patients.csv'].map(name=>landingPrefix+'/'+name);
function el(text=''){
  const attributes=new Map();
  return {textContent:text,href:'',
    getAttribute:k=>attributes.has(k)?attributes.get(k):null,
    setAttribute:(k,v)=>attributes.set(k,String(v)),
    removeAttribute:k=>attributes.delete(k),
    querySelector:()=>null,querySelectorAll:()=>[],click:()=>{}};
}
function setup({route='/datasets',chosen=null,ns='s3://health-processing',data=[encounter,patient],options=[]}={}){
  const headers=['NAME','NAMESPACE','SOURCE','UPDATED AT','QUALITY','COLUMN LINEAGE'].map(el);
  const rows=data.map(name=>{
    const cells=Array.from({length:6},(_,i)=>el(i===1||i===2?ns:''));
    const link=el(),span=el('source=synthea/source_version=v3.3.0/ing...');
    link.href='http://local/lineage/dataset/'+encodeURIComponent(ns)+'/'+encodeURIComponent(name);
    link.querySelector=q=>q==='span'?span:null;
    cells[0].querySelector=q=>q.includes('a[')?link:null;
    return {querySelectorAll:q=>q==='td'?cells:[],cells,link,span};
  });
  const table={querySelector:q=>q==='thead tr'?{querySelectorAll:()=>headers}:null,
    querySelectorAll:q=>q==='tbody tr'?rows:[]};
  const selector=el(ns),saved=new Map(),selected=[];let opened=0;
  if(chosen!==null)saved.set('selectedNamespace',chosen);
  selector.click=()=>opened++;
  const opt=options.map(o=>{const e=el(o);e.click=()=>{selected.push(o);saved.set('selectedNamespace',o)};return e;});
  const doc={readyState:'complete',body:{},getElementById:id=>id==='namespace-select'?selector:null,
    querySelectorAll:q=>q==='table'?[table]:q==='[role="option"]'?opt:[],addEventListener(){}};
  const win={location:{pathname:route,href:'http://local'+route},
    localStorage:{getItem:k=>saved.has(k)?saved.get(k):null},addEventListener(){}};
  let update;class Observer{constructor(fn){update=fn}observe(){}}
  vm.runInNewContext(src,{window:win,document:doc,URL,MutationObserver:Observer});
  return {headers,rows,selector,saved,selected,opened:()=>opened,update};
}
test('first-visit DataSets picks real processing data; prior selection and Jobs remain untouched',()=>{
  const a=setup({ns:'default'});assert.equal(a.opened(),1);a.update();assert.equal(a.opened(),1);
  const b=setup({ns:'default',options:['default','s3://health-processing']});
  assert.deepEqual(b.selected,['s3://health-processing']);
  assert.equal(b.saved.get('selectedNamespace'),'s3://health-processing');
  assert.equal(setup({ns:'default',chosen:'default'}).opened(),0);
  assert.equal(setup({route:'/jobs',ns:'default'}).opened(),0);
});
test('show real Encounter and Patient, exact Batch/date/Run, unmodified lineage hrefs, original source tooltip',()=>{
  const x=setup({chosen:'s3://health-processing'});
  assert.deepEqual(x.headers.slice(0,3).map(h=>h.textContent),['DATASET','BATCH','INGEST DATE']);
  assert.equal(x.rows[0].span.textContent,'Encounter');
  assert.equal(x.rows[1].span.textContent,'Patient');
  assert.equal(x.rows[0].cells[1].textContent,'40208104106');
  assert.equal(x.rows[0].cells[2].textContent,'2026-10-25');
  assert.equal(x.rows[0].link.getAttribute('data-public-description'),'Run: task004-encounter-20261025T154424Z-9');
  assert.equal(x.rows[0].link.getAttribute('title'),encounter);
  assert.ok(x.rows[0].link.href.endsWith(encodeURIComponent(encounter)));
  assert.match(x.rows[0].cells[1].getAttribute('title'),/Namespace: s3:\/\/health-processing/);
  assert.match(x.rows[0].cells[2].getAttribute('title'),/Marquez Source: s3:\/\/health-processing\nProducer: synthea/);
  x.update();assert.equal(x.rows[0].span.textContent,'Encounter');
});
test('unknown/malformed data falls back, no false descriptions or unsanitized markup',()=>{
  assert.equal(setup({ns:'default',chosen:'default'}).headers[0].textContent,'NAME');
  const a=setup({data:['entity=encounter/ingest_date=2026-10-25']});
  assert.equal(a.headers[0].textContent,'NAME');
  const b=setup({data:['source=synthea/entity=<img src=x>/batch_id=x/ingest_date=2026-10-25/run_id=x']});
  assert.equal(b.rows[0].link.getAttribute('data-public-dataset'),null);
  assert.equal(b.headers[0].textContent,'NAME');
});
test('changing namespace restores upstream labels and visible values',()=>{
  const x=setup({chosen:'s3://health-processing'});
  x.selector.textContent='default';x.update();
  assert.deepEqual(x.headers.slice(0,3).map(h=>h.textContent),['NAME','NAMESPACE','SOURCE']);
  assert.equal(x.rows[0].span.textContent,'source=synthea/source_version=v3.3.0/ing...');
  assert.equal(x.rows[0].cells[1].textContent,'s3://health-processing');
  assert.equal(x.rows[0].link.getAttribute('data-public-dataset'),null);
});
test('packer injects readonly and UX scripts before original bundle and rejects double patch',()=>{
  const os=require('node:os'),{install}=require('../install-overlay.cjs');
  const d=fs.mkdtempSync(path.join(os.tmpdir(),'portal-public-'));
  try{
    fs.mkdirSync(path.join(d,'dist'));
    fs.writeFileSync(path.join(d,'dist/index.html'),'<html><head></head><body><script src="./bundle.js"></script></body></html>');
    const s=install(d);
    assert.ok(s.indexOf('public-readonly.js')<s.indexOf('public-datasets.js'));
    assert.ok(s.indexOf('public-datasets.js')<s.indexOf('bundle.js'));
    assert.match(s,/public-datasets.css/);
    assert.throws(()=>install(d),/Unsupported/);
  }finally{fs.rmSync(d,{recursive:true,force:true});}
});

test('real Landing uses distinct file types, full batch and ingest date without inventing a run',()=>{
  const x=setup({chosen:'s3://health-landing',ns:'s3://health-landing',data:landingNames});
  assert.deepEqual(x.headers.slice(0,3).map(h=>h.textContent),
    ['DATASET','BATCH','INGEST DATE']);
  assert.deepEqual(x.rows.map(r=>r.span.textContent),
    ['Batch Manifest','Encounters CSV','Patients CSV']);
  assert.deepEqual(x.rows.map(r=>r.link.getAttribute('data-public-description')),
    ['File: manifest.json','File: encounters.csv','File: patients.csv']);
  assert.deepEqual(x.rows.map(r=>r.cells[1].textContent),
    ['40208104106','40208104106','40208104106']);
  assert.deepEqual(x.rows.map(r=>r.cells[2].textContent),
    ['2026-10-25','2026-10-25','2026-10-25']);
  assert.match(x.rows[0].cells[1].getAttribute('title'),/Namespace: s3:\/\/health-landing/);
  assert.match(x.rows[0].cells[2].getAttribute('title'),/Marquez Source: s3:\/\/health-landing/);
  for(let i=0;i<3;i++){
    assert.ok(x.rows[i].link.href.endsWith(encodeURIComponent(landingNames[i])));
    assert.equal(x.rows[i].link.getAttribute('title'),landingNames[i]);
  }
  x.update();
  assert.equal(x.rows[2].span.textContent,'Patients CSV','re-render remains stable');
});
test('all 12 public Landing records are differentiated by exact (batch,file), not timestamps',()=>{
  const batches=['39625216978','40186737808','40194178133','40208104106'];
  const names=batches.flatMap(b=>['manifest.json','encounters.csv','patients.csv'].map(file=>
    'source=synthea/source_version=v3.3.0/ingest_date=2026-10-25/batch_id=synthea-new-only-gh-'+b+'/'+file));
  const x=setup({chosen:'s3://health-landing',ns:'s3://health-landing',data:names});
  assert.equal(x.rows.length,12);
  const keys=x.rows.map(r=>r.cells[1].textContent+'|'+r.span.textContent);
  assert.equal(new Set(keys).size,12);
});
test('unknown landing leaf or partial metadata retains honest Marquez default and links',()=>{
  for(const name of [
    landingPrefix+'/unverified_file.csv',
    'source=synthea/ingest_date=2026-10-25/manifest.json',
    'source=synthea/batch_id=synthea-new-only-gh-40208104106/manifest.json'
  ]){
    const x=setup({chosen:'s3://health-landing',ns:'s3://health-landing',data:[name]});
    assert.equal(x.headers[0].textContent,'NAME');
    assert.equal(x.rows[0].span.textContent,'source=synthea/source_version=v3.3.0/ing...');
    assert.equal(x.rows[0].link.getAttribute('data-public-dataset'),null);
  }
});
