import {test,expect,type BrowserContext} from '@playwright/test';
import {encode} from 'next-auth/jwt';
const origin='http://127.0.0.1:13000';
async function session(context:BrowserContext){const email='founder@leadengine.example';await context.addCookies([{name:'authjs.session-token',value:await encode({token:{sub:email,email},secret:'fixture-session-secret-only-for-local-tests-123456789',salt:'authjs.session-token',maxAge:3600}),url:origin,httpOnly:true,sameSite:'Lax'}]);}
test.beforeEach(async({context})=>session(context));

test('Growth persists grounded research through the signed gateway and leased worker',async({page,context})=>{
 const response=await context.request.post('/api/intent-radar/discover',{headers:{origin},data:{configuration:{keywords:['website']}}});expect(response.status()).toBe(202);
 const job=(await response.json()).id;
 await expect.poll(async()=>(await(await context.request.get('/api/intent-radar/jobs/'+job)).json()).status).toBe('COMPLETED');
 await page.goto('/intent-radar/growth');await expect(page.getByRole('heading',{name:'Growth Intelligence',exact:true})).toBeVisible();
 await expect(page.getByText('Historical comparison is not established',{exact:true})).toBeVisible();
 await expect(page.getByRole('option',{name:'90 days · insufficient history'})).toHaveAttribute('disabled','');
 await page.getByRole('button',{name:/conversations$/,exact:false}).first().click();await expect(page.getByRole('status').filter({hasText:'collected conversations'})).toBeVisible();
 await page.goto('/intent-radar/growth/research');await page.getByLabel('Research title',{exact:true}).fill('Owned Growth browser review');
 await page.getByLabel('Question or focus',{exact:true}).fill('Which website workflow problem is present?');
 await page.getByRole('button',{name:'Generate from collected evidence',exact:true}).click();
 await expect(page).toHaveURL(/growth\/research\/[a-f0-9-]{36}$/);
 await expect(page.getByText('COMPLETE',{exact:true})).toBeVisible({timeout:45000});
 await expect(page.getByText('AI semantic interpretation — review required',{exact:true})).toBeVisible();
 await expect(page.getByText('Synthetic fixture: this discussion asks how to compare website options.',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Save research',exact:true}).click();await expect(page.getByRole('button',{name:'Unsave',exact:true})).toBeVisible();
 await page.getByLabel('Add a shared note',{exact:true}).fill('Specific team research context from browser acceptance.');await page.getByRole('button',{name:'Add note',exact:true}).click();
 await expect(page.locator('.growth-note').getByText('Specific team research context from browser acceptance.',{exact:true})).toBeVisible();
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Download MD',exact:true}).click();expect((await download).suggestedFilename()).toMatch(/\.md$/);
 const detail=page.url();await page.reload();await expect(page.locator('.growth-note').getByText('Specific team research context from browser acceptance.',{exact:true})).toBeVisible();
 await page.goto('/intent-radar/growth/saved');await expect(page.getByRole('link',{name:/Owned Growth browser review/})).toBeVisible();
 await page.goto('/intent-radar/growth/themes');await expect(page.getByRole('heading',{name:'Website partner comparisons',exact:true})).toBeVisible();
 await page.getByRole('link',{name:/Website partner comparisons/}).first().click();await expect(page.getByRole('button',{name:'Save theme',exact:true})).toBeVisible();
 for(const width of [1440,390,320]){await page.setViewportSize({width,height:900});await expect(page.getByRole('heading',{name:'Website partner comparisons',exact:true})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true)}
 await page.goto(detail);await expect(page.getByRole('heading',{name:'Owned Growth browser review',exact:true})).toBeVisible();
});

test('draft watchlists connect to real monitor controls without automatic collection',async({page,context})=>{
 await page.goto('/intent-radar/growth/watchlists');await page.getByLabel('Watchlist name',{exact:true}).fill('Reviewed market watchlist');await page.getByLabel('Reviewed keywords, separated by commas',{exact:true}).fill('reporting, workflow');
 await page.getByRole('button',{name:'Create draft watchlist',exact:true}).click();await expect(page.getByRole('heading',{name:'Reviewed market watchlist',exact:true})).toBeVisible();
 await expect(page.getByText('Draft',{exact:true})).toBeVisible();await page.getByRole('link',{name:'Manage schedule, pause and run history',exact:true}).click();await expect(page).toHaveURL(/intent-radar\/monitors\//);
 const jobs=await(await context.request.get('/api/intent-radar/jobs')).json();expect(jobs.items.some((j:{status:string})=>j.status==='RUNNING')).toBe(false);
});
