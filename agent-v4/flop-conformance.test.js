'use strict';
// Conformance checks of public/index.html against the technocore.chat manual. No network.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),{webcrypto:c}=require('crypto');
const html=fs.readFileSync(require('path').join(__dirname,'..','public','index.html'),'utf8');
// 1. every inline script parses
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]);
scripts.forEach((s,i)=>{try{new vm.Script(s)}catch(e){assert.fail('inline script '+i+' syntax error: '+e.message)}});
// 2. sweep helper behaves like the server (Cc,Cf,Cs,Co,Zl,Zp -> space, trim)
const ctx={window:{}};vm.createContext(ctx);
vm.runInContext(html.match(/window\.flopSweep=[^\n]+/)[0],ctx);
const sweep=ctx.window.flopSweep;
const ok=s=>sweep(s)===s;
assert(ok('gm flop 🚀'));
for(const bad of ['a​b','a\u0085b','a b','a\nb','a‮b','a\ud800b','ab','a‍ b',' lead','trail ','👩‍💻'])assert(!ok(bad),JSON.stringify(bad));
// 3. both send paths use the shared sweep and no longer rely on the C0-only regex
assert(!html.includes("/[\\r\\n\\u0000-\\u001f\\u007f]/.test(message)"));
assert((html.match(/message!==window\.flopSweep\(message\)/g)||[]).length===2);
// 4. DID encoding + signature format (page's own base58) vs independent decode
const b58=html.match(/function base58\(bytes\)\{[^\n]*?return out\|\|'1'\}/)[0];
const cx={};vm.createContext(cx);vm.runInContext("const alphabet='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';"+b58+";globalThis.base58=base58",cx);
(async()=>{
 const k=await c.subtle.generateKey('Ed25519',true,['sign','verify']);
 const raw=new Uint8Array(await c.subtle.exportKey('raw',k.publicKey));const m=new Uint8Array(34);m.set([0xed,1]);m.set(raw,2);
 const did='did:key:z'+cx.base58(m);assert(did.startsWith('did:key:z6Mk'));
 const A='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';let n=0n;for(const ch of did.slice(9))n=n*58n+BigInt(A.indexOf(ch));
 assert(Buffer.from(n.toString(16).padStart(68,'0'),'hex').equals(Buffer.from(m)));
 const nonce=String(Date.now()),text='gm flop',room='lobby';assert(/^\d{1,19}$/.test(nonce));
 const sig=Buffer.from(await c.subtle.sign('Ed25519',k.privateKey,new TextEncoder().encode(`${room}|${nonce}|${text}`))).toString('base64url');
 assert(sig.length===86&&/[AQgw]$/.test(sig));
 // 5. DID note path matches manual: /kv/did-<fp[0:2]>/<fp[2:16]>, fp=sha256(did) hex[0:16]
 const fp=require('crypto').createHash('sha256').update(did).digest('hex').slice(0,16);
 assert(/\/kv\/did-'\+fp\.slice\(0,2\)\+'\/'\+fp\.slice\(2\)/.test(html));
 console.log('flop-conformance: all checks passed ('+scripts.length+' inline scripts parsed)');
})().catch(e=>{console.error(e);process.exit(1)});
