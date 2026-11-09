import {test,expect} from '@playwright/test';
import {encode} from 'next-auth/jwt';
const secret='fixture-session-secret-only-for-local-tests-123456789';
test('master counts, filters, pagination and bulk actions',async({page,context})=>{
 const token=await encode({token:{sub:'founder@leadengine.example',email:'founder@leadengine.example'},secret,salt:'authjs.session-token',maxAge:3600});
 await context.addCookies([{name:'authjs.session-token',value:token,url:'http://127.0.0.1:13000',httpOnly:true,sameSite:'Lax'}]);
 await page.route('**/api/automation/master-leads?*',async route=>{
  const url=new URL(route.request().url());const n=url.searchParams.get('page')||'1';
  await route.fulfill({json:{items:[{prospect_id:'controlled-'+n,business_id:Number(n),name:'Controlled '+n,city:'London',country:'United Kingdom',vertical:'dentists',phone:'123',public_email:null,contact_state:'MANUAL_CONTACT_REQUIRED',sales_state:'QUALIFIED',commercial_fit:'HIGH',business_scale:'SMALL_GROUP',social_profiles:[]}],total:26,counts:{all:26,today:2,manual:26}}});
 });
 await page.route('**/api/automation/identity-review',route=>route.fulfill({json:{total:1,items:[{id:99,name:'Controlled identity review',domain:'controlled.invalid',city:'London',run_id:1}]}}));
 await page.route('**/api/sales/lists',route=>route.fulfill({json:[]}));
 await page.goto('/master-leads');
 await expect(page.getByRole('button',{name:'New Today 2',exact:true})).toBeVisible();
 await expect(page.getByText('Identity review required (1)',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Next',exact:true}).click();
 await expect(page.getByText('Controlled 2',{exact:true})).toBeVisible();
 await page.getByText('Filters',{exact:true}).click();
 await page.getByLabel('Usable email',{exact:true}).selectOption('no');
 await expect(page.getByText('Controlled 1',{exact:true})).toBeVisible();
 await page.getByLabel('Select Controlled 1',{exact:true}).check();
 const bulk=page.getByLabel('Bulk action',{exact:true});
 for(const value of ['sales','assign','list','followup','dnc','export'])await expect(bulk.locator('option[value="'+value+'"]')).toHaveCount(1);
 await page.getByRole('button',{name:'New Today 2',exact:true}).click();
 await expect(page.getByLabel('Bulk action',{exact:true})).toHaveCount(0);
});

test('outreach limits and market pagination preserve existing APIs',async({page,context})=>{
 const token=await encode({token:{sub:'founder@leadengine.example',email:'founder@leadengine.example'},secret,salt:'authjs.session-token',maxAge:3600});await context.addCookies([{name:'authjs.session-token',value:token,url:'http://127.0.0.1:13000',httpOnly:true,sameSite:'Lax'}]);
 let targets={daily_qualified_lead_target:100,daily_email_target:100,max_hour:10,max_day:100,followup_days:3,automation_timezone:'Asia/Kolkata'};
 await page.route('**/api/automation/targets',route=>{if(route.request().method()==='PUT')targets=route.request().postDataJSON();return route.fulfill({json:targets});});
 await page.route('**/api/automation/markets/page?*',route=>{const n=new URL(route.request().url()).searchParams.get('page')||'1';return route.fulfill({json:{total:30,items:[{id:'market-'+n,country:'United Kingdom',city:'Controlled city '+n,vertical:'dentists',enabled:1,priority:0,cooldown_days:7,total_scans:0}]}})});
 await page.goto('/settings/limits');await page.getByLabel('Hourly email limit',{exact:true}).fill('3');await page.getByRole('button',{name:'Save Limits',exact:true}).click();await expect.poll(()=>targets.max_hour).toBe(3);
 await page.goto('/settings/markets');await page.getByRole('button',{name:'Next',exact:true}).click();await expect(page.getByText('Controlled city 2, United Kingdom',{exact:true})).toBeVisible();
});
