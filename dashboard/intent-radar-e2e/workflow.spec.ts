import {test,expect,type BrowserContext} from '@playwright/test';
import {encode} from 'next-auth/jwt';
const origin='http://127.0.0.1:13000';
const title='Ask HN: recommend a website development partner?';
async function session(context:BrowserContext){const email='founder@leadengine.example';await context.addCookies([{name:'authjs.session-token',value:await encode({token:{sub:email,email},secret:'fixture-session-secret-only-for-local-tests-123456789',salt:'authjs.session-token',maxAge:3600}),url:origin,httpOnly:true,sameSite:'Lax'}]);}
test.beforeEach(async({context})=>{
 await session(context);
 const workspaces=await(await context.request.get('/api/organization/workspaces')).json();
 const original=workspaces.items.find((w:{name:string})=>w.name==='PlaneByte');
 expect((await context.request.put('/api/organization/active',{headers:{origin},data:{organization_id:original.organization_id}})).status()).toBe(200);
});

test('product switch, wizard, monitor lifecycle, discovery, evidence, saved opportunities and alerts persist',async({page,context})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await page.getByRole('button',{name:'Switch PlaneByte product'}).click();
 await page.getByRole('menuitem',{name:/Intent Radar/}).click();await expect(page.getByRole('heading',{name:'Intent Radar',exact:true})).toBeVisible();
 await page.getByRole('link',{name:'Create Monitor',exact:true}).first().click();
 const wizard=page.getByRole('dialog');await wizard.getByRole('button',{name:'Continue'}).click();
 await wizard.getByLabel('Monitor name',{exact:true}).fill('Browser website demand');await wizard.getByLabel('Add Keywords',{exact:true}).fill('website');await wizard.getByLabel('Add Keywords',{exact:true}).press('Enter');
 for(let i=0;i<3;i++)await wizard.getByRole('button',{name:'Continue'}).click();
 await wizard.getByRole('button',{name:'Create Monitor',exact:true}).click();await expect(wizard).not.toBeVisible();
 const card=page.locator('.ir-monitor').filter({hasText:'Browser website demand'});
 await expect(card.getByText('Never',{exact:true})).toBeVisible();expect((await(await context.request.get('/api/intent-radar/jobs')).json()).items).toHaveLength(0);
  await card.getByRole('button',{name:'Actions for Browser website demand'}).click();await page.getByRole('menuitem',{name:'Pause',exact:true}).click();await expect(card.getByRole('button',{name:'Run manual check'})).toBeDisabled();
  await card.getByRole('button',{name:'Actions for Browser website demand'}).click();await page.getByRole('menuitem',{name:'Resume',exact:true}).click();await card.getByRole('button',{name:'Run manual check'}).click();await expect(card.getByText('COMPLETED',{exact:true})).toBeVisible();
 await card.getByRole('button',{name:'Run manual check'}).click();await expect.poll(async()=> (await(await context.request.get('/api/intent-radar/jobs')).json()).items.filter((j:{status:string})=>j.status==='COMPLETED').length).toBe(2);
 expect((await(await context.request.get('/api/intent-radar/signals')).json()).total).toBe(1);expect((await(await context.request.get('/api/intent-radar/alerts')).json()).total).toBe(1);
 await page.getByRole('link',{name:'Intent Signals',exact:true}).click();await page.getByRole('link',{name:title,exact:true}).first().click();
 await expect(page.getByRole('heading',{name:'Original conversation evidence'})).toBeVisible();await expect(page.getByRole('link',{name:/Open original public discussion/})).toHaveAttribute('href','https://news.ycombinator.com/item?id=999123');
 await page.getByLabel('Signal status',{exact:true}).selectOption('Reviewed');
 await expect.poll(async()=> (await(await context.request.get('/api/intent-radar/signals')).json()).items[0].status).toBe('Reviewed');
 await page.getByLabel('Your review notes',{exact:true}).fill('Browser human review preserved');await page.getByRole('button',{name:'Save note',exact:true}).click();
 await expect.poll(async()=> (await(await context.request.get('/api/intent-radar/signals')).json()).items[0].notes).toBe('Browser human review preserved');
 await page.getByRole('button',{name:'Save signal',exact:true}).click();await page.getByRole('button',{name:'Add to Opportunity',exact:true}).click();
 await page.getByRole('link',{name:'Saved Signals',exact:true}).click();await page.getByLabel('Collection',{exact:true}).fill('Reviewed demand');await page.getByLabel('Saved signal notes',{exact:true}).fill('Source evidence retained');await page.getByRole('button',{name:'Save collection and notes'}).click();await page.reload();await expect(page.getByLabel('Collection',{exact:true})).toHaveValue('Reviewed demand');
 await page.getByRole('link',{name:'Opportunities',exact:true}).click();await page.getByLabel('Opportunity status',{exact:true}).selectOption('Saved');await page.getByLabel('Priority',{exact:true}).selectOption('High');await page.getByLabel('Opportunity notes',{exact:true}).fill('Human selected opportunity');await page.getByRole('button',{name:'Save opportunity',exact:true}).click();await expect.poll(async()=> (await(await context.request.get('/api/intent-radar/opportunities')).json()).items[0].status).toBe('Saved');await page.reload();await expect(page.getByLabel('Opportunity notes',{exact:true})).toHaveValue('Human selected opportunity');
 await page.getByRole('link',{name:'Alerts',exact:true}).click();await page.getByRole('button',{name:'Mark read',exact:true}).click();await expect(page.getByRole('button',{name:'Mark unread',exact:true})).toBeVisible();await page.reload();await expect(page.getByRole('button',{name:'Mark unread',exact:true})).toBeVisible();
 const notifications=await(await context.request.get('/api/organization/notifications')).json();expect(notifications.items.find((n:{kind:string})=>n.kind==='INTENT_RADAR').read_at).toBeTruthy();
 await page.getByRole('button',{name:'Workspace notifications'}).click();await expect(page.getByRole('link',{name:'Intent Radar monitor activity — review alerts'})).toBeVisible();await page.keyboard.press('Escape');
 await page.getByRole('button',{name:'Switch PlaneByte product'}).click();await page.getByRole('menuitem',{name:/Lead Engine/}).click();await expect(page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'Find Leads',exact:true})).toBeVisible();expect((await(await context.request.get('/api/workflow/safety')).json()).sending_enabled).toBe(false);expect(errors).toEqual([]);
});

test('manual discovery cancellation and workspace switching cannot expose cached evidence',async({page,context})=>{
 const seeded=await context.request.post('/api/intent-radar/discover',{headers:{origin},data:{configuration:{keywords:['website']}}});expect(seeded.status()).toBe(202);const seededId=(await seeded.json()).id;
 await expect.poll(async()=> (await(await context.request.get('/api/intent-radar/jobs/'+seededId)).json()).status).toBe('COMPLETED');
  await page.goto('/intent-radar/discover');await page.getByRole('button',{name:'Advanced Search',exact:true}).click();await page.getByLabel('Add Keywords',{exact:true}).fill('website');await page.getByLabel('Add Keywords',{exact:true}).press('Enter');
  await page.getByRole('button',{name:'Review Search',exact:true}).click();await page.getByRole('button',{name:'Search Public Conversations',exact:true}).click();await page.getByRole('button',{name:'Cancel check',exact:true}).click();await expect(page.getByText('CANCELLED',{exact:true})).toBeVisible();
 const ws=await(await context.request.get('/api/organization/workspaces')).json();const original=ws.items.find((w:{name:string})=>w.name==='PlaneByte');
 await page.goto('/intent-radar/signals');const signal=(await(await context.request.get('/api/intent-radar/signals')).json()).items[0];expect(signal).toBeTruthy();
 await page.getByRole('button',{name:'Workspace: '+original.name,exact:true}).click();await page.getByRole('menuitemradio',{name:'Isolated Radar workspace',exact:true}).click();await expect(page.getByRole('button',{name:'Workspace: Isolated Radar workspace'})).toBeVisible();
  expect((await(await context.request.get('/api/intent-radar/signals')).json()).total).toBe(0);expect((await context.request.get('/api/intent-radar/signals/'+signal.id)).status()).toBe(404);await page.goto('/intent-radar/saved');await expect(page.getByRole('heading',{name:'Your saved research will appear here'})).toBeVisible();await page.goto('/intent-radar/signals');await expect(page.getByRole('link',{name:title,exact:true})).toHaveCount(0);
 for(const width of [1440,390,320]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)}
});

test('monitor edit, duplicate, archive and restore use persisted revisions',async({page,context})=>{
 const created=await context.request.post('/api/intent-radar/monitors',{headers:{origin},data:{name:'Lifecycle monitor',configuration:{keywords:['website']},status:'Draft'}});expect(created.status()).toBe(201);
 await page.goto('/intent-radar/monitors');const card=page.locator('.ir-monitor').filter({has:page.getByRole('link',{name:'Lifecycle monitor',exact:true})});
 await card.getByRole('link',{name:'Edit',exact:true}).click();await page.getByRole('button',{name:'Edit Monitor',exact:true}).click();const wizard=page.getByRole('dialog');await wizard.getByRole('button',{name:'Continue'}).click();await wizard.getByLabel('Monitor name',{exact:true}).fill('Edited lifecycle monitor');for(let i=0;i<3;i++)await wizard.getByRole('button',{name:'Continue'}).click();await wizard.getByRole('button',{name:'Save Monitor',exact:true}).click();await expect(wizard).not.toBeVisible();await page.reload();await expect(page.getByRole('heading',{name:'Edited lifecycle monitor',exact:true,level:1})).toBeVisible();
  await page.locator('.ir-monitor').getByRole('button',{name:'Actions for Edited lifecycle monitor'}).click();await page.getByRole('menuitem',{name:'Duplicate',exact:true}).click();await page.goto('/intent-radar/monitors');const copy=page.locator('.ir-monitor').filter({has:page.getByRole('link',{name:'Edited lifecycle monitor (copy)',exact:true})});await expect(copy.getByText('Draft',{exact:true})).toBeVisible();await copy.getByRole('button',{name:'Actions for Edited lifecycle monitor (copy)'}).click();await page.getByRole('menuitem',{name:'Archive',exact:true}).click();await page.getByRole('button',{name:'Archive monitor',exact:true}).click();await expect(copy).toHaveCount(0);await page.getByRole('button',{name:'Archived',exact:true}).click();await copy.getByRole('button',{name:'Actions for Edited lifecycle monitor (copy)'}).click();await page.getByRole('menuitem',{name:'Restore draft',exact:true}).click();await page.getByRole('button',{name:'Current',exact:true}).click();await expect(copy.getByText('Draft',{exact:true})).toBeVisible();
});

test('unentitled workspace hides product navigation and denies direct APIs and page',async({page,context})=>{
 await page.goto('/intent-radar');await page.getByRole('button',{name:'Workspace: PlaneByte',exact:true}).click();await page.getByRole('menuitemradio',{name:'Radar unavailable workspace',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Intent Radar is unavailable'})).toBeVisible();
 await page.goto('/');await page.getByRole('button',{name:'Switch PlaneByte product'}).click();await expect(page.getByRole('menuitem',{name:/Lead Engine/})).toBeVisible();await expect(page.getByRole('menuitem',{name:/Intent Radar/})).toHaveCount(0);await page.keyboard.press('Escape');
 for(const route of ['overview','monitors','signals','saved','alerts','jobs'])expect((await context.request.get('/api/intent-radar/'+route)).status()).toBe(404);
 await page.goto('/intent-radar');await expect(page.getByRole('heading',{name:'Intent Radar is unavailable'})).toBeVisible();
});
