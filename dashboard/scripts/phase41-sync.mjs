import {chromium} from '@playwright/test';
import {encode} from 'next-auth/jwt';
import fs from 'node:fs/promises';
const origin='https://leads.planebyte.com',file='../docs/phase41-controlled.json',state=JSON.parse(await fs.readFile(file,'utf8'));
const browser=await chromium.launch({channel:'chrome',headless:true});
try{
 const context=await browser.newContext(),salt='__Secure-authjs.session-token',email=process.env.CHECK_EMAIL;
 const token=await encode({token:{sub:email,email},secret:process.env.AUTH_SECRET,salt,maxAge:900});await context.addCookies([{name:salt,value:token,url:origin,httpOnly:true,secure:true,sameSite:'Lax'}]);
 const api=async(path,method='GET')=>{const response=await context.request.fetch(origin+'/api'+path,{method,headers:{Origin:origin},timeout:180000});if(!response.ok())throw new Error('Production API check failed.');return response.json();};
 const account=await api('/email/account');if(account.send_mode!=='test'||account.live_approved)throw new Error('Test mode must remain active.');
 state.sync=await api('/email/sync','POST');const messages=await api('/email/leads/517/threads/'+state.sent.thread_id),sales=await api('/sales/leads/517'),workspace=await api('/leads/517/workspace');
 const outbound=messages.find(m=>m.id===state.sent.id),incoming=messages.filter(m=>m.direction==='INBOUND'&&m.verified_reply),ids=new Set(incoming.map(m=>m.id));
 state.checks.verified_reply=Boolean(outbound?.engagement?.events.some(e=>e.event_type==='REPLIED_VERIFIED'));
 state.checks.inbound_verified=incoming.length>0;state.checks.reply_activity=sales.activities.some(a=>a.event_type==='REPLY_DETECTED'&&ids.has(a.metadata?.message_id));state.checks.reply_status_preserved=workspace.lead_status==='REPLIED';
 state.checks.test_mode_retained=account.send_mode==='test';state.reply_acceptance={verified_inbound_count:incoming.length,normalized_reply_events:outbound?.engagement?.events.filter(e=>e.event_type==='REPLIED_VERIFIED').length||0};
 state.checked_at=new Date().toISOString();await fs.writeFile(file,JSON.stringify(state,null,2));console.log(JSON.stringify({checks:state.checks,reply_acceptance:state.reply_acceptance}));
 if(!state.checks.verified_reply||!state.checks.inbound_verified||!state.checks.reply_activity)process.exitCode=1;
}catch(e){console.error('Controlled production reply acceptance did not finish.');process.exitCode=1;}finally{await browser.close();}
