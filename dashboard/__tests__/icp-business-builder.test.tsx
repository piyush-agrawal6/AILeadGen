import {it,expect,vi,beforeEach} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {ICPSettings} from '@/components/workspaces/icp-builder';
import {request} from '@/lib/intelligence';
import {applyTargeting} from '@/components/workflows/icp-targeting';
import {initialPlan} from '@/components/workflows/types';
vi.mock('@/lib/intelligence',()=>({request:vi.fn()}));
const calls=vi.mocked(request);
const status={enabled:true,configured:true,can_generate:true,requests_used_today:0,daily_limit:10,period_timezone:'UTC'};
const draft={name:'Software teams',description:'Teams needing custom applications',status:'INACTIVE',criteria:{company:{industries:['Software'],countries:['GB'],revenue_currency:'USD'},contact:{job_titles:['CTO']},intent:{business_needs:['Custom applications']},weights:{'company.industries':5}}};
const candidate={draft,reason:'A recommended segment for the saved application engineering services.',assumptions:['CTOs are suggested buyers, not verified customers.'],based_on_services:['Custom applications']};
const proposal={proposal_id:'owned-proposal',candidates:[candidate,{...candidate,draft:{...draft,name:'Service businesses'}}],questions:['Which regions should be prioritized?'],changed_fields:[],source:'BUSINESS_PROFILE'};
function mount(){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><ICPSettings/></QueryClientProvider>)}
beforeEach(()=>vi.resetAllMocks());

it('shows meaningful creation choices without empty pagination and reviews three-method targeting safely',async()=>{
 calls.mockImplementation(async(path)=>path.endsWith('/ai-status')?status:path.endsWith('/suggest')?proposal:{items:[],total:0,can_edit:true});mount();
 fireEvent.click(await screen.findByRole('button',{name:'Generate My ICP'}));
 expect(await screen.findByText('Compare suggested audiences')).toBeVisible();expect(screen.getByText('Service businesses')).toBeVisible();
 expect(screen.queryByRole('button',{name:'Previous profiles'})).not.toBeInTheDocument();
 fireEvent.click(screen.getAllByRole('button',{name:'Review this profile'})[0]);
 expect(screen.getByLabelText('Profile name')).toHaveValue('Software teams');expect(screen.getByLabelText('Profile status')).toHaveValue('INACTIVE');
 expect(screen.getByText('Assumptions to review before saving')).toBeVisible();
 expect(calls.mock.calls.filter(([,options])=>options?.method==='POST').map(([path])=>path)).toEqual(['/organization/icps/suggest']);
});

it('refines the currently edited draft, shows changed fields, and saves only after explicit review',async()=>{
 calls.mockImplementation(async(path,options)=>{
  if(path.endsWith('/ai-status'))return status as never;
  if(path.endsWith('/suggest'))return proposal as never;
  if(path.endsWith('/refine'))return {...proposal,proposal_id:'refined-proposal',source:'AI_REFINED',candidates:[{...candidate,draft:{...draft,name:'Owner edited audience',criteria:{...draft.criteria,company:{...draft.criteria.company,countries:['Germany']}}}}],changed_fields:['criteria.company.countries']} as never;
  if(options?.method==='POST')return {...draft,id:'saved',revision:1,generation_source:'AI_REFINED'} as never;
  return {items:[],total:0,can_edit:true} as never;
 });mount();fireEvent.click(await screen.findByRole('button',{name:'Generate My ICP'}));fireEvent.click((await screen.findAllByRole('button',{name:'Review this profile'}))[0]);
 fireEvent.change(screen.getByLabelText('Profile name'),{target:{value:'Owner edited audience'}});fireEvent.click(screen.getByText('Refine this draft with AI'));
 fireEvent.change(screen.getByLabelText('Follow-up instructions'),{target:{value:'Focus on Germany.'}});fireEvent.click(screen.getByRole('button',{name:'Preview refinement'}));
 expect(await screen.findByText(/Refinement ready to review/)).toBeVisible();expect(screen.getByLabelText('Countries')).toHaveValue('Germany');
 const refinement=calls.mock.calls.find(([path])=>path.endsWith('/refine'));expect(JSON.parse(String(refinement?.[1]?.body)).draft.name).toBe('Owner edited audience');
 expect(calls.mock.calls.filter(([path,options])=>options?.method==='POST'&&path==='/organization/icps')).toHaveLength(0);
 fireEvent.click(screen.getByRole('button',{name:'Create targeting profile'}));await waitFor(()=>expect(calls.mock.calls.some(([path,options])=>path==='/organization/icps'&&options?.method==='POST')).toBe(true));
 const save=calls.mock.calls.find(([path,options])=>path==='/organization/icps'&&options?.method==='POST');const body=JSON.parse(String(save?.[1]?.body));expect(body.ai_proposal_id).toBe('refined-proposal');expect(body.status).toBe('INACTIVE');expect(body.criteria.weights['company.industries']).toBe(5);
});

it('preserves manual setup and company-profile fallback when AI cannot generate',async()=>{
 calls.mockImplementation(async(path)=>{if(path.endsWith('/suggest'))throw new Error('Add a business description or services to your company profile first.');return path.endsWith('/ai-status')?status:{items:[],total:0,can_edit:true}});mount();
 fireEvent.click(await screen.findByRole('button',{name:'Generate My ICP'}));expect(await screen.findByRole('alert')).toHaveTextContent('Add a business description');
 expect(screen.getByRole('link',{name:'Review company profile or analyze my website'})).toHaveAttribute('href','/settings/company');fireEvent.click(screen.getByRole('button',{name:'Create Manually'}));expect(screen.getByLabelText('Profile name')).toHaveValue('');
});

it('applies supported targeting without starting discovery or silently keeping an unrelated industry',()=>{
 const plan=initialPlan();const result=applyTargeting(plan,{profile:{id:'owned',name:'Software',revision:2,criteria:{company:{},contact:{}}},filters:{countries:['Germany'],cities:[],verticals:[],search_criteria:plan.search_criteria},warnings:[],post_discovery:[],requires_city_review:false});
 expect(result.countries).toEqual(['Germany']);expect(result.verticals).toEqual([]);expect(result.icp_id).toBe('owned');expect(result.request_id).toBe(plan.request_id);expect(calls).not.toHaveBeenCalled();
});
