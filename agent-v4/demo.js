'use strict';
// Offline two-agent signed task exchange. No FLOP network interaction.
const crypto=require('node:crypto');
const {createIdentity,signReceipt,verifyReceipt}=require('./identity');
function runDemo(){
 const requester=createIdentity(),worker=createIdentity();
 const request={schema:'computepilot.task.v1',taskId:crypto.randomUUID(),from:requester.agentId,to:worker.agentId,task:{type:'sum',values:[12,30]},issuedAt:new Date().toISOString(),maxCostUsd:0};
 const signedRequest=signReceipt(request,requester.privateKey);
 if(!verifyReceipt(signedRequest,requester.publicKey))throw Error('Invalid requester signature');
 const answer=request.task.values.reduce((a,b)=>a+b,0);
 const receipt={schema:'computepilot.receipt.v1',taskId:request.taskId,requestHash:crypto.createHash('sha256').update(JSON.stringify(signedRequest)).digest('hex'),worker:worker.agentId,result:{value:answer},costUsd:0,completedAt:new Date().toISOString(),network:'OFFLINE_SIMULATION',flopSettled:false};
 const signedReceipt=signReceipt(receipt,worker.privateKey);
 const signatureValid=verifyReceipt(signedReceipt,worker.publicKey);
 const resultValid=receipt.result.value===42;
 const tampered=JSON.parse(JSON.stringify(signedReceipt));tampered.payload.result.value=999;
 const tamperRejected=!verifyReceipt(tampered,worker.publicKey);
 if(!signatureValid||!resultValid||!tamperRejected)throw Error('Verification failed');
 return {requester:requester.agentId,worker:worker.agentId,taskId:request.taskId,signatureValid,resultValid,tamperRejected,flopSettled:false,network:'OFFLINE_SIMULATION'};
}
if(require.main===module)console.log(JSON.stringify(runDemo(),null,2));
module.exports={runDemo};
