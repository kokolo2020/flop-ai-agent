'use strict';
// Prototype local signing primitives. No FLOP registration or settlement.
const crypto = require('node:crypto');
const fs = require('node:fs');
function createIdentity() {
 const {publicKey,privateKey}=crypto.generateKeyPairSync('ed25519');
 const publicPem=publicKey.export({type:'spki',format:'pem'});
 const privatePem=privateKey.export({type:'pkcs8',format:'pem'});
 const fingerprint=crypto.createHash('sha256').update(publicKey.export({type:'spki',format:'der'})).digest('hex');
 return {agentId:'local:ed25519:'+fingerprint,publicKey:publicPem,privateKey:privatePem};
}
function canonical(v) {
 if(Array.isArray(v)) return '['+v.map(canonical).join(',')+']';
 if(v&&typeof v==='object') return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';
 return JSON.stringify(v);
}
function signReceipt(payload,privateKey) {
 const bytes=Buffer.from(canonical(payload));
 return {payload,signature:crypto.sign(null,bytes,privateKey).toString('base64'),algorithm:'Ed25519'};
}
function verifyReceipt(receipt,publicKey) {
 if(!receipt||receipt.algorithm!=='Ed25519'||typeof receipt.signature!=='string')return false;
 try{return crypto.verify(null,Buffer.from(canonical(receipt.payload)),publicKey,Buffer.from(receipt.signature,'base64'));}catch{return false}
}
module.exports={createIdentity,signReceipt,verifyReceipt,canonical};
