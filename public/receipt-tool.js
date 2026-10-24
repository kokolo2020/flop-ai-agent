'use strict';
(()=>{
  const el=id=>document.getElementById(id);
  let revision=0;
  el('receiptJson').oninput=()=>{revision++;el('receiptStatus').textContent='Input changed. Check integrity to review this version.';el('receiptDetails').textContent='';};
  el('checkReceipt').onclick=async()=>{
    const current=++revision;
    el('receiptDetails').textContent='';
    try{
      const raw=el('receiptJson').value;
      if(raw.length>2000000)throw Error('Job export exceeds size limit.');
      const job=JSON.parse(raw);
      if(!job || typeof job.output!=='string' || !job.receipt)throw Error('Expected a job object with receipt and output.');
      const valid=await ReceiptCore.verify(job.receipt,job.output);
      if(current!==revision)return;
      const legacy=job.receipt.schema==='computepilot.receipt.v5';
      el('receiptStatus').textContent=valid?(legacy?'PASS · Legacy V5 local integrity only.':'PASS · V6 local integrity only.'):'FAIL · Unsupported format, receipt mismatch or altered output.';
      if(valid)el('receiptDetails').textContent='Record encoding: '+(legacy?'legacy (unversioned)':ReceiptCore.ENCODING)+'\nSignature: NOT VERIFIED\nFLOP activity: NOT VERIFIED\nSettlement: NOT VERIFIED';
    }catch{
      if(current===revision)el('receiptStatus').textContent='Invalid job export. Expected JSON with receipt and output; no raw input is echoed.';
    }
  };
  el('exampleReceipt').onclick=async()=>{
    const current=++revision;
    const output='[SIMULATED ONLY] Offline receipt integrity example.';
    const receipt=await ReceiptCore.seal({job_id:'OFFLINE-EXAMPLE',output_sha256:await ReceiptCore.sha256(output),execution_status:'SIMULATED',flop_settlement:'NOT_VERIFIED',signature:'NOT_SIGNED'});
    if(current!==revision)return;
    el('receiptJson').value=JSON.stringify({output,receipt},null,2);
    el('receiptStatus').textContent='Synthetic example loaded. No inference, signing or network activity occurred.';
    el('receiptDetails').textContent='';
  };
  el('clearReceipt').onclick=()=>{revision++;el('receiptJson').value='';el('receiptDetails').textContent='';el('receiptStatus').textContent='No receipt checked.';};
})();
