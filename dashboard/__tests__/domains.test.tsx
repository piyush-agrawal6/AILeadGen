import {it,expect,vi,beforeEach} from 'vitest';
import {render,screen,fireEvent} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {DomainSettings} from '@/components/workspaces/domains';
import {request} from '@/lib/intelligence';
vi.mock('@/lib/intelligence',()=>({request:vi.fn()}));
const call=vi.mocked(request);
function mount(){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><DomainSettings/></QueryClientProvider>)}
beforeEach(()=>vi.resetAllMocks());
it('shows the one-time DNS proof and retains it when verification fails',async()=>{
 call.mockImplementation(async(path,options)=>{
  if(path.endsWith('/verify'))throw new Error('DNS is temporarily unavailable. Retry later.');
  if(options?.method==='POST')return {id:'owned-record',domain:'example.com',record_type:'TXT',record_name:'_heysow-verify.example.com',record_value:'heysow-verification=controlled-one-time-proof',expires_at:'2026-12-01T00:00:00Z'} as never;
  return {items:[],can_edit:true} as never;
 });
 mount();fireEvent.change(await screen.findByLabelText('Company domain'),{target:{value:'example.com'}});
 fireEvent.click(screen.getByRole('button',{name:'Create verification record'}));
 expect(await screen.findByLabelText('Record value')).toHaveValue('heysow-verification=controlled-one-time-proof');
 fireEvent.click(screen.getByRole('button',{name:'Check DNS record'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('DNS is temporarily unavailable.');
 expect(screen.getByLabelText('Record value')).toHaveValue('heysow-verification=controlled-one-time-proof');
 expect(screen.queryByText(/^Domain ownership verified\./)).not.toBeInTheDocument();
});
it('displays verified history to a viewer without mutation controls',async()=>{
 call.mockResolvedValue({items:[{id:'owned-record',domain:'example.com',status:'VERIFIED',verified_at:'2026-11-06T00:00:00Z'}],can_edit:false});
 mount();expect(await screen.findByText('example.com')).toBeVisible();
 expect(screen.queryByRole('button',{name:'Create verification record'})).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Revoke verification'})).not.toBeInTheDocument();
 expect(screen.queryByLabelText('Record value')).not.toBeInTheDocument();
});
it('distinguishes a missing TXT record from proven domain ownership',async()=>{
 call.mockImplementation(async(path)=>path.endsWith('/verify')?{status:'PENDING'} as never:{items:[{id:'owned-record',domain:'example.com',status:'PENDING',verified_at:null}],can_edit:true} as never);
 mount();fireEvent.click(await screen.findByRole('button',{name:'Check ownership'}));
 expect(await screen.findByRole('status')).toHaveTextContent('The matching TXT record was not found yet.');
 expect(screen.queryByText(/^Domain ownership verified\./)).not.toBeInTheDocument();
});
