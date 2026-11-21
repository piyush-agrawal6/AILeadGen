import {test,expect} from '@playwright/test';
import {encode} from 'next-auth/jwt';

test('an approved internal follow-up persists and records its real manual outcome',async({page,context})=>{
  const email='founder@leadengine.example',url='http://127.0.0.1:13000';
  await context.addCookies([{name:'authjs.session-token',value:await encode({token:{sub:email,email},secret:'fixture-session-secret-only-for-local-tests-123456789',salt:'authjs.session-token',maxAge:3600}),url,httpOnly:true}]);
  const signalResponse=await context.request.get('/api/intent-radar/signals');expect(signalResponse.ok()).toBe(true);
  const signal=(await signalResponse.json()).items.find((x:{title:string})=>x.title==='Controlled export example');expect(signal).toBeDefined();
  const premature=await context.request.post(`/api/intent-radar/opportunities/${signal.id}`,{headers:{origin:url}});expect(premature.status()).toBe(409);
  const review=await context.request.patch(`/api/intent-radar/signals/${signal.id}`,{headers:{origin:url},data:{revision:signal.revision,status:'Qualified',notes:'Human review in disposable acceptance workspace.'}});expect(review.ok()).toBe(true);
  const created=await context.request.post(`/api/intent-radar/opportunities/${signal.id}`,{headers:{origin:url}});expect(created.ok()).toBe(true);
  const opp=await created.json();await page.goto(`/intent-radar/actions?opportunity=${opp.id}`);
  await page.getByLabel('Title',{exact:true}).fill('Review controlled evidence');await page.getByLabel('Assignee’s workspace email').fill(email);await page.getByLabel('Due (your local time)').fill('2027-01-05T10:00');await page.getByRole('button',{name:'Prepare for review'}).click();await expect(page.getByText('Needs review',{exact:true})).toBeVisible();await page.getByRole('button',{name:'Approve and create follow-up'}).click();await page.reload();await page.getByRole('button',{name:'Record outcome'}).click();await page.getByLabel('User-reported outcome').fill('Evidence reviewed');await page.getByRole('button',{name:'Complete follow-up',exact:true}).click();await expect(page.getByText('User-reported outcome: Evidence reviewed')).toBeVisible();
});

test('connection directory stays usable at supported widths',async({page,context},info)=>{
  const email='founder@leadengine.example',url='http://127.0.0.1:13000';
  await context.addCookies([{name:'authjs.session-token',value:await encode({token:{sub:email,email},secret:'fixture-session-secret-only-for-local-tests-123456789',salt:'authjs.session-token',maxAge:3600}),url,httpOnly:true}]);
  await page.goto('/intent-radar/integrations');
  for(const width of [1440,1024,768,390,320]){
    await page.setViewportSize({width,height:900});
    await expect(page.getByRole('link',{name:/Google Sheets/})).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await page.screenshot({path:info.outputPath(`integrations-${width}.png`)});
  }
  await page.getByRole('combobox',{name:'Category'}).selectOption('Automation');
  await expect(page.getByRole('heading',{name:'Google Sheets'})).toHaveCount(0);
  await page.getByRole('combobox',{name:'Category'}).selectOption('All');
  await page.getByLabel('Search integrations').fill('absent-name');await expect(page.getByText('No matching integrations.')).toBeVisible();
});
test('workspace downloads a file and approves a fixed-range export',async({page,context})=>{
  const email='founder@leadengine.example',url='http://127.0.0.1:13000';
  await context.addCookies([{name:'authjs.session-token',value:await encode({token:{sub:email,email},secret:'fixture-session-secret-only-for-local-tests-123456789',salt:'authjs.session-token',maxAge:3600}),url,httpOnly:true}]);
  await page.goto('/intent-radar/signals');await expect(page.getByText('Controlled export example').first()).toBeVisible();
  const downloaded=page.waitForEvent('download');await page.getByRole('button',{name:'Export',exact:true}).click();expect((await downloaded).suggestedFilename()).toBe('planebyte-signals.csv');
  await page.goto('/intent-radar/integrations');await page.locator('a[href="/intent-radar/integrations/sheets"]').click();
  await page.route('https://accounts.google.com/**',route=>route.fulfill({body:'Controlled consent handoff'}));
  const handoff=page.waitForRequest(r=>r.url().startsWith('https://accounts.google.com/'));await page.getByText('Authorize Google Sheets writes').click();const consent=new URL((await handoff).url());const callback=new URL(consent.searchParams.get('redirect_uri')!);expect(callback.href).toBe(url+'/intent-radar/integrations/sheets/callback');callback.searchParams.set('state',consent.searchParams.get('state')!);callback.searchParams.set('code','offline-code');await page.goto(callback.href);await expect(page.getByText(/Authorization saved/)).toBeVisible();await page.getByText('Return to workspace connections').click();
  await page.getByLabel('Existing spreadsheet URL or ID').fill('controlled-sheet-id');await page.getByText('Check access and load worksheets').click();await page.getByText('Preview write (100 records maximum)').click();await expect(page.getByText('Controlled export example')).toBeVisible();await page.getByText('Approve overwriting this exact range').click();await expect(async()=>{await page.getByText('Refresh export history').click();await expect(page.getByText(/· COMPLETED/)).toBeVisible();}).toPass({timeout:15000});
});
