#!/usr/bin/env node
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('discovery/index.html','utf8');
const data=JSON.parse(fs.readFileSync('data/discovery/candidates.json','utf8'));
assert.equal(Array.isArray(data.entries),true);
assert.equal(new Set(data.entries.map(x=>x.id)).size,data.entries.length);
assert.ok(data.entries.every(x=>/^https:\/\//.test(x.sourceUrl)));
assert.ok(html.includes("../data/discovery/candidates.json"));
const match=html.match(/<script>([\s\S]*?)<\/script>/);
assert.ok(match,'dashboard script exists');
new vm.Script(match[1],{filename:'discovery-dashboard.js'});
for(const key of ['untested','working','not-working','needs-files','needs-account','duplicate','needs-review'])assert.ok(match[1].includes("'"+key+"'"));
assert.ok(html.includes('localStorage')&&html.includes('Export review JSON')&&html.includes('Import review JSON'));
assert.ok(!match[1].includes('innerHTML'),'candidate text must not be injected as HTML');
console.log('PASS: dashboard syntax, candidate data, unique IDs, URLs, status controls and safe rendering ('+data.entries.length+' entries)');
