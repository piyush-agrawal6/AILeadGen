import {test,expect,type BrowserContext} from '@playwright/test';
import {encode} from 'next-auth/jwt';
import {randomUUID} from 'node:crypto';
const secret='fixture-session-secret-only-for-local-tests-123456789';
async function session(context:BrowserContext,email='founder@leadengine.example'){const token=await encode({token:{sub:email,email},secret,salt:'authjs.session-token',maxAge:3600});await context.addCookies([{name:'authjs.session-token',value:token,url:'http://127.0.0.1:13000',httpOnly:true,sameSite:'Lax'}])}
test('unauthenticated pages and APIs retain session and CSP protection',async({page,request})=>{await page.goto('/');await expect(page).toHaveURL(/\/login/);await expect(page.getByRole('button',{name:/Continue with Google/})).toBeVisible();expect((await request.post('/api/workflow/runs',{data:{kind:'OUTREACH'}})).status()).toBe(401);const response=await request.get('/login');expect(response.headers()['content-security-policy']).toContain('nonce-');expect(response.headers()['content-security-policy']).not.toContain('unsafe-eval')});
test('real local fixture campaign remains shared and linked across operations APIs',async({page,context,browser})=>{
 await session(context);expect((await context.request.put('/api/automation/controls',{headers:{origin:'http://127.0.0.1:13000'},data:{scan_paused:false,email_paused:true}})).status()).toBe(200);expect((await context.request.put('/api/foundation/roles',{headers:{origin:'http://127.0.0.1:13000'},data:{email:'cofounder@leadengine.example',role:'OPERATOR'}})).status()).toBe(200);const cid=randomUUID();const response=await context.request.post('/api/campaigns',{headers:{origin:'http://127.0.0.1:13000'},data:{cities:['Miami'],verticals:['dentists'],target:5,fixture:true,request_id:cid,lighthouse_enabled:false}});expect(response.status()).toBe(201);
 await expect.poll(async()=>{const r=await context.request.get('/api/operations/campaigns/'+cid);return (await r.json()).status},{timeout:45000}).toBe('COMPLETED');
 const result=await(await context.request.get('/api/operations/campaigns/'+cid+'/leads')).json();expect(result.qualified).toBeGreaterThan(0);expect(result.total_accounted).toBe(result.qualified);const id=result.items[0].business_id;
 await page.goto('/leads/'+id);await expect(page.getByRole('heading',{name:'Team workflow'})).toBeVisible();await page.getByLabel('Add note',{exact:true}).fill('Shared campaign context retained.');await page.getByRole('button',{name:'Add note',exact:true}).click();await expect(page.getByText('Shared campaign context retained.',{exact:true})).toBeVisible();
 const second=await browser.newContext();await session(second,'cofounder@leadengine.example');const other=await second.newPage();await other.goto('/leads/'+id);await expect(other.getByText('Shared campaign context retained.',{exact:true})).toBeVisible();const assignment=other.waitForResponse(response=>response.request().method()==='PATCH'&&response.url().endsWith('/leads/'+id+'/workflow'));await other.getByLabel('Assigned to',{exact:true}).selectOption('cofounder@leadengine.example');expect((await assignment).status()).toBe(200);await page.reload();await expect(page.getByLabel('Assigned to',{exact:true})).toHaveValue('cofounder@leadengine.example');await second.close();
 await page.goto('/campaigns?selected='+cid);await expect(page.getByRole('dialog')).toBeVisible();await expect(page.getByText('Total accounted',{exact:true})).toBeVisible();await expect(page.getByRole('link',{name:'Run Emails',exact:true}).last()).toHaveAttribute('href','/outreach/new?campaign='+cid);
 expect((await context.request.post('/api/workflow/runs',{headers:{origin:'http://127.0.0.1:13000'},data:{kind:'OUTREACH'}})).status()).toBe(422);
});


test('requested workspace limits save through the authenticated production proxy without activation',async({page,context})=>{
 await session(context);await page.goto('/settings/limits');
 for(const [label,value] of [['Daily qualified lead target','500'],['Daily email target','500'],['Hourly email limit','50'],['Daily email limit','500'],['Follow-up days','3'],['Automation timezone','Asia/Kolkata']])await page.getByLabel(label,{exact:true}).fill(value);
 await page.getByRole('button',{name:'Save Limits',exact:true}).click();await expect(page.getByRole('status')).toContainText('Outreach limits saved');await page.reload();await expect(page.getByLabel('Hourly email limit',{exact:true})).toHaveValue('50');await expect(page.getByLabel('Daily email limit',{exact:true})).toHaveValue('500');
 const targets=await(await context.request.get('/api/automation/targets')).json();expect(targets.max_hour).toBe(50);expect(targets.max_day).toBe(500);
 const safety=await(await context.request.get('/api/workflow/safety')).json();expect(safety.sending_enabled).not.toBe(true);
});
