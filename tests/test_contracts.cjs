const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const R=require('../public/receipt-core.js');
const I=require('../public/inference-result.js');
const fixtures=require('./fixtures/receipt-contract.json');

test('shared canonical vectors include integer-key and Unicode sorting',async()=>{
 for(const v of fixtures.vectors){assert.equal(R.canonical(v.value),v.canonical,v.id);assert.equal(await R.sha256(R.canonical(v.value)),v.sha256,v.id);}
 assert.equal(R.canonical({z:1,a:2}),R.canonical({a:2,z:1}));
});
test('unsupported JSON values cannot silently change a receipt',()=>{
 for(const value of [undefined,NaN,Infinity,1.5,2**53,1n,{bad:undefined},'\ud800',new Date(),Array(1)])assert.throws(()=>R.canonical(value));
 const cycle=[];cycle.push(cycle);assert.throws(()=>R.canonical(cycle));
});
test('new receipts reject altered output and format downgrades',async()=>{
 const output='synthetic fixture',receipt=await R.seal({output_sha256:await R.sha256(output)});
 assert.equal(await R.verify(receipt,output),true);
 assert.equal(await R.verify(receipt,output+'!'),false);
 assert.equal(await R.verify({...receipt,record_encoding:'unknown'},output),false);
 assert.equal(await R.verify({...receipt,schema:'computepilot.receipt.v5'},output),false);
});
test('incomplete, missing-ID and empty output are never completed',()=>{
 const complete={id:'fixture',status:'completed',output:[{content:[{type:'output_text',text:'answer'}]}]};
 assert.equal(I.providerResult(complete).execution_status,'COMPLETED');
 for(const changed of [{...complete,status:'incomplete'},{...complete,status:'failed'},{...complete,id:null},{...complete,output:[]},{...complete,status:undefined},null]){
  const r=I.providerResult(changed);assert.notEqual(r.execution_status,'COMPLETED');
  assert.equal(I.checks(r.output,r.execution_status,r.request_id).execution_completed,false);
 }
});
test('format checks cannot turn a quality FAIL or unavailable audit into PASS',()=>{
 assert.equal(Object.values(I.checks('answer','COMPLETED','fixture')).every(Boolean),true);
 assert.equal(I.reviewStatus({status:'COMPLETED',verdict:'FAIL',score:10}),'FAIL');
 assert.equal(I.reviewStatus({status:'COMPLETED',verdict:'FLAG',score:60}),'FLAG');
 assert.equal(I.reviewStatus({status:'COMPLETED',verdict:'PASS',score:101}),'UNAVAILABLE');
});
test('V12 entry point isolates the lab and has no key or paid-call controls',()=>{
 const html=fs.readFileSync('public/index.html','utf8');
 assert.match(html,/miner-test\.html/);assert.match(html,/receipts\.html/);assert.match(html,/legacy-lab\.html/);
 assert.doesNotMatch(html,/vaultRestore|tcPrepare|id="access"|v10Demo/);
 const lab=fs.readFileSync('public/legacy-lab.html','utf8');
 assert.doesNotMatch(lab,/computePilotVault|id="vaultRestore"|say-signed|id="access"|id="showAccess"/);assert.match(lab,/value="live" disabled/);
 assert.doesNotMatch(lab,/fetch\('\/\.netlify\/functions\/infer/);
});
