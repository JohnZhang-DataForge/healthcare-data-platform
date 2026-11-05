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
function setup({route='/datasets',chosen=null,ns='s3://health-processing',
               data=[encounter,patient],options=[],showEmpty=false,refreshLoadsContent=true}={}){
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
  const selector=el(ns),saved=new Map(),session=new Map(),selected=[],redirected=[],timers=[];
  let opened=0,refreshClicks=0,emptyVisible=showEmpty;
  if(chosen!==null)saved.set('selectedNamespace',chosen);
  selector.click=()=>opened++;
  const opt=options.map(o=>{const e=el(o);e.click=()=>{selected.push(o);saved.set('selectedNamespace',o);selector.textContent=o};return e;});
  const emptyButton=el('Refresh');
  emptyButton.click=()=>{refreshClicks++;if(refreshLoadsContent)emptyVisible=false};
  const listeners={};
  const doc={readyState:'complete',body:{},getElementById:id=>id==='namespace-select'?selector:null,
    querySelectorAll:q=>q==='table'?[table]:q==='[role="option"]'?opt:q==='button'?(emptyVisible?[emptyButton]:[]):[],
    addEventListener:(type,handler)=>{listeners[type]=handler}};
  const win={location:{pathname:route.split('?')[0],href:'http://local'+route,
    search:route.includes('?')?'?'+route.split('?').slice(1).join('?'):'',hash:'',
    replace:u=>redirected.push(u)},
    setTimeout:fn=>{timers.push(fn);return timers.length},
    clearTimeout:id=>{timers[id-1]=null},
    localStorage:{getItem:k=>saved.has(k)?saved.get(k):null},
    sessionStorage:{
      getItem:k=>session.has(k)?session.get(k):null,
      setItem:(k,v)=>session.set(k,v),
      removeItem:k=>session.delete(k)
    },addEventListener(){}};
  let update;class Observer{constructor(fn){update=fn}observe(){}}
  vm.runInNewContext(src,{window:win,document:doc,URL,MutationObserver:Observer});
  const manualChoose=value=>{
    const option=opt.find(o=>o.textContent===value);
    if(!option)throw Error('Unavailable manual option '+value);
    listeners.click({target:{closest:()=>option}});
    option.click();
    update();
  };
  const flushTimers=()=>{
    const tasks=timers.splice(0,timers.length);
    tasks.forEach(fn=>{if(fn)fn()});
  };
  return {headers,rows,selector,saved,session,selected,redirected,
    opened:()=>opened,refreshClicks:()=>refreshClicks,flushTimers,update,win,manualChoose};
}
test('public trailing slash route displays Processing and Landing, with exact preserved dataset hrefs',()=>{
  for(const route of ['/datasets','/datasets/']){
    const p=setup({route,chosen:'s3://health-processing'});
    assert.deepEqual(p.headers.slice(0,3).map(h=>h.textContent),['DATASET','BATCH','INGEST DATE'],route+' Processing');
    assert.equal(p.rows[0].span.textContent,'Encounter');
    assert.equal(p.rows[1].span.textContent,'Patient');
    assert.equal(p.rows[0].link.getAttribute('data-public-description'),'Run: task004-encounter-20261025T154424Z-9');
    assert.ok(p.rows[0].link.href.endsWith(encodeURIComponent(encounter)));
    const l=setup({route,chosen:'s3://health-landing',ns:'s3://health-landing',data:landingNames});
    assert.deepEqual(l.headers.slice(0,3).map(h=>h.textContent),['DATASET','BATCH','INGEST DATE'],route+' Landing');
    assert.deepEqual(l.rows.map(r=>r.span.textContent),['Batch Manifest','Encounters CSV','Patients CSV']);
    assert.deepEqual(l.rows.map(r=>r.link.getAttribute('data-public-description')),['File: manifest.json','File: encounters.csv','File: patients.csv']);
    assert.ok(l.rows.every(r=>r.cells[1].textContent==='40208104106'));
    assert.ok(l.rows.every(r=>r.link.getAttribute('title')!==null));
    const first=setup({route,ns:'default'});
    assert.equal(first.opened(),1,'first visitor opens namespace selector on '+route);
    const chosen=setup({route,ns:'s3://health-processing',chosen:'s3://health-processing'});
    assert.equal(chosen.opened(),0,'explicit useful Processing choice preserved on '+route);
  }
  for(const route of ['/jobs','/jobs/']){
    const jobs=setup({route,ns:'default'});
    assert.equal(jobs.opened(),1,'Jobs must pick an actual nonempty namespace on '+route);
    assert.equal(jobs.headers[0].textContent,'NAME','Jobs table must remain native');
  }
  for(const route of ['/datasets/some-other-path','/datasets-old','/lineage/job/x/y']){
    const other=setup({route,ns:'default'});
    assert.equal(other.opened(),0,route+' must not trigger namespace popup');
    assert.equal(other.headers[0].textContent,'NAME',route+' must not rewrite unrelated tables');
  }
});

test('first-visit Datasets picks Landing and Jobs picks actual Airflow separately',()=>{
  const a=setup({ns:'default'});assert.equal(a.opened(),1);a.update();assert.equal(a.opened(),1);
  const b=setup({ns:'default',options:['default','s3://health-landing']});
  assert.deepEqual(b.selected,['s3://health-landing']);
  assert.equal(b.saved.get('selectedNamespace'),'s3://health-landing');
  assert.equal(setup({ns:'default',chosen:'default',options:['s3://health-landing']}).selected[0],
    's3://health-landing','empty default is not a good showcase');
  const jobs=setup({route:'/jobs',ns:'s3://health-landing',chosen:'s3://health-landing',
    options:['s3://health-landing','healthcare-platform-airflow']});
  assert.deepEqual(jobs.selected,['healthcare-platform-airflow']);
  assert.equal(jobs.saved.get('selectedNamespace'),'healthcare-platform-airflow');
  assert.equal(jobs.headers[0].textContent,'NAME','native Jobs table untouched');
});

test('public root is native Marquez Dashboard, never redirects or mutates namespace',()=>{
  for(const route of ['/','/?utm_source=chatgpt.com']){
    const native=setup({route,chosen:'healthcare-platform-airflow',
      ns:'healthcare-platform-airflow',options:['s3://health-landing']});
    assert.deepEqual(native.redirected,[],route+' retains native Dashboard');
    assert.equal(native.opened(),0);
    assert.equal(native.selected.length,0);
    assert.equal(native.session.size,0);
  }
  for(const route of ['/jobs','/datasets','/lineage/job/x/y','/datasets/column-level/foo']){
    assert.deepEqual(setup({route,chosen:'s3://health-processing'}).redirected,[]);
  }
});
test('return to Datasets independently selects Landing; direct useful Processing bookmark remains valid',()=>{
  const x=setup({route:'/datasets',chosen:'healthcare-platform-airflow',
    ns:'healthcare-platform-airflow',options:['s3://health-landing']});
  assert.deepEqual(x.selected,['s3://health-landing']);
  x.update();
  assert.equal(x.session.get('publicMarquezDatasetsNamespace'),'s3://health-landing');
  const direct=setup({route:'/datasets',chosen:'s3://health-processing',
    ns:'s3://health-processing',options:['s3://health-landing']});
  assert.equal(direct.selected.length,0);
  assert.equal(direct.session.get('publicMarquezDatasetsNamespace'),'s3://health-processing');
});
test('live-proven Jobs namespace is preferred; fallback Spark Business never chooses empty Landing',()=>{
  const first=setup({route:'/jobs/',ns:'s3://health-landing',chosen:'s3://health-landing',
    options:['default','s3://health-landing','healthcare-platform-airflow','healthcare-platform-spark-business']});
  assert.deepEqual(first.selected,['healthcare-platform-airflow']);
  assert.equal(first.session.get('publicMarquezJobsNamespace'),undefined,
    'per-section choice is written after the MUI selector has rendered the new value');
  first.update();
  assert.equal(first.session.get('publicMarquezJobsNamespace'),'healthcare-platform-airflow');
  const fallback=setup({route:'/jobs',ns:'s3://health-landing',chosen:'s3://health-landing',
    options:['s3://health-landing','healthcare-platform-spark-business']});
  assert.deepEqual(fallback.selected,['healthcare-platform-spark-business']);
  fallback.update();
  assert.equal(fallback.session.get('publicMarquezJobsNamespace'),'healthcare-platform-spark-business');
});

test('tab navigation keeps useful independent defaults and honors visitor manual selection',()=>{
  const choices=['s3://health-landing','s3://health-processing',
    'healthcare-platform-airflow','healthcare-platform-spark-business'];
  const x=setup({route:'/datasets',ns:'s3://health-landing',chosen:'s3://health-landing',
    data:landingNames,options:choices});
  assert.equal(x.selector.textContent,'s3://health-landing');
  x.win.location.pathname='/jobs';x.update();
  assert.equal(x.selector.textContent,'healthcare-platform-airflow');
  assert.equal(x.session.get('publicMarquezJobsNamespace'),undefined);
  x.update();
  assert.equal(x.session.get('publicMarquezJobsNamespace'),'healthcare-platform-airflow');
  x.win.location.pathname='/datasets';x.update();
  assert.equal(x.selector.textContent,'s3://health-landing');
  x.update();
  x.manualChoose('s3://health-processing');
  assert.equal(x.session.get('publicMarquezDatasetsNamespace'),'s3://health-processing');
  x.win.location.pathname='/jobs';x.update();
  assert.equal(x.selector.textContent,'healthcare-platform-airflow');
  x.manualChoose('healthcare-platform-spark-business');
  assert.equal(x.session.get('publicMarquezJobsNamespace'),'healthcare-platform-spark-business');
  x.win.location.pathname='/datasets';x.update();
  assert.equal(x.selector.textContent,'s3://health-processing');
  x.win.location.pathname='/jobs';x.update();
  assert.equal(x.selector.textContent,'healthcare-platform-spark-business');
});

test('direct Dataset bookmark retains useful Processing but stale Jobs choice cannot hide datasets',()=>{
  const valid=setup({route:'/datasets/',chosen:'s3://health-processing',
    ns:'s3://health-processing',options:['s3://health-landing']});
  assert.equal(valid.selected.length,0);
  const invalid=setup({route:'/datasets',chosen:'healthcare-platform-airflow',
    ns:'healthcare-platform-airflow',options:['s3://health-landing']});
  assert.deepEqual(invalid.selected,['s3://health-landing']);
  const job=setup({route:'/jobs',chosen:'s3://health-landing',
    ns:'s3://health-landing',options:['healthcare-platform-airflow']});
  assert.deepEqual(job.selected,['healthcare-platform-airflow']);
  for(const route of ['/lineage/dataset/hello/world','/lineage/job/x/y','/jobs/some-job']){
    const detail=setup({route,ns:'s3://health-landing',options:['healthcare-platform-airflow']});
    assert.equal(detail.opened(),0);
    assert.equal(detail.selected.length,0);
  }
});
test('native Refresh is automatically invoked once for actual empty Jobs after namespace switch',()=>{
  const x=setup({route:'/jobs',chosen:'s3://health-landing',ns:'s3://health-landing',
    options:['s3://health-landing','healthcare-platform-airflow'],showEmpty:true});
  assert.deepEqual(x.selected,['healthcare-platform-airflow']);
  assert.equal(x.refreshClicks(),0,'wait until the selected Namespace is rendered');
  x.update();
  assert.equal(x.refreshClicks(),0,'the existing Redux fetch gets its first opportunity');
  x.flushTimers();
  assert.equal(x.refreshClicks(),1,'native MUI empty-state Refresh invoked without user click');
  x.update();x.flushTimers();
  assert.equal(x.refreshClicks(),1,'no duplicate HTTP requests or refresh loop');
});
test('Landing Datasets also self-refreshes once after native render when list incorrectly remains empty',()=>{
  const x=setup({route:'/datasets',chosen:'healthcare-platform-airflow',
    ns:'healthcare-platform-airflow',options:['s3://health-landing'],showEmpty:true});
  x.update();x.flushTimers();
  assert.deepEqual(x.selected,['s3://health-landing']);
  assert.equal(x.refreshClicks(),1);
  x.update();x.flushTimers();
  assert.equal(x.refreshClicks(),1);
});
test('empty-state retry is strictly bounded even if network data stays unavailable',()=>{
  const x=setup({route:'/jobs',chosen:'healthcare-platform-airflow',
    ns:'healthcare-platform-airflow',showEmpty:true,refreshLoadsContent:false});
  x.flushTimers();x.update();x.flushTimers();x.update();x.flushTimers();
  assert.equal(x.refreshClicks(),1,'genuinely empty API does not trigger repeated requests');
});
test('existing populated list never refreshes, including native Dashboard and detail routes',()=>{
  for(const route of ['/datasets','/jobs','/']){
    const x=setup({route,chosen:route==='/jobs'?'healthcare-platform-airflow':'s3://health-landing',
      ns:route==='/jobs'?'healthcare-platform-airflow':'s3://health-landing'});
    x.flushTimers();x.update();x.flushTimers();
    assert.equal(x.refreshClicks(),0,route+' must not generate an unnecessary request');
  }
  const deep=setup({route:'/lineage/job/n/id',showEmpty:true,
    chosen:'healthcare-platform-airflow',ns:'healthcare-platform-airflow'});
  deep.flushTimers();
  assert.equal(deep.refreshClicks(),0,'never click refresh on a lineage detail');
});
test('switching away before pending refresh fires cancels the stale refresh',()=>{
  const x=setup({route:'/jobs',chosen:'healthcare-platform-airflow',
    ns:'healthcare-platform-airflow',showEmpty:true});
  x.win.location.pathname='/';x.update();x.flushTimers();
  assert.equal(x.refreshClicks(),0,'no Jobs request after navigating to native Dashboard');
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
    for (const asset of ['public-readonly.css','public-datasets.css','public-readonly.js','public-datasets.js']) {
      fs.writeFileSync(path.join(d,'dist',asset), 'fixture for '+asset);
    }
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

test('fingerprinted script URLs change with content; stable assets keep stable cache keys',()=>{
  const {fingerprintUrl,install}=require('../install-overlay.cjs');
  const os=require('node:os');
  const d=fs.mkdtempSync(path.join(os.tmpdir(),'portal-fingerprint-'));
  try{
    fs.mkdirSync(path.join(d,'dist'));
    fs.writeFileSync(path.join(d,'dist/index.html'),'<html><head></head><body><script src="./bundle.js"></script></body></html>');
    const files=['public-readonly.css','public-datasets.css','public-readonly.js','public-datasets.js'];
    files.forEach((asset,i)=>fs.writeFileSync(path.join(d,'dist',asset),'version-one-'+i));
    const before=fingerprintUrl(d,'public-datasets.js');
    assert.match(before,/^\/public-datasets\.js\?v=[0-9a-f]{20}$/);
    const cssBefore=fingerprintUrl(d,'public-datasets.css');
    const output=install(d);
    assert.ok(output.includes(before));
    assert.ok(output.includes(cssBefore));
    fs.writeFileSync(path.join(d,'dist','public-datasets.js'),'version-two');
    assert.notEqual(fingerprintUrl(d,'public-datasets.js'),before);
    assert.equal(fingerprintUrl(d,'public-datasets.css'),cssBefore);
    assert.throws(()=>fingerprintUrl(d,'missing.js'),/ENOENT/);
  }finally{fs.rmSync(d,{recursive:true,force:true});}
});
