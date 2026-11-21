import {test,expect,type BrowserContext} from '@playwright/test';
import {encode} from 'next-auth/jwt';
async function session(context:BrowserContext){const email='ui@leadengine.example',secret='fixture-session-secret-only-for-local-tests-123456789';const token=await encode({token:{email,sub:email},secret,salt:'authjs.session-token',maxAge:3600});await context.addCookies([{name:'authjs.session-token',value:token,url:'http://127.0.0.1:13000',httpOnly:true,sameSite:'Lax'}])}
test('shared shell persists collapse, supports mobile keyboard navigation and uses one appearance menu',async({page,context})=>{
 await session(context);const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/settings');await expect(page.getByRole('heading',{name:'Settings',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Collapse sidebar',exact:true}).click();await expect(page.locator('.app-shell')).toHaveClass(/sidebar-collapsed/);
 await page.reload();await expect(page.locator('.app-shell')).toHaveClass(/sidebar-collapsed/);
 expect((await context.cookies()).find(cookie=>cookie.name==='planebyte-sidebar')?.value).toBe('collapsed');
 await page.getByRole('button',{name:'Expand sidebar',exact:true}).click();
 await page.screenshot({path:test.info().outputPath('settings-desktop.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});const open=page.getByRole('button',{name:'Open navigation',exact:true});await open.click();
 const drawer=page.getByRole('dialog',{name:'Navigation',exact:true});await expect(drawer).toBeVisible();await page.keyboard.press('Tab');expect(await page.evaluate(()=>!!document.activeElement?.closest('[role="dialog"]'))).toBe(true);
 await page.keyboard.press('Escape');await expect(drawer).toBeHidden();await expect(open).toBeFocused();
 await open.click();await drawer.getByRole('link',{name:'Help & support',exact:true}).click();await expect(page).toHaveURL(/\/help$/);await expect(drawer).toBeHidden();
 await page.setViewportSize({width:1024,height:844});await page.getByRole('button',{name:'Account menu',exact:true}).click();await page.getByRole('menuitem',{name:'Appearance',exact:true}).focus();await page.keyboard.press('ArrowRight');
 await page.getByRole('menuitemradio',{name:'Dark',exact:true}).click();await expect(page.locator('html')).toHaveClass(/dark/);
 await page.reload();await expect(page.locator('html')).toHaveClass(/dark/);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:test.info().outputPath('shell-mobile-dark.png'),fullPage:true});
 await page.getByRole('button',{name:'Account menu',exact:true}).click();await page.getByRole('menuitem',{name:'Appearance',exact:true}).focus();await page.keyboard.press('ArrowRight');await page.getByRole('menuitemradio',{name:'Light',exact:true}).click();
 await expect(page.locator('html')).toHaveClass(/light/);expect(errors).toEqual([]);
});
test('short company names remain real and incomplete setup permits settings while product work stays blocked',async({page,context})=>{
 await session(context);const headers={origin:'http://127.0.0.1:13000'};
 const created=await context.request.post('/api/organization/workspaces',{headers,data:{name:'b.',request_id:crypto.randomUUID()}});expect(created.status()).toBe(201);
 await page.goto('/settings');await expect(page.getByRole('button',{name:'Workspace: b.',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Workspace: b.',exact:true}).click();await expect(page.getByRole('menuitemradio',{name:'b.',exact:true})).toHaveAttribute('aria-checked','true');await page.keyboard.press('Escape');
 expect((await context.request.get('/api/organization/profile')).status()).toBe(200);expect((await context.request.get('/api/operations/dashboard')).status()).toBe(403);
 await page.goto('/onboarding');await expect(page.getByRole('heading',{name:'Set up your workspace'})).toBeVisible();await page.getByRole('button',{name:'Save and continue'}).click();await expect(page.getByRole('alert').filter({hasText:'Choose at least one business objective.'})).toBeVisible();await page.getByLabel('Find potential customers',{exact:true}).check();await page.getByRole('button',{name:'Save and continue'}).click();await page.getByRole('button',{name:'Edit Profile',exact:true}).first().click();await page.getByLabel('Company description',{exact:true}).fill('Controlled manual onboarding draft.');await page.getByRole('button',{name:'Save and continue'}).click();await expect(page.getByRole('alert').filter({hasText:'Save your company profile'})).toBeVisible();await page.getByRole('button',{name:'Save Changes',exact:true}).first().click();await expect(page.getByText('Organization profile saved.')).toBeVisible();await page.getByRole('button',{name:'Save and exit'}).click();await expect(page).toHaveURL(/\/settings$/);await page.goto('/onboarding');await expect(page.getByText('Controlled manual onboarding draft.',{exact:true})).toBeVisible();
});
