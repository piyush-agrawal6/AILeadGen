import {describe,it,expect,vi,beforeEach} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {CompanyProfileSettings} from '@/components/workspaces/company-profile';
import {request} from '@/lib/intelligence';
vi.mock('@/lib/intelligence',()=>({request:vi.fn()}));
const mocked=vi.mocked(request);
const profile={organization_id:'owned',version:'one',name:'Controlled Engineering',website:'https://controlled.example.com',description:'Existing description',industry:'Engineering',company_size:'',country:'United Kingdom',city:'Bristol',timezone:'Europe/London',contact_email:'contact@controlled.example.com',countries_served:['United Kingdom'],can_edit:true,onboarding_status:'COMPLETED'};
function mount(){const client=new QueryClient({defaultOptions:{queries:{retry:false}}});render(<QueryClientProvider client={client}><CompanyProfileSettings/></QueryClientProvider>)}
beforeEach(()=>vi.resetAllMocks());
describe('company profile settings',()=>{
 it('saves the exact edited fields and version without posting workspace ownership',async()=>{
  mocked.mockResolvedValueOnce(profile).mockResolvedValueOnce({...profile,name:'Updated Engineering',version:'two'});
  mount();fireEvent.change(await screen.findByLabelText('Company name'),{target:{value:'Updated Engineering'}});fireEvent.click(screen.getByRole('button',{name:'Save company profile'}));
  expect(await screen.findByRole('status')).toHaveTextContent('Company profile saved.');
  const call=mocked.mock.calls.find(([path,options])=>path==='/organization/profile'&&options?.method==='PUT');
  const payload=JSON.parse(String(call?.[1]?.body));expect(payload.name).toBe('Updated Engineering');expect(payload.version).toBe('one');expect(payload.organization_id).toBeUndefined();expect(payload.can_edit).toBeUndefined();
 });
 it('keeps viewer controls disabled and does not offer a save action',async()=>{
  mocked.mockResolvedValueOnce({...profile,can_edit:false});mount();expect(await screen.findByLabelText('Company name')).toBeDisabled();expect(screen.queryByRole('button',{name:'Save company profile'})).not.toBeInTheDocument();
 });
 it('preserves edits on conflict and provides an explicit reload action',async()=>{
  mocked.mockResolvedValueOnce(profile).mockRejectedValueOnce(new Error('Company profile changed. Reload it before saving.'));
  mount();fireEvent.change(await screen.findByLabelText('Company name'),{target:{value:'Unsaved owner edit'}});fireEvent.click(screen.getByRole('button',{name:'Save company profile'}));
  await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent('Company profile changed.'));expect(screen.getByLabelText('Company name')).toHaveValue('Unsaved owner edit');expect(screen.getByRole('button',{name:'Reload saved profile'})).toBeVisible();
 });
});
