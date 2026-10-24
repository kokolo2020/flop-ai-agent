// Synthetic state-machine fixtures; never imported as measured host evidence.
const test = require('node:test');
const assert = require('node:assert/strict');
const {readiness,validate} = require('../public/miner-readiness.js');
const now = Date.parse('2026-10-24T00:00:00Z');
function report() {
  return {schema:'computepilot.miner-test.v12',kind:'preflight',simulated:false,
    evidence:'LOCAL_OBSERVATION_UNSIGNED',flop_activity:'NOT_VERIFIED',mining_activation:'NOT_PERFORMED',
    collected_at:new Date(now).toISOString(),host:{os:'Linux',arch:'x86_64'},
    gpus:[{name:'NVIDIA A40','memory.total':46068}],ssh_access:'PASS',
    probes:Object.fromEntries(['nvidia_smi','docker_server','compose','docker_gpu'].map(k=>[k,{status:'PASS'}]))};
}
test('passing host never unblocks operator or activation stages',()=>{
  const stages=readiness(report(),'a40',now);
  assert.equal(stages[1].state,'READY');
  assert.equal(stages[0].state,'BLOCKED'); assert.equal(stages[4].state,'BLOCKED');
});
test('stale and future reports cannot stay ready',()=>{
  for(const offset of [-300001,60001]) {
    const r=report();r.collected_at=new Date(now+offset).toISOString();
    assert.equal(readiness(r,'a40',now)[1].state,'ACTION_NEEDED');
  }
});
test('target selection, SSH and Docker are actual gates',()=>{
  assert.equal(readiness(report(),'a100-80',now)[1].state,'ACTION_NEEDED');
  const r=report();r.ssh_access='NOT_TESTED';assert.equal(readiness(r,'a40',now)[1].state,'ACTION_NEEDED');
  r.ssh_access='PASS';r.probes.docker_gpu.status='GPU_INVENTORY_MISMATCH';
  assert.equal(readiness(r,'a40',now)[1].state,'ACTION_NEEDED');
});
test('measured access failure has unreachable state',()=>{
  const r=report();r.probes.docker_server.status='TIMEOUT_OR_OS_ERROR';
  assert.equal(readiness(r,'a40',now)[1].state,'UNREACHABLE');
});
test('fixtures and upgraded network claims rejected',()=>{
  for(const changes of [{simulated:true},{flop_activity:'VERIFIED'},{mining_activation:'PERFORMED'},{evidence:'PROTOCOL_FIXTURE_CHECK_ONLY'}])
    assert.throws(()=>validate({...report(),...changes}));
});
test('contradictory benchmark summaries cannot grant readiness',()=>{
  const r={...report(),kind:'benchmark',requested:2,successful:2,failed:0,rows:[],
    model:'Qwen/Qwen2.5B',precision:'BF16',model_identity:'measured'};
  assert.equal(readiness(r,'a40',now)[2].state,'ACTION_NEEDED');
});
test('AIPerf import cannot certify model identity',()=>{
  const r={...report(),kind:'aiperf',evidence:'EXTERNAL_OBSERVATION_UNSIGNED',requested:1,successful:1,failed:0,metrics:{},model_identity:'NOT_VERIFIED'};
  assert.equal(readiness(r,'a40',now)[2].state,'ACTION_NEEDED');
});
test('a bundle consistency pass cannot grant admission or activation readiness',()=>{
  const r={...report(),kind:'bundle',configuration_checks:'PASS',checks:[{check:'manifest_matches_supplied_pin',status:'PASS'}],operator_release_verification:'NOT_PERFORMED',network_identity:'NOT_VERIFIED',operator_admission:'NOT_VERIFIED',activation_gate:'BLOCKED'};
  const stages=readiness(r,'a40',now);
  assert.equal(stages[0].state,'ACTION_NEEDED');
  assert.equal(stages[3].state,'BLOCKED');assert.equal(stages[4].state,'BLOCKED');
  assert.throws(()=>validate({...r,operator_admission:'VERIFIED'}));
  assert.throws(()=>validate({...r,operator_release_verification:'PASS'}));
});
