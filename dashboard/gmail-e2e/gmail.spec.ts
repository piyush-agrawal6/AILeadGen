import {test,expect,BrowserContext} from '@playwright/test';
import {encode} from 'next-auth/jwt';
async function identity(context:BrowserContext,email:string){
 const token=await encode({token:{email,sub:email},secret:'fixture-session-secret-only-for-local-tests-123456789',salt:'authjs.session-token',maxAge:3600});
 await context.addCookies([{name:'authjs.session-token',value:token,url:'http://127.0.0.1:13000',httpOnly:true,sameSite:'Lax'}]);
}
test('owned Gmail lifecycle, secure callback, approval and cross-customer denial',async({page,context,browser})=>{
 await identity(context,'founder@leadengine.example');
 await page.route('https://accounts.google.com/o/oauth2/v2/auth?**',route=>route.fulfill({contentType:'text/html',body:'<h1>Synthetic Gmail consent destination</h1>'}));
 await page.goto('/settings/integrations');
 await expect(page.getByRole('heading',{name:'Workspace Gmail',exact:true})).toBeVisible();
 const outbound=page.waitForRequest(request=>request.url().startsWith('https://accounts.google.com/o/oauth2/v2/auth?'));
 await page.getByRole('button',{name:'Connect your Gmail',exact:true}).click();
 const url=new URL((await outbound).url()),state=url.searchParams.get('state');
 expect(url.searchParams.get('scope')).toContain('gmail.send');expect(url.searchParams.get('scope')).toContain('gmail.readonly');
 expect(url.searchParams.get('code_challenge_method')).toBe('S256');expect(url.searchParams.has('client_secret')).toBe(false);
 await page.goto('/settings/integrations/gmail-callback?state='+state+'&code=synthetic-gmail-code');
 await expect(page.getByRole('status').filter({hasText:'Your workspace Gmail is connected'})).toBeVisible();
 expect(new URL(page.url()).search).toBe('');
 const stored=await(await context.request.get('/api/email/gmail')).json(),connection=stored.items[0];
 expect(connection.email_address).toBe('founder@leadengine.example');
 expect(JSON.stringify(stored)).not.toMatch(/synthetic-browser|ciphertext|google_subject/);
 await page.goto('/settings/integrations');
 await page.getByRole('button',{name:'Check Gmail health'}).click();
 await expect(page.getByRole('status').filter({hasText:'Mailbox connection verified'})).toBeVisible();
 await page.getByRole('button',{name:'Approve reviewed workspace sending'}).click();
 await expect(page.getByRole('status').filter({hasText:'Workspace sending approval saved'})).toBeVisible();
  expect((await(await context.request.get('/api/email/account')).json()).can_send).toBe(true); // synthetic Gmail transport only
 const other=await browser.newContext();await identity(other,'cofounder@leadengine.example');
 expect((await other.request.get('/api/email/gmail')).status()).toBe(200);
 expect((await(await other.request.get('/api/email/gmail')).json()).items).toEqual([]);
 expect((await other.request.post('/api/email/gmail/'+connection.id+'/health',{headers:{origin:'http://127.0.0.1:13000'}})).status()).toBe(404);
 expect((await other.request.delete('/api/email/gmail/'+connection.id,{headers:{origin:'http://127.0.0.1:13000'}})).status()).toBe(404);
 await other.close();
 await page.getByRole('button',{name:'Disconnect Gmail'}).click();
 await expect(page.getByRole('status')).toContainText('Historical conversations were retained');
 const disconnected=await(await context.request.get('/api/email/gmail')).json();expect(disconnected.items[0].status).toBe('DISCONNECTED');
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test('campaign routing, inert preparation, manual approval, owned reply sync and reviewed history recovery',async({page,context,browser})=>{
 await identity(context,'founder@leadengine.example');const headers={origin:'http://127.0.0.1:13000'};
 const authorization=await(await context.request.post('/api/email/gmail/authorize',{headers})).json();const state=new URL(authorization.authorization_url).searchParams.get('state');
 const response=await context.request.post('/api/email/gmail/connect',{headers,data:{state,code:'synthetic-gmail-code'}});expect(response.status()).toBe(200);const account=(await(await context.request.get('/api/email/account')).json());expect(account.can_send).toBe(false);
 const campaigns=(await(await context.request.get('/api/operations/campaigns')).json()).items;const campaign=campaigns[0];expect(campaign).toBeTruthy();
 await page.goto('/outreach/new?campaign='+campaign.id);await page.getByRole('button',{name:'Route selected campaign to this mailbox'}).click();await expect(page.getByRole('button',{name:'Mailbox route saved'})).toBeVisible();
 const templates=(await(await context.request.get('/api/email/templates')).json());const template=Array.isArray(templates)?templates[0]:templates.items[0];
 const options={kind:'OUTREACH',campaign_id:campaign.id,account_id:account.id,template_id:template.id,window_start:'00:00',window_end:'23:59',recipient_timezone:false};
 const draft=await context.request.post('/api/workflow/runs',{headers,data:options});expect(draft.status()).toBe(201);const initial=(await draft.json()).id;
 expect((await context.request.post('/api/workflow/runs/'+initial+'/prepare',{headers})).status()).toBe(200);expect((await context.request.post('/api/workflow/runs/'+initial+'/start',{headers})).status()).toBeGreaterThanOrEqual(400);
 expect((await(await context.request.get('/api/email/gmail/policy')).json()).sending_approved).toBe(0);
 expect((await context.request.post('/api/workflow/runs/'+initial+'/stop',{headers})).status()).toBe(200);
 await page.goto('/settings/integrations');await page.getByRole('button',{name:'Approve reviewed workspace sending'}).click();await expect(page.getByText(/Workspace sending approval saved/)).toBeVisible();
 const approved=await context.request.post('/api/workflow/runs',{headers,data:options});expect(approved.status()).toBe(201);const run=(await approved.json()).id;
 expect((await context.request.post('/api/workflow/runs/'+run+'/prepare',{headers})).status()).toBe(200);
 const start=await context.request.post('/api/workflow/runs/'+run+'/start',{headers});expect(start.status(),await start.text()).toBe(200);
 await expect.poll(async()=> (await(await context.request.get('/api/workflow/runs/'+run)).json()).status,{timeout:20000}).toBe('COMPLETED');
 await page.getByRole('button',{name:'Sync owned replies'}).click();await expect(page.getByText('Bounded inbox synchronization completed.')).toBeVisible();
 await page.getByRole('button',{name:'Sync owned replies'}).click();await expect(page.getByText(/Gmail history expired\. An explicit restart/)).toBeVisible();
 await page.getByRole('button',{name:'Review recent sync restart'}).click();await page.getByRole('button',{name:'Confirm restart recent sync'}).click();await expect(page.getByText('Bounded inbox synchronization completed.')).toBeVisible();
 const leads=await(await context.request.get('/api/leads')).json();const lead=leads.items[0];await page.goto('/leads/'+lead.id);await page.getByRole('button',{name:/A conversation with Hotel 0/}).click();await expect(page.getByText('Synthetic customer reply: please share the reviewed options.')).toBeVisible();await page.getByRole('button',{name:'Reply / Follow up'}).click();await page.getByLabel('Subject',{exact:true}).fill('Reviewed customer response');await page.getByLabel('Body',{exact:true}).fill('We will share the options for your review.');await page.getByRole('button',{name:/Preview/}).click();await expect(page.getByRole('button',{name:'Confirm Send'})).toBeVisible();
 const other=await browser.newContext();await identity(other,'cofounder@leadengine.example');expect((await other.request.get('/api/leads/'+lead.id)).status()).toBe(404);expect((await other.request.put('/api/email/campaigns/'+campaign.id+'/mailbox',{headers,data:{account_id:account.id}})).status()).toBe(404);await other.close();
 await page.getByRole('button',{name:'Close composer'}).click();await page.goto('/settings/integrations');await page.getByRole('button',{name:'Remove sending approval'}).click();await expect(page.getByText('Workspace sending approval removed.')).toBeVisible();expect((await(await context.request.get('/api/email/account')).json()).can_send).toBe(false);
});
