'use client';
import {useRef,useState} from 'react';
import {Button} from '@/components/ui/button';
import {request} from '@/lib/intelligence';
import {useRadarRead} from '../provider';

export type CrmState={configured:boolean;health:string;connection:null|{id:string;status:string;portal_id:string|null;scopes:string[];last_success_at:string|null}};
export function HubSpotConnection(){
  const q=useRadarRead<CrmState>('/hubspot'),[busy,setBusy]=useState(false),[error,setError]=useState('');const lock=useRef(false);
  const c=q.data?.connection;const [verified,setVerified]=useState('');
  async function verify(){if(!c||lock.current)return;lock.current=true;setBusy(true);setError('');setVerified('');try{const r=await request<{items:unknown[]}>('/intent-radar/hubspot/connections/'+c.id+'/pipelines');await q.refetch();setVerified(`Verified CRM access: ${r.items.length} deal pipelines.`)}catch(e){setError(e instanceof Error?e.message:'Verification unavailable.')}finally{lock.current=false;setBusy(false)}}
  async function change(disconnect:boolean){if(lock.current)return;lock.current=true;setBusy(true);setError('');try{
    if(disconnect&&c){await request('/intent-radar/hubspot/connections/'+c.id,{method:'DELETE'});await q.refetch();}
    else{const r=await request<{authorization_url:string}>('/intent-radar/hubspot/authorize',{method:'POST'});const u=new URL(r.authorization_url);if(u.origin!=='https://app.hubspot.com'||u.pathname!=='/oauth/authorize'||!u.searchParams.get('state'))throw Error('Invalid authorization URL');location.assign(u.href)}
  }catch(e){setError(e instanceof Error?e.message:'Connection failed.')}finally{lock.current=false;setBusy(false)}}
  if(q.isLoading)return <p role="status">Checking CRM connection…</p>;
  return <section className="mx-auto max-w-3xl space-y-3"><h1 className="text-2xl font-semibold">HubSpot</h1>{q.isError||!q.data?.configured?<p>Connection unavailable for this workspace.</p>:<><p>{c?.status==='CONNECTED'?`Authorized portal ${c.portal_id}`:c?.status==='REAUTH_REQUIRED'?'Reconnect required':'Not connected'}</p>{c?.status==='CONNECTED'&&<details><summary>Granted permissions</summary><ul>{c.scopes.map(s=><li key={s}>{s}</li>)}</ul></details>}<p className="text-sm">{q.data.health}</p><div className="flex flex-wrap gap-2">{c?.status==='CONNECTED'&&<Button variant="outline" disabled={busy} onClick={()=>void verify()}>Verify portal access</Button>}<Button disabled={busy} onClick={()=>void change(false)}>{c?.status==='CONNECTED'?'Reconnect':'Connect HubSpot'}</Button>{c&&c.status!=='DISCONNECTED'&&<Button variant="outline" disabled={busy} onClick={()=>void change(true)}>Disconnect workspace</Button>}</div>{c?.status==='DISCONNECTED'&&<p>Workspace access removed. Uninstall the app in HubSpot to revoke the portal grant.</p>}</>}{verified&&c?.status==='CONNECTED'&&<p role="status">{verified}</p>}{error&&<p role="alert">{error}</p>}</section>
}
