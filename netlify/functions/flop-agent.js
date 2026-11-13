const crypto = require('node:crypto');
const ORIGIN = 'https://api.flop.network';
const GENESIS = '0x99c172c095340ace980631f9123544c6bebd4839f3437e463533422d8be2d631';
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const pickReceipt = r => Object.fromEntries(['request_id','state','response_status','model','settled_spend','settled_spend_raw','terminal_event','channel_id'].map(k=>[k,r[k]??null]));
exports.createHandler = (env, transport = fetch) => async event => {
  const reply = (statusCode, data) => ({statusCode,headers:{'content-type':'application/json','cache-control':'no-store'},body:JSON.stringify(data)});
  if(event.httpMethod !== 'POST') return reply(405,{error:'POST required'});
  const expected = env.COMPUTEPILOT_ACCESS_TOKEN;
  if(!expected) return reply(503,{error:'App access token is not configured. No inference submitted.'});
  const supplied = Object.entries(event.headers||{}).find(([k])=>k.toLowerCase()==='x-computepilot-token')?.[1]||'';
  const a=Buffer.from(supplied), b=Buffer.from(expected);
  if(a.length!==b.length || !crypto.timingSafeEqual(a,b)) return reply(401,{error:'Unauthorized'});
  let body; try{body=JSON.parse(event.body||'{}')}catch{return reply(400,{error:'Invalid JSON'})}
  const action=body.action;
  if(!['status','run','receipt'].includes(action))return reply(400,{error:'Invalid action'});
  if(['run','receipt'].includes(action)&&!UUID.test(body.request_id||''))return reply(400,{error:'A UUID v4 request ID is required'});
  const goal=typeof body.goal==='string'?body.goal.trim():'';
  if(action==='run'&&(!goal||goal.length>1000))return reply(400,{error:'Task must contain 1–1000 characters'});
  let submitted=false;
  const request = async(path, data) => {
    const response=await transport(ORIGIN+path,{method:data?'POST':'GET',headers:{'user-agent':'ComputePilot-devnet-check/1.0',...(path.startsWith('/v1/')&&env.FLOP_API_KEY?{authorization:'Bearer '+env.FLOP_API_KEY}:{}),...(data?{'content-type':'application/json','Idempotency-Key':body.request_id,'X-Request-ID':body.request_id}:{})},...(data?{body:JSON.stringify(data)}:{}),signal:AbortSignal.timeout(data?25000:5000)});
    let json;try{json=await response.json()}catch{json={}}
    return {ok:response.ok,status:response.status,data:json,retry_after:response.headers.get('retry-after')};
  };
  const receipt = async()=>{
    const r=await request('/v1/keys/me/receipts/'+encodeURIComponent(body.request_id));
    const d=r.data.receipt||r.data;
    return {http:r.status,receipt:r.ok&&d.request_id===body.request_id?pickReceipt(d):null};
  };
  try {
    if(action==='receipt'){
      if(!env.FLOP_API_KEY)return reply(503,{error:'FLOP credential not configured',request_id:body.request_id});
      return reply(200,{request_id:body.request_id,...await receipt(),note:'Ledger observation only; not independent chain finality. No inference submitted.'});
    }
    const h=await request('/health');const n=h.data.network||{};
    const healthy=h.ok&&h.data.status==='ok'&&h.data.connected===true&&h.data.syncing===false&&n.network==='devnet'&&n.observed_genesis_hash===GENESIS;
    const base={provider:'FLOP devnet',checked_at:new Date().toISOString(),healthy,credential_configured:!!env.FLOP_API_KEY,inference_submitted:false};
    if(!healthy)return reply(503,{...base,error:'Gateway health or devnet identity check failed. No inference submitted.'});
    if(!env.FLOP_API_KEY)return reply(503,{...base,error:'FLOP_API_KEY is missing. A valid bounded FLOP credential is required; faucet balance is not API allowance.'});
    const key=await request('/v1/keys/me');
    if(!key.ok)return reply(key.status===401?401:503,{...base,error:key.status===401?'FLOP credential expired, revoked or invalid. Operator access is required.':'FLOP credential inspection failed.',credential_http:key.status});
    const k=key.data;
    if(k.credential!=='ephemeral')return reply(503,{...base,error:'Use a bounded child or wallet credential, never an owner key on this hosted app.'});
    if(!Number.isFinite(k.remaining_quota)||k.remaining_quota<=0||!Number.isFinite(k.expires_at)||k.expires_at<=Date.now())return reply(503,{...base,error:'Credential allowance is exhausted or expired.'});
    const model=env.FLOP_MODEL;
    const m=await request('/v1/models');
    const ready=!!model&&m.ok&&Array.isArray(m.data.data)&&m.data.data.some(x=>x.id===model);
    const status={...base,remaining_quota:k.remaining_quota,expires_at:k.expires_at,model:model||null,ready};
    if(action==='status')return reply(200,{...status,...(!ready?{error:'Configure FLOP_MODEL to an exact model advertised by this gateway.'}:{})});
    if(!ready)return reply(503,{...status,error:'Configured FLOP model is unavailable. No inference submitted.'});
    submitted=true;
    const out=await request('/v1/chat/completions',{model,messages:[{role:'user',content:goal}],max_tokens:64});
    const text=typeof out.data.choices?.[0]?.message?.content==='string'?out.data.choices[0].message.content.trim():'';
    let proof;try{proof=await receipt()}catch{proof={http:null,receipt:null}}
    return reply(200,{...status,inference_submitted:true,request_id:body.request_id,completion_http:out.status,retry_after:out.retry_after,text:out.ok?text:'',status:out.ok&&text?'text_received':'failed_or_unresolved',...proof,note:'One request, maximum 64 output tokens. Receipt settlement is separate from receiving text. No automatic retries or other provider fallback.'});
  }catch{return reply(502,{error:submitted?'Request outcome is unknown. Check this same request ID; do not submit replacement work.':'Connection check failed. No inference submitted.',inference_submitted:submitted,request_id:body.request_id||null,status:submitted?'unresolved':'blocked'});}
};
exports.handler=(event)=>exports.createHandler(process.env)(event);
