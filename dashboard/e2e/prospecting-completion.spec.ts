import {test,expect} from '@playwright/test';
import {encode} from 'next-auth/jwt';
import {randomUUID} from 'node:crypto';
test.beforeEach(async({context})=>{const email='founder@leadengine.example',secret='fixture-session-secret-only-for-local-tests-123456789';const token=await encode({token:{sub:email,email},secret,salt:'authjs.session-token',maxAge:3600});await context.addCookies([{name:'authjs.session-token',value:token,url:'http://127.0.0.1:13000',httpOnly:true,sameSite:'Lax'}])});
test('real saved-search API persists multi-country filters, duplicates and archives without starting work',async({page,context})=>{
 const before=await(await context.request.get('/api/workflow/runs')).json();const name='Controlled saved search '+randomUUID();
 await page.goto('/find-leads');await page.locator('summary').filter({hasText:/^Saved searches$/}).click();await page.getByRole('checkbox',{name:'United States',exact:true}).check();
 await page.getByLabel('Qualified leads required',{exact:true}).fill('10');await page.getByText('Company targeting filters',{exact:true}).click();
 await page.getByLabel('Include keywords',{exact:true}).fill('independent, dental');await page.getByLabel('Minimum employees',{exact:true}).fill('10');
 await page.getByLabel('Search name',{exact:true}).fill(name);await page.getByRole('button',{name:'Save as new search',exact:true}).click();await expect(page.getByRole('status').filter({hasText:'Search saved. No discovery was started.'})).toBeVisible();
 await page.getByLabel('Qualified leads required',{exact:true}).fill('12');await page.getByRole('button',{name:'Update search',exact:true}).click();
 await expect.poll(async()=>{const result=await(await context.request.get('/api/discovery/searches?search='+encodeURIComponent(name))).json();return result.items[0]?.revision}).toBe(2);
 await page.reload();await page.locator('summary').filter({hasText:/^Saved searches$/}).click();await page.getByLabel('Load saved search',{exact:true}).selectOption({label:name});await expect(page.getByLabel('Qualified leads required',{exact:true})).toHaveValue('12');
 await expect(page.getByRole('checkbox',{name:'United States',exact:true})).toBeChecked();await expect(page.getByRole('checkbox',{name:'United Kingdom',exact:true})).toBeChecked();
 await page.getByLabel('Search name',{exact:true}).fill(name+' copy');await page.getByRole('button',{name:'Duplicate search',exact:true}).click();await expect(page.getByRole('status').filter({hasText:'Search saved.'})).toBeVisible();
 await page.getByRole('button',{name:'Archive search',exact:true}).click();await expect(page.getByRole('status').filter({hasText:'Search archived.'})).toBeVisible();
 expect((await(await context.request.get('/api/workflow/runs')).json()).total).toBe(before.total);
 const archived=await(await context.request.get('/api/discovery/searches?archived=true&search='+encodeURIComponent(name))).json();expect(archived.items).toHaveLength(1);
});
test('company contact, evidence, notes, list and actual no-email verification job are connected',async({page,context})=>{
 const origin='http://127.0.0.1:13000';expect((await context.request.put('/api/automation/controls',{headers:{origin},data:{scan_paused:false,email_paused:true}})).status()).toBe(200);
 const cid=randomUUID();const created=await context.request.post('/api/campaigns',{headers:{origin},data:{cities:['London'],verticals:['dentists'],target:5,fixture:true,request_id:cid}});expect(created.status()).toBe(201);
 await expect.poll(async()=> (await(await context.request.get('/api/operations/campaigns/'+cid)).json()).status).toBe('COMPLETED');
 const results=await(await context.request.get('/api/operations/campaigns/'+cid+'/leads')).json();const business=results.items.find((row:{business_id:number})=>row.business_id);expect(business).toBeTruthy();
 await page.goto('/leads/'+business.business_id);await page.getByRole('button',{name:'Add contact',exact:true}).click();await page.getByLabel('Full name',{exact:true}).fill('Avery Controlled');await page.getByLabel('Job title',{exact:true}).fill('CTO');await page.getByLabel('Source URL',{exact:true}).fill('https://controlled.example/team');await page.getByLabel('Source evidence',{exact:true}).fill('Avery Controlled, CTO, as recorded in the supplied public team source.');await page.getByRole('button',{name:'Save contact',exact:true}).click();await page.getByRole('link',{name:'Avery Controlled',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Avery Controlled',exact:true})).toBeVisible();await expect(page.getByText('CTO',{exact:true})).toBeVisible();
 await page.getByLabel('Contact note',{exact:true}).fill('Owner reviewed this professional record.');await page.getByRole('button',{name:'Add contact note',exact:true}).click();await expect(page.getByText('Owner reviewed this professional record.',{exact:true})).toBeVisible();
 const list=await context.request.post('/api/sales/lists',{headers:{origin},data:{name:'Controlled contact list '+randomUUID()}});expect(list.status()).toBe(201);const listId=(await list.json()).id;
 await page.reload();await page.getByLabel('Add contact to list',{exact:true}).selectOption(listId);await page.getByRole('button',{name:'Add contact to list',exact:true}).click();await expect(page.getByRole('button',{name:/Remove from Controlled contact list/})).toBeVisible();
 await page.getByRole('button',{name:'Check email domain and MX',exact:true}).click();await expect(page.getByText('no business email',{exact:true})).toBeVisible();
 await page.getByRole('link',{name:'View job history',exact:true}).click();await expect(page.getByRole('heading',{name:'Enrichment job',exact:true})).toBeVisible();await expect(page.getByText('no business email',{exact:true})).toBeVisible();
 expect((await(await context.request.get('/api/workflow/safety')).json()).sending_enabled).toBe(false);
});

test('lists retain company/contact membership on archive and tasks complete without email work',async({page,context})=>{
 const origin='http://127.0.0.1:13000',name='Controlled sales list '+randomUUID();
 await context.request.put('/api/automation/controls',{headers:{origin},data:{scan_paused:false,email_paused:true}});
 const cid=randomUUID();const created=await context.request.post('/api/campaigns',{headers:{origin},data:{cities:['London'],verticals:['dentists'],target:5,fixture:true,request_id:cid}});expect(created.status()).toBe(201);
 await expect.poll(async()=> (await(await context.request.get('/api/operations/campaigns/'+cid)).json()).status).toBe('COMPLETED');
 const leads=await(await context.request.get('/api/operations/campaigns/'+cid+'/leads')).json();const company=leads.items.find((row:{business_id:number})=>row.business_id);
 await page.goto('/lists');await page.getByRole('button',{name:'Create list',exact:true}).click();await page.getByLabel('List name',{exact:true}).fill(name);await page.getByRole('dialog').getByRole('button',{name:'Create list',exact:true}).click();await expect(page.getByRole('status').filter({hasText:'List created.'})).toBeVisible();await page.getByRole('link',{name,exact:true}).click();
 await expect(page).toHaveURL(/\/lists\/[a-f0-9-]{36}$/);const listId=page.url().split('/').at(-1)!;
 expect((await context.request.post('/api/sales/lists/'+listId+'/companies',{headers:{origin},data:{business_ids:[company.business_id]}})).status()).toBe(200);await page.reload();
 await expect(page.getByRole('heading',{name:'Companies',exact:true})).toBeVisible();expect((await context.request.get('/api/sales/lists/'+listId+'/export.csv')).status()).toBe(200);
 await page.getByRole('button',{name:'Archive list',exact:true}).click();await page.getByRole('button',{name:'Confirm archive',exact:true}).click();await expect(page.getByText('Archived list · history retained',{exact:true})).toBeVisible();expect((await(await context.request.get('/api/sales/lists/'+listId)).json()).company_count).toBe(1);
 await page.goto('/tasks');await page.getByText('Create sales task',{exact:true}).click();await page.getByLabel('Find company',{exact:true}).fill(String(company.name).slice(0,8));await page.getByRole('combobox',{name:'Company',exact:true}).selectOption(String(company.business_id));await expect(page.getByRole('combobox',{name:'Company',exact:true})).toHaveValue(String(company.business_id));await page.getByLabel('Task title',{exact:true}).fill('Controlled source review');await page.getByRole('combobox',{name:'New task type',exact:true}).selectOption('REVIEW');await page.getByLabel('Due date (your local time)',{exact:true}).fill('2026-12-01T09:00');await page.getByRole('button',{name:'Create task',exact:true}).click();await expect(page.getByRole('status').filter({hasText:'Task created.'})).toBeVisible();await page.getByRole('button',{name:'Complete Controlled source review',exact:true}).click();await expect(page.getByRole('heading',{name:'Controlled source review',exact:true})).toHaveCount(0);await page.getByRole('combobox',{name:'Task status',exact:true}).selectOption('COMPLETED');await expect(page.getByRole('heading',{name:'Controlled source review',exact:true})).toBeVisible();expect((await(await context.request.get('/api/workflow/safety')).json()).sending_enabled).toBe(false);
});
