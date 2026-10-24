'use strict';
// Shared server/browser execution contract. Format checks never establish quality.
(function(root) {
  function providerResult(data) {
    if(!data || typeof data!=='object' || Array.isArray(data)) return {execution_status:'FAILED',output:'',request_id:null,reason:'INVALID_PROVIDER_RESPONSE'};
    const output=Array.isArray(data.output)?data.output.flatMap(item=>Array.isArray(item?.content)?item.content.filter(c=>c?.type==='output_text' && typeof c.text==='string').map(c=>c.text):[]).join('\n'):'';
    const request_id=typeof data.id==='string' && data.id.length>0 && data.id.length<=200?data.id:null;
    if(data.status==='incomplete') return {execution_status:'INCOMPLETE',output,request_id,reason:'PROVIDER_RESPONSE_INCOMPLETE'};
    if(data.status!=='completed') return {execution_status:'FAILED',output:'',request_id,reason:'PROVIDER_DID_NOT_COMPLETE'};
    if(!request_id || !output.trim() || output.length>50000) return {execution_status:'FAILED',output:'',request_id,reason:'MISSING_OR_INVALID_PROVIDER_OUTPUT'};
    return {execution_status:'COMPLETED',output,request_id,reason:null};
  }
  function checks(output,status,requestId,simulation=false) {
    return {nonempty:typeof output==='string' && !!output.trim(),max_output_chars:typeof output==='string' && output.length<=50000,
      no_fake_flop_settlement:typeof output==='string' && !/FLOP (settled|payment confirmed|reward earned)/i.test(output),
      execution_completed:simulation?status==='SIMULATED' && output.startsWith('[SIMULATED ONLY]'):status==='COMPLETED' && typeof requestId==='string' && !!requestId};
  }
  function reviewStatus(audit) {
    if(audit?.status==='COMPLETED' && ['PASS','FLAG','FAIL'].includes(audit.verdict) && Number.isInteger(audit.score) && audit.score>=0 && audit.score<=100) return audit.verdict;
    return audit?.status==='NOT_REQUESTED'?'NOT_REQUESTED':'UNAVAILABLE';
  }
  const api={providerResult,checks,reviewStatus};
  if(typeof module!=='undefined' && module.exports) module.exports=api;
  else root.InferenceResult=api;
})(globalThis);
