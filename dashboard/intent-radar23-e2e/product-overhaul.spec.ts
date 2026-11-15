import {test,expect,type BrowserContext} from '@playwright/test';
import {encode} from 'next-auth/jwt';
const origin='http://127.0.0.1:13000';
async function session(context:BrowserContext){const email='founder@leadengine.example';await context.addCookies([{name:'authjs.session-token',value:await encode({token:{sub:email,email},secret:'fixture-session-secret-only-for-local-tests-123456789',salt:'authjs.session-token',maxAge:3600}),url:origin,httpOnly:true,sameSite:'Lax'}]);}
test('global assistant persists grounded multi-turn guidance without executing actions',async({page,context})=>{
 test.setTimeout(90000);await session(context);
 const response=await context.request.post('/api/intent-radar/discover',{headers:{origin},data:{configuration:{keywords:['website']}}});expect(response.status()).toBe(202);const job=(await response.json()).id;
 await expect.poll(async()=>(await(await context.request.get('/api/intent-radar/jobs/'+job)).json()).status).toBe('COMPLETED');
 await page.goto('/intent-radar');await page.getByRole('button',{name:'Ask PlaneByte',exact:true}).click();
 await expect(page.getByRole('dialog')).toBeVisible();await page.getByRole('textbox',{name:'Ask PlaneByte',exact:true}).fill('What source evidence is collected here?');
 await page.getByRole('button',{name:'Send question',exact:true}).click();
 await expect(page.getByText('AI guidance — review required',{exact:true})).toBeVisible({timeout:45000});
 await expect(page.getByRole('dialog').getByText('Evidence',{exact:true})).toBeVisible();
 await page.getByRole('textbox',{name:'Ask PlaneByte',exact:true}).fill('What should I review next?');await page.getByRole('button',{name:'Send question',exact:true}).click();
 await expect(page.getByText('AI guidance — review required',{exact:true})).toHaveCount(2,{timeout:45000});
 await page.getByRole('button',{name:'Close intelligence assistant'}).click();await page.goto('/billing');
 await page.getByRole('button',{name:'Ask PlaneByte',exact:true}).click();await expect(page.getByText('What should I review next?',{exact:true})).toBeVisible();
 for(const width of [390,320]){await page.setViewportSize({width,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);await expect(page.getByRole('button',{name:'Close intelligence assistant'})).toBeVisible();}
});
for(const width of [1920,1440,1280,1024,768,390,320])test(`product routes remain usable without horizontal overflow at ${width}px`,async({page,context},info)=>{
 test.setTimeout(180000);await session(context);await page.setViewportSize({width,height:900});const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 for(const path of ['/intent-radar','/intent-radar/graph','/intent-radar/assistant','/intent-radar/discover','/intent-radar/signals','/intent-radar/opportunities','/intent-radar/saved','/intent-radar/monitors','/intent-radar/alerts','/intent-radar/growth','/intent-radar/growth/themes','/intent-radar/growth/trends','/intent-radar/growth/research','/intent-radar/growth/watchlists','/intent-radar/growth/competitors','/intent-radar/growth/reports','/intent-radar/integrations','/settings','/settings/company','/settings/icp','/account/profile','/account/security','/billing','/help']){
  await page.goto(path);await expect(page.locator('main').first()).toBeVisible();await expect(page.getByRole('button',{name:'Ask PlaneByte',exact:true})).toBeVisible();
  await expect(page.locator('[role="alert"]').filter({hasText:/could not|unavailable|failed to load/i})).toHaveCount(0);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),path).toBe(true);
  await page.screenshot({path:info.outputPath(path.replaceAll('/','_')+'-'+width+'.png'),fullPage:true});
  if(width===1440||width===320){await page.evaluate(()=>document.documentElement.classList.add('dark'));expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),path+' dark').toBe(true);await page.screenshot({path:info.outputPath(path.replaceAll('/','_')+'-'+width+'-dark.png'),fullPage:true});await page.evaluate(()=>document.documentElement.classList.remove('dark'));}
 }
 expect(errors).toEqual([]);
});

test('workspace counts and follow-up use real stored data without AI quota',async({page,context})=>{
 await session(context);const before=await (await context.request.get('/api/organization/usage')).json();
 await page.goto('/intent-radar');await page.getByRole('button',{name:'Ask PlaneByte',exact:true}).click();
 await page.getByRole('textbox',{name:'Ask PlaneByte',exact:true}).fill('How many signals have I generated yet?');await page.getByRole('button',{name:'Send question',exact:true}).click();
 await expect(page.getByText('Workspace data — no AI used',{exact:true})).toBeVisible({timeout:30000});
 await expect(page.getByRole('dialog').getByText(/Your workspace contains \d+ collected conversation records/).first()).toBeVisible();
 await page.getByRole('textbox',{name:'Ask PlaneByte',exact:true}).fill('And today?');await page.getByRole('button',{name:'Send question',exact:true}).click();
 await expect(page.getByText('Workspace data — no AI used',{exact:true})).toHaveCount(2,{timeout:30000});
 await expect(page.getByText(/This window uses original publication dates/)).toBeVisible();
 await page.getByRole('textbox',{name:'Ask PlaneByte',exact:true}).fill('Hi');await page.getByRole('button',{name:'Send question',exact:true}).click();
 await expect(page.getByText('Product guidance — no AI used',{exact:true})).toBeVisible();
 const after=await (await context.request.get('/api/organization/usage')).json();
 expect(after.provider_usage.requests).toBe(before.provider_usage.requests);
 expect(after.usage.find((x:{dimension:string})=>x.dimension==='ai_calls').used).toBe(before.usage.find((x:{dimension:string})=>x.dimension==='ai_calls').used);
});


test('business graph saves reviewed context, preserves filters and hands a question to the real assistant',async({page,context})=>{
 test.setTimeout(120000);await session(context);
 await page.goto('/intent-radar/graph');
 await page.getByRole('button',{name:'Positioning',exact:true}).click();
 const positioning=page.getByRole('textbox',{name:'Business positioning',exact:true});
 await positioning.fill('Reviewed workflow research for software teams.');
 await page.getByRole('button',{name:'Save business context',exact:true}).click();
 await expect(page.getByText('Context saved.',{exact:true})).toBeVisible();
 await page.reload();await page.getByRole('button',{name:'Positioning',exact:true}).click();
 await expect(positioning).toHaveValue('Reviewed workflow research for software teams.');
 await page.getByRole('button',{name:'Show structured list',exact:true}).click();
 await expect(page.locator('.pb-graph-tree')).toContainText('Reviewed workflow research for software teams.');
 let releaseOverview!:()=>void;const overviewGate=new Promise<void>(resolve=>{releaseOverview=resolve});
 await page.route(url=>url.pathname==='/api/intent-radar/overview',async route=>{await overviewGate;await route.continue()});
 await page.goto('/intent-radar');const overviewReady=page.waitForResponse(response=>new URL(response.url()).pathname==='/api/intent-radar/overview');
 await page.getByRole('textbox',{name:'Ask about your workspace'}).fill('How many signals have I discovered?');
 releaseOverview();await overviewReady;
 await expect(page.getByRole('textbox',{name:'Ask about your workspace'})).toHaveValue('How many signals have I discovered?');
 await page.getByRole('button',{name:'Open question in assistant'}).click();
 await expect(page.getByRole('dialog').getByRole('textbox',{name:'Ask PlaneByte',exact:true})).toHaveValue('How many signals have I discovered?');
 await page.getByRole('button',{name:'Send question',exact:true}).click();
 await expect(page.getByText('Workspace data — no AI used',{exact:true})).toBeVisible({timeout:30000});
 await page.getByRole('button',{name:'Close intelligence assistant'}).click();
 await page.goto('/settings/company');await expect(page.getByRole('navigation',{name:'Settings categories'})).toBeVisible();
 await page.goto('/intent-radar/signals');
 const review=page.getByRole('link',{name:/^Review /}).first();
 await expect(review).toBeVisible();await review.click();await expect(page.getByRole('dialog',{name:'Signal evidence'})).toBeVisible();await page.getByRole('button',{name:'Close dialog',exact:true}).click();await expect(page).toHaveURL(/\/intent-radar\/signals$/);
});
