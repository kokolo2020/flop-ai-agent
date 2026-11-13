(()=>{
const $=id=>document.getElementById(id), storage='computepilot-flop-pending-v1';
let ready=false,busy=false,ledger=null,pending=null;
try{pending=JSON.parse(localStorage.getItem(storage)||'null')}catch{}
const render=()=>{$('run').disabled=busy||!ready||!!pending;$('check').disabled=busy;$('receipt').disabled=busy||!pending};
const save=()=>{if(pending)localStorage.setItem(storage,JSON.stringify(pending));else localStorage.removeItem(storage);render()};
const call=async(action)=>{
 if(busy)return;const token=$('token').value;if(!token){$('status').textContent='Enter your private app access token.';return}
 if(action==='run'){
  if(!ready||pending)return;const goal=$('goal').value.trim();if(!goal)return;
  pending={request_id:crypto.randomUUID(),created_at:new Date().toISOString()};
  try{save()}catch{$('status').textContent='Browser storage unavailable. Task not sent.';pending=null;return}
 }
 busy=true;render();$('status').textContent=action==='run'?'Sending one FLOP request…':'Checking FLOP…';
 try{
  const response=await fetch('/.netlify/functions/flop-agent',{method:'POST',headers:{'content-type':'application/json','x-computepilot-token':token},body:JSON.stringify({action,...(pending?{request_id:pending.request_id}:{}),...(action==='run'?{goal:$('goal').value.trim()}:{})})});
  const data=await response.json();ledger=data;$('evidence').textContent=JSON.stringify(data,null,2);
  if(action==='status'){ready=!!data.ready;$('status').textContent=ready?'FLOP ready. Bounded credential verified.':data.error||'FLOP not ready.'}
  else{
   if(data.text)$('answer').textContent=data.text;
   const terminal=data.receipt&&['settled','released'].includes(data.receipt.state);
   if(terminal||data.inference_submitted===false){pending=null;save()}
   ready=false;
   $('status').textContent=terminal?'Gateway receipt: '+data.receipt.state+'. Receiving text and settlement are separate.':data.error||'Outcome pending. Use Check pending receipt; do not repeat the task.';
  }
 }catch{$('status').textContent=pending?'Connection interrupted. Request ID saved; check its receipt before any new task.':'Connection check failed.';ready=false}
 finally{busy=false;render()}
};
$('check').onclick=()=>call('status');$('run').onclick=()=>call('run');$('receipt').onclick=()=>call('receipt');
$('download').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify({ledger,pending},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='computepilot-flop-evidence.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
if(pending)$('status').textContent='Unresolved request saved. Check its receipt before starting new work.';
render();
})();
