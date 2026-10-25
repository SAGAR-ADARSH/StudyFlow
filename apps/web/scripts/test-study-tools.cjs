// Focused DOM tests, without a browser download or running backend.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const Module = require('node:module');
const ts = require('typescript');
const { JSDOM } = require('jsdom');
const dom = new JSDOM('<!doctype html><html><body></body></html>', { url: 'http://localhost' });
global.window = dom.window;
global.document = dom.window.document;
global.navigator = dom.window.navigator;
global.HTMLElement = dom.window.HTMLElement;
global.localStorage = dom.window.localStorage;
global.IS_REACT_ACT_ENVIRONMENT = true;
const root = path.resolve(__dirname, '..');
const resolve = Module._resolveFilename;
Module._resolveFilename = function (name, ...args) {
  return resolve.call(this, name.startsWith('@/') ? path.join(root, name.slice(2)) : name, ...args);
};
for (const ext of ['.ts', '.tsx']) {
  require.extensions[ext] = (mod, filename) => mod._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
  }).outputText, filename);
}
const React = require('react');
const { act } = React;
const { createRoot } = require('react-dom/client');
const { TasksPanel } = require('../app/dashboard/tasks-panel.tsx');
const { FlashcardsPanel } = require('../app/dashboard/flashcards-panel.tsx');
const { StudyTimerPanel } = require('../app/dashboard/study-timer.tsx');
const { AnalyticsPanel } = require('../app/dashboard/analytics-panel.tsx');
const subjects = [{ id: 1, name: 'OS' }];
async function mount(Component, props, handler) {
  const calls = [];
  global.fetch = async (url, options) => { calls.push([url, options]); return handler(url, options); };
  const el = document.createElement('div'); document.body.append(el);
  const app = createRoot(el);
  await act(async () => { app.render(React.createElement(Component, props)); });
  return { el, calls, async close() { await act(async () => app.unmount()); el.remove(); } };
}
function response(value, status=200) { return { ok: status < 400, status, json: async () => value }; }
async function click(el) { await act(async () => el.dispatchEvent(new window.MouseEvent('click', { bubbles: true }))); }
function button(el, text) { return [...el.querySelectorAll('button')].find((b) => b.textContent.includes(text)); }
(async () => {
  // Loading state stays visible while an API request is pending, then error is readable.
  for (const [Comp, props] of [[TasksPanel,{subjects,topics:[],exams:[]}],[FlashcardsPanel,{subjects,topics:[]}],[StudyTimerPanel,{subjects,topics:[]}],[AnalyticsPanel,{}]]) {
    let release;
    const pending = new Promise((r) => { release = r; });
    const t = await mount(Comp, props, async () => { await pending; return response({ detail: 'Service unavailable' }, 503); });
    assert.match(t.el.textContent, /Loading/);
    await act(async () => release());
    assert.match(t.el.querySelector('[role="alert"]').textContent, /Service unavailable/);
    await t.close();
  }
  const task = { id:1,title:'Revise OS',status:'Pending',priority:'High',is_overdue:true,due_date:'2020-01-01',priority_score:100 };
  const tasks = await mount(TasksPanel,{subjects,topics:[],exams:[]}, async (url, opts) => opts?.method === 'PUT' ? response({detail:'Cannot save task'},400) : response([task]));
  assert.match(tasks.el.textContent, /Overdue \(1\)/);
  await click(tasks.el.querySelector('input[type="checkbox"][class]'));
  assert.match(tasks.el.querySelector('[role="alert"]').textContent, /Cannot save task/);
  await tasks.close();
  const card = { id:1,front:'What is a process?',back:'A running program.',review_status:'needs_revision',subject_id:1,is_generated:false };
  const cards = await mount(FlashcardsPanel,{subjects,topics:[]}, async (url, opts) => {
    if (url.includes('/documents')) return response({ items: [] });
    if (url.includes('/notes')) return response([]);
    if (opts?.method === 'PATCH') return response({...card,review_status:'known'});
    return response([card]);
  });
  await click(button(cards.el,'Enter Study Mode'));
  const flip = cards.el.querySelector('[aria-label="Flip card"]');
  await act(async () => flip.dispatchEvent(new window.KeyboardEvent('keydown',{key:'Enter',bubbles:true})));
  assert.match(flip.textContent,/Answer/);
  await click(button(cards.el,'Mark as Known'));
  assert.ok(cards.calls.some(([url,opts]) => url.endsWith('/review') && JSON.parse(opts.body).review_status === 'known'));
  await cards.close();
  const session = {id:1,subject_name:'OS',status:'paused',elapsed_seconds:125,created_at:'2026-10-18T10:00:00'};
  const timer = await mount(StudyTimerPanel,{subjects,topics:[]}, async (url,opts) => {
    if (opts?.method === 'POST') return response({...session,status:'active'});
    return response(url.endsWith('/active') ? session : [session]);
  });
  assert.match(timer.el.textContent, /02:05/);
  await click(button(timer.el,'Resume'));
  assert.ok(timer.calls.some(([url]) => url.endsWith('/resume')));
  await timer.close();
  console.log('PASS: 4 loading/error states; task save failure; flashcard keyboard flip/review API; paused timer recovery/resume.');
})().catch((error) => { console.error(error); process.exitCode = 1; });
