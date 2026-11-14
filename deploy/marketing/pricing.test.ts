import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const catalog=JSON.parse(readFileSync(new URL('../src/config/intent-radar-catalog.json',import.meta.url),'utf8'));
test('launch catalog has approved monthly USD prices and excludes Lead Engine',()=>{
 assert.deepEqual(catalog.plans.map((p:{code:string;monthly_minor:number|null})=>[p.code,p.monthly_minor]),[['starter',5900],['growth',14900],['scale',37900],['enterprise',null]]);
 assert.equal(catalog.product,'intent-radar');assert.equal(catalog.list_currency,'USD');assert.equal(catalog.interval,'monthly');
 assert.equal(catalog.prices_approved,true);assert.deepEqual(catalog.excluded_products,['lead-engine']);
});
test('unapproved quotas, annual discounts, trials and payment activation stay closed',()=>{
 assert.equal(catalog.allowances_approved,false);assert.equal(catalog.checkout_enabled,false);assert.equal(catalog.annual_billing,false);assert.equal(catalog.free_trial,false);
 assert.ok(catalog.plans.every((p:{limits:null})=>p.limits===null));
});
test('public comparison renders the canonical file and cannot create payment in marketing',()=>{
 const component=readFileSync(new URL('../src/components/family-pricing.tsx',import.meta.url),'utf8');
 assert.ok(component.includes('@/config/intent-radar-catalog.json'));assert.ok(component.includes('product=intent-radar'));
 assert.ok(!component.includes('product=lead-engine'));assert.ok(!component.includes('RAZORPAY')&&!component.includes('PAYU_MERCHANT'));
});
