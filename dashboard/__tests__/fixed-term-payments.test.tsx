import {render,screen} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {describe,it,expect} from 'vitest';
import {FixedTermPayments,type FixedTermData} from '@/components/workspaces/fixed-term-payments';
const plans=[{code:'starter',name:'Starter',monthly_minor:5900}];
const data:FixedTermData={items:[],checkout_enabled:false,yearly_prices_approved:false,renewal:'Original terms.',upgrade_policy:'Original terms.'};
function draw(value=data){return render(<QueryClientProvider client={new QueryClient()}><FixedTermPayments data={value} plans={plans}/></QueryClientProvider>)}
describe('retired provider preserves history without purchase initiation',()=>{
 it('does not render a retired checkout even if old configuration says enabled',()=>{
  const view=draw({...data,checkout_enabled:true});expect(view.container).toBeEmptyDOMElement();expect(screen.queryByRole('button',{name:/Continue/})).toBeNull();
 });
 it('retains historical paid receipt and refund-review rights',()=>{
  draw({...data,items:[{id:'fixture-order',provider:'payu',mode:'test',plan_code:'starter',interval:'monthly',currency:'USD',total_minor:5900,tax_minor:0,status:'PAID',period_start:1700000000,period_end:1702592000,created_at:'2026-11-15T00:00:00Z'}]});
  expect(screen.getByText('Historical prepaid purchases')).toBeVisible();expect(screen.getByText('$59.00')).toBeVisible();expect(screen.getByRole('link',{name:'Receipt'})).toHaveAttribute('href','/api/organization/billing/access/orders/fixture-order/receipt');expect(screen.getByRole('button',{name:'Request refund review'})).toBeVisible();expect(screen.queryByRole('button',{name:/Continue|PayU|checkout/i})).toBeNull();
 });
});
