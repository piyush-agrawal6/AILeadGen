import {test,expect,type BrowserContext} from '@playwright/test';
import {encode} from 'next-auth/jwt';
async function session(context:BrowserContext){const email='founder@leadengine.example',secret='fixture-session-secret-only-for-local-tests-123456789';const token=await encode({token:{sub:email,email},secret,salt:'authjs.session-token',maxAge:3600});await context.addCookies([{name:'authjs.session-token',value:token,url:'http://127.0.0.1:13000',httpOnly:true,sameSite:'Lax'}])}
test('internal experiment pages and consequential APIs are denied by default',async({page,context})=>{
 await session(context);const origin='http://127.0.0.1:13000';
 for(const route of ['/api/experiments/setup','/api/experiments/activate']){
  expect((await context.request.post(route,{headers:{origin}})).status()).toBe(404);
 }
 expect((await context.request.get('/api/experiments/current')).status()).toBe(404);
 const response=await page.goto('/experiments/nov-2026');expect(response?.status()).toBe(404);
 await expect(page.getByRole('heading',{name:'PlaneByte 5-Day Outreach Experiment',exact:true})).toHaveCount(0);
});

test('system health never advertises or calls archived experiment generation',async({page,context})=>{
 await session(context);const experimentRequests:string[]=[];
 page.on('request',request=>{if(new URL(request.url()).pathname.startsWith('/api/experiments'))experimentRequests.push(request.url())});
 await page.goto('/settings/system');await expect(page.getByRole('heading',{name:'System Health',exact:true})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Live Provider Checks',exact:true})).toBeVisible();
 await expect(page.getByRole('heading',{name:'AI Copy Generation',exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Check Primary AI (1 synthetic lead)',exact:true})).toHaveCount(0);
 expect(experimentRequests).toEqual([]);
});
