import {it,expect,vi,beforeEach} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {ICPSettings} from '@/components/workspaces/icp-builder';
import {request} from '@/lib/intelligence';
vi.mock('@/lib/intelligence',()=>({request:vi.fn()}));
const mocked=vi.mocked(request);
const status={enabled:true,configured:true,can_generate:true,requests_used_today:0,daily_limit:10,period_timezone:'UTC'};
const draft={name:'Dental clinics in India',description:'',status:'INACTIVE',criteria:{company:{industries:['dental clinics'],countries:['India']},contact:{},intent:{}}};
function mount(){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><ICPSettings/></QueryClientProvider>)}
beforeEach(()=>vi.resetAllMocks());
it('opens generated criteria for editing without automatically saving or searching',async()=>{
 mocked.mockImplementation(async(path)=>path.endsWith('/ai-status')?status:path.endsWith('/interpret')?{draft,review_required:true}:{items:[],total:0,can_edit:true});
 mount();fireEvent.click(await screen.findByText('Describe your ideal customers'));fireEvent.change(screen.getByLabelText('Your targeting instructions'),{target:{value:'Find dental clinics in India.'}});fireEvent.click(screen.getByRole('button',{name:'Generate criteria draft'}));
 expect(await screen.findByLabelText('Profile name')).toHaveValue(draft.name);expect(screen.getByLabelText('Countries')).toHaveValue('India');expect(screen.getByLabelText('Profile status')).toHaveValue('INACTIVE');
 expect(mocked.mock.calls.filter(([,options])=>options?.method==='POST').map(([path])=>path)).toEqual(['/organization/icps/interpret']);
 fireEvent.change(screen.getByLabelText('Profile name'),{target:{value:'Owner edited segment'}});expect(screen.getByLabelText('Profile name')).toHaveValue('Owner edited segment');
});
it('keeps the manual builder available when assisted generation is unavailable',async()=>{
 mocked.mockImplementation(async(path)=>{if(path.endsWith('/interpret'))throw new Error('Daily AI criteria limit reached.');return path.endsWith('/ai-status')?status:{items:[],total:0,can_edit:true}});
 mount();fireEvent.click(await screen.findByText('Describe your ideal customers'));fireEvent.change(screen.getByLabelText('Your targeting instructions'),{target:{value:'Find dental clinics in India.'}});fireEvent.click(screen.getByRole('button',{name:'Generate criteria draft'}));
 await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent('Daily AI criteria limit reached.'));
 fireEvent.click(screen.getByRole('button',{name:'New targeting profile'}));expect(screen.getByLabelText('Profile name')).toHaveValue('');
});
