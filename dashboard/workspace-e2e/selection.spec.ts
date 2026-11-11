import {test,expect,type BrowserContext} from '@playwright/test';
import {encode} from 'next-auth/jwt';
async function session(context:BrowserContext,email='founder@leadengine.example'){const secret='fixture-session-secret-only-for-local-tests-123456789';const token=await encode({token:{email,sub:email},secret,salt:'authjs.session-token',maxAge:3600});await context.addCookies([{name:'authjs.session-token',value:token,url:'http://127.0.0.1:13000',httpOnly:true,sameSite:'Lax'}])}
test('gated selector loads actual memberships and safely rejects a stale unavailable workspace',async({page,context})=>{
 await session(context);
 const response=await context.request.get('/api/organization/workspaces');expect(response.status()).toBe(200);
 const original=await response.json();expect(original.items).toHaveLength(1);
 await page.goto('/');const companyName=original.items[0].name;const selector=page.getByRole('button',{name:'Workspace: '+companyName,exact:true});await expect(selector).toBeVisible();
 for(const width of [1440,390]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)}
 // Simulate a stale list after membership revocation; the real API must reject it.
 const stale='00000000-0000-4000-8000-000000000099';
 await page.route('**/api/organization/workspaces',route=>route.fulfill({json:{...original,items:[...original.items,{organization_id:stale,name:'Unavailable former workspace',role:'VIEWER'}]}}));
 await page.reload();await selector.click();await page.getByRole('menuitemradio',{name:'Unavailable former workspace',exact:true}).click();
 await expect(page.locator('#workspace-switch-error')).toHaveText('Workspace could not be changed. Please retry.');
 await expect(selector.locator('strong')).toHaveText(companyName);
 const bounds=await selector.boundingBox();expect(bounds?.y).toBeGreaterThanOrEqual(0);
 await page.screenshot({path:test.info().outputPath('mobile-error.png'),fullPage:true});
 const current=await context.request.get('/api/organization/workspaces');expect((await current.json()).active_organization_id).toBe(original.active_organization_id);
});

test('company profile saves through the real owned API and handles concurrent edits',async({page,context})=>{
 await session(context);
 await page.goto('/settings/company');
 await expect(page.getByRole('heading',{name:'Company profile',exact:true})).toBeVisible();
 await page.getByLabel('Company description',{exact:true}).fill('Controlled company profile review. User-entered business information.');
 await page.getByRole('button',{name:'Save company profile'}).click();
 await expect(page.getByRole('status').filter({hasText:'Company profile saved.'})).toBeVisible();
 const stored:Record<string,unknown>=await(await context.request.get('/api/organization/profile')).json();
 expect(stored.description).toBe('Controlled company profile review. User-entered business information.');
 const update:Record<string,unknown>={};
 for(const key of ['name','website','description','industry','company_size','country','city','timezone','contact_email','countries_served','version'])update[key]=stored[key];
 update.industry='Concurrent controlled edit';
 expect((await context.request.put('/api/organization/profile',{headers:{origin:'http://127.0.0.1:13000'},data:update})).status()).toBe(200);
 await page.getByLabel('Company name',{exact:true}).fill('Unsaved owner draft');
 await page.getByRole('button',{name:'Save company profile'}).click();
 await expect(page.getByRole('alert').filter({hasText:'Company profile changed.'})).toBeVisible();
 await expect(page.getByLabel('Company name',{exact:true})).toHaveValue('Unsaved owner draft');
 await page.getByRole('button',{name:'Reload saved profile'}).click();
 await expect(page.getByLabel('Industry',{exact:true})).toHaveValue('Concurrent controlled edit');
 await expect(page.getByLabel('Company name',{exact:true})).toHaveValue(String(stored.name));
 for(const width of [1440,390]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)}
 await page.screenshot({path:test.info().outputPath('company-profile-mobile.png'),fullPage:true});
});

test('team invitation persists through the real API and revocation invalidates the link',async({page,context})=>{
 await session(context);
 await page.goto('/settings/team');
 await page.getByLabel('Teammate email',{exact:true}).fill('invited-controlled@example.test');
 await page.getByRole('button',{name:'Create invitation',exact:true}).click();
 const link=page.getByLabel('Private invitation link',{exact:true});await expect(link).toBeVisible();
 const token=(await link.inputValue()).split('#')[1];expect(token.length).toBeGreaterThan(40);
 const stored=await context.request.get('/api/organization/invitations');expect(stored.status()).toBe(200);
 const payload=await stored.json();const invite=payload.items.find((item:{email:string})=>item.email==='invited-controlled@example.test');
 expect(invite.status).toBe('PENDING');expect(JSON.stringify(payload)).not.toContain(token);
 for(const width of [1440,390]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)}
 await page.getByRole('button',{name:'Revoke',exact:true}).click();await expect(link).not.toBeVisible();
 await expect(page.getByText(/member · revoked/)).toBeVisible();
 await page.screenshot({path:test.info().outputPath('team-mobile.png'),fullPage:true});
});

test('the named signed-in recipient accepts once and the inviter receives a scoped notification',async({page,context,browser})=>{
 await session(context);
 const created=await context.request.post('/api/organization/invitations',{headers:{origin:'http://127.0.0.1:13000'},data:{email:'cofounder@leadengine.example',role:'VIEWER'}});
 expect(created.status()).toBe(201);const invitation=await created.json();
 const recipient=await browser.newContext();await session(recipient,'cofounder@leadengine.example');
 try{
  const recipientPage=await recipient.newPage();await recipientPage.goto('/accept-invitation#'+invitation.token);
  await recipientPage.getByRole('button',{name:'Use code from invitation link'}).click();
  await expect(recipientPage).toHaveURL(/\/accept-invitation$/);
  await recipientPage.getByRole('button',{name:'Accept invitation',exact:true}).click();
  await expect(recipientPage.getByRole('status')).toContainText('Invitation accepted.');
  const memberships=await recipient.request.get('/api/organization/workspaces');expect(memberships.status()).toBe(200);
  expect((await memberships.json()).items[0].role).toBe('VIEWER');
  const replay=await recipient.request.post('/api/organization/invitations/respond',{headers:{origin:'http://127.0.0.1:13000'},data:{token:invitation.token,action:'ACCEPT'}});expect(replay.status()).toBe(409);
  const notifications=await context.request.get('/api/organization/notifications');expect((await notifications.json()).items.some((item:{kind:string;entity_id:string})=>item.kind==='INVITATION_ACCEPTED'&&item.entity_id===invitation.id)).toBe(true);
 }finally{await recipient.close()}
});

test('personal profile saves through the account API independently of company data',async({page,context})=>{
 await session(context);
 const company=await(await context.request.get('/api/organization/profile')).json();
 const membership=await(await context.request.get('/api/organization/workspaces')).json();
 await page.goto('/settings/profile');await page.getByLabel('Display name',{exact:true}).fill('Controlled Account Owner');
 await page.getByLabel('Your timezone',{exact:true}).fill('Asia/Kolkata');
 await page.getByRole('button',{name:'Save your profile',exact:true}).click();
 await expect(page.getByRole('status')).toHaveText('Your profile has been saved.');
 const saved=await(await context.request.get('/api/profile')).json();expect(saved.display_name).toBe('Controlled Account Owner');expect(saved.timezone).toBe('Asia/Kolkata');
 expect((await(await context.request.get('/api/organization/profile')).json()).version).toBe(company.version);
 expect((await(await context.request.get('/api/organization/workspaces')).json()).active_organization_id).toBe(membership.active_organization_id);
 for(const width of [1440,390]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)}
});

test('explicit workspace creation selects its own new profile and retains the original workspace',async({page,context})=>{
 await session(context);
 const original=await(await context.request.get('/api/organization/workspaces')).json();
 await page.goto('/settings/workspaces');await page.getByLabel('Company name',{exact:true}).fill('Controlled New Workspace');
 await page.getByRole('button',{name:'Create workspace',exact:true}).click();
 await expect(page).toHaveURL(/\/onboarding$/);
 await page.goto('/settings/company');
 await expect(page.getByLabel('Company name',{exact:true})).toHaveValue('Controlled New Workspace');
 const workspaces=await(await context.request.get('/api/organization/workspaces')).json();
 expect(workspaces.items).toHaveLength(original.items.length+1);expect(workspaces.active_organization_id).not.toBe(original.active_organization_id);
 const denied=await context.request.get('/api/operations/dashboard');expect(denied.status()).toBe(403);expect((await denied.json()).code).toBe('ONBOARDING_INCOMPLETE');
 await page.getByRole('button',{name:'Workspace: Controlled New Workspace',exact:true}).click();await page.getByRole('menuitemradio',{name:original.items.find((item:{organization_id:string})=>item.organization_id===original.active_organization_id).name,exact:true}).click();
 await expect(page).toHaveURL(/\/$/);
 expect((await(await context.request.get('/api/organization/workspaces')).json()).active_organization_id).toBe(original.active_organization_id);
});

test('ICP builder saves owned criteria, versions changes and duplicates inactive',async({page,context})=>{
 await session(context);
 await page.goto('/settings/icp');
 await page.getByRole('button',{name:'New targeting profile',exact:true}).click();
 await page.getByLabel('Profile name',{exact:true}).fill('Controlled hospitality segment');
 await page.getByLabel('Industries',{exact:true}).fill('Hospitality');
 await page.getByLabel('Countries',{exact:true}).fill('United Kingdom');
 await page.getByText('Matching weights',{exact:true}).click();await page.getByLabel('Weight company.industries',{exact:true}).fill('8');
 await page.getByRole('button',{name:'Create targeting profile',exact:true}).click();
 await expect(page.getByRole('status').filter({hasText:'Targeting profile saved.'})).toBeVisible();
 await page.getByLabel('Profile status',{exact:true}).selectOption('ACTIVE');
 await page.getByRole('button',{name:'Save targeting profile',exact:true}).click();
 await page.getByRole('button',{name:'Version history',exact:true}).click();
 await expect(page.getByText('Version 2 · active',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Compare versions',exact:true}).click();
 await expect(page.getByRole('status').filter({hasText:'1 changed field between versions 1 and 2.'})).toBeVisible();
 await expect(page.getByRole('cell',{name:'ACTIVE',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Duplicate profile',exact:true}).click();
 await expect(page.getByLabel('Profile name',{exact:true})).toHaveValue('Controlled hospitality segment copy');
 await expect(page.getByLabel('Profile status',{exact:true})).toHaveValue('INACTIVE');
 const stored=await(await context.request.get('/api/organization/icps')).json();expect(stored.total).toBe(2);expect(stored.items.every((item:{criteria:{weights:Record<string,number>}})=>item.criteria.weights['company.industries']===8)).toBe(true);
 for(const width of [1440,390]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)}
 await page.screenshot({path:test.info().outputPath('icp-builder-mobile.png'),fullPage:true});
});

test('manual onboarding resumes and unlocks only its own workspace without starting work',async({page,context})=>{
 await session(context);
 const headers={origin:'http://127.0.0.1:13000'};
 const created=await context.request.post('/api/organization/workspaces',{headers,data:{name:'Controlled Onboarding Company',request_id:crypto.randomUUID()}});expect(created.status()).toBe(201);
 const denied=await context.request.get('/api/operations/dashboard');expect(denied.status()).toBe(403);
 await page.goto('/settings/company');await page.getByRole('button',{name:'Save company profile',exact:true}).click();await expect(page.getByText('Company profile saved.',{exact:true})).toBeVisible();
 const icp=await context.request.post('/api/organization/icps',{headers,data:{name:'Controlled setup customers',status:'ACTIVE',criteria:{company:{industries:['Software'],countries:['India']}},request_id:crypto.randomUUID()}});expect(icp.status()).toBe(201);
 await page.goto('/settings/setup');await expect(page).toHaveURL(/\/onboarding$/);await page.getByLabel('Build prospect lists',{exact:true}).check();await page.getByRole('button',{name:'Save and continue',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Company profile',exact:true})).toBeVisible();await page.getByRole('button',{name:'Save and continue',exact:true}).click();
 await page.getByRole('button',{name:'Add product or service',exact:true}).click();await page.getByLabel('Product or service name',{exact:true}).fill('Software engineering');await page.getByRole('button',{name:'Save and continue',exact:true}).click();
  const selectedICP=await icp.json();
  const [loadedICP]=await Promise.all([page.waitForResponse(response=>response.url().endsWith('/api/organization/icps/'+selectedICP.id)&&response.request().method()==='GET'),page.getByLabel('Default ideal customer profile',{exact:true}).selectOption(selectedICP.id)]);
  expect(loadedICP.status()).toBe(200);expect((await loadedICP.json()).status).toBe('ACTIVE');
  await page.getByRole('button',{name:'Save and continue',exact:true}).click();
 await page.getByLabel('I confirm this target geography.',{exact:true}).check();await page.getByLabel('Set up mailbox and CRM integrations later.',{exact:true}).check();await page.getByRole('button',{name:'Save and continue',exact:true}).click();
 await page.reload();await expect(page.getByRole('button',{name:'Finish setup',exact:true})).toBeVisible();await page.getByRole('button',{name:'Finish setup',exact:true}).click();
 await expect(page.getByText('Setup is complete. No discovery or outreach has started.',{exact:true})).toBeVisible();
 const dashboard=await context.request.get('/api/operations/dashboard');expect(dashboard.status()).toBe(200);
 const saved=await context.request.get('/api/organization/onboarding');expect((await saved.json()).status).toBe('COMPLETED');
 for(const width of [1440,390]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)}
});

test('approved ICP prefills discovery and support/legal pages remain useful and responsive',async({page,context})=>{
 await session(context);const headers={origin:'http://127.0.0.1:13000'};
 const before=await(await context.request.get('/api/workflow/runs')).json();
 const created=await context.request.post('/api/organization/icps',{headers,data:{name:'Reviewed dental geography',status:'ACTIVE',criteria:{company:{industries:['Dentistry'],countries:['GB'],employee_min:10},contact:{job_titles:['Owner']}},request_id:crypto.randomUUID()}});expect(created.status()).toBe(201);const profile=await created.json();
 await page.goto('/find-leads?icp='+profile.id);await expect(page.getByRole('combobox',{name:'Ideal customer profile',exact:true})).toHaveValue(profile.id);
 await expect(page.getByRole('heading',{name:'Reviewed dental geography'})).toBeVisible();await expect(page.getByRole('checkbox',{name:'dentists',exact:true})).toBeChecked();await expect(page.getByRole('checkbox',{name:'hospitality',exact:true})).not.toBeChecked();
 await page.getByText('Company targeting filters',{exact:true}).click();await expect(page.getByLabel('Minimum employees',{exact:true})).toHaveValue('10');
 await page.locator('summary').filter({hasText:/Criteria requiring evidence/}).click();await expect(page.getByText('contact: job titles',{exact:true})).toBeVisible();
 expect((await(await context.request.get('/api/workflow/runs')).json()).total).toBe(before.total);
 await page.goto('/recommendations');await expect(page.getByRole('heading',{name:'Recommendations',exact:true})).toBeVisible();
 await page.goto('/help');await expect(page.getByRole('heading',{name:'How can we help?',exact:true})).toBeVisible();await page.getByLabel('Search help topics').fill('verification');await expect(page.getByRole('heading',{name:'Professional contacts and verification'})).toBeVisible();await expect(page.getByRole('link',{name:'Contact Support'})).toHaveAttribute('href',/^mailto:contact@planebyte\.com/);
 for(const width of [1440,390,320]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);const title=await page.locator('.shell-page-title').boundingBox(),workspace=await page.getByRole('button',{name:/^Workspace:/}).boundingBox();expect(title&&workspace&&title.x+title.width<=workspace.x).toBe(true)}
 await page.screenshot({path:test.info().outputPath('help-mobile-refined.png'),fullPage:true});
 for(const route of ['/privacy','/terms']){await page.goto(route);await expect(page.getByRole('main')).toBeVisible();await expect(page.getByText(/Development review copy/)).toBeVisible();await expect(page.locator('.auth-story')).toHaveCount(0);await expect(page.getByRole('link',{name:'Back to sign in'})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)}
});
