import {beforeEach,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {GmailSettings,GmailCallback} from '@/components/workspaces/gmail';
import {PlanForm} from '@/components/workflows/mailbox-plan';
import {initialPlan} from '@/components/workflows/types';
import {request} from '@/lib/intelligence';
vi.mock('@/lib/intelligence',()=>({request:vi.fn()}));
vi.mock('@/components/workflows/plan-form',()=>({PlanForm:()=> <p>Campaign plan fields</p>}));
const calls=vi.mocked(request);
const connection={id:'owned-connection',revision:1,account_id:'gmail-owned',email_address:'customer@example.test',status:'CONNECTED',last_success_at:null};
function mount(child:React.ReactNode){return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>{child}</QueryClientProvider>)}
beforeEach(()=>{vi.resetAllMocks();window.history.replaceState({},'','/')});
it('keeps mailbox operations unavailable to viewers and approval separate from connection',async()=>{
 calls.mockImplementation(async(path)=>path.endsWith('/policy')?{revision:0,max_hour:5,max_day:50,sending_approved:0,can_approve:false} as never:{items:[connection],configured:true,can_connect:false} as never);
 mount(<GmailSettings/>);
 expect(await screen.findByText(/Only the mailbox owner/)).toBeVisible();
 expect(screen.queryByRole('button',{name:'Disconnect Gmail'})).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Approve reviewed workspace sending'})).not.toBeInTheDocument();
 expect(calls.mock.calls.every(([,options])=>!options?.method)).toBe(true);
});
it('disconnects the owned connection while retaining conversation history',async()=>{
 let disconnected=false;
 calls.mockImplementation(async(path,options)=>{
  if(options?.method==='DELETE'){disconnected=true;return {status:'DISCONNECTED'} as never;}
  if(path.endsWith('/policy'))return {revision:0,max_hour:5,max_day:50,sending_approved:0,can_approve:true} as never;
  return {items:[{...connection,status:disconnected?'DISCONNECTED':'CONNECTED'}],configured:true,can_connect:true} as never;
 });
 mount(<GmailSettings/>);fireEvent.click(await screen.findByRole('button',{name:'Disconnect Gmail'}));
 expect(await screen.findByText(/Historical conversations were retained/)).toBeVisible();
 expect(calls).toHaveBeenCalledWith('/email/gmail/owned-connection',{method:'DELETE'});
 expect(calls.mock.calls.every(([path])=>!path.includes('/send'))).toBe(true);
});
it('records explicit owner sending approval using the current policy revision',async()=>{
 calls.mockImplementation(async(path)=>path.endsWith('/policy')?{revision:7,max_hour:3,max_day:25,sending_approved:0,can_approve:true} as never:{items:[connection],configured:true,can_connect:true} as never);
 mount(<GmailSettings/>);fireEvent.click(await screen.findByRole('button',{name:'Approve reviewed workspace sending'}));
 expect(await screen.findByText(/Workspace sending approval saved/)).toBeVisible();
 expect(calls).toHaveBeenCalledWith('/email/gmail/policy',{method:'PUT',body:JSON.stringify({revision:7,max_hour:3,max_day:25,confirmation:'APPROVE_SENDING'})});
});
it('removes OAuth callback secrets before its single scoped exchange and never sends mail',async()=>{
 const state='hsw_'+'a'.repeat(43);window.history.replaceState({},'','/settings/integrations/gmail-callback?state='+state+'&code=synthetic-code');
 calls.mockResolvedValue({status:'CONNECTED'});mount(<GmailCallback/>);
 expect(await screen.findByText(/Your workspace Gmail is connected/)).toBeVisible();
 expect(window.location.search).toBe('');expect(calls).toHaveBeenCalledTimes(1);
 expect(calls).toHaveBeenCalledWith('/email/gmail/connect',{method:'POST',body:JSON.stringify({state,code:'synthetic-code'})});
 expect(screen.getByRole('link',{name:'Return to workspace integrations'})).toHaveAttribute('href','/settings/integrations');
});
it('shows safe cancellation without submitting a failed OAuth grant',async()=>{
 window.history.replaceState({},'','/settings/integrations/gmail-callback?error=private-provider-error');mount(<GmailCallback/>);
 expect(await screen.findByRole('alert')).not.toHaveTextContent('private-provider-error');expect(calls).not.toHaveBeenCalled();
});
it('routes a chosen campaign explicitly before adding the owned account to the run',async()=>{
 const change=vi.fn(),value={...initialPlan(),kind:'OUTREACH' as const,campaign_id:'chosen-campaign'};
 calls.mockResolvedValue({id:'gmail-owned',provider:'gmail_oauth',email_address:'customer@example.test'});
 mount(<PlanForm value={value} onChange={change}/>);
 expect(await screen.findByText('customer@example.test')).toBeVisible();expect(change).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Route selected campaign to this mailbox'}));
 await waitFor(()=>expect(change).toHaveBeenCalledWith({...value,account_id:'gmail-owned'}));
 expect(calls).toHaveBeenCalledWith('/email/campaigns/chosen-campaign/mailbox',{method:'PUT',body:JSON.stringify({account_id:'gmail-owned'})});
 expect(calls.mock.calls.every(([path])=>!path.includes('/send'))).toBe(true);
});
it('reports deferred inbox work honestly and retries the saved cursor only on an explicit click',async()=>{
 calls.mockImplementation(async(path,options)=>{
  if(path==='/email/sync')return {status:'RETRY_DEFERRED'} as never;
  if(path.endsWith('/sync-retry'))return {status:'SYNCED'} as never;
  return path.endsWith('/policy')?{revision:0,max_hour:5,max_day:50,sending_approved:0,can_approve:false} as never:{items:[connection],configured:true,can_connect:true} as never;
 });
 mount(<GmailSettings/>);fireEvent.click(await screen.findByRole('button',{name:'Sync owned replies'}));
 expect(await screen.findByText(/Inbox synchronization was deferred/)).toBeVisible();
 expect(calls.mock.calls.some(([path])=>path.endsWith('/sync-retry'))).toBe(false);
 fireEvent.click(screen.getByRole('button',{name:'Retry saved inbox sync'}));
 expect(await screen.findByText('Bounded inbox synchronization completed.')).toBeVisible();
 expect(calls).toHaveBeenCalledWith('/email/gmail/owned-connection/sync-retry',{method:'POST',body:JSON.stringify({revision:1,confirmation:'RETRY_SYNC'})});
});
