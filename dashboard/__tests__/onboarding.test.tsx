import {it,expect,vi,beforeEach} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {OnboardingSettings} from '@/components/workspaces/onboarding';
import {request} from '@/lib/intelligence';
vi.mock('@/lib/intelligence',()=>({request:vi.fn()}));
const mocked=vi.mocked(request);
const progress={revision:3,current_step:'REVIEW',objectives:['BUILD_LISTS'],services:[{name:'Engineering',category:'',description:''}],default_icp_id:'owned',preferences:{geography_mode:'GLOBAL',countries:[],geography_confirmed:true,integrations_skipped:true,start_discovery:false},status:'IN_PROGRESS',can_edit:true};
function mount(){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><OnboardingSettings/></QueryClientProvider>)}
beforeEach(()=>vi.resetAllMocks());
it('resumes review and completes only the saved revision without discovery or sending',async()=>{
 mocked.mockImplementation(async(path,options)=>path==='/organization/profile'?{name:'Controlled company',version:'saved'}:path==='/organization/icps/owned'?{id:'owned',name:'Customers',status:'ACTIVE'}:options?.method==='POST'?{status:'COMPLETED',discovery_started:false,outreach_started:false}:progress);
 mount();fireEvent.click(await screen.findByRole('button',{name:'Finish setup'}));
 expect(await screen.findByText('Setup is complete. No discovery or outreach has started.')).toBeVisible();
 const mutation=mocked.mock.calls.find(([,options])=>options?.method==='POST');
 expect(mutation?.[0]).toBe('/organization/onboarding/complete');expect(JSON.parse(String(mutation?.[1]?.body))).toEqual({revision:3});
 expect(mocked.mock.calls.every(([path])=>path.startsWith('/organization/'))).toBe(true);
});
it('retains draft choices when saved progress conflicts',async()=>{
 mocked.mockImplementation(async(path,options)=>{if(options?.method==='PUT')throw new Error('Setup changed. Reload your saved progress before saving.');return path==='/organization/profile'?{name:'Controlled company',version:'saved'}:path==='/organization/icps/owned'?{id:'owned',name:'Customers',status:'ACTIVE'}:{...progress,current_step:'OBJECTIVES'}});
 mount();fireEvent.click(await screen.findByLabelText('Find potential customers'));fireEvent.click(screen.getByRole('button',{name:'Save and continue'}));
 await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent('Setup changed.'));
 expect(screen.getByLabelText('Find potential customers')).toBeChecked();
 const mutation=mocked.mock.calls.find(([,options])=>options?.method==='PUT');const body=JSON.parse(String(mutation?.[1]?.body));expect(body.can_edit).toBeUndefined();expect(body.status).toBeUndefined();expect(body.revision).toBe(3);
});
