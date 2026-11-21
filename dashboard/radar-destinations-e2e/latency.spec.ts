import {test,expect} from '@playwright/test';
import {encode} from 'next-auth/jwt';
test('bounded authenticated workspace read timings',async({context})=>{
 const origin='http://127.0.0.1:13000',email='founder@leadengine.example';
 await context.addCookies([{name:'authjs.session-token',value:await encode({token:{sub:email,email},secret:'fixture-session-secret-only-for-local-tests-123456789',salt:'authjs.session-token',maxAge:3600}),url:origin,httpOnly:true}]);
 for(const path of ['organization/workspaces','intent-radar/overview/summary','intent-radar/opportunities','intent-radar/signals','intent-radar/discoveries','intent-radar/monitors','intent-radar/settings']){
  const read=async()=>{const start=performance.now();const response=await context.request.get(origin+'/api/'+path,{timeout:15000});expect(response.status()).toBe(200);await response.body();return Math.round(performance.now()-start);};
  const first=await read(),samples:number[]=[];for(let i=0;i<5;i++)samples.push(...await Promise.all([read(),read()]));samples.sort((a,b)=>a-b);
  console.log('release-latency',JSON.stringify({path,first_ms:first,warm_n:samples.length,concurrency:2,p50_ms:samples[4],p95_ms:samples[9]}));
 }
});
