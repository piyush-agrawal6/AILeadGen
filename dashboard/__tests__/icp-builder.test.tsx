import {it,expect,vi,beforeEach} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {ICPSettings} from '@/components/workspaces/icp-builder';
import {request} from '@/lib/intelligence';
vi.mock('@/lib/intelligence',()=>({request:vi.fn()}));
const mocked=vi.mocked(request);
const profile={id:'controlled',name:'Dental companies',description:'',status:'INACTIVE',revision:1,criteria:{company:{industries:['Dentistry'],revenue_currency:'USD'},contact:{},intent:{}}};
function mount(){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><ICPSettings/></QueryClientProvider>)}
beforeEach(()=>vi.resetAllMocks());
it('creates reviewed criteria without workspace ownership or scan/send actions',async()=>{
 mocked.mockImplementation(async(path,options)=>options?.method==='POST'?profile:{items:[],total:0,can_edit:true});
 mount();fireEvent.click(await screen.findByRole('button',{name:'New targeting profile'}));
 fireEvent.change(screen.getByLabelText('Profile name'),{target:{value:'Dental companies'}});
 fireEvent.change(screen.getByLabelText('Industries'),{target:{value:'Dentistry\n\n'}});
 fireEvent.click(screen.getByRole('button',{name:'Create targeting profile'}));
 expect(await screen.findByText('Targeting profile saved. No scan or email has been started.')).toBeVisible();
 const call=mocked.mock.calls.find(([,options])=>options?.method==='POST');const body=JSON.parse(String(call?.[1]?.body));
 expect(body.criteria.company.industries).toEqual(['Dentistry']);expect(body.status).toBe('INACTIVE');expect(body.organization_id).toBeUndefined();
 expect(mocked.mock.calls.every(([path])=>path.startsWith('/organization/icps'))).toBe(true);
});
it('keeps viewer criteria read-only and hides creation',async()=>{
 mocked.mockResolvedValue({items:[profile],total:1,can_edit:false});mount();fireEvent.click(await screen.findByRole('button',{name:'Open profile'}));
 await waitFor(()=>expect(screen.getByLabelText('Profile name')).toBeDisabled());
 expect(screen.queryByRole('button',{name:'New targeting profile'})).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'Save targeting profile'})).not.toBeInTheDocument();
});
