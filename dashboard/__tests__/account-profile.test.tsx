import {it,expect,vi,beforeEach} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {AccountProfileSettings} from '@/components/workspaces/account-profile';
import {request} from '@/lib/intelligence';
vi.mock('@/lib/intelligence',()=>({request:vi.fn()}));
const mocked=vi.mocked(request);
const profile={display_name:'Account Owner',job_title:'',phone:'',timezone:'UTC',locale:'en',email:'owner@example.test',version:'a'.repeat(64)};
function mount(){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><AccountProfileSettings/></QueryClientProvider>)}
beforeEach(()=>vi.resetAllMocks());
it('saves personal preferences without accepting an email or workspace selector',async()=>{
 mocked.mockResolvedValueOnce(profile).mockResolvedValueOnce({...profile,display_name:'Updated Owner',version:'b'.repeat(64)});mount();
 fireEvent.change(await screen.findByLabelText('Display name'),{target:{value:'Updated Owner'}});fireEvent.click(screen.getByRole('button',{name:'Save your profile'}));
 expect(await screen.findByRole('status')).toHaveTextContent('has been saved.');
 const payload=JSON.parse(String(mocked.mock.calls[1][1]?.body));expect(payload.email).toBeUndefined();expect(payload.organization_id).toBeUndefined();expect(payload.display_name).toBe('Updated Owner');
});
it('preserves an unsaved personal edit on conflict',async()=>{
 mocked.mockResolvedValueOnce(profile).mockRejectedValueOnce(new Error('Your profile changed. Reload it before saving.'));mount();
 fireEvent.change(await screen.findByLabelText('Display name'),{target:{value:'Unsaved Name'}});fireEvent.click(screen.getByRole('button',{name:'Save your profile'}));
 await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent('profile changed.'));expect(screen.getByLabelText('Display name')).toHaveValue('Unsaved Name');expect(screen.getByRole('button',{name:'Reload your profile'})).toBeVisible();
});
