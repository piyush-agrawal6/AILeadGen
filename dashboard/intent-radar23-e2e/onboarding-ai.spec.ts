import {test,expect,type BrowserContext,type Page,type TestInfo} from '@playwright/test';
import {encode} from 'next-auth/jwt';
const origin='http://127.0.0.1:13000';
async function session(c:BrowserContext,email='cofounder@leadengine.example'){await c.addCookies([{name:'authjs.session-token',value:await encode({token:{sub:email,email},secret:'fixture-session-secret-only-for-local-tests-123456789',salt:'authjs.session-token',maxAge:3600}),url:origin,httpOnly:true,sameSite:'Lax'}]);}

async function capture(page:Page,info:TestInfo,step:string){
 if(process.env.ONBOARDING_VISUAL_EVIDENCE!=='1')return;
 for(const width of [320,390,768,1024,1440,1920]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:info.outputPath(`${step}-${width}.png`)})}
}
test('owner reviews AI setup; saved business answers survive activation and payment deferral',async({page,context},info)=>{
  await session(context);await page.goto('/intent-radar');await expect(page).toHaveURL(/\/onboarding$/);
  await expect(page.getByLabel('Company website',{exact:true})).toBeVisible();await capture(page,info,'business');
 await page.getByLabel('Company website',{exact:true}).fill('https://example.com');await page.getByRole('button',{name:'Analyze my website'}).click();
 await expect(page.getByText('Business profile ready for review',{exact:true})).toBeVisible({timeout:45000});await capture(page,info,'profile');await page.getByRole('button',{name:'Save business profile & continue'}).click();
 const candidates=page.getByRole('checkbox',{name:/^Include /});await expect(candidates).toHaveCount(5,{timeout:45000});expect((await(await context.request.get('/api/organization/icps')).json()).total).toBe(0);
 await capture(page,info,'icp');await page.getByRole('radio',{name:'Set Software studios as primary ICP'}).check();await page.getByRole('button',{name:'Save ideal customers & continue'}).click();await expect(page.locator('#onboarding-research-keywords')).toBeVisible();await page.reload();await expect(page.locator('#onboarding-research-keywords')).toBeVisible();await capture(page,info,'research');await page.locator('#onboarding-research-keywords').fill('Workflow tools');await page.locator('#onboarding-excluded-keywords').fill('recruitment');await page.getByRole('button',{name:'Save research setup & continue'}).click();
 await expect(page.getByRole('button',{name:'Continue to secure checkout'})).toBeVisible();await capture(page,info,'activation');await expect(page.getByLabel('PlaneByte Copilot',{exact:true})).toHaveCount(0);
 for(const width of [1440,768,390,320]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await expect(page.getByRole('link',{name:'privacy policies'})).toBeVisible();}
 const state=await(await context.request.get('/api/organization/onboarding/assistant-context')).json();expect(state.progress.status).toBe('COMPLETED');expect(state.progress.preferences.research_keywords).toEqual(['Workflow tools']);expect(state.progress.default_icp_id).toBeTruthy();expect((await context.request.get('/api/intent-radar/overview')).status()).toBe(402);
 await page.reload();await expect(page.getByRole('heading',{name:'Your reviewed context is saved'})).toBeVisible();await expect(page.getByRole('link',{name:'Manage Subscription'})).toBeVisible();
});
test('failed analysis leaves an editable manual form and completed users can open their workspace',async({page,context})=>{
 await session(context,'founder@leadengine.example');await page.goto('/intent-radar');await expect(page).toHaveURL(/\/intent-radar$/);
 expect((await context.request.post('/api/organization/workspaces',{headers:{origin},data:{name:'Isolated recovery workspace',request_id:crypto.randomUUID()}})).status()).toBe(201);
 await page.goto('/onboarding');await page.getByLabel('Company website',{exact:true}).fill('https://example.com/failure');await page.getByRole('button',{name:'Analyze my website'}).click();await expect(page.getByText('Analysis did not complete',{exact:true}).first()).toBeVisible({timeout:45000});
 await page.getByRole('button',{name:/Back to your business/}).click();await page.getByRole('button',{name:'Set up manually'}).click();await page.getByLabel('Company name',{exact:true}).fill('Offline Engineering');await page.getByLabel('Company description',{exact:true}).fill('Custom workflow engineering for software companies.');
 if(!await page.getByLabel('Product or service name',{exact:true}).count())await page.getByRole('button',{name:/Add.*(service|offering|product)/i}).click();await page.getByLabel('Product or service name',{exact:true}).first().fill('Application engineering');await page.getByRole('button',{name:'Save business profile & continue'}).click();await expect(page.getByRole('heading',{name:'Choose your ideal customers'})).toBeVisible();
});
