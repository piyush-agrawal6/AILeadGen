import {chromium,expect as baseExpect} from '@playwright/test';
import {encode} from 'next-auth/jwt';
import fs from 'node:fs/promises';
import {randomUUID} from 'node:crypto';
const expect=baseExpect.configure({timeout:90000});
const origin='https://leads.planebyte.com',file='../docs/phase4-production.json',action=process.argv[2]||'prepare';
const targets=JSON.parse(await fs.readFile('../docs/phase4-acceptance-targets.json','utf8'));
const state=await fs.readFile(file,'utf8').then(JSON.parse).catch(()=>({checks:{},reports:{}}));const save=()=>fs.writeFile(file,JSON.stringify(state,null,2));
const browser=await chromium.launch({channel:'chrome',headless:true});
try{
 const context=await browser.newContext({viewport:{width:1440,height:900}}),salt='__Secure-authjs.session-token',email=process.env.CHECK_EMAIL;
 state.checks.unauthenticated_email_protected=(await context.request.get(origin+'/api/email/account')).status()===401;
 const token=await encode({token:{sub:email,email,name:'PlaneByte acceptance'},secret:process.env.AUTH_SECRET,salt,maxAge:900});await context.addCookies([{name:salt,value:token,url:origin,httpOnly:true,secure:true,sameSite:'Lax'}]);
 const api=async(path,method='GET',data)=>{const r=await context.request.fetch(origin+'/api'+path,{method,data,headers:{Origin:origin},timeout:180000});const b=await r.json();if(!r.ok())throw new Error(`${method} ${path}: ${r.status()} ${typeof b.detail==='string'?b.detail:'request failed'}`);return b;};
 const account=await api('/email/account');if(account.send_mode!=='test'||account.email_address!=='rajendra@planebyte.com')throw new Error('Expected verified Hostinger identity in test mode.');state.checks.test_mode=true;
 if(action==='prepare'){
  state.provider_health=await api('/email/health','POST');
  if(!state.list)state.list=await api('/sales/lists','POST',{name:'Phase 4 controlled acceptance',description:'Existing real prospects from both current scans; test mode only.'});
  if(!state.view)state.view=await api('/sales/views','POST',{name:'High fit website review',filters:{commercial_fit:'HIGH',min_website:40,sort_by:'website',sort_dir:'desc'}});
  await api('/sales/bulk','POST',{lead_ids:targets.map(t=>t.id),action:'list',list_id:state.list.id});
  await api('/sales/bulk','POST',{lead_ids:targets.map(t=>t.id),action:'status',status:'READY_TO_CONTACT'});
  for(const t of targets){if(!state.reports[t.id]){state.reports[t.id]=await api('/leads/'+t.id+'/pdf-reports','POST');await save();}}
  state.checks.both_real_scans_used=true;console.log(JSON.stringify({provider:state.provider_health,targets:targets.map(t=>({id:t.id,run_id:t.run_id})),reports:state.reports}));
 }else if(action==='health'){
  state.provider_health=await api('/email/health','POST');
  if(state.provider_health.smtp!=='READY'||state.provider_health.imap!=='READY')throw new Error('Hostinger connection health did not pass.');
  console.log(JSON.stringify({provider_health:state.provider_health,send_mode:account.send_mode}));
 }else if(action==='reports'){
  for(const t of targets){const r=await api('/client-reports/'+state.reports[t.id].id);state.reports[t.id]=r;if(r.status!=='READY')throw new Error('Client report is '+r.status);}
  state.checks.reports_ready=true;console.log('Both current-dataset client reports are ready.');
 }else if(action==='send'){
  if(state.sent){console.log('Controlled acceptance message was already sent; no resend.');}
  else{
   const t=targets[0],page=await context.newPage();page.setDefaultTimeout(90000);await page.goto(origin+'/leads/'+t.id);await page.getByRole('button',{name:'Compose email',exact:true}).click();await expect(page.getByRole('dialog')).toContainText('TEST MODE');
   state.subject='PlaneByte Phase 4 controlled acceptance '+randomUUID().slice(0,8);
   await page.getByLabel('Subject',{exact:true}).fill(state.subject);await page.getByLabel('Body',{exact:true}).fill('Controlled PlaneByte acceptance test. No discovered prospect is being contacted.\n\nPlease reply normally to this email with "Phase 4 reply test" so we can verify IMAP synchronization and reliable reply matching.\n\nThis test attaches the existing stored PlaneByte client review for '+t.name+'.\n\nPlaneByte\nhttps://planebyte.com\nrajendra@planebyte.com');
   await page.getByRole('button',{name:'Preview email',exact:true}).click();await expect(page.getByRole('dialog')).toContainText('To: '+account.test_recipient);await expect(page.getByRole('dialog')).toContainText('PlaneByte client PDF');await fs.mkdir('../output/qa-phase4-live',{recursive:true});await page.screenshot({path:'../output/qa-phase4-live/send-preview.png'});
   const waiting=page.waitForResponse(r=>r.url().endsWith('/email/leads/'+t.id+'/send')&&r.request().method()==='POST');await page.getByRole('button',{name:'Confirm Send',exact:true}).click();const response=await waiting;state.sent=await response.json();if(state.sent.status!=='SENT'||!state.sent.test_mode)throw new Error('Controlled send did not complete safely.');await save();console.log(JSON.stringify({status:state.sent.status,test_mode:state.sent.test_mode,subject:'[TEST] '+state.subject,test_recipient:account.test_recipient}));
  }
 }else if(action==='sync'){
  if(!state.sent?.thread_id||state.sent.status!=='SENT'||!state.sent.test_mode)throw new Error('A persisted controlled test send is required before reply acceptance.');
  state.sync=await api('/email/sync','POST');const sales=await api('/sales/leads/'+targets[0].id);const workspace=await api('/leads/'+targets[0].id+'/workspace');
  const messages=await api('/email/leads/'+targets[0].id+'/threads/'+state.sent.thread_id);
  const outbound=messages.find(m=>m.id===state.sent.id&&m.direction==='OUTBOUND'&&m.status==='SENT'&&m.test_mode);
  const replies=messages.filter(m=>m.direction==='INBOUND'&&m.status==='RECEIVED');const replyIds=new Set(replies.map(m=>m.id));
  state.checks.message_persisted=Boolean(outbound);
  state.checks.imap_reply_persisted=replies.length>0;
  state.checks.reply_detected=sales.activities.some(a=>a.event_type==='REPLY_DETECTED'&&replyIds.has(a.metadata?.message_id));
  state.checks.reply_activity=sales.activities.some(a=>a.event_type==='EMAIL_RECEIVED'&&a.metadata?.reply_verified&&replyIds.has(a.metadata?.message_id));
  state.checks.reply_status=workspace.lead_status==='REPLIED';
  state.checks.controlled_flow_complete=['message_persisted','imap_reply_persisted','reply_detected','reply_activity','reply_status'].every(k=>state.checks[k]);
  state.reply_acceptance={thread_id:state.sent.thread_id,inbound_count:replies.length,status:workspace.lead_status};
  // Keep bodies and unrelated sales metadata out of deployment evidence.
  delete state.sales;
  console.log(JSON.stringify({sync:state.sync,checks:state.checks,status:workspace.lead_status}));
 }else if(action==='visual'){
  const page=await context.newPage();page.setDefaultTimeout(90000);const errors=[];page.on('pageerror',e=>errors.push(e.message));await fs.mkdir('../output/qa-phase4-live',{recursive:true});
  for(const [width,height] of [[1366,768],[1440,900],[1920,1080],[390,844]]){await page.setViewportSize({width,height});await page.goto(origin+'/outreach');await expect(page.getByRole('heading',{name:'Outreach',exact:true})).toBeVisible();await expect(page.getByRole('table')).toBeVisible();await expect(page.getByRole('button',{name:'Create list',exact:true})).toBeVisible();if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Outreach overflows the viewport');await page.screenshot({path:`../output/qa-phase4-live/outreach-${width}.png`});}
  await page.setViewportSize({width:1440,height:900});await page.goto(origin+'/settings/email');await expect(page.getByText('Hostinger Email',{exact:false})).toBeVisible();await page.screenshot({path:'../output/qa-phase4-live/email-settings.png'});await page.goto(origin+'/settings/templates');await expect(page.getByRole('heading',{name:'Email templates',exact:true})).toBeVisible();await page.screenshot({path:'../output/qa-phase4-live/templates.png'});state.checks.production_visual_sizes=["1366x768","1440x900","1920x1080","390x844"];state.checks.browser_errors=errors;if(errors.length)throw new Error('Browser errors found.');
 }else if(action==='suppression'){
  const t=targets[1];await api('/leads/'+t.id+'/workflow','PATCH',{lead_status:'DO_NOT_CONTACT'});const compose=await api('/email/leads/'+t.id+'/compose');if(!compose.suppressed||compose.recipients.length)throw new Error('Suppression did not block composer defaults.');state.checks.suppression_blocks_composer=true;
  await api('/sales/leads/'+t.id+'/unsuppress?confirmation=ALLOW%20CONTACT','POST');await api('/leads/'+t.id+'/workflow','PATCH',{lead_status:t.lead_status,assigned_to:t.assigned_to});console.log('Suppression verified on the second real scan; original status restored.');
 }else if(action==='restore'){
  for(const t of targets){const sales=await api('/sales/leads/'+t.id);for(const f of sales.followups.filter(f=>f.status==='OPEN'))await api('/sales/leads/'+t.id+'/followups/'+f.id,'PATCH',{status:'CANCELED'});await api('/leads/'+t.id+'/workflow','PATCH',{lead_status:t.lead_status,assigned_to:t.assigned_to});}
  state.checks.original_sales_statuses_restored=true;
 }
 state.checked_at=new Date().toISOString();await save();
}catch(e){console.error(e.name+': '+String(e.message).split('Call log:')[0]);process.exitCode=1;}finally{await browser.close();}
