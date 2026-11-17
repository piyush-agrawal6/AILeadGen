import {it,expect,vi,beforeEach} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {AIOnboarding} from '@/components/workspaces/onboarding-ai';
import {request} from '@/lib/intelligence';
vi.mock('@/lib/intelligence',()=>({request:vi.fn()}));
vi.mock('@/components/workspaces/use-workspace',()=>({useWorkspace:()=>({data:{active_organization_id:'owned'}})}));
vi.mock('@/components/workspaces/use-products',()=>({useProducts:()=>({data:{intent_radar:{enabled:false}}})}));
const mocked=vi.mocked(request);
const profile={organization_id:'owned',version:'saved',can_edit:true,onboarding_status:'IN_PROGRESS',name:'Manual company',website:'https://example.com',description:'Reviewed engineering',industry:'Software',company_size:'',country:'',city:'',timezone:'',contact_email:'',countries_served:[],target_customers:[],target_industries:[],specialties:[],positioning:'',products_services:[{name:'Engineering',category:'',description:''}]};
const progress={revision:1,current_step:'COMPANY',objectives:['RESEARCH_MARKETS'],services:profile.products_services,default_icp_id:null,preferences:{setup_mode:'MANUAL',company_review_id:null,icp_review_id:null,research_keywords:[],excluded_keywords:[]},status:'IN_PROGRESS',can_edit:true};
function mount(state:unknown){mocked.mockImplementation(async(path)=>path.endsWith('/assistant-context')?state:path==='/billing/subscription'?{enabled:true,required:true,active:false,can_manage:true,plans:[{code:'starter',name:'Starter',monthly_minor:5900,audience:'Starter',limits:null}],trial_blockers:['Controlled test: no checkout initiated'],terms_version:'approved-test'}:path.includes('/reviews/')?(state as {reviews:{company:unknown}}).reviews.company:{items:[]});render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}})}><AIOnboarding/></QueryClientProvider>)}
beforeEach(()=>vi.resetAllMocks());
it('keeps invited read-only members out of company editing and assistant actions',async()=>{mount({progress:{...progress,can_edit:false},company:{...profile,can_edit:false},reviews:{},capabilities:{company_analysis:false,icp_recommendations:false}});expect(await screen.findByText('Your workspace owner is preparing this company')).toBeVisible();expect(screen.queryByRole('button',{name:'Approve company profile'})).not.toBeInTheDocument();expect(screen.queryByRole('textbox')).not.toBeInTheDocument();expect(mocked.mock.calls.every(([,options])=>!options?.method)).toBe(true)});
it('rejecting a previously accepted AI section removes its unapproved values',async()=>{mount({progress:{...progress,preferences:{...progress.preferences,company_review_id:'review'}},company:profile,reviews:{company:{id:'review',status:'READY',preview:{suggestions:{name:'Proposed company'}},can_retry:false}},capabilities:{company_analysis:true,icp_recommendations:true}});fireEvent.click(await screen.findByRole('button',{name:'Accept this section'}));expect(screen.getByRole('textbox',{name:'Company name'})).toHaveValue('Proposed company');fireEvent.click(screen.getByRole('button',{name:'Reject suggestions'}));expect(screen.getByRole('textbox',{name:'Company name'})).toHaveValue('Manual company');expect(mocked.mock.calls.every(([,options])=>!options?.method)).toBe(true)});
it('completing setup cannot advertise a product without verified enrollment',async()=>{mount({progress:{...progress,status:'COMPLETED'},company:profile,reviews:{},capabilities:{company_analysis:false,icp_recommendations:false}});expect(await screen.findByRole('heading',{name:'Your reviewed context is saved'})).toBeVisible();await waitFor(()=>expect(screen.getByRole('link',{name:'Open workspace settings →'})).toBeVisible());expect(screen.queryByRole('link',{name:'Discover conversations'})).not.toBeInTheDocument()});
it('stops failed analysis and preserves editable saved context on a worker storage failure',async()=>{mount({progress:{...progress,preferences:{...progress.preferences,company_review_id:'failed-review'}},company:profile,reviews:{company:{id:'failed-review',status:'FAILED',progress_stage:'FAILED',error_code:'SETUP_STORAGE_UNAVAILABLE',preview:null,can_retry:true}},capabilities:{company_analysis:true,icp_recommendations:true}});expect(await screen.findAllByText('Analysis did not complete')).toHaveLength(2);expect(screen.getAllByText(/worker could not access required storage/)).toHaveLength(2);expect(screen.queryByRole('button',{name:'Cancel'})).not.toBeInTheDocument();expect(screen.getByRole('textbox',{name:'Company name'})).toHaveValue('Manual company');expect(mocked.mock.calls.every(([,options])=>!options?.method)).toBe(true)});

it('restores all five steps, persistent desktop Copilot and an accessible mobile drawer',async()=>{
 mount({progress,company:profile,reviews:{},capabilities:{company_analysis:true,icp_recommendations:true}});
 const rail=await screen.findByRole('navigation',{name:'Onboarding Progress'});
 for(const name of ['Your Business','Business Profile','Ideal Customers','Research Setup','Plan & Payment'])expect(rail).toHaveTextContent(name);
 expect(screen.getByRole('complementary')).toHaveClass('ai-copilot-container');
 fireEvent.click(screen.getByRole('button',{name:'Open AI Copilot'}));
 expect(await screen.findByRole('dialog',{name:'PlaneByte AI Copilot'})).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'Close AI Copilot'}));
 await waitFor(()=>expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
});

it('resumes completed research at mandatory real billing without a local activation bypass',async()=>{
 const state={payment:{required:true,active:false},progress:{...progress,status:'COMPLETED'},company:profile,reviews:{},capabilities:{company_analysis:true,icp_recommendations:true}};
 mount(state);
 expect(await screen.findByRole('heading',{name:'Choose Your Plan & Payment'})).toBeVisible();
 expect(screen.queryByRole('heading',{name:'Your reviewed context is saved'})).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:/Finish setup.*enter workspace/})).not.toBeInTheDocument();
 expect(mocked.mock.calls.some(([path])=>path==='/billing/subscription')).toBe(true);
 expect(mocked.mock.calls.every(([,options])=>!options?.method)).toBe(true);
});

it('terminates failed Copilot guidance and retries the same owned job without discarding the draft',async()=>{
 const state={progress,company:profile,reviews:{},capabilities:{company_analysis:true,icp_recommendations:true}};
 let retried=false;
 const failed={id:'advice-owned',status:'FAILED',progress_stage:'FAILED',error_code:'AI_OUTPUT_TRUNCATED',can_retry:true,preview:null};
 mocked.mockImplementation(async(path,options)=>{
  if(path.endsWith('/assistant-context'))return state;
  if(path.endsWith('/assistant'))return {mode:'AI guidance',job:failed};
  if(path.endsWith('/control')){expect(JSON.parse(String(options?.body))).toEqual({action:'RETRY'});retried=true;return {status:'QUEUED'}}
  if(path.endsWith('/reviews/advice-owned'))return retried?{...failed,status:'READY',can_retry:false,preview:{answer:'Reviewed guidance based on the saved engineering offering.'}}:failed;
  return {items:[]};
 });
 render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}})}><AIOnboarding/></QueryClientProvider>);
 fireEvent.change(await screen.findByRole('textbox',{name:'Company name'}),{target:{value:'Unsaved manual edit'}});
 fireEvent.change(screen.getByRole('textbox',{name:'Ask Copilot about your business'}),{target:{value:'Explain our offering'}});
 fireEvent.click(screen.getByRole('button',{name:'Send question to Copilot'}));
 expect(await screen.findByText(/provider stopped before completing its structured response/)).toBeVisible();
 expect(screen.queryByText('Thinking and consulting workspace context…')).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Retry guidance'}));
 expect(await screen.findByText('Reviewed guidance based on the saved engineering offering.')).toBeVisible();
 expect(screen.getByRole('textbox',{name:'Company name'})).toHaveValue('Unsaved manual edit');
 expect(mocked.mock.calls.filter(([path])=>path.endsWith('/assistant'))).toHaveLength(1);
 expect(mocked.mock.calls.some(([path])=>path.endsWith('/website-reviews/advice-owned/control'))).toBe(true);
});
