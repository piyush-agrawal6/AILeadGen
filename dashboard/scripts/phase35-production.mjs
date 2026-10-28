import {chromium,expect as playwrightExpect} from '@playwright/test';
const expect=playwrightExpect.configure({timeout:60000});
import {encode} from 'next-auth/jwt';
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
const origin='https://leadengine-livid.vercel.app',record='../docs/phase35-production.json',output='../output/qa-live/phase35';
await fs.mkdir(output,{recursive:true});
const state=await fs.readFile(record,'utf8').then(JSON.parse).catch(()=>({reports:{},checks:{}}));
const save=()=>fs.writeFile(record,JSON.stringify(state,null,2));
const browser=await chromium.launch({channel:'chrome',headless:true});
try{
 const context=await browser.newContext({viewport:{width:1440,height:900}});
 state.checks.unauthenticated_pdf_rejected=(await context.request.get(origin+'/api/client-reports/unknown/download')).status()===401;
 const email=process.env.CHECK_EMAIL,salt='__Secure-authjs.session-token';
 const token=await encode({token:{sub:email,email,name:'PlaneByte'},secret:process.env.AUTH_SECRET,salt,maxAge:900});
 await context.addCookies([{name:salt,value:token,url:origin,httpOnly:true,secure:true,sameSite:'Lax'}]);
 const page=await context.newPage();page.setDefaultTimeout(120000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(origin+'/leads?search=GK%20Dental');await page.getByRole('link',{name:'GK Dental',exact:true}).waitFor();
 await page.getByRole('button',{name:'light theme',exact:true}).click();
 const row=page.locator('tbody tr').filter({has:page.getByRole('link',{name:'GK Dental',exact:true})});
 const status=row.getByRole('combobox',{name:'Lead status for GK Dental'});const original=await status.inputValue();
 async function setStatus(value){if(await status.inputValue()===value)return;const saved=page.waitForResponse(r=>r.url().includes('/workflow')&&r.request().method()==='PATCH');await status.selectOption(value);if(!(await saved).ok())throw new Error('Status save failed');await expect(status).toBeEnabled();}
 try{await setStatus('LOST');await page.reload();await expect(status).toHaveValue('LOST');state.checks.inline_lost_persists=true;}
 finally{await setStatus(original);await page.reload();await expect(status).toHaveValue(original);state.checks.workflow_restored=true;}
 await page.screenshot({path:output+'/workspace.png'});
 const filters=page.getByRole('button',{name:/More filters/});await filters.click();await page.screenshot({path:output+'/filters.png'});await page.keyboard.press('Escape');await expect(filters).toBeFocused();state.checks.live_filter_escape_focus=true;
 // The first PDF is generated through the visible workspace action.
 if(!state.reports.reachable){
  const generate=row.getByRole('button',{name:'Generate PDF',exact:true});
  if(await generate.count())await generate.click();
  await row.getByRole('link',{name:'Download PDF',exact:true}).waitFor({timeout:180000});
  const href=await row.getByRole('link',{name:'Download PDF',exact:true}).getAttribute('href');const id=href.split('/')[3];
  state.reports.reachable=await (await context.request.get(origin+'/api/client-reports/'+id)).json();await save();
 }
 async function generateReport(kind,businessId){
  if(state.reports[kind])return;
  const response=await context.request.post(origin+`/api/leads/${businessId}/pdf-reports`,{headers:{Origin:origin}});
  if(response.status()!==202)throw new Error('PDF request rejected: HTTP '+response.status());
  state.reports[kind]=await response.json();await save();
 }
 if(!process.env.NO_WEBSITE_LEAD_ID)throw new Error('Choose an existing no-website observation for acceptance.');
 for(const [kind,businessId] of [['unreachable',3918],['no-website',Number(process.env.NO_WEBSITE_LEAD_ID)],['reachable-v2',3953]])await generateReport(kind,businessId);
 for(const [kind,initial] of Object.entries(state.reports)){
  let report=initial;const deadline=Date.now()+240000;
  while(['QUEUED','GENERATING'].includes(report.status)&&Date.now()<deadline){await new Promise(r=>setTimeout(r,4000));const response=await context.request.get(origin+'/api/client-reports/'+report.id);if(!response.ok())throw new Error('Report status unavailable');report=await response.json();}
  if(report.status!=='READY')throw new Error(kind+' PDF did not become ready: '+report.status);
  const response=await context.request.get(origin+'/api/client-reports/'+report.id+'/download');const bytes=await response.body();
  if(!response.ok()||bytes.subarray(0,5).toString()!=='%PDF-'||bytes.length<10000)throw new Error('Invalid '+kind+' PDF download');
  const sha=createHash('sha256').update(bytes).digest('hex');if(initial.sha256&&initial.sha256!==sha)throw new Error('An immutable report changed');
  state.reports[kind]={...report,bytes:bytes.length,sha256:sha,downloaded:true};await save();
  if(kind!=='reachable-v2')await fs.writeFile('../output/pdf/planebyte-'+kind+'.pdf',bytes);
 }
 state.checks.version_preserved=state.reports['reachable-v2'].version>state.reports.reachable.version;
 const firstAgain=await context.request.get(origin+'/api/client-reports/'+state.reports.reachable.id+'/download');
 state.checks.old_version_unchanged=createHash('sha256').update(await firstAgain.body()).digest('hex')===state.reports.reachable.sha256;
 await page.goto(origin+'/leads/3953');await page.getByRole('heading',{name:'Client PDF report'}).waitFor();await page.screenshot({path:output+'/detail.png',fullPage:true});
 await page.goto(origin+'/reports');await page.getByRole('heading',{name:'Client PDF reports'}).waitFor();await page.screenshot({path:output+'/reports.png'});
 await page.goto(origin+'/scans/new');state.checks.duplicate_location_tab_removed=await page.getByRole('tab',{name:'Country / Cities',exact:true}).count()===0;await page.getByRole('button',{name:'Select Recommended',exact:true}).click();await page.screenshot({path:output+'/new-scan.png'});
 const health=await context.request.get(origin+'/api/system/hosted-health',{timeout:120000});state.hosted_health=await health.json();
 state.checked_at=new Date().toISOString();state.session_type='Short-lived signed acceptance session; Google login was separately confirmed by the user.';state.browser_errors=errors;await save();
 if(errors.length||Object.values(state.checks).some(value=>value!==true))throw new Error('A production acceptance check failed; inspect the saved record.');
 console.log(JSON.stringify({checks:state.checks,reports:Object.values(state.reports).map(r=>({status:r.status,version:r.version,bytes:r.bytes})),browser_errors:errors}));
}catch(error){console.error(error.name+': '+String(error.message).split('Call log:')[0]);process.exitCode=1;}finally{await browser.close();}
