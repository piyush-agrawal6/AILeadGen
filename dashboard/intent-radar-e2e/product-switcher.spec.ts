import {test,expect,type Page} from '@playwright/test';
import {encode} from 'next-auth/jwt';

test.beforeEach(async({context})=>{
 const email='founder@leadengine.example';
 await context.addCookies([{name:'authjs.session-token',value:await encode({token:{sub:email,email},secret:'fixture-session-secret-only-for-local-tests-123456789',salt:'authjs.session-token',maxAge:3600}),url:'http://127.0.0.1:13000',httpOnly:true,sameSite:'Lax'}]);
 const workspaces=await(await context.request.get('/api/organization/workspaces')).json();
 const workspace=workspaces.items.find((item:{name:string})=>item.name==='PlaneByte');
 expect((await context.request.put('/api/organization/active',{headers:{origin:'http://127.0.0.1:13000'},data:{organization_id:workspace.organization_id}})).status()).toBe(200);
});

async function checkPlacement(page:Page){
 const menu=page.getByRole('menu',{name:'Switch PlaneByte product'});
 await expect(menu).toBeVisible();
 await expect(menu.getByRole('menuitem')).toHaveCount(2);
 await expect(menu.getByText('Prospecting and sales intelligence',{exact:true})).toBeVisible();
 await expect(menu.getByText('Buyer-intent intelligence',{exact:true})).toBeVisible();
 await expect(menu.getByText('Beta',{exact:true})).toBeVisible();
 await expect.poll(()=>menu.evaluate(element=>{
  const rect=element.getBoundingClientRect();
  const trigger=document.querySelector('.product-switcher-trigger[data-state="open"]')!.getBoundingClientRect();
  const expectedLeft=Math.max(12,Math.min(trigger.left,innerWidth-12-rect.width));
  return rect.top>=trigger.bottom && Math.abs(rect.left-expectedLeft)<=1 && rect.right<=innerWidth-11 && rect.bottom<=innerHeight-11;
 })).toBe(true);
 expect(await menu.evaluate(element=>{
  const style=getComputedStyle(element);
  const rect=element.getBoundingClientRect();
  return style.backgroundColor!=='rgba(0, 0, 0, 0)' && Number(style.zIndex)>81 && !element.closest('.shell-sidebar') && element.scrollWidth<=element.clientWidth && document.elementsFromPoint(rect.left+10,rect.top+10).some(node=>node===element||element.contains(node));
 })).toBe(true);
 for(const item of await menu.getByRole('menuitem').all()){
  expect(await item.evaluate(element=>{
   const icon=element.querySelector('.product-menu-icon')!.getBoundingClientRect();
   const copy=element.querySelector('.product-menu-copy')!.getBoundingClientRect();
   const indicator=element.querySelector('.product-menu-indicator')!.getBoundingClientRect();
   return icon.right<copy.left && copy.right<indicator.left && copy.height<=element.getBoundingClientRect().height;
  })).toBe(true);
 }
}

test('product dropdown floats without shifting navigation and supports keyboard, dismissal and workspace-preserving switches',async({page,context},testInfo)=>{
 await page.goto('/');
 const trigger=page.locator('.product-switcher-trigger:visible');
 const navigation=page.getByRole('navigation',{name:'Main navigation',includeHidden:true});
 const before=await navigation.boundingBox();
 await trigger.focus();await page.keyboard.press('Enter');
 await checkPlacement(page);
 await expect(trigger).toHaveAttribute('aria-expanded','true');
 const lead=page.getByRole('menuitem',{name:/Lead Engine/}),radar=page.getByRole('menuitem',{name:/Intent Radar/});
 await expect(lead).toBeFocused();await expect(lead).toHaveAttribute('aria-current','page');
 await page.keyboard.press('ArrowDown');await expect(radar).toBeFocused();
 await page.keyboard.press('Home');await expect(lead).toBeFocused();
 await page.keyboard.press('End');await expect(radar).toBeFocused();
 expect(await navigation.boundingBox()).toEqual(before);
 await page.screenshot({path:testInfo.outputPath('expanded-open.png')});
 await page.keyboard.press('Escape');await expect(page.getByRole('menu')).toHaveCount(0);await expect(trigger).toBeFocused();
 await expect(trigger).toHaveAttribute('aria-expanded','false');expect(await navigation.boundingBox()).toEqual(before);
 await trigger.click();await page.mouse.click(600,350);await expect(page.getByRole('menu')).toHaveCount(0);
 const original=(await(await context.request.get('/api/organization/workspaces')).json()).active_organization_id;
 await trigger.click();await radar.click();await expect(page).toHaveURL(/\/intent-radar$/);
 await expect(page.getByRole('heading',{name:'Intent Radar',exact:true})).toBeVisible();
 await page.screenshot({path:testInfo.outputPath('intent-radar-dashboard.png')});
 await expect(navigation.getByRole('link',{name:'Discover Intent',exact:true})).toBeVisible();
 await expect(navigation.getByRole('link',{name:'Find Leads',exact:true})).toHaveCount(0);
 await trigger.click();await expect(radar).toHaveAttribute('aria-current','page');await page.screenshot({path:testInfo.outputPath('intent-radar-selected.png')});await lead.click();await expect(page).toHaveURL('/');
 await expect(navigation.getByRole('link',{name:'Find Leads',exact:true})).toBeVisible();
 expect((await(await context.request.get('/api/organization/workspaces')).json()).active_organization_id).toBe(original);
 await page.getByRole('button',{name:'Collapse sidebar'}).click();
 await trigger.click();await checkPlacement(page);await page.screenshot({path:testInfo.outputPath('collapsed-open.png')});
 await page.keyboard.press('Escape');await expect(trigger).toBeFocused();
 await page.keyboard.press('ArrowDown');await page.keyboard.press('i');await expect(radar).toBeFocused();await page.keyboard.press('Enter');await expect(page).toHaveURL(/\/intent-radar$/);
 await trigger.click();await lead.click();await expect(page).toHaveURL('/');
 expect((await(await context.request.get('/api/organization/workspaces')).json()).active_organization_id).toBe(original);
 await page.setViewportSize({width:1440,height:450});
 await page.locator('#desktop-navigation .shell-sidebar').evaluate(element=>{element.scrollTop=40});
 await trigger.click();await checkPlacement(page);await page.keyboard.press('Escape');
});

test('product dropdown fits mobile drawers and closes the drawer when switching',async({page},testInfo)=>{
 for(const width of [390,320]){
  await page.setViewportSize({width,height:700});await page.goto('/');
  await page.getByRole('button',{name:'Open navigation'}).click();
  const trigger=page.locator('.product-switcher-trigger:visible');
  await trigger.click();await checkPlacement(page);
  await page.screenshot({path:testInfo.outputPath(`mobile-${width}-open.png`)});
  await page.keyboard.press('Escape');await expect(trigger).toBeFocused();await expect(page.getByRole('dialog',{name:'Navigation'})).toBeVisible();
  await trigger.click();await page.mouse.click(100,350);await expect(page.getByRole('menu')).toHaveCount(0);
  await trigger.click();await page.getByRole('menuitem',{name:/Intent Radar/}).click();await expect(page).toHaveURL(/\/intent-radar$/);
  await expect(page.getByRole('dialog',{name:'Navigation'})).toHaveCount(0);
  await page.getByRole('button',{name:'Open navigation'}).click();await trigger.click();await page.getByRole('menuitem',{name:/Lead Engine/}).click();await expect(page).toHaveURL('/');
  await expect(page.getByRole('dialog',{name:'Navigation'})).toHaveCount(0);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 }
});

test('product dropdown remains readable and viewport-contained at 80, 125 and 200 percent browser zoom emulation',async({page},testInfo)=>{
 await page.goto('/');
 const cdp=await page.context().newCDPSession(page);
 for(const zoom of [0.8,1.25,2]){
  // Browser zoom changes the CSS viewport and device pixel ratio together.
  await cdp.send('Emulation.setDeviceMetricsOverride',{width:Math.round(1440/zoom),height:Math.round(900/zoom),deviceScaleFactor:zoom,mobile:false});
  if(await page.getByRole('button',{name:'Open navigation'}).isVisible())await page.getByRole('button',{name:'Open navigation'}).click();
  await page.getByRole('button',{name:'Switch PlaneByte product'}).click();await checkPlacement(page);
  await page.screenshot({path:testInfo.outputPath(`zoom-${zoom*100}-open.png`)});
  await page.keyboard.press('Escape');await expect(page.getByRole('menu')).toHaveCount(0);
  if(await page.getByRole('dialog',{name:'Navigation'}).isVisible())await page.keyboard.press('Escape');
 }
});
