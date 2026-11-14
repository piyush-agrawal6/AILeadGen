import {test,expect,type BrowserContext} from '@playwright/test';
import {encode} from 'next-auth/jwt';
const origin='http://127.0.0.1:13000';
async function session(context:BrowserContext){const email='founder@leadengine.example';await context.addCookies([{name:'authjs.session-token',value:await encode({token:{sub:email,email},secret:'fixture-session-secret-only-for-local-tests-123456789',salt:'authjs.session-token',maxAge:3600}),url:origin,httpOnly:true,sameSite:'Lax'}]);}
for(const width of [1440,768,390])test(`Intent-only release preserves research and shared settings at ${width}px`,async({page,context})=>{
 test.setTimeout(180000);await page.setViewportSize({width,height:900});await session(context);
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await expect(page).toHaveURL(/\/intent-radar$/);await expect(page.getByRole('heading',{name:'Intent Radar',exact:true})).toBeVisible();
 if(width<768)await page.getByRole('button',{name:'Open navigation'}).click();
 expect(await page.getByRole('button',{name:'Switch PlaneByte product'}).count()).toBe(0);
 for(const label of ['Find Leads','Companies','Contacts','Campaigns','Outreach','Schedules'])await expect(page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:label,exact:true})).toHaveCount(0);
 if(width<768)await page.keyboard.press('Escape');
 for(const path of ['/campaigns','/scans/4','/outreach','/settings/limits','/settings/templates','/settings/integrations']){await page.goto(path);await expect(page).toHaveURL(/\/intent-radar$/);}
 for(const path of ['/intent-radar/signals','/intent-radar/monitors','/intent-radar/growth','/intent-radar/growth/research','/intent-radar/settings','/settings','/settings/developer','/help','/billing']){
  await page.goto(path);await expect(page.locator('main').first()).toBeVisible();
  if(path!=='/billing')await expect(page.locator('body')).not.toContainText('Lead Engine');else await expect(page.getByRole('heading',{name:'Billing & usage',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 }
 const access=await(await context.request.get('/api/organization/products')).json();expect(access.lead_engine_available).toBe(false);expect(access.lead_engine).toBe(false);expect(access.intent_radar.enabled).toBe(true);
 expect((await context.request.get('/api/workflow/safety')).status()).toBe(404);
 expect(errors).toEqual([]);
});
test('unentitled workspace receives a stable restricted page rather than a redirect loop',async({page,context})=>{
 await session(context);const workspaces=await(await context.request.get('/api/organization/workspaces')).json();const blocked=workspaces.items.find((w:{name:string})=>w.name==='Radar unavailable workspace');
 expect((await context.request.put('/api/organization/active',{headers:{origin},data:{organization_id:blocked.organization_id}})).status()).toBe(200);
 await page.goto('/');await expect(page).toHaveURL(/\/intent-radar$/);await expect(page.getByRole('heading',{name:'Intent Radar access is restricted'})).toBeVisible();
 expect((await context.request.get('/api/intent-radar/overview')).status()).toBe(404);await expect(page.getByRole('link',{name:'Review workspace access'})).toBeVisible();
});
