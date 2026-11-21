import {test,expect,type BrowserContext} from '@playwright/test';
import {encode} from 'next-auth/jwt';
import {createInFixtureAccount} from './create-in-fixture-account';
async function session(context:BrowserContext,email='founder@leadengine.example'){const secret='fixture-session-secret-only-for-local-tests-123456789';const token=await encode({token:{email,sub:email},secret,salt:'authjs.session-token',maxAge:3600});await context.addCookies([{name:'authjs.session-token',value:token,url:'http://127.0.0.1:13000',httpOnly:true,sameSite:'Lax'}])}
const headers={origin:'http://127.0.0.1:13000'};
const baseName='Browser QA Workspace';
test.beforeEach(async({context})=>{await session(context);const list=await(await context.request.get('/api/organization/workspaces')).json();const owned=list.items.find((i:{name:string;role:string})=>i.name===baseName&&i.role==='OWNER');expect(owned).toBeTruthy();expect((await context.request.put('/api/organization/active',{headers,data:{organization_id:owned.organization_id}})).status()).toBe(200);});
test('gated selector loads actual memberships and safely rejects a stale unavailable workspace',async({page,context})=>{
 await session(context);
 const response=await context.request.get('/api/organization/workspaces');expect(response.status()).toBe(200);
 const original=await response.json();expect(original.items.find((i:{organization_id:string})=>i.organization_id===original.active_organization_id).role).toBe('OWNER');
 await page.goto('/settings');const companyName=baseName;const selector=page.getByRole('button',{name:'Workspace: '+companyName,exact:true});await expect(selector).toBeVisible();
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
 await page.getByRole('button',{name:'Edit Profile',exact:true}).first().click();
 await page.getByLabel('Company description',{exact:true}).fill('Controlled company profile review. User-entered business information.');
 await page.getByRole('button',{name:'Save Changes',exact:true}).first().click();
 await expect(page.getByText('Organization profile saved.',{exact:true})).toBeVisible(); await page.getByRole('button',{name:'Edit Profile',exact:true}).first().click();
 const stored:Record<string,unknown>=await(await context.request.get('/api/organization/profile')).json();
 expect(stored.description).toBe('Controlled company profile review. User-entered business information.');
 const update:Record<string,unknown>={};
 for(const key of ['name','website','description','industry','company_size','country','city','timezone','contact_email','countries_served','version'])update[key]=stored[key];
 update.industry='Concurrent controlled edit';
 expect((await context.request.put('/api/organization/profile',{headers:{origin:'http://127.0.0.1:13000'},data:update})).status()).toBe(200);
 await page.locator('#company-name').fill('Unsaved owner draft');
 await page.getByRole('button',{name:'Save Changes',exact:true}).first().click();
 await expect(page.getByRole('alert').filter({hasText:'Company profile changed.'})).toBeVisible();
 await expect(page.locator('#company-name')).toHaveValue('Unsaved owner draft');
 await page.getByRole('button',{name:'Reload',exact:true}).click(); await page.getByRole('button',{name:'Edit Profile',exact:true}).first().click();
 await expect(page.getByLabel('Industry',{exact:true})).toHaveValue('Concurrent controlled edit');
 await expect(page.locator('#company-name')).toHaveValue(String(stored.name));
 for(const width of [1440,390]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)}
 await page.screenshot({path:test.info().outputPath('company-profile-mobile.png'),fullPage:true});
});

test('team invitation persists through the real API and revocation invalidates the link',async({page,context})=>{
 await session(context);
 await page.goto('/settings/team');
 await page.getByRole('button',{name:'Invite Member',exact:true}).click();await page.getByLabel('Work email',{exact:true}).fill('invited-controlled@example.com');
 await page.getByRole('button',{name:'Send Invitation',exact:true}).click();
 const link=page.getByLabel('Private invitation link',{exact:true});await expect(link).toBeVisible();
 const token=(await link.inputValue()).split('#')[1];expect(token.length).toBeGreaterThan(40);
 const stored=await context.request.get('/api/organization/invitations');expect(stored.status()).toBe(200);
 const payload=await stored.json();const invite=payload.items.find((item:{email:string})=>item.email==='invited-controlled@example.com');
 expect(invite.status).toBe('PENDING');expect(JSON.stringify(payload)).not.toContain(token);
 for(const width of [1440,390]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)}
 await page.getByRole('button',{name:'Revoke',exact:true}).click();await expect(link).not.toBeVisible();
 await expect(page.getByRole('row').filter({hasText:'invited-controlled@example.com'})).toContainText('Revoked');
 await page.screenshot({path:test.info().outputPath('team-mobile.png'),fullPage:true});
});

test('the named signed-in recipient accepts once and the inviter receives a scoped notification',async({page,context,browser})=>{
 await session(context);
 const created=await context.request.post('/api/organization/invitations',{headers:{origin:'http://127.0.0.1:13000'},data:{email:'recipient@example.com',role:'VIEWER'}});
 expect(created.status()).toBe(201);const invitation=await created.json();
 const recipient=await browser.newContext();await session(recipient,'recipient@example.com');
 try{
  const recipientPage=await recipient.newPage();await recipientPage.goto('/accept-invitation#'+invitation.token);
  await expect(recipientPage.getByLabel('Invitation code')).toHaveValue(invitation.token);
  await expect(recipientPage).toHaveURL(/\/accept-invitation$/);
  await recipientPage.getByRole('button',{name:'Accept Invitation',exact:true}).click();
  await expect(recipientPage.getByRole('status')).toContainText('Invitation accepted.');
  const memberships=await recipient.request.get('/api/organization/workspaces');expect(memberships.status()).toBe(200);
  expect((await memberships.json()).items.find((i:{name:string})=>i.name===baseName).role).toBe('VIEWER');
  const replay=await recipient.request.post('/api/organization/invitations/respond',{headers:{origin:'http://127.0.0.1:13000'},data:{token:invitation.token,action:'ACCEPT'}});expect(replay.status()).toBe(409);
  const notifications=await context.request.get('/api/organization/notifications');expect(notifications.status()).toBe(200);expect(JSON.stringify((await notifications.json()).items)).toMatch(/INVITATION_ACCEPTED|invitation accepted|Teammate joined workspace/i);
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
 await page.goto('/settings/workspaces');await page.getByRole('button',{name:'Create Workspace',exact:true}).click();await page.getByLabel('Workspace / company name').fill('Controlled New Workspace');
 if(process.env.SHARED_BILLING_ACCOUNTS_ENABLED==='true'){
  const selector=page.getByRole('combobox',{name:/Billing account/});await expect(selector).toHaveValue('');await selector.selectOption('independent');
 }
 await page.getByRole('button',{name:'Create & Continue',exact:true}).click();
 await expect(page).toHaveURL(/\/onboarding$/);
 await page.goto('/settings/company');await page.getByRole('button',{name:'Edit Profile',exact:true}).first().click();
 await expect(page.locator('#company-name')).toHaveValue('Controlled New Workspace');
 const workspaces=await(await context.request.get('/api/organization/workspaces')).json();
 expect(workspaces.items).toHaveLength(original.items.length+1);expect(workspaces.active_organization_id).not.toBe(original.active_organization_id);
 if(process.env.SHARED_BILLING_ACCOUNTS_ENABLED==='true')expect(workspaces.items.find((i:{organization_id:string})=>i.organization_id===workspaces.active_organization_id).billing_account).toMatchObject({id:workspaces.active_organization_id,shared:false});
 const denied=await context.request.get('/api/operations/dashboard');expect(denied.status()).toBe(403);expect((await denied.json()).code).toBe('ONBOARDING_INCOMPLETE');
 await page.getByRole('button',{name:'Workspace: Controlled New Workspace',exact:true}).click();await page.getByRole('menuitemradio',{name:original.items.find((item:{organization_id:string})=>item.organization_id===original.active_organization_id).name,exact:true}).click();
 await expect(page).toHaveURL(/\/intent-radar$/);
 expect((await(await context.request.get('/api/organization/workspaces')).json()).active_organization_id).toBe(original.active_organization_id);
});

test('ICP builder saves owned criteria, versions changes and duplicates inactive',async({page,context})=>{
 await session(context);
 await page.goto('/settings/icp');
 await expect(page).toHaveURL(/\/intent-radar\/ideal-customers$/);await expect(page.locator('a[href="/intent-radar/ideal-customers/new"]').first()).toBeVisible();
 const base='/api/organization/icps';const draft={name:'Controlled hospitality segment',status:'INACTIVE',description:'',criteria:{company:{industries:['Hospitality'],countries:['GB']},weights:{'company.industries':8}}};const made=await context.request.post(base,{headers,data:{...draft,request_id:crypto.randomUUID()}});expect(made.status()).toBe(201);const first=await made.json();const endpoint=base+'/'+first.id;const update={...draft,status:'ACTIVE',revision:first.revision};expect((await context.request.put(endpoint,{headers,data:update})).status()).toBe(200);expect((await context.request.put(endpoint,{headers,data:update})).status()).toBe(409);
 const versions=await(await context.request.get(endpoint+'/versions')).json();expect(versions.items.length).toBe(2);const comparison=await(await context.request.get(endpoint+'/compare?before=1&after=2')).json();expect(comparison.changes.status).toEqual({before:'INACTIVE',after:'ACTIVE'});const duplicate=await(await context.request.post(endpoint+'/duplicate',{headers,data:{name:draft.name+' copy',request_id:crypto.randomUUID()}})).json();expect(duplicate.status).toBe('INACTIVE');expect(duplicate.criteria.weights['company.industries']).toBe(8);await page.reload();await expect(page.getByText(draft.name,{exact:true}).first()).toBeVisible();
 for(const width of [1440,390]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)}
 await page.screenshot({path:test.info().outputPath('icp-builder-mobile.png'),fullPage:true});
});

test('manual onboarding resumes and unlocks only its own workspace without starting work',async({page,context})=>{
 await session(context);
 const headers={origin:'http://127.0.0.1:13000'};
 await createInFixtureAccount(context,'Controlled Onboarding Company',baseName);
 const denied=await context.request.get('/api/operations/dashboard');expect(denied.status()).toBe(403);
 await page.goto('/settings/setup');await expect(page).toHaveURL(/\/onboarding$/);await page.getByLabel('Build prospect lists',{exact:true}).check();await page.getByRole('button',{name:'Save and continue'}).click();await page.getByRole('button',{name:'Edit Profile',exact:true}).first().click();await page.getByLabel('Company description',{exact:true}).fill('Reviewed engineering services');await page.getByRole('button',{name:'Save Changes',exact:true}).first().click();await expect(page.getByText('Organization profile saved.')).toBeVisible();await page.getByRole('button',{name:'Save and continue'}).click();await page.getByRole('button',{name:'Add product or service'}).click();await page.getByLabel('Product or service name',{exact:true}).last().fill('Software engineering');await page.getByRole('button',{name:'Save and continue'}).click();
 const made=await context.request.post('/api/organization/icps',{headers,data:{name:'Controlled setup customers',status:'ACTIVE',criteria:{company:{industries:['Software'],countries:['India']}},request_id:crypto.randomUUID()}});expect(made.status()).toBe(201);await page.reload();const primary=(await made.json()).id;await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/organization/icps/'+primary)&&r.ok()),page.getByLabel('Default ideal customer profile').selectOption(primary)]);await page.getByRole('button',{name:'Save and continue'}).click();await page.getByLabel('I confirm this target geography.').check();await page.getByLabel('Set up mailbox and CRM integrations later.').check();await page.getByRole('button',{name:'Save and continue'}).click();await page.reload();await page.getByRole('button',{name:'Finish setup'}).click();await expect(page.getByText('Setup is complete. No background job has started.')).toBeVisible();const saved=await(await context.request.get('/api/organization/onboarding')).json();expect(saved.status).toBe('COMPLETED');expect(saved.default_icp_id).toBe(primary);expect((await context.request.get('/api/intent-radar/overview')).status()).toBe(404);expect((await(await context.request.get('/api/organization/products')).json()).intent_radar.enabled).toBe(false);
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
 await page.goto('/help');const search=page.getByLabel('Search help articles');await search.fill('verification');await expect(page.getByText(/Search results for/)).toBeVisible();await expect(page.getByText('Contact Support',{exact:true}).first()).toBeVisible();
 for(const width of [1440,390,320]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)}
 for(const route of ['/privacy','/terms']){await page.goto(route);await expect(page.getByRole('main')).toBeVisible();await expect(page.getByRole('heading',{level:1})).toBeVisible();expect(await page.locator('main').innerText()).toMatch(/PlaneByte/i);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)}
});
