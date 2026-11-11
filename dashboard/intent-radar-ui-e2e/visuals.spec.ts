import {test,expect,type Page,type TestInfo} from '@playwright/test';
import {encode} from 'next-auth/jwt';
const baseline=process.env.RADAR_UI_BASELINE==='1';
test.beforeEach(async({context,baseURL})=>{
 const email='founder@leadengine.example';
 await context.addCookies([{name:'authjs.session-token',value:await encode({token:{sub:email,email},secret:'fixture-session-secret-only-for-local-tests-123456789',salt:'authjs.session-token',maxAge:3600}),url:baseURL!,httpOnly:true,sameSite:'Lax'}]);
 const workspaces=await(await context.request.get('/api/organization/workspaces')).json();
 const selected=workspaces.items.find((w:{name:string})=>w.name==='Isolated Radar workspace');
 expect((await context.request.put('/api/organization/active',{headers:{origin:baseURL!},data:{organization_id:selected.organization_id}})).status()).toBe(200);
});
async function capture(page:Page,info:TestInfo,name:string){await expect(page.locator('.ir-page')).toBeVisible();await page.waitForLoadState('networkidle');await expect(page.locator('.ir-skeleton')).toHaveCount(0);await expect(page.getByRole('heading',{name:/^Loading (source|saved) evidence/})).toHaveCount(0);await page.screenshot({path:info.outputPath(`${name}.png`)});}
test('fresh and populated isolated synthetic workspace visual walkthrough',async({page,context,baseURL},info)=>{
 const pages=['','discover','monitors','signals','opportunities','saved','alerts','integrations','settings'];
 for(const route of pages){await page.goto('/intent-radar'+(route?'/'+route:''));await capture(page,info,`empty-${route||'overview'}`);if(!baseline){await page.setViewportSize({width:390,height:844});await capture(page,info,`empty-mobile-${route||'overview'}`);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.setViewportSize({width:1440,height:900})}}
 await page.goto('/intent-radar/discover');await page.getByRole('button',{name:baseline?'Advanced Filters':'Advanced Search',exact:true}).click();await capture(page,info,'advanced-search');
 await page.goto('/intent-radar/monitors/new');await expect(page.getByRole('dialog')).toBeVisible();await page.screenshot({path:info.outputPath('monitor-wizard-goal.png')});await page.getByRole('dialog').getByRole('button',{name:'Continue',exact:true}).click();await page.screenshot({path:info.outputPath('monitor-wizard-topics.png')});await page.keyboard.press('Escape');
 const headers={origin:baseURL!};
 const response=await context.request.post('/api/intent-radar/monitors',{headers,data:{name:'Website demand · visual fixture',description:'Controlled synthetic browser fixture — not customer data.',goal:'Find recommendation requests',configuration:{keywords:['website'],topics:['Software development'],result_limit:20},status:'Active'}});expect(response.status()).toBe(201);const monitor=await response.json();
 const started=await context.request.post('/api/intent-radar/discover',{headers,data:{monitor_id:monitor.id,configuration:monitor.configuration}});expect(started.status()).toBe(202);const job=await started.json();
 await expect.poll(async()=> (await(await context.request.get('/api/intent-radar/jobs/'+job.id)).json()).status).toBe('COMPLETED');
 const signal=(await(await context.request.get('/api/intent-radar/signals')).json()).items[0];expect(signal).toBeTruthy();
 expect((await context.request.post('/api/intent-radar/saved/'+signal.id,{headers})).status()).toBe(200);
 expect((await context.request.post('/api/intent-radar/opportunities/'+signal.id,{headers})).status()).toBe(201);
 for(const route of pages){await page.goto('/intent-radar'+(route?'/'+route:''));await capture(page,info,`populated-${route||'overview'}`);if(!baseline){await page.setViewportSize({width:390,height:844});await capture(page,info,`populated-mobile-${route||'overview'}`);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.setViewportSize({width:1440,height:900})}}
 await page.goto('/intent-radar/signals/'+signal.id);await capture(page,info,'signal-detail');
 await page.getByRole('button',{name:'Switch PlaneByte product'}).click();await page.screenshot({path:info.outputPath('product-dropdown.png')});await page.keyboard.press('Escape');
 await page.getByRole('button',{name:'Collapse sidebar'}).click();await page.screenshot({path:info.outputPath('collapsed-sidebar.png')});
 await page.setViewportSize({width:390,height:844});await page.goto('/intent-radar');await capture(page,info,'mobile-overview');await page.getByRole('button',{name:'Open navigation'}).click();await page.screenshot({path:info.outputPath('mobile-navigation.png')});
});
