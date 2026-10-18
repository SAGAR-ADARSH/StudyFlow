// Run against the running web app: node scripts/test-auth.cjs
// Uses the actual TypeScript client and an in-memory browser storage shim.
const ts = require('typescript');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const Module = require('node:module');
const base = process.env.WEB_URL || 'http://localhost:3000';
const storage = new Map();
global.window = {};
global.localStorage = {
  getItem: key => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, value),
  removeItem: key => storage.delete(key),
};
const realFetch = global.fetch;
global.fetch = (url, options) => {
  // Simulate a preview gateway consuming Authorization before Next.js sees it.
  const headers = new Headers(options?.headers);
  headers.delete('Authorization');
  return realFetch(new URL(url, base), { ...options, headers });
};
const code = ts.transpileModule(fs.readFileSync('lib/api.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText;
const mod = new Module('api-client');
mod._compile(code, 'api-client.cjs');
const api = mod.exports;
(async () => {
  await assert.rejects(api.getMe(), error => error instanceof api.ApiError && error.status === 401);
  const email = `auth-regression-${Date.now()}@studyflow.edu`;
  await api.register({ email, password: 'RegressionPass123', display_name: 'Auth regression' });
  assert.ok(api.getToken(), 'registration must store the token');
  assert.equal((await api.getMe()).email, email);
  api.clearToken();
  await api.login(email, 'RegressionPass123');
  assert.ok(api.getToken(), 'login must store the token');
  assert.equal((await api.getMe()).email, email);
  await Promise.all([api.getSemesters(), api.getSubjects(), api.getTopics(), api.getExams(), api.getDocuments()]);
  api.setToken('invalid');
  await assert.rejects(api.getMe(), error => error instanceof api.ApiError && error.status === 401);
  api.clearToken();
  console.log('PASS: register, login, token persistence, dashboard requests with Authorization stripped, invalid/missing token');
})().catch(error => { console.error(error); process.exitCode = 1; });
