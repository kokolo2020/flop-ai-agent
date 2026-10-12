exports.handler = async (event) => {
 const json=(statusCode,obj)=>({statusCode,headers:{'content-type':'application/json','cache-control':'no-store'},body:JSON.stringify(obj)});
 if(event.httpMethod!=='POST')return json(405,{error:'POST required'});
 const key=process.env.OPENAI_API_KEY;
 if(!key)return json(503,{error:'AI provider not configured. Set OPENAI_API_KEY in Netlify environment variables.'});
 let body;try{body=JSON.parse(event.body||'{}')}catch{return json(400,{error:'Invalid JSON'})}
 const prompt=body.prompt;
 if(typeof prompt!=='string'||prompt.trim().length<1||prompt.length>2000)return json(400,{error:'Prompt must contain 1–2000 characters'});
 try{
  const ctrl=new AbortController();const timeout=setTimeout(()=>ctrl.abort(),20000);
  let response;
  try{response=await fetch('https://api.openai.com/v1/responses',{method:'POST',signal:ctrl.signal,headers:{'authorization':'Bearer '+key,'content-type':'application/json'},body:JSON.stringify({model:process.env.OPENAI_MODEL||'gpt-4.1-mini',input:prompt,max_output_tokens:300,store:false})})}finally{clearTimeout(timeout)}
  const data=await response.json();
  if(!response.ok)return json(502,{error:'Provider request failed',provider_status:response.status});
  const output=(data.output||[]).flatMap(item=>(item.content||[]).filter(x=>x.type==='output_text').map(x=>x.text)).join('\n');
  return json(200,{output:output||'No text output returned',provider:'OpenAI',model:data.model,request_id:data.id,usage:data.usage||null,flop_eligible:false});
 }catch(e){return json(502,{error:e.name==='AbortError'?'Provider timed out':'Provider unavailable'})}
};