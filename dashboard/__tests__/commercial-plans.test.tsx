import {render,screen} from '@testing-library/react';
import {expect,it} from 'vitest';
import {readFileSync} from 'node:fs';
import {CommercialPlans,type CommercialCatalog} from '@/components/workspaces/commercial-plans';
const catalog=JSON.parse(readFileSync('../app/billing/commercial_catalog.json','utf8')) as CommercialCatalog;
it('shows approved USD prices and inert preserved selection without inventing quotas or opening payment',()=>{
 render(<CommercialPlans selectedPlan="growth" data={{catalog,provider:'creem',checkout_enabled:false,blockers:['Recurring capability unverified'],historical_payments:[]}}/>);
 expect(screen.getByText('$59',{selector:'.commercial-price'})).toBeVisible();
 expect(screen.getByText(/Your selection is saved/)).toBeVisible();
 expect(screen.getByRole('link',{name:'Request Growth access'})).toHaveAttribute('href',expect.stringContaining('mailto:'));
 expect(screen.queryByRole('button',{name:/pay|checkout|subscribe/i})).not.toBeInTheDocument();
 expect(screen.getByText('600,000')).toBeVisible();
 expect(screen.getByText('Monthly monitoring checks')).toBeVisible();
 expect(screen.queryByText('Pending approval')).not.toBeInTheDocument();
 expect(screen.queryByText(/internal test|₹100|₹200|₹300/i)).not.toBeInTheDocument();
});
