import {describe,it,expect,vi,beforeEach} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {CompanyProfileSettings} from '@/components/workspaces/company-profile';
import {CapabilityFeatures} from '@/components/workspaces/features';
import {request} from '@/lib/intelligence';
vi.mock('@/lib/intelligence',()=>({request:vi.fn()}));const mocked=vi.mocked(request);
const profile={organization_id:'owned',version:'v1',name:'Existing company',website:'https://example.com',description:'Owner description',industry:'',company_size:'',country:'',city:'',timezone:'UTC',contact_email:'',countries_served:[],target_customers:[],target_industries:[],specialties:[],positioning:'',products_services:[],can_edit:true,onboarding_status:'IN_PROGRESS'};
const preview={id:'review-owned',website:'https://example.com',status:'READY',progress_stage:'READY',can_retry:false,preview:{suggestions:{name:'Evidence company',description:'Published company information',products_services:[{name:'Engineering',category:'',description:''}]},sources:{name:{url:'https://example.com/about',kind:'AI_SUPPORTED_BY_PUBLIC_TEXT'}},evidence:{name:[{url:'https://example.com/about',quote:'Evidence company provides engineering.'}]},source_url:'https://example.com',retrieved_at:'2026-11-06T01:00:00Z',missing_fields:['timezone','company_size'],ownership_verified:false,pages_reviewed:2}};
function mount(){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><CapabilityFeatures.Provider value={{companyDiscovery:true}}><CompanyProfileSettings/></CapabilityFeatures.Provider></QueryClientProvider>)}
beforeEach(()=>{vi.resetAllMocks();HTMLElement.prototype.scrollIntoView=vi.fn();mocked.mockImplementation(async(path,options)=>path==='/organization/profile'?(options?.method==='PUT'?{...profile,...JSON.parse(String(options.body)),version:'v2'}:profile):path.endsWith('/capabilities')?{can_analyze:true,ai_enabled:true,configured:true,max_pages:5}:preview)});
describe('reviewed company AI auto-fill',()=>{
 it('only applies selected fields to the draft and requires a separate save with owned evidence',async()=>{
  mount();fireEvent.click(await screen.findByRole('button',{name:'Analyze Website with AI'}));
  await screen.findByRole('heading',{name:'Suggested company details'});expect(screen.getByLabelText('Company name',{exact:true})).toHaveValue('Existing company');
  fireEvent.click(screen.getByRole('checkbox',{name:/Company name/}));fireEvent.click(screen.getByRole('checkbox',{name:/Products and services/}));
  fireEvent.click(screen.getByRole('button',{name:/Apply Suggested Details/}));
  expect(screen.getByLabelText('Company name',{exact:true})).toHaveValue('Evidence company');expect(screen.getByLabelText('Company description',{exact:true})).toHaveValue('Owner description');
  expect(mocked.mock.calls.some(([,options])=>options?.method==='PUT')).toBe(false);
  expect(screen.getByText(/Not established:/).closest('p')).toHaveTextContent('Company timezone, Company size');
  fireEvent.click(screen.getByRole('button',{name:'Save company profile'}));await screen.findByText('Company profile saved.');
  const mutation=mocked.mock.calls.find(([path,options])=>path==='/organization/profile'&&options?.method==='PUT');const body=JSON.parse(String(mutation![1]!.body));
  expect(body.review_id).toBe('review-owned');expect(body.reviewed_fields).toEqual(['name','products_services']);expect(body.description).toBe('Owner description');expect(body.products_services[0].name).toBe('Engineering');expect(body.organization_id).toBeUndefined();
 });
 it('structures a no-website description without starting website discovery and keeps manual editing',async()=>{
  mount();fireEvent.click(await screen.findByRole('button',{name:'No website? Describe your business'}));
  fireEvent.change(screen.getByLabelText('Describe your business'),{target:{value:'We provide engineering services for international businesses.'}});
  fireEvent.click(screen.getByRole('button',{name:'Structure Business Details with AI'}));await screen.findByRole('heading',{name:'Suggested company details'});
  const mutation=mocked.mock.calls.find(([path,options])=>path==='/organization/website-reviews'&&options?.method==='POST');const body=JSON.parse(String(mutation![1]!.body));
  expect(body.source_kind).toBe('DESCRIPTION');expect(body.website).toBe('');expect(body.use_ai).toBe(true);expect(body.description).toContain('engineering services');
  fireEvent.click(screen.getByRole('button',{name:'Edit Manually'}));expect(screen.getByLabelText('Company name',{exact:true})).toHaveFocus();
 });
 it('shows provider failure safely and preserves an unsaved manual draft',async()=>{
  mocked.mockImplementation(async(path,options)=>path==='/organization/profile'?profile:path.endsWith('/capabilities')?{can_analyze:true,max_pages:5}:options?.method==='POST'?Promise.reject(new Error('AI unavailable. Please retry.')):preview);
  mount();fireEvent.change(await screen.findByLabelText('Company name',{exact:true}),{target:{value:'Unsaved manual company'}});fireEvent.click(await screen.findByRole('button',{name:'Analyze Website with AI'}));
  await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent('AI unavailable'));expect(screen.getByLabelText('Company name',{exact:true})).toHaveValue('Unsaved manual company');expect(screen.getByRole('button',{name:'Save company profile'})).toBeEnabled();
 });
 it('does not request AI capabilities or expose extraction actions to a viewer',async()=>{
  mocked.mockResolvedValue({...profile,can_edit:false});mount();await screen.findByLabelText('Company name',{exact:true});
  expect(screen.queryByRole('button',{name:'Analyze Website with AI'})).not.toBeInTheDocument();expect(mocked.mock.calls.map(([path])=>path)).toEqual(['/organization/profile']);
 });
});
