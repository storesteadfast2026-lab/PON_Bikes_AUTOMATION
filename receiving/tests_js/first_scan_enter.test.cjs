// Run: node --test receiving/tests_js/first_scan_enter.test.cjs
// Executes the actual template JavaScript with DOM/fetch adapters, no browser dependency.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const template = fs.readFileSync(path.join(__dirname, '../templates/receiving/first_scan_scanner.html'), 'utf8');
const script = template.match(/<script>\s*([\s\S]*?)\s*<\/script>/)[1];
const settle = () => new Promise(resolve => setImmediate(resolve));

function scanner({actionAttribute = '/containers/12/first-scan/'} = {}) {
  const nodes = new Map();
  let focused;
  const node = (id) => {
    if (!nodes.has(id)) nodes.set(id, {
      listeners: {}, value: '', textContent: '', disabled: false, readOnly: false,
      addEventListener(type, handler) { this.listeners[type] = handler; },
      focus() { focused = id; }, select() { this.selected = true; },
      children: [],
      replaceChildren() { this.children = []; },
      appendChild(child) { this.children.push(child); },
      append(...children) { this.children.push(...children); },
    });
    return nodes.get(id);
  };
  const input = node('scanned-value');
  const form = node('continuous-scan-form');
  const button = node('register-button');
  form.querySelector = () => button;
  // HTMLFormElement.action is shadowed by the hidden input named "action".
  form.action = {toString() { return '[object HTMLInputElement]'; }};
  form.getAttribute = (name) => name === 'action' ? actionAttribute : null;
  const state = {
    status: 'ACTIVE', elapsed_seconds: 0, paused_seconds: 0, active_seconds: 0,
    current_total: 0, expected_total: 10, current_pallet: '', pallet_total: 0,
    pallet_expected: null, completion: 0, pallet_completion: 0, recent: [], last_scan: null,
  };
  node('scanner-state').textContent = JSON.stringify(state);
  const requests = [];
  const events = [];
  let gate = null;
  let failNetwork = false;
  const context = {
    Date, JSON,
    document: {
      getElementById(id) { return id === 'scanner-photo-form' ? null : node(id); },
      createElement() { return {children: [], textContent: '',
        append(...children) { this.children.push(...children); },
        appendChild(child) { this.children.push(child); }}; },
      createTextNode(value) { return value; },
    },
    window: {location: {href: '/containers/12/first-scan/'}, setInterval() {}},
    FormData: class { constructor() { this.value = input.value; } },
    async fetch(url, options) {
      assert.equal(typeof url, 'string');
      assert.equal(url, '/containers/12/first-scan/');
      assert.ok(!url.includes('[object HTMLInputElement]'));
      requests.push({url, options, value: options.body.value});
      if (gate) await gate;
      if (failNetwork) throw new Error('network unavailable');
      const value = options.body.value;
      let result = 'SUCCESS', resolved = '', inputType = 'PALLET';
      if (/^T\d+$/.test(value)) {
        state.current_pallet = value;
        state.pallet_total = 0;
      } else if (['BIKE-A', 'LONG-A-0001'].includes(value) && state.current_pallet) {
        resolved = 'BIKE-A';
        inputType = value === 'BIKE-A' ? 'CODE' : 'LONG_CODE';
        state.current_total++;
        state.pallet_total++;
      } else {
        result = 'ERROR';
      }
      const event = {scanned_value: value, input_type: inputType, resolved_code: resolved,
        long_code: resolved ? 'LONG-A-0001' : '', pallet: state.current_pallet,
        result, message: result, time: '12:00:00'};
      events.push(event);
      state.last_scan = event;
      state.recent = events.filter(item => item.resolved_code && item.pallet === state.current_pallet).slice(-10).reverse();
      return {json: async () => ({ok: result === 'SUCCESS', level: result.toLowerCase(),
        message: result, state: JSON.parse(JSON.stringify(state))})};
    },
  };
  vm.runInNewContext(script, context);
  const dispatch = (target, type, details = {}) => {
    const event = {prevented: false, repeat: false, preventDefault() { this.prevented = true; }, ...details};
    target.listeners[type](event);
    return event;
  };
  return {
    input, button, form, node, state, requests, events,
    focused: () => focused,
    enter(value, details = {}) { input.value = value; return dispatch(input, 'keydown', {key: 'Enter', ...details}); },
    submit() { return dispatch(form, 'submit'); },
    block() { let release; gate = new Promise(resolve => { release = resolve; }); return release; },
    failNetwork() { failNetwork = true; },
  };
}

test('Enter registers a pallet and updates the displayed current pallet', async () => {
  const s = scanner();
  assert.equal(s.enter('T2525').prevented, true);
  await settle();
  assert.equal(s.events.length, 1);
  assert.equal(s.node('current-pallet').textContent, 'T2525');
  assert.equal(s.requests[0].options.headers['X-Requested-With'], 'XMLHttpRequest');
  assert.equal(s.requests[0].url, '/containers/12/first-scan/');
});

for (const [value, type] of [['BIKE-A', 'CODE'], ['LONG-A-0001', 'LONG_CODE']]) {
  test(`Enter registers ${type} through the existing scan POST`, async () => {
    const s = scanner();
    s.enter('T2525'); await settle();
    s.enter(value); await settle();
    assert.equal(s.events.at(-1).input_type, type);
    assert.equal(s.events.at(-1).pallet, 'T2525');
    assert.equal(s.node('container-total').textContent, 1);
    assert.equal(s.node('pallet-total').textContent, 1);
    assert.equal(s.node('recent-scans-body').children.length, 1);
    const recentValue = s.node('recent-scans-body').children[0].children[1];
    assert.ok(recentValue.children.includes(value));
  });
}

test('manual button form submit remains a fallback', async () => {
  const s = scanner(); s.input.value = 'T2525';
  assert.equal(s.submit().prevented, true);
  await settle();
  assert.equal(s.events.length, 1);
  assert.equal(s.events[0].scanned_value, 'T2525');
  assert.equal(s.requests[0].url, '/containers/12/first-scan/');
  assert.match(template, /type="submit">Register scan<\/button>/);
});

test('missing action attribute falls back to current URL despite the named action input', async () => {
  const s = scanner({actionAttribute: null});
  s.enter('T2525'); await settle();
  assert.equal(s.requests.length, 1);
  assert.equal(s.events.length, 1);
  assert.equal(s.requests[0].url, '/containers/12/first-scan/');
  assert.equal(s.input.value, '');
  assert.equal(s.focused(), 'scanned-value');
});

test('Enter plus submit and repeated keydown make exactly one request/event', async () => {
  const s = scanner(); const release = s.block();
  s.enter('T2525'); s.submit(); s.enter('T2525', {repeat: true});
  assert.equal(s.requests.length, 1);
  assert.equal(s.button.disabled, true);
  release(); await settle();
  assert.equal(s.events.length, 1);
  s.submit(); await settle();
  assert.equal(s.requests.length, 1);
});

test('success clears input and restores focus/readiness', async () => {
  const s = scanner(); s.enter('T2525'); await settle();
  assert.equal(s.input.value, '');
  assert.equal(s.input.readOnly, false);
  assert.equal(s.button.disabled, false);
  assert.equal(s.focused(), 'scanned-value');
});

test('continuous consecutive scans need no touch or confirmation', async () => {
  const s = scanner();
  for (const value of ['T2525', 'BIKE-A', 'LONG-A-0001', 'T2526', 'BIKE-A']) {
    s.enter(value); await settle();
    assert.equal(s.focused(), 'scanned-value');
    assert.equal(s.input.value, '');
  }
  assert.equal(s.events.length, 5);
  assert.equal(s.node('container-total').textContent, 3);
  assert.equal(s.node('pallet-total').textContent, 1);
  assert.equal(s.node('current-pallet').textContent, 'T2526');
});

test('handled invalid barcode clears/refocuses without increasing bike counts', async () => {
  const s = scanner(); s.enter('UNKNOWN'); await settle();
  assert.equal(s.events[0].result, 'ERROR');
  assert.equal(s.state.current_total, 0);
  assert.equal(s.input.value, '');
  assert.equal(s.focused(), 'scanned-value');
  s.enter('T2525'); await settle();
  assert.equal(s.events.at(-1).result, 'SUCCESS');
});

test('failed network keeps/selects value, unlocks input and does not retry automatically', async () => {
  const s = scanner(); s.failNetwork(); s.enter('T2525'); await settle();
  assert.equal(s.input.value, 'T2525');
  assert.equal(s.input.selected, true);
  assert.equal(s.input.readOnly, false);
  assert.equal(s.button.disabled, false);
  assert.equal(s.focused(), 'scanned-value');
  assert.equal(s.requests.length, 1);
});

test('keyboard-wedge Enter keyCode works without a virtual keyboard', async () => {
  const s = scanner(); s.enter('T2525', {key: 'Unidentified', keyCode: 13}); await settle();
  assert.equal(s.events.length, 1);
});
