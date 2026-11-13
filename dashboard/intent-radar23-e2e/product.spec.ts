import {test,expect,type BrowserContext} from '@playwright/test';
import {encode} from 'next-auth/jwt';
const origin='http://127.0.0.1:13000';
async function session(context:BrowserContext){const email='founder@leadengine.example';await context.addCookies([{name:'authjs.session-token',value:await encode({token:{sub:email,email},secret:'fixture-session-secret-only-for-local-tests-123456789',salt:'authjs.session-token',maxAge:3600}),url:origin,httpOnly:true,sameSite:'Lax'}]);}
test.beforeEach(async({context})=>session(context));

test('four actual provider families and nine read-only MCP contracts are discoverable',async({page,context})=>{
 const response=await context.request.get('/api/intent-radar/capabilities');expect(response.status()).toBe(200);
 const catalog=await response.json();expect(catalog.sources.map((s:{id:string})=>s.id).sort()).toEqual(['discourse','hacker_news','rss','stack_exchange']);
 await page.goto('/intent-radar/integrations');
 for(const source of catalog.sources)await expect(page.getByRole('button',{name:'View details for '+source.name,exact:true})).toBeVisible();
 await page.getByRole('button',{name:'View details for Approved Discourse',exact:true}).click();
 await expect(page.getByRole('dialog')).toContainText('Not configured');await page.getByRole('button',{name:'Close dialog'}).click();
 await page.getByRole('tab',{name:'AI Assistants & MCP',exact:true}).click();
 await page.getByRole('button',{name:'View details for Intent Radar MCP',exact:true}).click();
 const dialog=page.getByRole('dialog');
 for(const name of ['search_intent_signals','list_intent_monitors','get_intent_signal','list_intent_opportunities','list_intent_sources','get_intent_analysis','get_intent_run','get_intent_source_health','get_intent_workspace_context'])await expect(dialog.locator('dl code').filter({hasText:name})).toBeVisible();
 await expect(dialog).toContainText('Client connection is not verified');
 await page.screenshot({path:(process.env.RADAR23_EVIDENCE_ROOT||'../data/artifacts/verification/intent-radar23-product-product')+'/evidence-mcp.png',fullPage:true});
 await page.getByRole('button',{name:'Close dialog'}).click();
 await page.goto('/intent-radar/signals');await page.getByRole('button',{name:'All Filters',exact:true}).click();
 const options=page.getByLabel('Source filter',{exact:true});
 for(const source of catalog.sources)await expect(options.getByRole('option',{name:source.name,exact:true})).toBeAttached();
});

test('feedback refreshes AI score and opportunity detail persists through real routing',async({page,context})=>{
 const search=await context.request.post('/api/intent-radar/discover',{headers:{origin},data:{configuration:{keywords:['website']}}});expect(search.status()).toBe(202);const job=(await search.json()).id;
 await expect.poll(async()=> (await(await context.request.get('/api/intent-radar/jobs/'+job)).json()).status).toBe('COMPLETED');
 const signal=(await(await context.request.get('/api/intent-radar/signals')).json()).items[0];
 await page.goto('/intent-radar/signals/'+signal.id);await page.getByRole('button',{name:'Analyze signal',exact:true}).click();
 await expect(page.getByText('AI interpretation',{exact:true})).toBeVisible();
 const before=(await(await context.request.get('/api/intent-radar/signals/'+signal.id+'/analysis')).json()).items[0].scoring.overall;
 await expect(page.getByText(before+'/100 relevance',{exact:true})).toBeVisible();
 await page.getByLabel('Feedback label',{exact:true}).selectOption('Not relevant');await page.getByRole('button',{name:'Save relevance feedback',exact:true}).click();
 await expect(page.getByText((before-10)+'/100 relevance',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Disable my feedback',exact:true}).click();await expect(page.getByText(before+'/100 relevance',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Add to Opportunity',exact:true}).click();
 await expect.poll(async()=> (await(await context.request.get('/api/intent-radar/opportunities')).json()).total).toBe(1);
 const opportunity=(await(await context.request.get('/api/intent-radar/opportunities')).json()).items[0];
 expect((await context.request.get('/api/intent-radar/opportunities/'+opportunity.id)).status()).toBe(200);
 await page.goto('/intent-radar/opportunities/'+opportunity.id);await expect(page.getByRole('heading',{name:'Opportunity detail',exact:true})).toBeVisible();
 await page.getByLabel('Opportunity notes',{exact:true}).fill('Product audit evidence-backed research');await page.getByRole('button',{name:'Save opportunity',exact:true}).click();
 await expect.poll(async()=> (await(await context.request.get('/api/intent-radar/opportunities/'+opportunity.id)).json()).notes).toBe('Product audit evidence-backed research');
 await page.reload();await expect(page.getByLabel('Opportunity notes',{exact:true})).toHaveValue('Product audit evidence-backed research');await expect(page.getByRole('heading',{name:signal.title,exact:true})).toBeVisible();
 for(const width of [1440,390,320]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:(process.env.RADAR23_EVIDENCE_ROOT||'../data/artifacts/verification/intent-radar23-product-product')+'/evidence-opportunity-'+width+'.png',fullPage:true})}
});

test('saved multi-source monitor advertises its real providers and exposes source-run history',async({page,context})=>{
 const created=await context.request.post('/api/intent-radar/monitors',{headers:{origin},data:{name:'Product audit multi-source monitor',status:'Active',configuration:{keywords:['website'],sources:['hacker_news','stack_exchange']}}});expect(created.status()).toBe(201);const monitor=await created.json();
 const search=await context.request.post('/api/intent-radar/discover',{headers:{origin},data:{monitor_id:monitor.id,configuration:monitor.configuration}});expect(search.status()).toBe(202);const job=(await search.json()).id;
 await expect.poll(async()=> (await(await context.request.get('/api/intent-radar/jobs/'+job)).json()).status).toBe('COMPLETED');
 await page.goto('/intent-radar/monitors/'+monitor.id);await expect(page.locator('.ir-monitor .ir-source')).toContainText('Stack Exchange');
 await expect(page.getByRole('heading',{name:'Monitor run history',exact:true})).toBeVisible();await expect(page.getByText(/hacker_news · COMPLETE/)).toBeVisible();await expect(page.getByText(/stack_exchange · COMPLETE/)).toBeVisible();
});

test('every active Radar page captures real-route desktop and mobile persisted states',async({page,context})=>{
 const signal=(await(await context.request.get('/api/intent-radar/signals')).json()).items[0];
 const opportunity=(await(await context.request.get('/api/intent-radar/opportunities')).json()).items[0];
 const monitor=(await(await context.request.get('/api/intent-radar/monitors')).json()).items[0];
 expect((await context.request.post('/api/intent-radar/saved/'+signal.id,{headers:{origin},data:{}})).status()).toBe(200);
 const routes=['','discover','monitors','monitors/new','monitors/'+monitor.id,'signals','signals/'+signal.id,'saved','opportunities','opportunities/'+opportunity.id,'alerts','integrations','settings'];
 for(const [index,route] of routes.entries()){
  await page.goto('/intent-radar/'+route);await expect(page.locator('.ir-page')).toBeVisible();
  await expect(page.locator('.ir-skeleton')).toHaveCount(0);await expect(page.getByRole('heading',{name:'404',exact:true})).toHaveCount(0);
  for(const width of [1440,390]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:(process.env.RADAR23_EVIDENCE_ROOT||'../data/artifacts/verification/intent-radar23-product-product')+'/page-'+index+'-'+width+'.png',fullPage:true})}
 }
});
