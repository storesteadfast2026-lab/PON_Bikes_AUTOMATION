const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const template = fs.readFileSync(path.join(__dirname, '../templates/receiving/configure_import.html'), 'utf8');
const script = template.match(/<script>([\s\S]*?)<\/script>/)[1];
const settle = () => new Promise(resolve => setImmediate(resolve));
function setup() {
  const nodes = new Map(); const requests = [];
  function node(id) {
    if (!nodes.has(id)) nodes.set(id, {id, value:'', checked:false, disabled:false, textContent:'', dataset:{}, listeners:{}, children:[],
      addEventListener(type,fn){this.listeners[type]=fn;}, appendChild(item){this.children.push(item);return item;}, replaceChildren(...items){this.children=items;}});
    return nodes.get(id);
  }
  const fields = {
    sheet_name:Object.assign(node('id_sheet_name'),{value:'Manifest'}), start_row:Object.assign(node('id_start_row'),{value:'20'}),
    start_column:Object.assign(node('id_start_column'),{value:'D'}), code_column:Object.assign(node('id_code_column'),{value:'D'}),
    long_code_column:Object.assign(node('id_long_code_column'),{value:''}), description_column:Object.assign(node('id_description_column'),{value:'E'}),
    quantity_column:Object.assign(node('id_quantity_column'),{value:'F'}), container_column:Object.assign(node('id_container_column'),{value:'G'}),
    location_stream:Object.assign(node('id_location_stream'),{checked:false})};
  node('import-config-form').elements=fields; node('source-preview-wrap').dataset.previewUrl='/sources/9/source-preview/';
  for(const id of ['source-preview-table','reread-source-file','source-preview-note','preview-start-row','preview-start-column','preview-first-cell','summary-code','summary-long-code','summary-description','summary-quantity','summary-container','workbook-data-rows','workbook-bike-units','workbook-spare-units']) node(id);
  function element(tag){return {tag,textContent:'',className:'',children:[],colSpan:1,appendChild(item){this.children.push(item);return item;}};}
  vm.runInNewContext(script,{URLSearchParams,AbortController,document:{getElementById:node,createElement:element},async fetch(url){
    requests.push(url);const parsed=new URL(url,'http://test.local');const startRow=Number(parsed.searchParams.get('start_row'));const startColumn=parsed.searchParams.get('start_column');
    return {ok:true,json:async()=>({ok:true,detected_mapping:{code_column:'H',long_code_column:'',description_column:'I',quantity_column:'J',container_column:'K'},summary:{data_rows:69,bike_units:134,spare_units:6},preview:{start_row:startRow,start_column:startColumn,first_cell:`${startColumn}${startRow}`,columns:[{letter:startColumn,original_header:'Original source header',meaning:'Not mapped'}],rows:[{number:startRow,values:['VALUE']}]}})};
  }});
  return {node,fields,requests};
}
test('changing row immediately requests and displays the real row',async()=>{const s=setup();s.fields.start_row.value='21';s.fields.start_row.listeners.input();await settle();assert.match(s.requests[0],/start_row=21/);assert.equal(s.node('preview-start-row').textContent,21);assert.equal(s.node('preview-first-cell').textContent,'D21');});
test('changing column immediately requests and displays the real column',async()=>{const s=setup();s.fields.start_column.value='F';s.fields.start_column.listeners.input();await settle();assert.match(s.requests[0],/start_column=F/);assert.equal(s.node('preview-start-column').textContent,'F');assert.equal(s.node('preview-first-cell').textContent,'F20');});
test('re-read refreshes mapping through the read-only endpoint',async()=>{const s=setup();s.node('reread-source-file').listeners.click();await settle();assert.match(s.requests[0],/refresh_detection=1/);assert.equal(s.fields.code_column.value,'H');assert.equal(s.fields.description_column.value,'I');assert.equal(s.node('summary-code').textContent,'H');});

test('preview refresh updates data rows bike qty and spare parts qty',async()=>{const s=setup();s.fields.start_row.listeners.input();await settle();assert.equal(s.node('workbook-data-rows').textContent,69);assert.equal(s.node('workbook-bike-units').textContent,134);assert.equal(s.node('workbook-spare-units').textContent,6);});
