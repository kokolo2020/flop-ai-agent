// Cross-runtime test bridge. Reads/writes synthetic JSON only; no network.
const fs=require('node:fs');
const R=require('../../public/receipt-core.js');
(async()=>{
 const request=JSON.parse(fs.readFileSync(0,'utf8'));
 const result=await Promise.all(request.map(async item=>item.action==='seal'?R.seal(item.body):R.verify(item.receipt,item.output)));
 process.stdout.write(JSON.stringify(result));
})().catch(()=>{process.stderr.write('Invalid receipt contract test input');process.exitCode=1;});
