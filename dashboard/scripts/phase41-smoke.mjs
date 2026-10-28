import {chromium,expect as baseExpect} from '@playwright/test';
import {encode} from 'next-auth/jwt';
import fs from 'node:fs/promises';
const expect=baseExpect.configure({timeout:90000}),origin='https://leads.planebyte.com',state={checks:{},screenshots:[]};
const browser=await chromium.launch({channel:'chrome',headless:true});
try{
 const context=await browser.newContext({viewport:{width:1440,height:900}});
 const anonymous=await context.request.get(origin+'/api/email/activity-summary');state.checks.private_metrics_protected=anonymous.status()===401;
 const pixel=await context.request.get(origin+'/t/o/'+'x'.repeat(43)+'.gif');state.checks.public_pixel=pixel.status()===200&&(await pixel.body()).subarray(0,6).toString()==='GIF89a';
 const salt='__Secure-authjs.session-token',email=process.env.CHECK_EMAIL;
 const token=await encode({token:{sub:email,email,name:'PlaneByte acceptance'},secret:process.env.AUTH_SECRET,salt,maxAge:900});await context.addCookies([{name:salt,value:token,url:origin,httpOnly:true,secure:true,sameSite:'Lax'}]);
 const accountResponse=await context.request.get(origin+'/api/email/account'),account=await accountResponse.json();
 if(account.send_mode!=='test'||account.live_approved!==false)throw new Error('Production must remain in test mode.');state.checks.test_mode_preserved=true;
 const page=await context.newPage();page.setDefaultTimeout(90000);const errors=[];page.on('pageerror',e=>errors.push(e.message));await fs.mkdir('../output/qa-phase41',{recursive:true});
 for(const [width,height] of [[1366,768],[1440,900],[1920,1080],[390,844]]){
  await page.setViewportSize({width,height});await page.goto(origin+'/outreach');await expect(page.getByRole('table')).toBeVisible();await expect(page.getByRole('heading',{name:'Email activity',exact:true})).toBeVisible();
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Outreach overflows the viewport.');
  const path=`../output/qa-phase41/outreach-${width}.png`;await page.screenshot({path,fullPage:true});state.screenshots.push(path);
 }
 state.checks.responsive_outreach=true;await page.setViewportSize({width:1440,height:900});await page.goto(origin+'/settings/email');await expect(page.getByRole('heading',{name:'Tracking',exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'TEST MODE',exact:true})).toBeVisible();await page.screenshot({path:'../output/qa-phase41/email-settings.png',fullPage:true});state.checks.tracking_settings=true;
 const draft=JSON.parse(await fs.readFile('../docs/phase41-first-live-draft.json','utf8'));await page.goto(draft.lead_url);await page.getByRole('button',{name:'Compose email',exact:true}).click();await page.getByRole('button',{name:'Load saved draft',exact:true}).click();await expect(page.getByLabel('Subject',{exact:true})).toHaveValue(draft.draft.subject);await page.getByRole('button',{name:'Preview email',exact:true}).click();await expect(page.getByRole('dialog')).toContainText('To: '+account.test_recipient);await expect(page.getByRole('button',{name:'Confirm Send',exact:true})).toBeVisible();await page.screenshot({path:'../output/qa-phase41/prepared-draft-preview.png'});state.checks.prepared_draft_loaded_and_previewed=true;state.checks.first_live_send_not_performed=true;
 state.checks.browser_errors=errors;if(errors.length)throw new Error('Production browser errors found.');
 state.checked_at=new Date().toISOString();await fs.writeFile('../docs/phase41-browser.json',JSON.stringify(state,null,2));console.log(JSON.stringify(state.checks));
}catch(e){console.error('Production browser acceptance did not finish: '+e.name);process.exitCode=1;}finally{await browser.close();}
