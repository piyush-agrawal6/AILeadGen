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
 await expect(page.getByRole('status')).toContainText('Your workspace Gmail is connected');
 expect(new URL(page.url()).search).toBe('');
 const stored=await(await context.request.get('/api/email/gmail')).json(),connection=stored.items[0];
 expect(connection.email_address).toBe('founder@leadengine.example');
 expect(JSON.stringify(stored)).not.toMatch(/synthetic-browser|ciphertext|google_subject/);
 await page.goto('/settings/integrations');
 await page.getByRole('button',{name:'Check Gmail health'}).click();
 await expect(page.getByRole('status')).toContainText('Mailbox connection verified');
 await page.getByRole('button',{name:'Approve reviewed workspace sending'}).click();
 await expect(page.getByRole('status')).toContainText('Workspace sending approval saved');
 expect((await(await context.request.get('/api/email/account')).json()).can_send).toBe(false);
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
