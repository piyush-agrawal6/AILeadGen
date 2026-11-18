import {render,screen,cleanup} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {readFileSync} from 'node:fs';
import {UsageOverview,type UsageData} from '@/components/workspaces/usage';
const state=vi.hoisted(()=>({data:undefined as UsageData|undefined}));
vi.mock('@tanstack/react-query',()=>({useQuery:()=>({data:state.data,isPending:false,error:null})}));
vi.mock('@/components/workspaces/use-workspace',()=>({useWorkspace:()=>({data:{active_organization_id:'fixture-workspace'}})}));
const catalog=JSON.parse(readFileSync('../app/billing/commercial_catalog.json','utf8'));
function fixture(paid:boolean):UsageData{return {access:{kind:paid?'Commercial subscription':'Approved Beta',intent_radar:true,growth_intelligence:true},subscription:null,commercial:{catalog,provider:'creem',checkout_enabled:false,blockers:[],historical_payments:[]},usage:[{dimension:'ai_calls',label:'AI reservations today',used:1,limit:5,remaining:4,basis:'Daily safety',resets_at:null,near_limit:false},...(paid?[{dimension:'plan_ai_tokens',label:'Shared AI token capacity',used:1100,reserved:100,limit:600000,remaining:598900,basis:'Verified paid period',resets_at:null,near_limit:false}]:[])],provider_usage:{requests:2,input_tokens_reported:100,output_tokens_reported:20,estimated_cost_usd:null,unreported_requests:1},source_requests:[],team_seats:1,sandbox_tools_available:false,support_url:'mailto:contact@planebyte.com',unmetered:[]}}
afterEach(cleanup);
it('prioritizes monthly usage, shows uncertain reservations and separates daily safety limits',()=>{
 state.data=fixture(true);render(<UsageOverview/>);
 expect(screen.getByRole('heading',{name:'Your subscription allowances'})).toBeVisible();
 expect(screen.getByText('1,000 completed · 100 pending or uncertain')).toBeVisible();
 expect(screen.getByText('Daily operator safety limits')).toBeVisible();
 expect(screen.getByRole('heading',{name:'Daily limits',hidden:true})).not.toBeVisible();
 expect(screen.getByText(/Unknown outcomes retain reserved capacity/)).toBeVisible();
 expect(screen.getByRole('heading',{name:'Compare Plans',hidden:true})).not.toBeVisible();
 expect(screen.queryByRole('button',{name:/pay|checkout|subscribe/i})).not.toBeInTheDocument();
});
it('does not represent Beta operator budgets as a purchased monthly subscription',()=>{
 state.data=fixture(false);render(<UsageOverview selectedPlan="growth"/>);
 expect(screen.getByRole('heading',{name:'Current Beta operator limits'})).toBeVisible();
 expect(screen.queryByRole('heading',{name:'Your subscription allowances'})).not.toBeInTheDocument();
 expect(screen.getByText('$149',{selector:'.commercial-price'})).toBeVisible();
 expect(screen.getByRole('button',{name:/Choose Growth/})).toBeVisible();
 expect(screen.queryByRole('link',{name:/Choose Growth/})).not.toBeInTheDocument();
});
