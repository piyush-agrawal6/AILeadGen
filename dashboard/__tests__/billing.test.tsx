import {act,render,screen,fireEvent,waitFor} from '@testing-library/react';
import {focusManager,QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {afterEach,expect,it,vi} from 'vitest';
import {BillingWorkspace} from '@/components/workspaces/billing';
import {planDestination} from '@/lib/plan-intent';
vi.mock('@/components/workspaces/use-products',()=>({useProducts:()=>({data:{organization_id:'controlled-workspace'}})}));
const response={mode:'test',provider_configured:false,webhook_configured:false,controlled_workspace:true,can_manage:true,checkout_available:false,public_checkout_enabled:false,plans:[{code:'starter',name:'Starter — internal test',amount:10000,currency:'INR',period:'monthly',internal_test_only:true,provider_plan_id:null,limits:{searches:20,ai_calls:10,ai_tokens:100000,monitors:3,team_members:1,api_requests:1000}}],subscriptions:[],usage:[],payments:[],plan_changes:'Cancel before switching test plans.'};
afterEach(()=>{vi.unstubAllGlobals();focusManager.setFocused(undefined);});
it('keeps marketing selections inert and rejects unknown products and return URLs',()=>{expect(planDestination('intent-radar','growth')).toBe('/billing?plan=growth');expect(planDestination('lead-engine','growth')).toBeNull();expect(planDestination('intent-radar','https://evil.example')).toBeNull();});
it('labels sandbox pricing, requires consent and blocks unconfigured checkout',async()=>{const fetch=vi.fn().mockResolvedValue(new Response(JSON.stringify(response),{headers:{'content-type':'application/json'}}));vi.stubGlobal('fetch',fetch);render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><BillingWorkspace selectedPlan="starter"/></QueryClientProvider>);expect(await screen.findByText('Starter — internal test')).toBeVisible();expect(screen.getByText(/No real money is collected/)).toBeVisible();const submit=screen.getByRole('button',{name:'Start test subscription'});expect(submit).toBeDisabled();fireEvent.click(screen.getByRole('checkbox'));expect(submit).toBeDisabled();expect(fetch.mock.calls.every(([,options])=>!options?.method||options.method==='GET')).toBe(true);});
it('does not open checkout for a known rejected creation and reloads provider state',async()=>{const ready={...response,provider_configured:true,checkout_available:true,plans:response.plans.map(p=>({...p,provider_plan_id:'plan_fixture'}))};const fetch=vi.fn(async(_url:string,options?:RequestInit)=>new Response(JSON.stringify(options?.method==='POST'?{id:'controlled-id',status:'REJECTED'}:ready),{headers:{'content-type':'application/json'}}));vi.stubGlobal('fetch',fetch);render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><BillingWorkspace/></QueryClientProvider>);await screen.findByText('Starter — internal test');fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(screen.getByRole('button',{name:'Start test subscription'}));await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent('No mandate was created'));expect(fetch.mock.calls.filter(([,o])=>o?.method==='POST')).toHaveLength(1);});

const active={id:'controlled-id',plan_code:'starter',mode:'test',status:'active',current_end:null,paid_end:null,settled_current_period:true,cancel_at_cycle_end:0,plan:response.plans[0]};
it('refreshes externally changed billing when the owner returns to the tab',async()=>{
 let changed=false;
 vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({...response,subscriptions:[{...active,status:changed?'pending':'active',settled_current_period:!changed}]}),{headers:{'content-type':'application/json'}})));
 const client=new QueryClient({defaultOptions:{queries:{retry:false,staleTime:600_000,refetchOnWindowFocus:false}}});
 render(<QueryClientProvider client={client}><BillingWorkspace/></QueryClientProvider>);
 expect(await screen.findByText(/Provider settlement verified/)).toBeVisible();
 changed=true;act(()=>{focusManager.setFocused(false);focusManager.setFocused(true);});
 expect(await screen.findByText(/Payment or provider verification pending/)).toBeVisible();
 expect(screen.queryByText(/Provider settlement verified/)).not.toBeInTheDocument();
 client.clear();
});
it('refreshes only this workspace entitlement cache after a billing action',async()=>{
 vi.stubGlobal('fetch',vi.fn(async(_url:string,options?:RequestInit)=>new Response(JSON.stringify(options?.method==='POST'?active:{...response,subscriptions:[active]}),{headers:{'content-type':'application/json'}})));
 const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
 client.setQueryData(['plane-products','controlled-workspace'],{enabled:true});client.setQueryData(['plane-products','other-workspace'],{enabled:true});
 render(<QueryClientProvider client={client}><BillingWorkspace/></QueryClientProvider>);
 fireEvent.click(await screen.findByRole('button',{name:'Check provider status'}));
 await waitFor(()=>expect(client.getQueryState(['plane-products','controlled-workspace'])?.isInvalidated).toBe(true));
 expect(client.getQueryState(['plane-products','other-workspace'])?.isInvalidated).toBe(false);
 client.clear();
});
