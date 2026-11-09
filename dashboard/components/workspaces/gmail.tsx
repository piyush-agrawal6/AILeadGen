"use client";
import {useEffect,useRef,useState} from 'react';
import Link from 'next/link';
import {useQuery,useQueryClient} from '@tanstack/react-query';
import {request} from '@/lib/intelligence';
import {Button} from '@/components/ui/button';
type Connection={id:string;revision:number;account_id:string|null;email_address:string|null;status:string;last_success_at:string|null};
type Connections={items:Connection[];can_connect:boolean;configured:boolean};
type Policy={revision:number;max_hour:number;max_day:number;sending_approved:number;can_approve:boolean};
export function GmailSettings(){
 const state=useQuery({queryKey:['customer-gmail'],queryFn:()=>request<Connections>('/email/gmail'),retry:false});
 const policy=useQuery({queryKey:['customer-mail-policy'],queryFn:()=>request<Policy>('/email/gmail/policy'),retry:false});
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [hour,setHour]=useState<number|null>(null),[day,setDay]=useState<number|null>(null);
 const connection=state.data?.items[0];
 async function act(action:'connect'|'disconnect'|'health'|'sync'|'retry'|'approve'|'disable'){
  if(busy)return;setBusy(true);setError('');setNotice('');
  try{
   if(action==='connect'){
    const result=await request<{authorization_url:string}>('/email/gmail/authorize',{method:'POST'}),url=new URL(result.authorization_url);
    if(url.protocol!=='https:'||url.hostname!=='accounts.google.com'||url.pathname!=='/o/oauth2/v2/auth')throw new Error('Gmail authorization could not be started securely.');
    window.location.assign(url.href);return;
   }
   if(action==='approve'||action==='disable'){
    if(!policy.data)throw new Error('Load the current sending policy first.');
    await request('/email/gmail/policy',{method:'PUT',body:JSON.stringify({revision:policy.data.revision,max_hour:hour??policy.data.max_hour,max_day:day??policy.data.max_day,confirmation:action==='approve'?'APPROVE_SENDING':'DISABLE_SENDING'})});
    setNotice(action==='approve'?'Workspace sending approval saved. Platform controls and a reviewed preview are still required for every message.':'Workspace sending approval removed.');
   }else{
    if(!connection)throw new Error('Connect your Gmail account first.');
    const path=action==='sync'?'/email/sync':'/email/gmail/'+connection.id+(action==='health'?'/health':action==='retry'?'/sync-retry':'');
    const result=await request<{status?:string}>(path,{method:action==='disconnect'?'DELETE':'POST',...(action==='retry'?{body:JSON.stringify({revision:connection.revision,confirmation:'RETRY_SYNC'})}:{})});
    setNotice(action==='disconnect'?'Mailbox disconnected locally; tokens and sending approval were removed. Historical conversations were retained.':action==='health'?'Mailbox connection verified. No email was sent.':result.status==='SYNCED'?'Bounded inbox synchronization completed.':'Inbox synchronization was deferred. Check the connection or explicitly retry the saved cursor.');
   }
   await Promise.all([state.refetch(),policy.refetch()]);
  }catch(reason){setError(reason instanceof Error?reason.message:'The Gmail operation could not be completed.');}
  finally{setBusy(false)}
 }
 return <section aria-label="Workspace Gmail" className="space-y-5 rounded-lg border p-5"><header><h2 className="text-lg font-semibold">Workspace Gmail</h2><p className="mt-2 text-sm text-muted-foreground">Connect your own verified Google mailbox to this workspace. Sign-in alone does not connect Gmail. Existing internal mailboxes are never used as a customer sender.</p></header>
 {state.isPending?<p role="status">Loading Gmail connection…</p>:state.isError?<p role="alert">Gmail connections are unavailable in this workspace.</p>:<>
 <p className="text-sm">{connection?.email_address||'No customer mailbox connected'} · {connection?.status.replaceAll('_',' ').toLowerCase()||'not connected'}</p>
 {!state.data?.configured&&<p className="text-sm">Gmail needs approved server configuration before you can connect.</p>}
 {state.data?.can_connect?<div className="flex flex-wrap gap-3"><Button disabled={busy||!state.data.configured} onClick={()=>void act('connect')}>{connection?'Reconnect your Gmail':'Connect your Gmail'}</Button>{connection&&connection.status!=='DISCONNECTED'&&<Button variant="outline" disabled={busy} onClick={()=>void act('disconnect')}>Disconnect Gmail</Button>}{connection?.status==='CONNECTED'&&<><Button variant="outline" disabled={busy} onClick={()=>void act('health')}>Check Gmail health</Button><Button variant="outline" disabled={busy} onClick={()=>void act('sync')}>Sync owned replies</Button><Button variant="outline" disabled={busy} onClick={()=>void act('retry')}>Retry saved inbox sync</Button></>}</div>:<p className="text-sm text-muted-foreground">Only the mailbox owner, with an owner or administrator workspace role, can operate this connection.</p>}
 {policy.data&&<div className="space-y-3 border-t pt-4"><p className="text-sm">Workspace sending approval: {policy.data.sending_approved?'approved':'disabled'}. Limits: {policy.data.max_hour}/hour, {policy.data.max_day}/day.</p>{policy.data.can_approve&&<><div className="grid gap-3 sm:grid-cols-2"><label className="text-sm">Hourly mailbox limit<input className="control mt-2 w-full" type="number" min={1} max={10} value={hour??policy.data.max_hour} onChange={event=>setHour(Number(event.target.value))} disabled={busy}/></label><label className="text-sm">Daily mailbox limit<input className="control mt-2 w-full" type="number" min={1} max={100} value={day??policy.data.max_day} onChange={event=>setDay(Number(event.target.value))} disabled={busy}/></label></div><Button variant="outline" disabled={busy||!connection||connection.status!=='CONNECTED'} onClick={()=>void act(policy.data!.sending_approved?'disable':'approve')}>{policy.data.sending_approved?'Remove sending approval':'Approve reviewed workspace sending'}</Button></>}<p className="text-xs text-muted-foreground">Reconnecting removes prior sending approval. Campaigns require an explicit mailbox route, every send requires a reviewed preview, and uncertain outcomes are never automatically resent.</p></div>}
 </>}{notice&&<p role="status" className="text-sm">{notice}</p>}{error&&<p role="alert" className="text-sm text-destructive">{error}</p>}</section>;
}
export function GmailCallback(){
 const started=useRef(false),cache=useQueryClient(),[message,setMessage]=useState('Verifying this Gmail connection…'),[failed,setFailed]=useState(false);
 useEffect(()=>{
  if(started.current)return;started.current=true;
  const params=new URLSearchParams(window.location.search),state=params.get('state'),code=params.get('code');
  window.history.replaceState(null,'',window.location.pathname);
  if(!state||!code||params.has('error')){setFailed(true);setMessage('Gmail authorization was canceled or is unavailable. Start a new connection from workspace integrations.');return;}
  void request('/email/gmail/connect',{method:'POST',body:JSON.stringify({state,code})}).then(async()=>{await cache.invalidateQueries({queryKey:['customer-gmail']});setMessage('Your workspace Gmail is connected. No email was sent and workspace sending remains unapproved.');}).catch(()=>{setFailed(true);setMessage('The Gmail connection could not be completed for this account and workspace. Start a new connection; no credentials are shown.');});
 },[cache]);
 return <section className="mx-auto max-w-2xl space-y-5"><h1 className="text-2xl font-semibold">Workspace Gmail connection</h1><p role={failed?'alert':'status'}>{message}</p><Link href="/settings/integrations" className="text-primary underline">Return to workspace integrations</Link></section>;
}
