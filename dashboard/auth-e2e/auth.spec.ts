import {test,expect} from '@playwright/test';
import path from 'node:path';
const output=path.resolve(import.meta.dirname,'../../data/artifacts/verification/planebyte-auth');
test('PlaneByte sign-in is responsive, readable and independent of private workspace data',async({page})=>{
 const privateRequests:string[]=[];const errors:string[]=[];
 page.on('request',r=>{if(r.url().includes('/api/')&&!r.url().includes('/api/auth/'))privateRequests.push(r.url())});
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
 await page.goto('/login');await expect(page).toHaveTitle('Sign in · PlaneByte');
 await expect(page.getByRole('heading',{name:'Welcome back'})).toBeVisible();
 await expect(page.getByRole('button',{name:'Continue with Google'})).toBeVisible();
 await expect(page.getByText(/HeySow/)).toHaveCount(0);
 for(const [width,height,name] of [[1440,960,'desktop'],[1024,768,'tablet-landscape'],[768,1024,'tablet'],[390,844,'mobile'],[320,568,'small-mobile']] as const){
  await page.setViewportSize({width,height});await page.evaluate(()=>document.fonts.ready);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  const images=page.locator('img');for(let i=0;i<await images.count();i++)expect(await images.nth(i).evaluate((el:HTMLImageElement)=>el.complete&&el.naturalWidth>0)).toBe(true);
  await expect(page.getByRole('link',{name:'Request access'})).toBeVisible();
  const form=await page.locator('.auth-form-content').boundingBox();expect(form!.width).toBeLessThanOrEqual(440);
  if(width===1440){expect(form!.width).toBeGreaterThanOrEqual(400);const story=await page.locator('.auth-story').boundingBox();expect(story!.width/width).toBeCloseTo(.45,2)}
  if(width<768)await expect(page.locator('.auth-story')).toBeHidden();
  await page.screenshot({path:path.join(output,name+'.png'),fullPage:true});
 }
 await page.emulateMedia({reducedMotion:'reduce'});expect(await page.locator('.auth-form-content').evaluate(el=>getComputedStyle(el).animationName)).toBe('none');
 expect(privateRequests).toEqual([]);expect(errors).toEqual([]);
});
test('safe errors, honest request access, legal pages and Google recovery work',async({page})=>{
  const signInError=page.locator('.auth-error[role="alert"]');
  await page.goto('/login?error=AccessDenied');await expect(signInError).toContainText('workspace');
 await page.screenshot({path:path.join(output,'access-error.png'),fullPage:true});
  await page.goto('/login?error=%3Cscript%3Eprivate-token%3C/script%3E');await expect(signInError).toBeVisible();await expect(signInError).toContainText('We couldn’t complete sign-in');await expect(signInError).not.toContainText('private-token');
 await page.goto('/login');await page.getByRole('link',{name:'Request access'}).click();
 await expect(page.getByRole('heading',{name:'Join PlaneByte'})).toBeVisible();await expect(page.getByText(/Public self-service registration is not available yet/)).toBeVisible();
 await expect(page.getByRole('link',{name:/Request workspace access/})).toHaveAttribute('href',/^mailto:contact@planebyte\.com\?/);
 await page.screenshot({path:path.join(output,'request-access.png'),fullPage:true});
 for(const route of ['/signup','/forgot-password','/reset-password','/verify-email','/accept-invitation?token=untrusted','/terms','/privacy']){
  await page.goto(route);await expect(page.getByRole('main')).toBeVisible();await expect(page.getByRole('link',{name:'Back to sign in'})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 }
 await page.goto('/forgot-password');await expect(page.getByRole('heading',{name:'Need help signing in?'})).toBeVisible();
 await expect(page.getByRole('link',{name:/Recover your Google account/})).toHaveAttribute('href','https://accounts.google.com/signin/recovery');
 await page.screenshot({path:path.join(output,'recovery.png'),fullPage:true});
 await page.getByRole('link',{name:'Back to sign in'}).click();await expect(page).toHaveURL(/\/login$/);
 await page.getByRole('link',{name:'Terms of Service',exact:true}).first().click();await expect(page).toHaveURL(/\/terms$/);
 await page.getByRole('link',{name:'Privacy Policy',exact:true}).first().click();await expect(page).toHaveURL(/\/privacy$/);
 await page.goto('/leads');await expect(page).toHaveURL(/\/login$/);expect((await page.request.get('/api/leads')).status()).toBe(401);
 expect((await page.request.get('/brand/mark.svg')).headers()['content-type']).toContain('image/svg+xml');
 expect((await page.request.get('/brand/mark.svg/private',{maxRedirects:0})).status()).toBe(307);
});
test('keyboard access and actual Auth.js Google action preserve the protected OAuth handoff',async({page})=>{
 await page.route('https://accounts.google.com/**',route=>route.fulfill({status:200,contentType:'text/plain',body:'Local test intercepted the OAuth destination; no Google login performed.'}));
 await page.goto('/login');await page.keyboard.press('Tab');await expect(page.getByRole('link',{name:'Skip to sign in'})).toBeFocused();
 await page.keyboard.press('Enter');await expect(page.locator('#authentication')).toBeFocused();await page.keyboard.press('Tab');
 await expect(page.getByRole('button',{name:'Continue with Google'})).toBeFocused();await page.keyboard.press('Enter');await page.waitForURL('https://accounts.google.com/**');
 const url=new URL(page.url());expect(url.searchParams.get('client_id')).toBe('heysow-local-fixture');expect(url.searchParams.get('response_type')).toBe('code');expect(url.searchParams.get('code_challenge')).toBeTruthy();
 expect(url.searchParams.get('redirect_uri')).toBe('http://127.0.0.1:13001/api/auth/callback/google');
});
