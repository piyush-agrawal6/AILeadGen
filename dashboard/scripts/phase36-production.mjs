import {chromium} from '@playwright/test';
import {encode} from 'next-auth/jwt';
import fs from 'node:fs/promises';
import {randomUUID,createHash} from 'node:crypto';
const origin='https://leads.planebyte.com',record='../docs/phase36-production.json',action=process.argv[2]||'check';
const state=await fs.readFile(record,'utf8').then(JSON.parse).catch(()=>({checks:{},reports:{}}));
const save=()=>fs.writeFile(record,JSON.stringify(state,null,2));
const browser=await chromium.launch({channel:'chrome',headless:true});
try {
 const context=await browser.newContext({viewport:{width:1440,height:1000}}),salt='__Secure-authjs.session-token',email=process.env.CHECK_EMAIL;
 state.checks.unauthenticated_protected=(await context.request.get(origin+'/api/deletions/lead/3953/preview')).status()===401;
 const token=await encode({token:{sub:email,email,name:'PlaneByte verification'},secret:process.env.AUTH_SECRET,salt,maxAge:900});
 await context.addCookies([{name:salt,value:token,url:origin,httpOnly:true,secure:true,sameSite:'Lax'}]);
 const api=async(path,method='GET',data)=>{const r=await context.request.fetch(origin+'/api'+path,{method,headers:{Origin:origin},data,timeout:120000});const body=await r.json();if(!r.ok())throw new Error(`${method} ${path}: ${r.status()} ${typeof body.detail==='string'?body.detail:'request failed'}`);return body;};
 if(action==='campaign'||action==='retry-campaign'){
  if(action==='retry-campaign'&&state.campaign){state.attempts=[...(state.attempts||[]),state.campaign];delete state.campaign;await save();}
  if(!state.campaign){const id=randomUUID();state.campaign=await api('/campaigns','POST',{cities:['London, United Kingdom'],verticals:['dentists'],opportunities:['WEBSITE','SEO','SECURITY'],quality:'balanced',business_scales:['SMALL_GROUP','MID_MARKET'],results:'all',target:10,lighthouse_enabled:true,social_enrichment_enabled:true,social_activity_enabled:true,request_id:id});await save();}
  state.campaign=await api('/campaigns/'+state.campaign.id);console.log(JSON.stringify({campaign:state.campaign.id,status:state.campaign.status,runs:state.campaign.runs}));
 } else if(action==='reports'){
  const ids=[['reachable',3953],['no-website',5446],['unreachable',3918]];
  for(const [kind,id] of ids)if(!state.reports[kind]){state.reports[kind]=await api('/leads/'+id+'/pdf-reports','POST');await save();}
  for(const [kind,r] of Object.entries(state.reports)){const report=await api('/client-reports/'+r.id);state.reports[kind]=report;if(report.status==='READY'){const response=await context.request.get(origin+'/api/client-reports/'+r.id+'/download');if(!response.ok())throw new Error('PDF download failed');await fs.writeFile('../output/pdf/planebyte-phase36-'+kind+'.pdf',await response.body());}console.log(kind+': '+report.status+' v'+report.version);}
  const prior=JSON.parse(await fs.readFile('../docs/brand-production.json','utf8')).reports;let preserved=true;
  for(const r of Object.values(prior)){const response=await context.request.get(origin+'/api/client-reports/'+r.id+'/download');preserved=preserved&&response.ok()&&createHash('sha256').update(await response.body()).digest('hex')===r.sha256;}
  state.checks.previous_reports_unchanged=preserved;if(!preserved)throw new Error('Previous report bytes changed');
 } else if(action==='scan-report'){
  const preferred=Number(process.argv[3]);const evidence=JSON.parse(await fs.readFile('../docs/phase36-status.json','utf8')),capture=[...(evidence.captures||[]),...(evidence.targeted_reaudit?.captures||[])].find(c=>c.status==='READY'&&(!preferred||c.business_id===preferred));
  if(!capture)throw new Error('No scan-time screenshot is ready yet.');
  if(!state.scan_report_business_id||state.scan_report_business_id!==capture.business_id){state.validation_reports={...state.validation_reports,['prior_reachable_'+(state.scan_report_business_id||'baseline')]:state.reports.reachable};state.reports.reachable=await api('/leads/'+capture.business_id+'/pdf-reports','POST');state.scan_report_business_id=capture.business_id;await save();}
  const mid=[...(evidence.campaign_intelligence||[]),...(evidence.targeted_reaudit?.intelligence||[])].find(i=>i.business_scale==='MID_MARKET'&&i.reachable);
  if(mid&&!state.reports['mid-market']){state.reports['mid-market']=await api('/leads/'+mid.business_id+'/pdf-reports','POST');state.mid_market_business_id=mid.business_id;await save();}
  console.log(JSON.stringify({capture_business_id:state.scan_report_business_id,mid_market_business_id:state.mid_market_business_id||null}));
 } else if(action==='resume-queued-report'){
  const report=state.reports.unreachable;const current=await api('/client-reports/'+report.id);
  if(current.status==='QUEUED'){const resumed=await api('/leads/'+report.business_id+'/pdf-reports','POST');if(resumed.id!==report.id)throw new Error('Queued report identity changed');state.reports.unreachable=resumed;console.log('Existing queued report dispatched.');}
  else console.log('Report status: '+current.status);
 } else if(action==='delete-qa'){
  const qa=JSON.parse(await fs.readFile('../tmp/phase36-delete-qa.json','utf8'));
  for(const item of qa.targets){if(state.checks['deleted_'+item.kind+'_'+item.id])continue;const p=await api('/deletions/'+item.kind+'/'+item.id+'/preview');if(!p.name.includes('Phase36 deletion QA'))throw new Error('Refusing to delete a non-QA record');if(p.active_run_ids.length)throw new Error('QA has active workers');await api('/deletions/'+item.kind+'/'+item.id,'DELETE',{confirmation:'DELETE',preview_token:p.token});state.checks['deleted_'+item.kind+'_'+item.id]=true;await save();}
 } else {
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(origin+'/leads/3953');await page.getByRole('heading',{name:'Social presence',exact:true}).waitFor();await page.getByRole('button',{name:'Delete lead',exact:true}).click();await page.getByRole('dialog').waitFor();await page.getByLabel('Deletion confirmation').waitFor();state.checks.live_deletion_preview=true;await fs.mkdir('../output/qa-phase36',{recursive:true});await page.screenshot({path:'../output/qa-phase36/delete-preview.png'});await page.keyboard.press('Escape');
  await page.goto(origin+'/scans/new');state.checks.default_mid_market=await page.getByRole('checkbox',{name:'Mid Market',exact:true}).isChecked();await page.screenshot({path:'../output/qa-phase36/new-scan.png'});
  state.checks.browser_errors=errors;state.health=await api('/system/hosted-health');console.log(JSON.stringify({checks:state.checks,health:state.health}));
 }
 state.checked_at=new Date().toISOString();await save();
}catch(e){console.error(e.name+': '+String(e.message).split('Call log:')[0]);process.exitCode=1;}finally{await browser.close();}
