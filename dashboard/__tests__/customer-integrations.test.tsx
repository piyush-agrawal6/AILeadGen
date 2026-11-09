import {it,expect,vi,beforeEach} from 'vitest';
import {render,screen,fireEvent} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {IntegrationSettings} from '@/components/workspaces/integrations';
import Callback from '@/app/acquisition/sheets/callback/page';
import {request} from '@/lib/intelligence';
vi.mock('@/lib/intelligence',()=>({request:vi.fn()}));
vi.mock('next/navigation',()=>({useRouter:()=>({push:vi.fn()})}));
const calls=vi.mocked(request);
const connection={id:'owned-connection',provider:'GOOGLE_SHEETS',status:'CONNECTED',last_success_at:null,last_error_code:null};
function mount(){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><IntegrationSettings/></QueryClientProvider>)}
beforeEach(()=>{vi.resetAllMocks();window.history.replaceState({},'','/')});

it('shows a truthful unavailable state without a connect button when secure setup is missing',async()=>{
 calls.mockResolvedValue({items:[],can_manage:true,google_sheets_configured:false});mount();
 expect(await screen.findByText(/Workspace connections need secure server setup/)).toBeVisible();
 expect(screen.queryByRole('button',{name:/Connect Google Sheets/})).not.toBeInTheDocument();
 expect(calls.mock.calls.every(([,options])=>!options?.method)).toBe(true);
});
it('keeps provider access and connection mutations unavailable to viewers',async()=>{
 calls.mockResolvedValue({items:[connection],can_manage:false,google_sheets_configured:true});mount();
 expect(await screen.findByText('An owner or administrator can manage this connection.')).toBeVisible();
 expect(screen.queryByLabelText('Spreadsheet URL or ID')).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Disconnect from this workspace'})).not.toBeInTheDocument();
});
it('reads chosen spreadsheet metadata and disconnects only the current workspace',async()=>{
 let disconnected=false;
 calls.mockImplementation(async(path,options)=>{
  if(options?.method==='DELETE'){disconnected=true;return {status:'DISCONNECTED',provider_access_revoked:false} as never}
  if(path.includes('/sheets?'))return {title:'Controlled business sheet',tabs:[{title:'Companies',sheetId:1}]} as never;
  return {items:[{...connection,status:disconnected?'DISCONNECTED':'CONNECTED'}],can_manage:true,google_sheets_configured:true} as never;
 });
 mount();fireEvent.change(await screen.findByLabelText('Spreadsheet URL or ID'),{target:{value:'controlled-spreadsheet'}});
 fireEvent.click(screen.getByRole('button',{name:'Check spreadsheet access'}));
 expect(await screen.findByRole('status')).toHaveTextContent('Spreadsheet access confirmed.');
 expect(screen.getByText('Companies',{exact:true})).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'Disconnect from this workspace'}));
 expect(await screen.findByText('Disconnected from this workspace. The Google account authorization is unchanged.')).toBeVisible();
 expect(calls.mock.calls.some(([path,options])=>path==='/organization/integrations/owned-connection'&&options?.method==='DELETE')).toBe(true);
 expect(calls.mock.calls.every(([path])=>path.startsWith('/organization/integrations'))).toBe(true);
});
it('routes workspace OAuth to its scoped API and clears the callback query before exchange',async()=>{
 const state='hsw_'+'a'.repeat(43);window.history.replaceState({},'','/acquisition/sheets/callback?state='+state+'&code=controlled-code');
 calls.mockResolvedValue({status:'CONNECTED'});render(<Callback/>);
 expect(await screen.findByText('Google Sheets connected with read-only access.')).toBeVisible();
 expect(window.location.search).toBe('');
 expect(calls).toHaveBeenCalledWith('/organization/integrations/google-sheets/connect',{method:'POST',body:JSON.stringify({code:'controlled-code',state})});
 expect(screen.getByRole('link',{name:'Return to workspace connections'})).toHaveAttribute('href','/settings/integrations');
});
it('preserves the existing internal callback route and never starts discovery',async()=>{
 window.history.replaceState({},'','/acquisition/sheets/callback?state=internal-controlled-state&code=controlled-code');
 calls.mockResolvedValue({status:'CONNECTED'});render(<Callback/>);
 expect(await screen.findByText('Google Sheets connected with read-only access.')).toBeVisible();
 expect(calls.mock.calls[0][0]).toBe('/acquisition/sheets/connect');
 expect(calls.mock.calls).toHaveLength(1);
});

it('stages a customer sheet in the shared review form without importing automatically',async()=>{
 const staged={id:'staged-customer-sheet',source_type:'GOOGLE_SHEETS',status:'MAPPING_REVIEW',origin:{filename:'Controlled sheet.csv'},manifest:{headers:['Company','Email'],sample:[['Controlled company','public@controlled.example']],sheet:'Companies',sheets:['Companies'],row_count:1,file_format:'GOOGLE_SHEETS'},counts:{}};
 calls.mockImplementation(async(path)=>{
  if(path==='/acquisition/settings')return {features:{import:true,sheets:true}} as never;
  if(path.endsWith('/mapping/suggest'))return {mapping:{company_name:'Company',email:'Email'},method:'HEADER_SUGGESTION',warning:null} as never;
  if(path.endsWith('/sheets/import'))return staged as never;
  if(path.includes('/sheets?'))return {title:'Controlled sheet',tabs:[{title:'Companies',sheetId:1}]} as never;
  return {items:[connection],can_manage:true,google_sheets_configured:true,google_sheets_import_enabled:true} as never;
 });
 mount();fireEvent.change(await screen.findByLabelText('Spreadsheet URL or ID'),{target:{value:'controlled-spreadsheet'}});fireEvent.click(screen.getByRole('button',{name:'Check spreadsheet access'}));fireEvent.click(await screen.findByRole('button',{name:'Review spreadsheet import'}));
 expect(await screen.findByRole('heading',{name:'Review spreadsheet mapping'})).toBeVisible();expect(await screen.findByRole('button',{name:'Import Leads'})).toBeDisabled();expect(screen.getByLabelText('Approve import mapping')).not.toBeChecked();
 expect(calls.mock.calls.some(([path])=>path==='/organization/integrations/owned-connection/sheets/import')).toBe(true);
 expect(calls.mock.calls.some(([path])=>path.endsWith('/approve'))).toBe(false);expect(calls.mock.calls.some(([path])=>path.startsWith('/acquisition/sheets/'))).toBe(false);
});
