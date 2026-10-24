// ALL provider/budget requests below are mocked. Never reads real credentials.
const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const {createRequire}=require('node:module');
const path=require('node:path');
const filename=path.resolve('netlify/functions/infer.js');

async function invoke(provider,{audit=false,auditor=null,enabled=true,body={prompt:'offline contract fixture'}}={}){
 let calls=0;
 const context={exports:{},require:createRequire(filename),Buffer,AbortController,AbortSignal,setTimeout,clearTimeout,
  process:{env:{AGENT_ACCESS_TOKEN:'OFFLINE_CONTRACT_TOKEN_NOT_A_SECRET',COMPUTEPILOT_LIVE_ENABLED:enabled?'true':'false',OPENAI_API_KEY:'FIXTURE_ONLY',SUPABASE_URL:'https://budget.invalid',SUPABASE_SERVICE_ROLE_KEY:'FIXTURE_ONLY'}},
  fetch:async()=>{calls++;return{ok:true,status:200,json:async()=>calls===1?{approved:true}:calls===2?provider:auditor};}};
 vm.runInNewContext(fs.readFileSync(filename,'utf8'),context,{filename});
 const result=await context.exports.handler({httpMethod:'POST',headers:{'x-agent-token':'OFFLINE_CONTRACT_TOKEN_NOT_A_SECRET'},body:JSON.stringify(body===null?null:{...body,audit})});
 return {http:result.statusCode,body:JSON.parse(result.body),calls};
}
const completed={id:'fixture-request',status:'completed',model:'fixture',output:[{content:[{type:'output_text',text:'Completed fixture answer.'}]}]};

test('paid adapter remains blocked before any network request when disabled',async()=>{
 const r=await invoke(completed,{enabled:false});assert.equal(r.http,503);assert.equal(r.calls,0);assert.equal(r.body.execution_status,'FAILED');
});
test('empty completed output fails without a fabricated answer or auditor call',async()=>{
 const r=await invoke({...completed,output:[]},{audit:true});assert.equal(r.http,502);assert.equal(r.body.execution_status,'FAILED');assert.equal(r.body.output,'');assert.equal(r.calls,2);
});
test('incomplete partial output is explicitly unsuccessful and never audited',async()=>{
 const r=await invoke({...completed,status:'incomplete'},{audit:true});assert.equal(r.http,422);assert.equal(r.body.execution_status,'INCOMPLETE');assert.equal(r.body.output,'Completed fixture answer.');assert.equal(r.calls,2);
});
test('completed output retains a failing second-model verdict',async()=>{
 const auditor={...completed,output:[{content:[{type:'output_text',text:'{"verdict":"FAIL","score":10,"reason":"Fixture failure"}'}]}]};
 const r=await invoke(completed,{audit:true,auditor});assert.equal(r.http,200);assert.equal(r.body.execution_status,'COMPLETED');assert.equal(r.body.quality_review,'FAIL');assert.equal(r.body.audit.fact_check,'NOT_VERIFIED');assert.equal(r.calls,3);
});
test('an incomplete auditor cannot produce a completed audit',async()=>{
 const r=await invoke(completed,{audit:true,auditor:{...completed,status:'incomplete'}});assert.equal(r.http,200);assert.equal(r.body.audit.status,'UNAVAILABLE');assert.equal(r.body.quality_review,'UNAVAILABLE');
});
test('JSON null is rejected before budget/provider requests',async()=>{
 const r=await invoke(completed,{body:null});assert.equal(r.http,400);assert.equal(r.calls,0);
});
