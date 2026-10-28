import {chromium,expect as playwrightExpect} from '@playwright/test';
import {encode} from 'next-auth/jwt';
import fs from 'node:fs/promises';
const expect=playwrightExpect.configure({timeout:60000}),origin='https://leadengine-livid.vercel.app',output='../output/qa-live/phase35';
const browser=await chromium.launch({channel:'chrome',headless:true});
try{
 const context=await browser.newContext({viewport:{width:1440,height:1000}}),salt='__Secure-authjs.session-token',email=process.env.CHECK_EMAIL;
 const token=await encode({token:{sub:email,email,name:'PlaneByte'},secret:process.env.AUTH_SECRET,salt,maxAge:600});await context.addCookies([{name:salt,value:token,url:origin,httpOnly:true,secure:true,sameSite:'Lax'}]);
 const page=await context.newPage();page.setDefaultTimeout(60000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(origin+'/reports');await expect(page.getByRole('link',{name:'Download PDF',exact:true})).toHaveCount(4);await page.waitForLoadState('networkidle');await page.screenshot({path:output+'/reports.png'});await page.getByRole('heading',{name:'Client PDF reports',exact:true}).scrollIntoViewIfNeeded();await page.screenshot({path:output+'/reports-client-pdfs.png'});
 await page.goto(origin+'/leads/3953');await expect(page.getByRole('link',{name:'Download latest PDF',exact:true})).toBeVisible();await page.waitForLoadState('networkidle');await page.screenshot({path:output+'/detail.png'});
 await page.goto(origin+'/scans/new');await page.getByRole('button',{name:'Select Recommended',exact:true}).click();await page.getByLabel('SEO',{exact:true}).scrollIntoViewIfNeeded();await page.screenshot({path:output+'/new-scan-options.png'});
 const legacyExports={};for(const kind of ['csv','xlsx']){const response=await context.request.get(origin+'/api/scans/29/export/'+kind);if(!response.ok())throw new Error('Existing '+kind+' export unavailable');const bytes=await response.body();if(kind==='xlsx'&&bytes.subarray(0,2).toString()!=='PK')throw new Error('Invalid XLSX export');if(kind==='csv'&&!bytes.toString().includes('Website Opportunity'))throw new Error('CSV opportunity columns missing');legacyExports[kind]={status:response.status(),bytes:bytes.length};}
 const result={legacy_exports:legacyExports,reports_visible:4,detail_existing_pdf_visible:true,scan_options_visible:true,browser_errors:errors,checked_at:new Date().toISOString()};await fs.writeFile('../docs/phase35-final-ui.json',JSON.stringify(result,null,2));if(errors.length)throw new Error('Live browser errors');console.log(JSON.stringify(result));
}catch(error){console.error(error.name+': '+String(error.message).split('Call log:')[0]);process.exitCode=1;}finally{await browser.close();}
