import {test,expect} from '@playwright/test';
import {encode} from 'next-auth/jwt';
import fs from 'node:fs/promises';
const output='../output/qa-brand';
const score={website_opportunity_score:62,seo_opportunity_score:97,security_opportunity_score:48,primary_opportunity:'SEO',secondary_opportunity:'WEBSITE',contactability_level:'HIGH',scoring_version:'qa',evidence:{WEBSITE:[],SEO:[],SECURITY:[]}};
const business={id:1,name:'Brand preview — QA only',vertical:'dentists',city:'Austin',country:'United States',website:'https://qa.example',phone:'+15125550123',public_email:'hello@qa.example',lead_status:'NEW',prospect_id:'qa-prospect',...score};
const report={id:'qa-report',business_id:1,business_name:business.name,version:1,status:'READY',created_at:'2026-10-26T10:00:00Z',created_by:'founder@leadengine.example'};
test.beforeEach(async({page,context})=>{
 await fs.mkdir(output,{recursive:true});const secret='brand-local-preview-secret-not-for-production-123456789',email='founder@leadengine.example';const token=await encode({token:{sub:email,email,name:'QA'},secret,salt:'authjs.session-token',maxAge:900});await context.addCookies([{name:'authjs.session-token',value:token,url:'http://127.0.0.1:13001',httpOnly:true,sameSite:'Lax'}]);
 await page.route('**/api/**',async route=>{const path=new URL(route.request().url()).pathname;let data:unknown={};
  if(path==='/api/intelligence/leads')data={items:[business],total:1,page:1,page_size:25,total_pages:1};
  else if(path==='/api/intelligence/overview')data={total_leads:1,statuses:[{lead_status:'NEW',count:1}]};
  else if(path==='/api/markets/presets')data=[{country_code:'US',country:'United States',cities:['Miami','Dallas','Austin'].map((name,i)=>({id:String(i),display_name:name,lookup_name:name+', United States',country:'United States',country_code:'US',priority:i}))}];
  else if(path==='/api/verticals')data=[{key:'home_services',display_name:'Home Services'},{key:'dentists',display_name:'Dentists'}];
  else if(path==='/api/campaigns'||path==='/api/reports')data=[];
  else if(path==='/api/sales/views'||path==='/api/sales/lists')data=[];
  else if(path==='/api/sales/outreach')data={items:[],counts:{today:0,replied:0},total:0,total_pages:1};
  else if(path==='/api/sales/leads/1')data={suppressed:false,currency:'GBP',followups:[],activities:[],lists:[],threads:[]};
  else if(path==='/api/system/limits')data={max_cities_per_scan:10,max_target_leads:1000,executor:'gcp'};
  else if(path==='/api/leads/1/workspace')data={id:'qa-prospect',lead_status:'NEW',assigned_to:null,first_seen_at:'2026-10-26',last_seen_at:'2026-10-26',times_discovered:1,business_scale:'LOCAL',notes:[],opportunity:score};
  else if(path==='/api/leads/1')data={business,website_status:'REACHABLE',profile:null,lighthouse:null,findings:[],contacts:[]};
  else if(path==='/api/users')data=[{id:'founder@leadengine.example',email:'founder@leadengine.example',display_name:'QA'}];
  else if(path==='/api/client-reports')data={items:[report],total:1,page:1,page_size:25,total_pages:1};
  await route.fulfill({json:data});
 });
});
test('new logo and requested dark palette are the default',async({page})=>{
 await page.goto('/leads');await expect(page.getByRole('link',{name:business.name})).toBeVisible();await expect(page.locator('body')).toHaveCSS('background-color','rgb(15, 17, 16)');await expect(page.locator('body')).toHaveCSS('color','rgb(237, 233, 225)');const logo=page.getByRole('link',{name:'PlaneByte overview'}).locator('img');await expect(logo).toHaveAttribute('src',/logo\.png/);await expect.poll(()=>logo.evaluate(element=>(element as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);await page.screenshot({path:output+'/workspace-dark.png'});
 await page.getByRole('button',{name:/More filters/}).click();await expect(page.getByRole('button',{name:'Apply filters'})).toHaveCSS('background-color','rgb(255, 90, 31)');await page.screenshot({path:output+'/filters-dark.png'});await page.keyboard.press('Escape');
});
test('brand theme remains usable in light mode and on a phone',async({page})=>{
 await page.goto('/leads');await page.getByRole('button',{name:'light theme',exact:true}).click();await expect(page.getByRole('link',{name:business.name})).toBeVisible();await page.screenshot({path:output+'/workspace-light.png'});await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'dark theme',exact:true}).click();await page.getByRole('button',{name:/More filters/}).click();await expect(page.getByRole('dialog')).toBeVisible();await page.screenshot({path:output+'/filters-phone.png'});await page.keyboard.press('Escape');expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
test('scan choices and lead detail carry the new branding',async({page})=>{
 await page.goto('/scans/new');await page.getByRole('button',{name:'Select Recommended'}).click();await page.getByLabel('SEO',{exact:true}).scrollIntoViewIfNeeded();await expect(page.getByRole('button',{name:'Start scan',exact:true})).toHaveCSS('background-color','rgb(255, 90, 31)');await page.screenshot({path:output+'/scan-dark.png'});await page.goto('/leads/1');await expect(page.getByRole('link',{name:'Download latest PDF'})).toBeVisible();await page.screenshot({path:output+'/detail-dark.png'});
});
test('permanent deletion requires a scoped preview and typed confirmation',async({page})=>{
 let removed=false;
 await page.route('**/api/deletions/lead/1/**',route=>route.fulfill({json:{name:business.name,token:'a'.repeat(64),observations:2,scans:2,canonical_leads:1,reports:3,files:5,shared_leads_retained:0,active_run_ids:[],removes_related_exports:true}}));
 await page.route('**/api/deletions/lead/1',async route=>{expect(route.request().method()).toBe('DELETE');expect(route.request().postDataJSON().confirmation).toBe('DELETE');removed=true;await route.fulfill({json:{deleted:true}});});
 await page.goto('/leads');await page.getByRole('button',{name:'Delete lead',exact:true}).click();
 await expect(page.getByRole('dialog')).toContainText('3 report versions');
 await expect(page.getByRole('button',{name:'Permanently delete',exact:true})).toBeDisabled();
 await page.getByLabel('Deletion confirmation').fill('DELETE');await page.getByRole('button',{name:'Permanently delete',exact:true}).click();
 await expect.poll(()=>removed).toBe(true);await expect(page.getByRole('dialog')).toHaveCount(0);
});
