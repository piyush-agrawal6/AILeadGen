import {test,expect} from '@playwright/test';
import {encode} from 'next-auth/jwt';
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
