import {test,expect} from '@playwright/test';
import {encode} from 'next-auth/jwt';
import fs from 'node:fs';
const catalog=JSON.parse(fs.readFileSync(new URL('../../app/billing/commercial_catalog.json',import.meta.url),'utf8'));
test('saved payment gate and cancellation render on mobile in both themes',async({page,context},info)=>{
 await context.addCookies([{name:'authjs.session-token',value:await encode({token:{sub:'founder@leadengine.example',email:'founder@leadengine.example'},secret:'fixture-session-secret-only-for-local-tests-123456789',salt:'authjs.session-token',maxAge:3600}),url:'http://127.0.0.1:13000',httpOnly:true,sameSite:'Lax'}]);
 const state={enabled:true,required:true,active:false,plans:catalog.plans,terms_version:'planebyte-subscriptions-2026-11-17-v2',can_manage:true,trial_eligible:true,paid_blockers:['Synthetic fixture: merchant acceptance pending'],trial_blockers:['Synthetic fixture: merchant acceptance pending'],contract:null};
 await page.route('**/api/billing/subscription',route=>route.fulfill({json:state}));
 await page.goto('/billing/subscription');
 await expect(page.getByRole('heading',{name:'Choose Your Plan & Payment',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Continue to secure card trial'})).toBeDisabled();
 await expect(page.getByText('Skip',{exact:true})).toHaveCount(0);
 await page.getByRole('checkbox').check();
 await page.getByLabel('Which paid plan should follow your 72-hour trial?').selectOption('growth');
 await expect(page.getByRole('checkbox')).not.toBeChecked();
 for(const theme of ['light','dark'])for(const width of [1440,768,390,320]){
  await page.setViewportSize({width,height:900});await page.evaluate(theme=>document.documentElement.classList.toggle('dark',theme==='dark'),theme);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:info.outputPath(`payment-${theme}-${width}.png`),fullPage:true});
 }
 await page.unroute('**/api/billing/subscription');
 await page.route('**/api/billing/subscription',route=>route.fulfill({json:{...state,contract:{id:'synthetic-contract',provider:'creem',environment:'test',status:'past_due',plan_code:'starter',period_start:1794890000,period_end:1797482000,cancel_confirmed_at:null}}}));
 await page.reload();await expect(page.getByRole('button',{name:'Cancel automatic renewal'})).toBeVisible();
});
