// Actual Second Scan template JavaScript with DOM/transport adapters.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const script = fs.readFileSync(path.join(__dirname,'../templates/receiving/second_scan_scanner.html'),'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
const settle = () => new Promise(resolve => setImmediate(resolve));
function setup(responses = []) {
  const nodes = new Map(); let focus = null; const requests = [];
  function node(id) {
    if (!nodes.has(id)) nodes.set(id,{value:'',listeners:{},children:[],textContent:'',
      addEventListener(type,fn){this.listeners[type]=fn;},
      focus(){focus=id;},select(){this.selected=true;},
      replaceChildren(){this.children=[];},append(...items){this.children.push(...items);}});
    return nodes.get(id);
  }
  const state = {location:'',scanned:0,total:2,phase:'WAITING_LOCATION',recent:[]};
  node('second-state').textContent = JSON.stringify(state);
  node('second-scan-form').getAttribute = () => '/containers/12/second-scan/';
  node('second-scan-form').action = {toString(){return '[object HTMLInputElement]';}};
  node('second-scan-form').querySelector = () => ({value:'csrf'});
  let resolveGate;
  let gate = null;
  vm.runInNewContext(script,{JSON,
    document:{getElementById:node,createElement:()=>({children:[],textContent:'',append(...items){this.children.push(...items);}})},
    FormData:class {constructor(){this.data={};}set(key,value){this.data[key]=value;}},
    async fetch(url,options){
      assert.equal(url,'/containers/12/second-scan/');
      requests.push({url,...options.body.data});
      if(gate) await gate;
      const result=responses.shift() || {ok:true,message:'Accepted',state};
      return {json:async()=>result};
    }
  });
  return {node,requests,focus:()=>focus,
    hold(){gate=new Promise(resolve=>{resolveGate=resolve;});},release(){resolveGate();gate=null;},
    enter(value,repeat=false){node('second-barcode').value=value;let prevented=false;node('second-barcode').listeners.keydown({key:'Enter',repeat,preventDefault(){prevented=true;}});assert.ok(prevented);},
    submit(value){node('second-barcode').value=value;node('second-scan-form').listeners.submit({preventDefault(){}});}
  };
}
test('Enter continuously sends location, movement, product and serial once each to real endpoint',async()=>{
  const s=setup();
  for(const value of ['AA010','101','XM0STBFR148','SERIAL-A','102','XM0STBFR148','SERIAL-B']){
    s.enter(value);await settle();
    assert.equal(s.node('second-barcode').value,'');
    assert.equal(s.focus(),'second-barcode');
  }
  assert.equal(s.requests.length,7);
  assert.deepEqual(s.requests.map(r=>r.barcode),['AA010','101','XM0STBFR148','SERIAL-A','102','XM0STBFR148','SERIAL-B']);
  assert.ok(s.requests.every(r=>r.action==='scan'&&!r.url.includes('[object')));
});
test('Enter + submit + held Enter cannot double register',async()=>{
  const s=setup();s.hold();s.enter('AA010');s.submit('AA010');s.enter('AA010',true);
  assert.equal(s.requests.length,1);assert.equal(s.node('second-barcode').readOnly,true);
  s.release();await settle();assert.equal(s.node('second-barcode').readOnly,false);
});
test('Register scan remains the same endpoint manual fallback',async()=>{
  const s=setup();s.submit('AA010');await settle();assert.equal(s.requests.length,1);assert.equal(s.requests[0].action,'scan');
});
test('Handled mismatch clears/refocuses and shows STOP without changing count',async()=>{
  const s=setup([{ok:false,message:'LABEL / BIKE MISMATCH — STOP',state:{phase:'WAITING_PRODUCT',location:'AA010',scanned:0,total:2,movement:'101',expected_product:'XM0STBFR148',bike_location:'AA010',recent:[]}}]);
  s.enter('WRONG');await settle();assert.match(s.node('second-feedback').textContent,/MISMATCH/);
  assert.equal(s.node('second-count').textContent,'0 / 2');assert.equal(s.node('second-barcode').value,'');assert.equal(s.focus(),'second-barcode');
});
test('Completed bike immediately updates counters and recent serial/product/location',async()=>{
  const s=setup([{ok:true,message:'Bike complete',state:{phase:'WAITING_MOVEMENT',location:'AA010',scanned:1,total:2,recent:[{movement:'101',location:'AA010',product_code:'XM0STBFR148',serial:'SERIAL-A'}]}}]);
  s.enter('SERIAL-A');await settle();assert.equal(s.node('second-count').textContent,'1 / 2');
  const row=s.node('second-history').children[0];assert.deepEqual(row.children.map(c=>c.textContent),['AA010 · Movement 101','XM0STBFR148','SERIAL-A']);
});
test('Finish reveals download-only links and disables scanning',async()=>{
  const s=setup([{ok:true,message:'Finished',state:{phase:'FINISHED',location:'AA010',scanned:2,total:2,recent:[]}}]);
  s.node('second-finish').listeners.click();await settle();assert.equal(s.requests[0].action,'finish');
  assert.equal(s.node('second-downloads').hidden,false);assert.equal(s.node('second-barcode').disabled,true);
});
