import {it,expect,vi,beforeEach} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {SheetExports} from '@/components/workspaces/sheet-exports';
import {request} from '@/lib/intelligence';
vi.mock('@/lib/intelligence',()=>({request:vi.fn(),label:(value:string)=>value.toLowerCase()}));
const calls=vi.mocked(request);
const draft={id:'owned-export',status:'DRAFT',row_count:1,columns:['Company','Website'],preview:[['Supplied company','https://controlled.example']],target_range:"'Companies'!A1:H2",spreadsheet_id:'controlled-sheet-id',review_digest:'a'.repeat(64),attempts:0,last_error_code:null,expires_at:'2026-11-08T00:00:00Z'};
function mount(){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><SheetExports connectionId="owned-connection"/></QueryClientProvider>)}
beforeEach(()=>{vi.resetAllMocks();calls.mockImplementation(async(path,options)=>{
 if(path.startsWith('/sales/lists'))return {items:path.includes('page=1&')?[{id:'owned-list',name:'Selected companies',member_count:1}]:[],total:1} as never;
 if(options?.method==='POST')return draft as never;
 return {items:[]} as never;
})});
it('prepares a snapshot and requires explicit overwrite confirmation before any write',async()=>{
 mount();fireEvent.change(await screen.findByLabelText('Company list'),{target:{value:'owned-list'}});fireEvent.change(screen.getByLabelText('Destination spreadsheet URL or ID'),{target:{value:'controlled-sheet-id'}});fireEvent.change(screen.getByLabelText('Destination tab title'),{target:{value:'Companies'}});
 fireEvent.click(screen.getByRole('button',{name:'Preview export'}));expect(await screen.findByText("Overwrite range: 'Companies'!A1:H2")).toBeVisible();
 const confirm=screen.getByRole('button',{name:'Confirm reviewed export'});expect(confirm).toBeDisabled();expect(calls.mock.calls.filter(([,options])=>options?.method==='POST')).toHaveLength(1);
 fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(confirm);
 await waitFor(()=>expect(calls).toHaveBeenCalledWith('/organization/integrations/sheets/exports/owned-export/approve',{method:'POST',body:JSON.stringify({review_digest:draft.review_digest,confirmation:'OVERWRITE_REVIEWED_RANGE'})}));
 expect(calls.mock.calls.some(([path])=>path.includes('email')||path.includes('discovery'))).toBe(false);
});
it('requires a fresh review before retrying an uncertain provider write',async()=>{
 calls.mockImplementation(async(path)=>path.startsWith('/sales/lists')?{items:[],total:0} as never:{items:[{...draft,status:'UNCERTAIN',attempts:1,last_error_code:'PROVIDER_OUTCOME_UNKNOWN'}]} as never);
 mount();expect(await screen.findByText(/An uncertain write may already have reached Google/)).toBeVisible();fireEvent.click(screen.getByRole('button',{name:'Review export'}));expect(screen.getByRole('button',{name:'Confirm reviewed export'})).toBeDisabled();
 expect(calls.mock.calls.every(([,options])=>!options?.method)).toBe(true);
});
