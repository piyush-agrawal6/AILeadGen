import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {AIOnboarding} from '@/components/workspaces/onboarding-ai';
import {request} from '@/lib/intelligence';
import real from './fixtures/onboarding-vertex-20261117.json';
vi.mock('@/lib/intelligence',()=>({request:vi.fn()}));
vi.mock('@/components/workspaces/use-workspace',()=>({useWorkspace:()=>({data:{active_organization_id:'contract-workspace'}})}));
vi.mock('@/components/workspaces/use-products',()=>({useProducts:()=>({data:{intent_radar:{enabled:false}}})}));

it('reviews actual Vertex fields, saves five actual recommendations, answers contextually and reaches verified payment',async()=>{
 const ids=Array.from({length:5},()=>crypto.randomUUID());
 const empty={...real.savedCompany,organization_id:'contract-workspace',version:null,name:'Fresh workspace',description:'',industry:'',website:'',positioning:'',specialties:[],target_customers:[],target_industries:[],countries_served:[],products_services:[]};
 let saved=empty as unknown as typeof real.savedCompany,approved=false,finished=false;
 const progress={revision:1,current_step:'COMPANY',objectives:['UNDERSTAND_CUSTOMER_NEEDS'],services:[],default_icp_id:null as string|null,preferences:{setup_mode:'AI',company_review_id:real.websiteReview.id,icp_review_id:null as string|null,research_keywords:[],excluded_keywords:[]},status:'IN_PROGRESS',can_edit:true};
 const posted:Record<string,unknown>[]=[];
 vi.mocked(request).mockImplementation(async(path,options)=>{
  const body=options?.body?JSON.parse(String(options.body)):undefined;
  if(body)posted.push({path,...body});
  if(path.endsWith('/assistant-context'))return {payment:{required:true,active:false},progress,company:saved,reviews:{company:real.websiteReview},capabilities:{company_analysis:true,icp_recommendations:true}};
  if(path.includes('/reviews/'))return path.endsWith(real.websiteReview.id)?real.websiteReview:path.endsWith(real.icpReview.id)?real.icpReview:real.copilotReview;
  if(path.includes('/icps?'))return {items:approved?ids.map((id,i)=>({id,name:real.icpReview.preview.candidates[i].draft.name,status:'ACTIVE'})):[]};
  if(path.endsWith('/company')){saved={...body.profile,organization_id:'contract-workspace',version:'reviewed-version',can_edit:true,onboarding_status:'IN_PROGRESS'};return {company:saved,progress:{...progress,revision:2,current_step:'ICP'}}}
  if(path.endsWith('/recommendations'))return {review:real.icpReview,progress:{...progress,revision:3,current_step:'ICP',preferences:{...progress.preferences,icp_review_id:real.icpReview.id}}};
  if(path.endsWith('/accept-profiles')){expect(body.candidates).toHaveLength(5);expect(new Set(body.candidates.map((c:{name:string})=>c.name)).size).toBe(5);approved=true;return {profiles:ids.map(id=>({id})),progress:{...progress,revision:4,current_step:'REVIEW',default_icp_id:ids[0]}}}
  if(path.endsWith('/assistant'))return {mode:'AI guidance · review required',job:real.copilotReview};
  if(path.endsWith('/finish')){expect(body.primary_icp_id).toBe(ids[0]);finished=true;return {status:'COMPLETED'}}
  if(path==='/billing/subscription')return {enabled:true,required:true,active:false,can_manage:true,terms_version:'approved-test',plans:[{code:'starter',name:'Starter',monthly_minor:5900,audience:'Starter',limits:null}],trial_blockers:['Contract replay does not initiate payments']};
  throw new Error('Unexpected API request: '+path);
 });
 render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}})}><AIOnboarding/></QueryClientProvider>);
 expect(real.provenance.provider).toBe('VERTEX_AI');
 await waitFor(()=>expect(screen.getByRole('textbox',{name:'Company name'})).toHaveValue('PlaneByte'));
 expect(screen.getByRole('textbox',{name:'Company description'})).toHaveValue(real.websiteReview.preview.suggestions.description);
 expect(screen.getByRole('textbox',{name:'Business positioning'})).toHaveValue(real.websiteReview.preview.suggestions.positioning);
 expect(screen.getAllByDisplayValue('Intent Radar')).toHaveLength(1);
 expect(screen.getAllByDisplayValue('Growth Intelligence')).toHaveLength(1);
 expect(screen.queryByText('View quoted evidence')).not.toBeInTheDocument();
 expect(screen.queryByText('Analysis details')).not.toBeInTheDocument();
 fireEvent.change(screen.getByRole('textbox',{name:'Company description'}),{target:{value:'Owner-reviewed description: '+real.websiteReview.preview.suggestions.description}});
 fireEvent.click(screen.getByRole('button',{name:/Save business profile & continue/}));
 for(const item of real.icpReview.preview.candidates)expect(await screen.findByText(item.draft.name,{exact:true})).toBeVisible();
 expect(saved.description).toMatch(/^Owner-reviewed description:/);
 fireEvent.click(screen.getByRole('button',{name:'Open AI Copilot'}));
 fireEvent.change(screen.getByRole('textbox',{name:'Ask Copilot about your business'}),{target:{value:'Which saved offerings fit our primary segment?'}});
 fireEvent.click(screen.getByRole('button',{name:'Send question to Copilot'}));
 await waitFor(()=>expect(document.querySelector('.ai-copilot-messages')).toHaveTextContent(real.copilotReview.preview.answer.replace(/\s+/g,' ').trim()));
 fireEvent.click(screen.getByRole('button',{name:'Close AI Copilot'}));
 fireEvent.click(screen.getByRole('button',{name:/Save ideal customers & continue/}));
 fireEvent.click(await screen.findByRole('button',{name:/Save research setup & continue/}));
 expect(await screen.findByRole('heading',{name:'Choose Your Plan & Payment'})).toBeVisible();
 expect(finished).toBe(true);
 expect(screen.queryByRole('heading',{name:'Your reviewed context is saved'})).not.toBeInTheDocument();
 expect(posted.some(v=>v.path==='/billing/subscription/checkout')).toBe(false);
});
