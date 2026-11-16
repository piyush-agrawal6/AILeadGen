import {render,screen,fireEvent} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {describe,it,expect} from 'vitest';
import {FixedTermPayments,type FixedTermData} from '@/components/workspaces/fixed-term-payments';
const plans=[{code:'starter',name:'Starter',monthly_minor:5900},{code:'growth',name:'Growth',monthly_minor:14900},{code:'scale',name:'Scale',monthly_minor:37900}];
const data:FixedTermData={items:[],checkout_enabled:false,yearly_prices_approved:false,renewal:'Manual renewal only.',upgrade_policy:'No early upgrades or unused-time credits.'};
function draw(value=data){return render(<QueryClientProvider client={new QueryClient()}><FixedTermPayments data={value} plans={plans}/></QueryClientProvider>)}
describe('fixed-term billing truthfulness',()=>{
 it('shows approved USD totals without requiring a GSTIN or opening payment',()=>{
  draw();expect(screen.getByText('Total: $59.00 USD')).toBeInTheDocument();expect(screen.getByText(/No GST is collected/)).toBeInTheDocument();expect(screen.queryByRole('button',{name:'Continue to PayU'})).toBeNull();expect(screen.queryByLabelText(/GSTIN/)).toBeNull();
 });
 it('keeps yearly pricing unpublished and checkout unavailable',()=>{
  draw();fireEvent.change(screen.getByLabelText('Access term'),{target:{value:'yearly'}});
  expect(screen.getByText(/Yearly price not yet available/)).toBeInTheDocument();expect(screen.getByText(/Yearly checkout is unavailable/)).toBeInTheDocument();expect(screen.queryByText(/Total:/)).toBeNull();
 });
 it('retains payment provider, test classification and verified receipt action',()=>{
  draw({...data,items:[{id:'fixture-order',provider:'payu',mode:'test',plan_code:'starter',interval:'monthly',currency:'USD',total_minor:5900,tax_minor:0,status:'PAID',period_start:1700000000,period_end:1702592000,created_at:'2026-11-15T00:00:00Z'}]});
  expect(screen.getByText('paid · payu · test')).toBeInTheDocument();expect(screen.getByRole('link',{name:'Download receipt'})).toHaveAttribute('href','/api/organization/billing/access/orders/fixture-order/receipt');expect(screen.getByRole('button',{name:'Request refund review'})).toBeInTheDocument();
 });
});
