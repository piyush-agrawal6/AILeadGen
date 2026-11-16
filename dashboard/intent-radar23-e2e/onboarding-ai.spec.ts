import {test,expect,type BrowserContext} from '@playwright/test';
import {encode} from 'next-auth/jwt';
const origin='http://127.0.0.1:13000';
async function session(context:BrowserContext,email='cofounder@leadengine.example'){await context.addCookies([{name:'authjs.session-token',value:await encode({token:{sub:email,email},secret:'fixture-session-secret-only-for-local-tests-123456789',salt:'authjs.session-token',maxAge:3600}),url:origin,httpOnly:true,sameSite:'Lax'}]);}
test('owner resumes AI setup, reviews saved context and shares defaults without starting work',async({page,context},info)=>{
 test.setTimeout(180000);await session(context);await page.goto('/intent-radar');await expect(page).toHaveURL(/\/onboarding$/);
 await page.getByLabel('Company website',{exact:true}).fill('https://example.com');await page.getByRole('button',{name:'Analyze my business with AI'}).click();
 await expect(page.getByText('Ready for your review',{exact:true})).toBeVisible({timeout:45000});
 for(const button of await page.getByRole('button',{name:'Accept this section'}).all())await button.click();
 await page.getByRole('button',{name:'Approve profile & prepare ideal customers'}).click();
 await expect(page.getByText('Review segment 1',{exact:true})).toBeVisible({timeout:45000});
 const before=await(await context.request.get('/api/organization/icps')).json();expect(before.total).toBe(0);
 await page.getByRole('checkbox',{name:'Review segment 1'}).check();await page.getByRole('checkbox',{name:'Review segment 2'}).check();
 await page.getByRole('radio',{name:'Use as primary ICP'}).last().check();
 await expect(page.getByRole('textbox',{name:'Research keywords',exact:true})).toHaveValue(/Custom applications/);
 for(const theme of ['light','dark'])for(const width of [1440,768,390,320]){await page.setViewportSize({width,height:900});await page.evaluate(value=>document.documentElement.classList.toggle('dark',value==='dark'),theme);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.evaluate(()=>{window.scrollTo(0,0);document.querySelector('main')?.scrollTo(0,0)});await page.screenshot({path:info.outputPath(`icp-${theme}-${width}.png`),fullPage:true});}
 await page.getByRole('button',{name:'Save reviewed customer profiles'}).click();await expect(page.getByRole('heading',{name:'Ready to explore, on your terms'})).toBeVisible();await page.reload();await expect(page.getByRole('heading',{name:'Ready to explore, on your terms'})).toBeVisible();
 await page.getByRole('button',{name:'Finish setup',exact:true}).click();await expect(page.getByRole('heading',{name:'Your reviewed context is saved'})).toBeVisible();
 const setup=await(await context.request.get('/api/organization/onboarding/assistant-context')).json();expect(setup.progress.status).toBe('COMPLETED');
 const overview=await(await context.request.get('/api/intent-radar/overview')).json();expect(overview.active_monitors).toBe(0);expect(overview.new_signals).toBe(0);
 await page.getByRole('link',{name:'Discover conversations'}).click();await expect(page.getByRole('heading',{name:'Find conversations that matter'})).toBeVisible();
 await page.getByRole('button',{name:'Advanced Search',exact:true}).click();await expect(page.getByRole('button',{name:'Remove Custom applications from Keywords',exact:true})).toBeVisible();
 const prefs=await(await context.request.get('/api/intent-radar/settings')).json();expect(prefs.discovery_keywords).toContain('Custom applications');expect(prefs.discovery_excluded).toEqual(['recruitment']);expect(prefs.default_icp_id).toBe(setup.progress.default_icp_id);
 await page.goto('/intent-radar/graph');await page.getByRole('button',{name:'Show structured list'}).click();await expect(page.locator('.pb-graph-tree')).toContainText('Software studios');await expect(page.locator('.pb-graph-tree')).toContainText('Custom applications');
 await page.goto('/intent-radar');await expect(page).toHaveURL(/\/intent-radar$/);
});
test('completed users bypass setup and new setup supports manual fallback with factual guidance',async({page,context},info)=>{
 test.setTimeout(120000);await session(context,'founder@leadengine.example');await page.goto('/intent-radar');await expect(page).toHaveURL(/\/intent-radar$/);
 const response=await context.request.post('/api/organization/workspaces',{headers:{origin},data:{name:'Synthetic manual onboarding',request_id:crypto.randomUUID()}});expect(response.status()).toBe(201);
 await page.goto('/onboarding');await page.getByLabel('Company website',{exact:true}).fill('https://example.com/failure');await page.getByRole('button',{name:'Analyze my business with AI'}).click();await expect(page.getByText('Analysis did not complete',{exact:true})).toBeVisible({timeout:45000});
 await page.locator('.ai-setup-assistant > summary').click();await page.getByLabel('Ask about your setup').fill('What company details are saved?');await page.getByRole('button',{name:'Ask PlaneByte',exact:true}).click();await expect(page.getByText('Saved workspace context — no AI used',{exact:true})).toBeVisible();
 await page.getByLabel('Company description',{exact:true}).fill('Manually reviewed application engineering.');await page.getByRole('button',{name:'Add an offering'}).click();await page.getByLabel('Offering name',{exact:true}).fill('Application engineering');
 for(const theme of ['light','dark']){await page.setViewportSize({width:320,height:844});await page.evaluate(value=>document.documentElement.classList.toggle('dark',value==='dark'),theme);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:info.outputPath(`manual-${theme}.png`),fullPage:true});}
 await page.getByRole('button',{name:'Back to website'}).click();await page.getByRole('button',{name:'Set up manually'}).click();await page.getByRole('button',{name:'Approve company profile',exact:true}).click();await page.getByText('Choose an existing profile or set up manually',{exact:true}).click();await page.getByRole('button',{name:'Create an additional profile manually'}).click();await page.getByLabel('Targeting profile name').fill('Manually reviewed audience');await page.getByLabel('Target industries').fill('Software');await page.getByRole('button',{name:'Create and select profile'}).click();await page.getByRole('button',{name:'Continue with selected profile'}).click();await page.reload();await expect(page.getByRole('heading',{name:'Ready to explore, on your terms'})).toBeVisible();await page.getByRole('button',{name:'Finish setup',exact:true}).click();await expect(page.getByRole('heading',{name:'Your reviewed context is saved'})).toBeVisible();await expect(page.getByRole('link',{name:'Discover conversations'})).toHaveCount(0);
});
