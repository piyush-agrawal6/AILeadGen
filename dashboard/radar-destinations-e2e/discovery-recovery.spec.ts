import {test,expect} from '@playwright/test';
import {encode} from 'next-auth/jwt';

test('reviewed discovery persists, runs, and shows source coverage on reload',async({page,context},info)=>{
  const email='founder@leadengine.example',url='http://127.0.0.1:13000';
  await context.addCookies([{name:'authjs.session-token',value:await encode({token:{sub:email,email},secret:'fixture-session-secret-only-for-local-tests-123456789',salt:'authjs.session-token',maxAge:3600}),url,httpOnly:true}]);
  await page.goto('/intent-radar/discover/new');
  await page.getByPlaceholder('e.g. CRM Alternatives & Dissatisfaction Discussions').fill('Controlled website search');
  await page.getByPlaceholder(/Type keyword/).fill('website');await page.getByPlaceholder(/Type keyword/).press('Enter');
  for(const width of [1440,1024,768,390,320]){
    await page.setViewportSize({width,height:900});
    await expect(page.getByRole('heading',{name:'Create Discovery'})).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await page.screenshot({path:info.outputPath(`discovery-builder-${width}.png`)});
  }
  await page.getByRole('button',{name:'Open AI Assistant'}).click();
  await expect(page.getByText('Discovery Assistant',{exact:true})).toBeVisible();
  await page.screenshot({path:info.outputPath('assistant-320.png')});await page.getByRole('button',{name:'Close assistant'}).click();
  await page.getByRole('button',{name:'Run Discovery',exact:true}).click();
  await expect(page).toHaveURL(/\/discover\/runs\//);const id=new URL(page.url()).pathname.split('/').at(-1);
  await expect.poll(async()=>{const r=await context.request.get('/api/intent-radar/discoveries/'+id);return r.ok()?(await r.json()).status:null},{timeout:45000}).toMatch(/^(COMPLETED|NO_RESULTS)$/);
  await page.reload();await expect(page.getByText('Items Scanned',{exact:true})).toBeVisible();
  const run=await(await context.request.get('/api/intent-radar/discoveries/'+id)).json();expect(run.configuration.keywords).toEqual(['website']);expect(run.source_runs[0].scanned).toBeGreaterThan(0);
  await page.screenshot({path:info.outputPath('results-320.png')});
});
