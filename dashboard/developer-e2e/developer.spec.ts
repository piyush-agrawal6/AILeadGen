import {test,expect} from '@playwright/test';
import {encode} from 'next-auth/jwt';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import path from 'node:path';
const exec=promisify(execFile);
test('real key, anonymous API client, official MCP client, reviewed action and revocation work together',async({page,context,playwright})=>{
 const email='founder@leadengine.example',secret='fixture-session-secret-only-for-local-tests-123456789';const session=await encode({token:{sub:email,email},secret,salt:'authjs.session-token',maxAge:3600});await context.addCookies([{name:'authjs.session-token',value:session,url:'http://127.0.0.1:13000',httpOnly:true,sameSite:'Lax'}]);
 await page.goto('/settings/developer');await expect(page.getByRole('heading',{name:'Developer access',exact:true})).toBeVisible();await page.getByLabel('Key name',{exact:true}).fill('Controlled browser integration');await page.getByLabel('mcp:use',{exact:true}).check();await page.getByLabel('lists:write',{exact:true}).check();await page.getByLabel('lists:read',{exact:true}).check();await page.getByRole('button',{name:'Create API key',exact:true}).click();const field=page.getByLabel('One-time API key',{exact:true});await expect(field).toBeVisible();const credential=await field.inputValue();expect(credential.startsWith('pbk_')).toBe(true);
 const machine=await playwright.request.newContext({baseURL:'http://127.0.0.1:13000',extraHTTPHeaders:{authorization:'Bearer '+credential}});
 try{
  expect((await machine.get('/api/v1/companies')).status()).toBe(200);expect((await machine.get('/api/organization/developer/keys')).status()).toBe(401);
  const root=path.resolve(import.meta.dirname,'../..'),python=process.env.LEADENGINE_TEST_PYTHON||path.join(root,'.venv/bin/python');
  const {stdout}=await exec(python,[path.join(root,'tests/mcp_client_probe.py')],{cwd:root,env:{...process.env,PLANEBYTE_TEST_API_CREDENTIAL:credential},timeout:45000,maxBuffer:32000});const probe=JSON.parse(stdout);expect(probe.tools).toBeGreaterThanOrEqual(9);expect(probe.status).toBe('PENDING');
  expect((await(await machine.get('/api/v1/lists')).json()).total).toBe(0);
  await page.getByRole('button',{name:'I have saved the key',exact:true}).click();await page.getByRole('button',{name:'Refresh proposals',exact:true}).click();await expect(page.getByText('"Controlled MCP browser list"',{exact:false})).toBeVisible();await page.getByRole('button',{name:'Review action',exact:true}).click();await page.getByRole('button',{name:'Confirm approved action',exact:true}).click();await expect.poll(async()=> (await(await machine.get('/api/v1/lists')).json()).total).toBe(1);
  await page.getByRole('button',{name:'Revoke Controlled browser integration',exact:true}).click();await page.getByRole('button',{name:'Confirm revoke',exact:true}).click();await expect.poll(async()=> (await machine.get('/api/v1/companies')).status()).toBe(401);
  await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:test.info().outputPath('developer-mobile.png'),fullPage:true});
  expect((await(await context.request.get('/api/workflow/safety')).json()).sending_enabled).toBe(false);
 }finally{await machine.dispose()}
});

test('webhook UI creates an encrypted owned subscription and preserves queued history on archive',async({page,context})=>{
 const email='founder@leadengine.example',secret='fixture-session-secret-only-for-local-tests-123456789';const session=await encode({token:{sub:email,email},secret,salt:'authjs.session-token',maxAge:3600});await context.addCookies([{name:'authjs.session-token',value:session,url:'http://127.0.0.1:13000',httpOnly:true,sameSite:'Lax'}]);
 await page.goto('/settings/developer');await page.getByText('Add webhook endpoint',{exact:true}).click();await page.getByLabel('Endpoint name',{exact:true}).fill('Controlled webhook browser receiver');await page.getByLabel('Public HTTPS receiver',{exact:true}).fill('https://receiver.example.com/events');await page.getByRole('button',{name:'Create webhook',exact:true}).click();await expect(page.getByLabel('Webhook signing secret',{exact:true})).toBeVisible();await page.getByRole('button',{name:'I saved the signing secret',exact:true}).click();await expect(page.getByLabel('Webhook signing secret',{exact:true})).toHaveCount(0);
 const listing=await(await context.request.get('/api/organization/webhooks')).json();const endpoint=listing.items.find((item:{name:string})=>item.name==='Controlled webhook browser receiver');expect(endpoint).toBeTruthy();expect(endpoint.signing_secret).toBeUndefined();
 const headers={origin:'http://127.0.0.1:13000'};expect((await context.request.put('/api/automation/controls',{headers,data:{scan_paused:false,email_paused:true}})).status()).toBe(200);
 const created=await context.request.post('/api/campaigns',{headers,data:{cities:['London'],verticals:['dentists'],target:5,fixture:true,request_id:crypto.randomUUID()}});expect(created.status(),await created.text()).toBe(201);
 await expect.poll(async()=>{const result=await(await context.request.get('/api/organization/webhooks/'+endpoint.id+'/deliveries')).json();return result.total},{timeout:30000}).toBeGreaterThan(0);
 await page.getByRole('button',{name:'Delivery history',exact:true}).click();await expect(page.getByRole('heading',{name:'Webhook delivery history',exact:true})).toBeVisible();await expect(page.getByText(/company.created · Queued/).first()).toBeVisible();
 await page.getByRole('button',{name:'Pause',exact:true}).click();await page.getByRole('button',{name:'Confirm webhook change',exact:true}).click();await expect(page.getByRole('button',{name:'Resume',exact:true})).toBeVisible();await page.getByRole('button',{name:'Archive',exact:true}).click();await page.getByRole('button',{name:'Confirm webhook change',exact:true}).click();await expect(page.getByText(/Archived · company.created/)).toBeVisible();
 const history=await(await context.request.get('/api/organization/webhooks/'+endpoint.id+'/deliveries')).json();expect(history.total).toBeGreaterThan(0);expect(history.items.every((item:{attempts:number})=>item.attempts===0)).toBe(true);
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:test.info().outputPath('webhook-mobile.png'),fullPage:true});expect((await(await context.request.get('/api/workflow/safety')).json()).sending_enabled).toBe(false);
});
