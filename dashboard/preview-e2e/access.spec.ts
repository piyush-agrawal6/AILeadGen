import {test,expect} from '@playwright/test';
import {encode} from 'next-auth/jwt';
test('literal secrets survive local startup and approved new accounts inherit no workspace',async({page,context})=>{
 const email='newuser@heysow.example';
 const token=await encode({token:{email,sub:email},secret:'fixture-session-$literal-sign-only-12345678901234567890',salt:'authjs.session-token',maxAge:3600});
 await context.addCookies([{name:'authjs.session-token',value:token,url:'http://127.0.0.1:13000',httpOnly:true,sameSite:'Lax'}]);
 await page.addInitScript(()=>localStorage.setItem('heysow-theme','dark'));
 const hydrationErrors:string[]=[];page.on('console',message=>{if(message.type()==='error'&&/hydrat/i.test(message.text()))hydrationErrors.push(message.text())});
 const reads:string[]=[];page.on('request',request=>{if(request.url().includes('/api/'))reads.push(new URL(request.url()).pathname)});
 const response=await context.request.get('/api/organization/workspaces');expect(response.status()).toBe(200);
 expect(await response.json()).toMatchObject({items:[],active_organization_id:null,active_onboarding_status:null});
 await page.goto('/');await expect(page.getByRole('heading',{name:'Welcome to PlaneByte',exact:true})).toBeVisible();
 await expect(page.getByRole('link',{name:'Create your workspace',exact:true})).toBeVisible();
 expect(reads.some(path=>path.startsWith('/api/sales')||path.startsWith('/api/dashboard'))).toBe(false);
 expect(hydrationErrors).toEqual([]);
 expect((await context.request.get('/api/leads')).status()).toBe(403);
 // Startup and a second page load must reuse valid signatures, never fail open.
 await page.reload();await expect(page.getByRole('heading',{name:'Welcome to PlaneByte',exact:true})).toBeVisible();
 await page.getByRole('link',{name:'Create your workspace',exact:true}).click();
 await page.getByLabel('Company name',{exact:true}).fill('Isolated Preview Company');
 await page.getByRole('button',{name:'Create workspace',exact:true}).click();
 await expect(page).toHaveURL(/\/onboarding$/);
 const owned=await(await context.request.get('/api/organization/workspaces')).json();
 expect(owned.items).toHaveLength(1);expect(owned.items[0]).toMatchObject({name:'Isolated Preview Company',role:'OWNER'});
 await page.goto('/');await expect(page.getByRole('link',{name:'Resume company setup',exact:true})).toBeVisible();
 expect((await context.request.get('/api/leads')).status()).toBe(403);
});
