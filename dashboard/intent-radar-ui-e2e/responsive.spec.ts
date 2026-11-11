import {test,expect} from '@playwright/test';
import {encode} from 'next-auth/jwt';
test('all product screens remain usable across desktop, tablet, narrow mobile and zoom emulation',async({page,context,baseURL},info)=>{
 const email='founder@leadengine.example';
 await context.addCookies([{name:'authjs.session-token',value:await encode({token:{sub:email,email},secret:'fixture-session-secret-only-for-local-tests-123456789',salt:'authjs.session-token',maxAge:3600}),url:baseURL!,httpOnly:true,sameSite:'Lax'}]);
 const workspaces=await(await context.request.get('/api/organization/workspaces')).json();const org=workspaces.items.find((w:{name:string})=>w.name==='PlaneByte');const headers={origin:baseURL!};
 expect((await context.request.put('/api/organization/active',{headers,data:{organization_id:org.organization_id}})).status()).toBe(200);
 const monitor=await(await context.request.post('/api/intent-radar/monitors',{headers,data:{name:'Responsive synthetic fixture',configuration:{keywords:['website']},status:'Active'}})).json();
 const job=await(await context.request.post('/api/intent-radar/discover',{headers,data:{monitor_id:monitor.id,configuration:monitor.configuration}})).json();
 await expect.poll(async()=> (await(await context.request.get('/api/intent-radar/jobs/'+job.id)).json()).status).toBe('COMPLETED');
 for(const width of [1440,1280,1024,768,390,320]){
  await page.setViewportSize({width,height:900});
  for(const route of ['','discover','monitors','signals','opportunities','saved','alerts','integrations','settings']){
   await page.goto('/intent-radar'+(route?'/'+route:''));await expect(page.locator('.ir-page')).toBeVisible();await page.waitForLoadState('networkidle');
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${route||'overview'} overflows at ${width}px`).toBe(true);
   const clipped=await page.locator('.ir-page button, .ir-page input, .ir-page select').evaluateAll(nodes=>nodes.filter(node=>{const r=node.getBoundingClientRect();return r.width>0&&r.height>0&&(r.left<0||r.right>innerWidth+1)}).map(node=>node.getAttribute('aria-label')||node.textContent));
   expect(clipped,`clipped controls on ${route} at ${width}px`).toEqual([]);
   if([1280,768,320].includes(width))await page.screenshot({path:info.outputPath(`${width}-${route||'overview'}.png`)});
  }
  await page.goto('/intent-radar/monitors/new');const dialog=page.getByRole('dialog',{name:'Create an intent monitor'});await expect(dialog).toBeVisible();const rect=await dialog.boundingBox();expect(rect!.x).toBeGreaterThanOrEqual(11);expect(rect!.x+rect!.width).toBeLessThanOrEqual(width-11);
  await dialog.getByRole('button',{name:'Continue',exact:true}).click();await dialog.getByLabel('Monitor name',{exact:true}).fill('Responsive unsaved fixture');await page.screenshot({path:info.outputPath(`${width}-wizard.png`)});await page.keyboard.press('Escape');await page.getByRole('button',{name:'Discard changes',exact:true}).click();
 }
 const cdp=await context.newCDPSession(page);
 for(const zoom of [1.25,1.5]){
  await cdp.send('Emulation.setDeviceMetricsOverride',{width:Math.round(1440/zoom),height:Math.round(900/zoom),deviceScaleFactor:zoom,mobile:false});await page.goto('/intent-radar');await expect(page.getByRole('heading',{name:'Intent Radar',exact:true})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:info.outputPath(`zoom-${zoom*100}.png`)});
 }
 await cdp.send('Emulation.clearDeviceMetricsOverride');await page.setViewportSize({width:1440,height:900});await page.goto('/intent-radar');await page.getByRole('button',{name:'Collapse sidebar'}).click();await page.getByRole('link',{name:'Discover Intent',exact:true}).first().hover();await expect(page.getByRole('tooltip')).toBeVisible();await page.screenshot({path:info.outputPath('collapsed-tooltip.png')});
 await page.emulateMedia({reducedMotion:'reduce'});expect(await page.locator('.ir-page').evaluate(e=>getComputedStyle(e).animationName)).toBe('none');
});
