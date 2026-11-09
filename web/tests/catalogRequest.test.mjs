import {test} from 'node:test';
import assert from 'node:assert/strict';
import {requestCatalog} from '../src/catalogRequest.ts';

test('a stalled request falls back, even when fetch ignores cancellation',async t=>{
  let calls=0;
  t.mock.method(globalThis,'fetch',()=>++calls===1?new Promise(()=>{}):Promise.resolve(Response.json({data:[]})));
  assert.deepEqual(await requestCatalog(['https://primary','https://fallback'],'/public/test',new AbortController().signal,10),[]);
  assert.equal(calls,2);
});
test('all stalled endpoints finish with an error',async t=>{
  t.mock.method(globalThis,'fetch',()=>new Promise(()=>{}));
  await assert.rejects(requestCatalog(['https://primary','https://fallback'],'/public/test',new AbortController().signal,10),/catalogue_unavailable/);
});
test('leaving the page cancels without starting fallback',async t=>{
  let calls=0;
  t.mock.method(globalThis,'fetch',()=>{calls++;return new Promise(()=>{});});
  const controller=new AbortController();
  const request=requestCatalog(['https://primary','https://fallback'],'/public/test',controller.signal,1000);
  controller.abort();
  await assert.rejects(request,/aborted/);
  assert.equal(calls,1);
});
test('invalid payload cannot appear as a successful empty catalogue',async t=>{
  t.mock.method(globalThis,'fetch',async()=>Response.json({message:'unavailable'}));
  await assert.rejects(requestCatalog(['https://primary'],'/public/test',new AbortController().signal),/catalogue_unavailable/);
});
test('HTTP failures fall back and duplicate endpoints are not repeated',async t=>{
  const calls=[];
  t.mock.method(globalThis,'fetch',async url=>{
    calls.push(url);
    return calls.length===1?new Response('',{status:503}):Response.json({data:[]});
  });
  assert.deepEqual(await requestCatalog(['https://primary','https://primary','https://fallback'],'/public/test',new AbortController().signal),[]);
  assert.deepEqual(calls,['https://primary/public/test','https://fallback/public/test']);
});
