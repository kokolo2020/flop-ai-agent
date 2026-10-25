// ComputePilot V11.1 read-only FLOP connectivity diagnostics.
// This intentionally DOES NOT verify FLOP protocol, chain identity, receipts or rewards.
const ENDPOINTS = Object.freeze([
  {name:'API',url:'https://api.flop.network/'},
  {name:'MCP',url:'https://mcp.flop.network/'},
  {name:'Faucet',url:'https://faucet.flop.network/'},
  {name:'Devnet RPC',url:'https://rpc.devnet.flop.network/'}
]);
const json=(statusCode,data)=>({statusCode,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store','x-content-type-options':'nosniff'},body:JSON.stringify(data)});
exports.handler=async (event)=>{
  if(event.httpMethod!=='GET')return json(405,{error:'GET required'});
  // Fixed, reviewed hosts only. No user URL input or credentials.
  const probes=[];
  for(const item of ENDPOINTS){
    const started=Date.now();
    const controller=new AbortController();
    const timeout=setTimeout(()=>controller.abort(),4000);
    try{
      const res=await fetch(item.url,{method:'GET',redirect:'manual',signal:controller.signal,headers:{accept:'application/json'}});
      probes.push({name:item.name,url:item.url,outcome:res.ok?'HTTP_RESPONSE_ONLY':res.status>=300&&res.status<400?'REDIRECT':'HTTP_ERROR',http_status:res.status,elapsed_ms:Date.now()-started,api_verified:false,protocol_verified:false});
      // Do not consume or trust response bodies: only report HTTP reachability.
      if(res.body&&typeof res.body.cancel==='function')await res.body.cancel().catch(()=>{});
    }catch(e){
      probes.push({name:item.name,url:item.url,outcome:e&&e.name==='AbortError'?'TIMEOUT':'NETWORK_ERROR',http_status:null,elapsed_ms:Date.now()-started,api_verified:false,protocol_verified:false});
    }finally{clearTimeout(timeout);}
  }
  return json(200,{
    schema:'computepilot-server-network-diagnostics-v1',
    version:'11.1',
    generated_at:new Date().toISOString(),
    source:'netlify-server-side-fixed-endpoint-get',
    network:'UNVERIFIED',testnet_ready:false,eligible_receipts:0,
    warning:'Reachability is not protocol verification. GET may return 405 for POST-only RPC; no chain ID, signed inference or settlement was tested.',
    probes
  });
};
