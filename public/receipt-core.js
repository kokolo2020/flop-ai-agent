'use strict';
// computepilot.json.v1: UTF-8, Unicode code-point key order, safe integers only.
(function(root) {
  const SCHEMA = 'computepilot.receipt.v6', ENCODING = 'computepilot.json.v1';
  function string(value) {
    for (const char of value) {
      const code = char.codePointAt(0);
      if (code >= 0xd800 && code <= 0xdfff) throw Error('Unpaired Unicode surrogate');
    }
    return JSON.stringify(value);
  }
  function compareKeys(a,b) {
    const x = Array.from(a,c=>c.codePointAt(0)), y = Array.from(b,c=>c.codePointAt(0));
    for(let i=0;i<Math.min(x.length,y.length);i++) if(x[i]!==y[i]) return x[i]-y[i];
    return x.length-y.length;
  }
  function canonical(value) {
    const seen = new Set();
    function encode(v,depth) {
      if(depth>100) throw Error('Receipt nesting limit exceeded');
      if(v===null) return 'null';
      if(typeof v==='string') return string(v);
      if(typeof v==='boolean') return v?'true':'false';
      if(typeof v==='number') {
        if(!Number.isSafeInteger(v)) throw Error('Use safe integers or decimal strings in receipts');
        return String(v===0?0:v);
      }
      if(typeof v!=='object' || seen.has(v)) throw Error('Expected acyclic JSON values');
      const proto=Object.getPrototypeOf(v);
      if(!Array.isArray(v) && proto!==Object.prototype && proto!==null) throw Error('Expected plain JSON object');
      if(Object.getOwnPropertySymbols(v).length) throw Error('Symbol fields are unsupported');
      seen.add(v);
      let result;
      if(Array.isArray(v)) {
        if(Object.keys(v).length!==v.length) throw Error('Sparse or extended arrays are unsupported');
        result='['+Array.from(v,x=>encode(x,depth+1)).join(',')+']';
      } else result='{'+Object.keys(v).sort(compareKeys).map(k=>string(k)+':'+encode(v[k],depth+1)).join(',')+'}';
      seen.delete(v);
      return result;
    }
    return encode(value,0);
  }
  async function sha256(text) {
    string(text); // Reject invalid Unicode before UTF-8 encoding.
    const bytes=await root.crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));
    return Array.from(new Uint8Array(bytes),x=>x.toString(16).padStart(2,'0')).join('');
  }
  async function seal(body) {
    if(!body || typeof body!=='object' || Array.isArray(body) || 'record_sha256' in body) throw Error('Expected unsealed receipt body');
    const record={...body,schema:SCHEMA,record_encoding:ENCODING};
    return {...record,record_sha256:await sha256(canonical(record))};
  }
  async function verify(receipt,output) {
    try {
      if(!receipt || typeof receipt!=='object' || Array.isArray(receipt) || typeof output!=='string' || !/^[a-f0-9]{64}$/.test(receipt.record_sha256) || !/^[a-f0-9]{64}$/.test(receipt.output_sha256)) return false;
      const {record_sha256,...body}=receipt;
      if(await sha256(output)!==receipt.output_sha256) return false;
      if(receipt.schema===SCHEMA && receipt.record_encoding===ENCODING) return await sha256(canonical(body))===record_sha256;
      if(receipt.schema==='computepilot.receipt.v5' && !('record_encoding' in receipt)) {
        // Read-only legacy compatibility: sorted Python or insertion-order browser.
        const sorted=canonical(body); // Also validates the restricted JSON domain.
        return await sha256(sorted)===record_sha256 || await sha256(JSON.stringify(body))===record_sha256;
      }
      return false;
    } catch {return false;}
  }
  const api={SCHEMA,ENCODING,canonical,sha256,seal,verify};
  if(typeof module!=='undefined' && module.exports) module.exports=api;
  else root.ReceiptCore=api;
})(globalThis);
