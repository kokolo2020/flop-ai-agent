// Deterministic research audit. This is NOT a marketplace lookup or FLOP eligibility oracle.
// Designed for Node's CommonJS environment, with no external dependencies.
'use strict';
const GPU_SPECS=Object.freeze({
 'RTX 5070 TI':{vram_gb:16,memory:'GDDR7'},
 'RTX 3090':{vram_gb:24,memory:'GDDR6X'},
 'RTX 4090':{vram_gb:24,memory:'GDDR6X'},
 'RTX 5090':{vram_gb:32,memory:'GDDR7'},
 'A100 80GB':{vram_gb:80,memory:'HBM2e'},
 'A100 40GB':{vram_gb:40,memory:'HBM2e'},
 'H100 80GB':{vram_gb:80,memory:'HBM3'}
});
function normalizeGPU(value){return String(value||'').trim().toUpperCase().replace(/^NVIDIA\s+/,'').replace(/^GEFORCE\s+/,'').replace(/\s+/g,' ')}
function auditOffers(offers,{budget_usd=250,hours=720}={}){
 if(!Array.isArray(offers)||offers.length>100)throw Error('offers must be an array with at most 100 entries');
 if(!Number.isFinite(budget_usd)||budget_usd<0||!Number.isFinite(hours)||hours<=0)throw Error('Invalid budget or hours');
 const seen=new Set();const rows=[];
 for(let i=0;i<offers.length;i++){
  const x=offers[i];if(!x||typeof x!=='object'||Array.isArray(x))throw Error('Invalid offer at index '+i);
  const flags=[];const model=normalizeGPU(x.gpu);const specs=GPU_SPECS[model];
  const id=String(x.offer_id||'').trim();
  if(!id)flags.push('MISSING_OFFER_ID');
  else if(seen.has(id))flags.push('DUPLICATE_OFFER_ID');else seen.add(id);
  if(!specs)flags.push('UNKNOWN_GPU_MODEL');
  if(x.vram_gb!==undefined&&specs&&Number(x.vram_gb)!==specs.vram_gb)flags.push('VRAM_MISMATCH');
  if(x.memory&&specs&&String(x.memory).toUpperCase()!==specs.memory.toUpperCase())flags.push('MEMORY_TYPE_MISMATCH');
  const hourly=Number(x.hourly_usd);
  if(!Number.isFinite(hourly)||hourly<0||x.hourly_usd===null||x.hourly_usd===undefined)flags.push('INVALID_HOURLY_PRICE');
  const url=String(x.url||'').trim();
  if(!/^https:\/\/(vast\.ai|cloud\.vast\.ai)\//i.test(url))flags.push('UNVERIFIED_SOURCE_URL');
  if(!/^\d{4}-\d{2}-\d{2}$/.test(String(x.observed_date||'')))flags.push('MISSING_OBSERVATION_DATE');
  // Marketplace listing metadata alone cannot prove live price, availability, or FLOP eligibility.
  const monthly=Number.isFinite(hourly)&&hourly>=0?Math.round(hourly*hours*100)/100:null;
  rows.push({offer_id:id,gpu:model,canonical_specs:specs||null,hourly_usd:monthly===null?null:hourly,monthly_usd:monthly,within_budget:monthly!==null&&monthly<=budget_usd,flags,marketplace_live_verified:false,flop_eligible:'UNVERIFIED',safe_to_rent:false});
 }
 return {checked_at:new Date().toISOString(),hours,budget_usd,rows,summary:{total:rows.length,flagged:rows.filter(r=>r.flags.length).length,unverified:rows.length,approved_for_rental:0},note:'This validates internal consistency only. No actual Vast.ai listing or FLOP approval was checked.'};
}
module.exports={auditOffers,normalizeGPU,GPU_SPECS};
