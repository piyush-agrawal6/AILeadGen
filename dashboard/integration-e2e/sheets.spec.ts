import {test,expect} from '@playwright/test';
import {encode} from 'next-auth/jwt';
test('new customer sees no internal connections and starts a scoped read-only OAuth handoff',async({page,context})=>{
 const email='founder@leadengine.example';
 const token=await encode({token:{email,sub:email},secret:'fixture-session-secret-only-for-local-tests-123456789',salt:'authjs.session-token',maxAge:3600});
 await context.addCookies([{name:'authjs.session-token',value:token,url:'http://127.0.0.1:13000',httpOnly:true,sameSite:'Lax'}]);
 const created=await context.request.post('/api/organization/workspaces',{headers:{origin:'http://127.0.0.1:13000'},data:{name:'Controlled customer connection',request_id:crypto.randomUUID()}});expect(created.status()).toBe(201);
 const connections=await context.request.get('/api/organization/integrations');expect(connections.status()).toBe(200);expect((await connections.json()).items).toEqual([]);
 expect((await context.request.get('/api/acquisition/sheets/metadata?spreadsheet=controlled-spreadsheet')).status()).toBe(403);
 await page.route('https://accounts.google.com/o/oauth2/v2/auth?**',route=>route.fulfill({contentType:'text/html',body:'<h1>Controlled OAuth handoff</h1>'}));
 await page.goto('/settings/integrations');await expect(page.getByRole('heading',{name:'Workspace integrations',exact:true})).toBeVisible();
 await expect(page.getByText('Status: not connected',{exact:true})).toBeVisible();
 const outbound=page.waitForRequest(request=>request.url().startsWith('https://accounts.google.com/o/oauth2/v2/auth?'));
 await page.getByRole('button',{name:'Connect Google Sheets (read only)',exact:true}).click();
 const url=new URL((await outbound).url());
 expect(url.searchParams.get('scope')).toBe('https://www.googleapis.com/auth/spreadsheets.readonly');
 expect(url.searchParams.get('state')).toMatch(/^hsw_[A-Za-z0-9_-]{43}$/);
 expect(url.searchParams.get('code_challenge_method')).toBe('S256');
 expect(url.searchParams.has('client_secret')).toBe(false);expect(url.searchParams.has('code_verifier')).toBe(false);
 await expect(page.getByRole('heading',{name:'Controlled OAuth handoff'})).toBeVisible();
 const stored=await(await context.request.get('/api/organization/integrations')).json();
 expect(stored.items).toHaveLength(1);expect(stored.items[0].status).toBe('NOT_CONNECTED');
 expect(JSON.stringify(stored)).not.toContain(url.searchParams.get('state'));
 // The browser destination is intercepted. No provider consent or exchange occurs.
});
