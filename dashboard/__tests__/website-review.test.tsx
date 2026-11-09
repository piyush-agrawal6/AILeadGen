import {it,expect,vi,beforeEach} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {WebsiteReview} from '@/components/workspaces/website-review';
import {request} from '@/lib/intelligence';
vi.mock('@/lib/intelligence',()=>({request:vi.fn()}));
const mocked=vi.mocked(request);
const review={id:'review-one',website:'https://example.com',status:'READY',can_retry:false,error_code:null,preview:{suggestions:{name:'Public company',description:'Public description'},sources:{name:{url:'https://example.com',kind:'STRUCTURED_DATA'},description:{url:'https://example.com',kind:'WEBSITE_METADATA'}},source_url:'https://example.com',retrieved_at:'2026-11-05T00:00:00Z',ownership_verified:false,pages_reviewed:1}};
function mount(){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><WebsiteReview/></QueryClientProvider>)}
beforeEach(()=>vi.resetAllMocks());
it('applies only explicitly selected and edited fields with the saved profile version',async()=>{
 mocked.mockImplementation(async(path,options)=>path==='/organization/profile'?{name:'Original',version:'before',can_edit:true}:path.endsWith('/confirm')?{name:'Owner edited company',version:'after',can_edit:true}:review);
 mount();fireEvent.change(await screen.findByLabelText('Public company website'),{target:{value:'https://example.com'}});fireEvent.click(screen.getByRole('button',{name:'Review website'}));
 fireEvent.click(await screen.findByLabelText('Apply company name'));fireEvent.change(screen.getByLabelText('Company name'),{target:{value:'Owner edited company'}});fireEvent.click(screen.getByRole('button',{name:'Confirm selected fields'}));
 expect(await screen.findByText('Selected fields saved.')).toBeVisible();
 const call=mocked.mock.calls.find(([path])=>path.endsWith('/confirm'));expect(JSON.parse(String(call?.[1]?.body))).toEqual({profile_version:'before',fields:{name:'Owner edited company'}});
 expect(mocked.mock.calls.every(([path])=>path.startsWith('/organization/'))).toBe(true);
});
it('retains edited evidence and selection after a profile conflict',async()=>{
 mocked.mockImplementation(async(path)=>{if(path.endsWith('/confirm'))throw new Error('Company profile changed.');return path==='/organization/profile'?{name:'Original',version:'before',can_edit:true}:review});
 mount();fireEvent.change(await screen.findByLabelText('Public company website'),{target:{value:'https://example.com'}});fireEvent.click(screen.getByRole('button',{name:'Review website'}));
 fireEvent.click(await screen.findByLabelText('Apply company name'));fireEvent.change(screen.getByLabelText('Company name'),{target:{value:'Unsaved edit'}});fireEvent.click(screen.getByRole('button',{name:'Confirm selected fields'}));
 await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent('Company profile changed.'));expect(screen.getByLabelText('Company name')).toHaveValue('Unsaved edit');expect(screen.getByLabelText('Apply company name')).toBeChecked();
});
