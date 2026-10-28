import { chromium } from '@playwright/test';
import { encode } from 'next-auth/jwt';
import fs from 'node:fs/promises';
const origin='https://leadengine-livid.vercel.app';
const browser=await chromium.launch({channel:'chrome',headless:true});
try{
const context=await browser.newContext({viewport:{width:1440,height:900}});
const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
await fs.mkdir('../output/qa-live',{recursive:true});
await page.goto(origin+'/login');await page.screenshot({path:'../output/qa-live/login.png'});
await page.getByRole('button',{name:/Sign in with Google/}).click();
await page.waitForTimeout(3000);
const text=await page.locator('body').innerText();
const oauth={host:new URL(page.url()).hostname,redirect_uri_mismatch:text.includes('redirect_uri_mismatch'),invalid_client:text.includes('invalid_client'),google_login_form:new URL(page.url()).hostname==='accounts.google.com'&&/Email or phone|Choose an account/i.test(text)};
await page.screenshot({path:'../output/qa-live/google-login-check.png'});
if(process.argv.includes('--oauth-only')){await fs.writeFile('../docs/oauth-check.json',JSON.stringify(oauth,null,2));console.log(JSON.stringify(oauth));await browser.close();process.exit(0);}
const salt='__Secure-authjs.session-token';
const token=await encode({token:{sub:process.env.CHECK_EMAIL,email:process.env.CHECK_EMAIL,name:'LeadEngine acceptance'},secret:process.env.AUTH_SECRET,salt,maxAge:900});
await context.addCookies([{name:salt,value:token,url:origin,httpOnly:true,secure:true,sameSite:'Lax'}]);
const pages=[];
for(const route of ['/','/scans/new','/leads','/settings','/system']){
 const response=await page.goto(origin+route);await page.waitForLoadState('networkidle');
 pages.push({route,status:response.status(),url:new URL(page.url()).pathname});
 await page.screenshot({path:'../output/qa-live/'+(route==='/'?'overview':route.slice(1).replaceAll('/','-'))+'.png'});
}
const response=await context.request.get(origin+'/api/intelligence/overview');
const result={session_type:'Signed short-lived acceptance session; not proof of Google consent',oauth,pages,authenticated_bff_status:response.status(),browser_errors:errors};
await fs.writeFile('../docs/live-dashboard-check.json',JSON.stringify(result,null,2));
console.log(JSON.stringify(result));
}catch(error){console.error(error.name+': '+String(error.message).split('Call log:')[0]);process.exitCode=1;}finally{await browser.close();}
