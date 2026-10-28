import { chromium,expect } from '@playwright/test';
import { encode } from 'next-auth/jwt';
import fs from 'node:fs/promises';
const origin='https://leadengine-livid.vercel.app';
const record='../docs/production-acceptance-scan.json';
const output='../output/production-acceptance';await fs.mkdir(output,{recursive:true});
const browser=await chromium.launch({channel:'chrome',headless:true});
try{
 const context=await browser.newContext({viewport:{width:1440,height:1000}});
 const email=process.env.CHECK_EMAIL;const salt='__Secure-authjs.session-token';
 const token=await encode({token:{sub:email,email,name:'Production acceptance'},secret:process.env.AUTH_SECRET,salt,maxAge:900});
 await context.addCookies([{name:salt,value:token,url:origin,httpOnly:true,secure:true,sameSite:'Lax'}]);
 const page=await context.newPage();page.setDefaultTimeout(60000);const errors=[];page.on('pageerror',error=>errors.push(error.message));
 const action=process.argv[2];
 if(action==='create'){
  try{await fs.access(record);throw new Error('Acceptance campaign already exists; inspect before creating another.');}catch(error){if(error.code!=='ENOENT')throw error;}
  const health=await (await context.request.get(origin+'/api/system/hosted-health',{timeout:120000})).json();
  for(const name of ['Cloud Worker Configuration','Canary','Lighthouse'])if(!health.checks.some(item=>item.name===name&&item.status==='ready'))throw new Error(name+' is not ready');
  await page.goto(origin+'/scans/new');await page.getByLabel('Austin',{exact:true}).check();
  await page.getByLabel('Home Services',{exact:true}).uncheck();await page.getByLabel('Dentists',{exact:true}).check();
  await page.getByLabel('Balanced',{exact:true}).check();await page.locator('select:has(option[value="include_previous"])').selectOption('include_previous');
  await page.getByLabel('Target qualified leads',{exact:true}).fill('5');
  const responsePromise=page.waitForResponse(response=>response.url()===origin+'/api/campaigns'&&response.request().method()==='POST',{timeout:120000});
  await page.getByRole('button',{name:'Start scan',exact:true}).click();const response=await responsePromise;
  const campaign=await response.json();if(response.status()!==201)throw new Error(JSON.stringify(campaign));
  await page.waitForURL('**/campaigns/'+campaign.id);await page.screenshot({path:output+'/campaign-created.png'});
  await fs.writeFile(record,JSON.stringify({campaign_id:campaign.id,configuration:campaign.configuration,created_at:campaign.created_at,created_via_authenticated_production_ui:true,google_oauth_verified_by_user:true,latest_campaign:campaign},null,2));
  console.log(JSON.stringify({campaign:campaign.id,runs:campaign.runs,status:campaign.status}));
 }else if(action==='progress'){
  const state=JSON.parse(await fs.readFile(record,'utf8'));
  await page.goto(origin+'/campaigns/'+state.campaign_id);await page.locator('h1').waitFor();
  await page.getByText('198',{exact:true}).first().waitFor();
  await page.screenshot({path:output+'/campaign-progress.png'});
  const response=await context.request.get(origin+'/api/campaigns/'+state.campaign_id);const campaign=await response.json();
  console.log(JSON.stringify({authenticated_progress_status:response.status(),campaign:campaign.id,status:campaign.status,counters:campaign.counters}));
 }else if(action==='verify'){
  const state=JSON.parse(await fs.readFile(record,'utf8'));
  const response=await context.request.get(origin+'/api/campaigns/'+state.campaign_id);const campaign=await response.json();
  if(campaign.status!=='COMPLETED')throw new Error('Campaign is '+campaign.status);
  const badOrigin=await context.request.post(origin+'/api/campaigns',{headers:{Origin:'https://untrusted.example'},data:{}});
  if(badOrigin.status()!==403)throw new Error('Cross-origin mutation was not rejected');
  await page.goto(origin+'/campaigns/'+campaign.id);await page.getByText('1 of 1 complete').waitFor();await page.screenshot({path:output+'/campaign-completed.png'});
  await page.getByRole('link',{name:/View results/}).click();await page.locator('tbody tr').first().waitFor();
  await page.goto(origin+'/leads?campaign='+campaign.id+'&min_seo=1&min_security=1');await page.locator('tbody tr').first().waitFor();await page.screenshot({path:output+'/qualified-leads.png'});
  const leads=await (await context.request.get(origin+'/api/intelligence/leads?campaign='+campaign.id+'&min_seo=1&min_security=1')).json();
  if(leads.items.length<5)throw new Error('Fewer than five qualified leads');
  const checked=[];
  for(const lead of leads.items.slice(0,5)){
   const workspace=await (await context.request.get(origin+`/api/leads/${lead.id}/workspace`)).json();
   for(const field of ['website_opportunity_score','seo_opportunity_score','security_opportunity_score'])if(workspace.opportunity?.[field]===null||workspace.opportunity?.[field]===undefined)throw new Error('Missing '+field+' for '+lead.id);
   if(!workspace.opportunity.primary_opportunity)throw new Error('Missing primary opportunity');
   await page.goto(origin+'/leads/'+lead.id);await page.getByRole('heading',{name:'Team workflow'}).waitFor();
   await expect(page.getByLabel('Lead status',{exact:true})).toBeEnabled({timeout:60000});
   await page.screenshot({path:output+'/lead-'+lead.id+'.png'});
   checked.push({id:lead.id,name:lead.name,city:lead.city,vertical:lead.vertical,website:lead.website,contactability:workspace.opportunity.contactability_level,business_scale:workspace.business_scale,first_seen:workspace.first_seen_at,last_seen:workspace.last_seen_at,scores:workspace.opportunity,notes:workspace.notes.length});
  }
  const id=leads.items[0].id;await page.goto(origin+'/leads/'+id);
  await page.getByRole('button',{name:'Shortlist',exact:true}).click();await expect(page.getByLabel('Lead status',{exact:true})).toHaveValue('SHORTLISTED',{timeout:60000});
  await page.getByLabel('Assigned to',{exact:true}).selectOption(email);await expect(page.getByLabel('Assigned to',{exact:true})).toHaveValue(email,{timeout:60000});
  const note='Production acceptance: workflow and reports tested. No outreach was sent.';
  if(!await page.getByText(note,{exact:true}).count()){await page.getByLabel('Add note',{exact:true}).fill(note);await page.getByRole('button',{name:'Add note',exact:true}).click();}
  await page.getByText(note,{exact:true}).waitFor();
  await page.getByRole('button',{name:'Mark Contacted',exact:true}).click();await expect(page.getByLabel('Lead status',{exact:true})).toHaveValue('CONTACTED',{timeout:60000});await page.reload();
  await expect(page.getByLabel('Lead status',{exact:true})).toHaveValue('CONTACTED',{timeout:60000});
  await expect(page.getByLabel('Assigned to',{exact:true})).toHaveValue(email,{timeout:60000});
  await page.getByText('Production acceptance: workflow and reports tested. No outreach was sent.').waitFor();
  await page.getByRole('button',{name:'Generate report',exact:true}).click();await page.getByRole('link',{name:/Open report/}).waitFor();
  const downloads={};for(const kind of ['csv','xlsx','html']){
   const path=kind==='html'?`/api/leads/${id}/report`:`/api/scans/${campaign.runs[0].id}/export/${kind}`;
   const download=await context.request.get(origin+path);if(download.status()!==200)throw new Error(kind+' HTTP '+download.status());
   const data=await download.body();await fs.writeFile(output+'/'+(kind==='html'?'report.html':'leads.'+kind),data);downloads[kind]={bytes:data.length,status:download.status(),contentType:download.headers()['content-type']};
  }
  await page.goto(origin+'/reports');await page.locator(`a[href="/api/scans/${campaign.runs[0].id}/export/csv"]`).waitFor();await page.screenshot({path:output+'/reports.png'});
  await page.goto(origin+'/system');await page.getByText('Cloud Worker Configuration',{exact:true}).waitFor();await page.getByText('Canary',{exact:true}).waitFor();await page.screenshot({path:output+'/system.png'});
  state.latest_campaign=campaign;state.ui_verification={leads:checked,workflow:true,assignment:true,notes:true,refresh_persistence:true,origin_rejection:true,downloads,browser_errors:errors};
  await fs.writeFile(record,JSON.stringify(state,null,2));if(errors.length)throw new Error(JSON.stringify(errors));
  console.log(JSON.stringify({campaign:campaign.id,fully_assessed_qualified:leads.total,ui_verified:checked.length,downloads,browser_errors:errors}));
 }else throw new Error('Use create or verify');
}catch(error){console.error(error.name+': '+String(error.message).split('Call log:')[0]);process.exitCode=1;}finally{await browser.close();}
