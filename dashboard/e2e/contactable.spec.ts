import {test,expect,type BrowserContext} from '@playwright/test';
import {encode} from 'next-auth/jwt';
async function session(context:BrowserContext){const name='authjs.session-token';const token=await encode({secret:'fixture-session-secret-only-for-local-tests-123456789',salt:name,token:{email:'founder@leadengine.example',name:'Founder'},maxAge:3600});await context.addCookies([{name,value:token,domain:'127.0.0.1',path:'/',httpOnly:true,sameSite:'Lax'}])}
test('archived fixed introduction results are denied by default at desktop and mobile widths',async({page,context})=>{
 await session(context);
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:900});
  const response=await page.goto('/outreach/results');expect(response?.status()).toBe(404);
  await expect(page.getByRole('heading',{name:'Outreach Results',exact:true})).toHaveCount(0);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 }
 expect((await context.request.get('/api/email/intro-analytics')).status()).toBe(404);
});
