import {test,expect,type Page,type APIRequestContext} from '@playwright/test';
import {createHash,createHmac,randomUUID} from 'node:crypto';
const email='browser.account@example.com',password='An isolated browser passphrase 837!';
async function mailbox(request:APIRequestContext){
 const path='/api/organization/_test/mailbox?email='+encodeURIComponent(email),stamp=String(Math.floor(Date.now()/1000)),nonce=randomUUID(),actor='founder@leadengine.example';
 const secret='fixture-signing-secret-only-for-local-tests-123456789';
 const signature=createHmac('sha256',secret).update([stamp,nonce,'GET',path,createHash('sha256').update('').digest('hex'),actor].join('\n')).digest('hex');
 const response=await request.get('http://127.0.0.1:18787'+path,{headers:{'x-le-user':actor,'x-le-timestamp':stamp,'x-le-nonce':nonce,'x-le-signature':signature}});
 expect(response.ok()).toBe(true);return (await response.json()).messages as {text:string}[];
}
async function layouts(page:Page,output:(name:string)=>string){for(const theme of ['light','dark'])for(const width of [1440,768,390,320]){await page.setViewportSize({width,height:900});await page.evaluate(t=>document.documentElement.classList.toggle('dark',t==='dark'),theme);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:output(`${theme}-${width}.png`),fullPage:true});}}
test('email registration verifies mailbox before workspace creation and supports recovery',async({page,context,request},info)=>{
 test.setTimeout(240000);
 await page.goto('/signup');
 const form=page.getByRole('button',{name:'Create account with email'}).locator('..');
 await form.getByLabel('Your name').fill('Browser test owner');await form.getByLabel('Company name').fill('Browser test company');await form.getByLabel('Company email').fill(email);await form.getByLabel('Password',{exact:true}).fill(password);await form.getByLabel('Confirm password',{exact:true}).fill(password);await form.getByRole('checkbox').check();
 await layouts(page,name=>info.outputPath('signup-'+name));await form.getByRole('button',{name:'Create account with email'}).click();
 await expect(page).toHaveURL(/\/verify-email$/);
 await expect.poll(async()=> (await mailbox(request)).length).toBeGreaterThan(0);
 const sentCode=(await mailbox(request)).at(-1)!.text.match(/code is (\d{6})/)![1];
 await page.getByLabel('Verification code').fill(sentCode==='999999'?'000000':'999999');await page.getByRole('button',{name:'Verify email and continue'}).click();await expect(page.getByRole('alert').filter({hasText:'The code is incorrect'})).toBeVisible();
 await expect.poll(async()=> (await mailbox(request)).length).toBeGreaterThan(0);
 const code=(await mailbox(request)).at(-1)!.text.match(/code is (\d{6})/)![1];
 await page.getByLabel('Verification code').fill(code);await layouts(page,name=>info.outputPath('verify-'+name));await page.getByRole('button',{name:'Verify email and continue'}).click();
 await expect(page).toHaveURL(/\/onboarding$/, {timeout:45000});
 const publicSession=await(await context.request.get('/api/auth/session')).json();expect(publicSession.user.email).toBe(email);expect(JSON.stringify(publicSession)).not.toContain('session_token');expect(JSON.stringify(publicSession)).not.toContain('planeByteSession');
 const usage=await(await context.request.get('/api/organization/usage')).json();expect(usage.access.kind).toBe('Seven-day trial');expect(usage.usage.find((r:{dimension:string})=>r.dimension==='plan_searches').limit).toBe(5);
 await page.goto('/settings?category=billing');await expect(page.getByRole('heading',{name:'One-time access & payments'})).toBeVisible();await expect(page.getByText('Total: $59.00 USD')).toBeVisible();await expect(page.getByRole('button',{name:'Continue to PayU'})).toHaveCount(0);await layouts(page,name=>info.outputPath('billing-'+name));await page.getByLabel('Access term').selectOption('yearly');await expect(page.getByText('Yearly price not yet available')).toBeVisible();await expect(page.getByRole('button',{name:'Continue to PayU'})).toHaveCount(0);
 await page.goto('/settings?category=account&tab=security');await expect(page.getByRole('heading',{name:'Your data & account'})).toBeVisible();await page.getByLabel('Data request').selectOption('EXPORT');await page.getByRole('checkbox').check();await page.getByRole('button',{name:'Submit data request'}).click();await expect(page.getByRole('status').filter({hasText:'Request recorded:'})).toBeVisible();await layouts(page,name=>info.outputPath('privacy-'+name));
 await page.goto('/forgot-password');const recovery=page.getByRole('button',{name:'Send recovery link'}).locator('..');await recovery.getByLabel('Email',{exact:true}).fill(email);await recovery.getByRole('button').click();await expect(page.getByRole('status')).toContainText('reset link');
 await expect.poll(async()=> (await mailbox(request)).some(m=>m.text.includes('?token='))).toBe(true);
 const reset=(await mailbox(request)).findLast(m=>m.text.includes('?token='))!.text.match(/\?token=([A-Za-z0-9_-]{43})/)![1];
 await page.goto('/reset-password?token='+reset);await page.getByLabel('New password').fill('A replacement browser passphrase 905!');await page.getByLabel('Confirm password').fill('A replacement browser passphrase 905!');await page.getByRole('button',{name:'Change password'}).click();await expect(page.getByRole('status')).toContainText('Password changed');
 const denied=await context.request.get('/api/organization/usage');expect(denied.status()).toBe(401);
 await page.goto('/login');const login=page.getByRole('button',{name:'Sign in with email'}).locator('..');await login.getByLabel('Email',{exact:true}).fill(email);await login.getByLabel('Password',{exact:true}).fill('A replacement browser passphrase 905!');await login.getByRole('button').click();await expect(page).toHaveURL(/\/onboarding$/,{timeout:45000});
});
