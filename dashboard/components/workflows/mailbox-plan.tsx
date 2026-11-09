"use client";
import {useState} from 'react';
import Link from 'next/link';
import {useQuery} from '@tanstack/react-query';
import {request} from '@/lib/intelligence';
import {Button} from '@/components/ui/button';
import {PlanForm as Fields} from './plan-form';
import type {Plan} from './types';
export function PlanForm({value,onChange}:{value:Plan;onChange:(value:Plan)=>void}){
 const account=useQuery({queryKey:['email-account'],queryFn:()=>request<{id:string;provider:string;email_address:string}>('/email/account'),enabled:value.kind==='OUTREACH',retry:false});
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[routed,setRouted]=useState<string|null>(null);
 const mailbox=account.data?.provider==='gmail_oauth'?account.data:null;
 async function route(){
  if(busy||!mailbox||!value.campaign_id)return;setBusy(true);setError('');
  try{await request('/email/campaigns/'+encodeURIComponent(value.campaign_id)+'/mailbox',{method:'PUT',body:JSON.stringify({account_id:mailbox.id})});setRouted(value.campaign_id);onChange({...value,account_id:mailbox.id});}
  catch(reason){setError(reason instanceof Error?reason.message:'The campaign mailbox route could not be saved.');}finally{setBusy(false)}
 }
 return <div className="space-y-5"><Fields value={value} onChange={next=>onChange({...next,account_id:next.campaign_id===value.campaign_id?value.account_id:null})}/>{value.kind==='OUTREACH'&&mailbox&&<section className="space-y-3 rounded-lg border p-4"><h2 className="font-semibold">Customer sending mailbox</h2><p className="text-sm">{mailbox.email_address}</p><p className="text-xs text-muted-foreground">Route the selected campaign to your own workspace Gmail, then review each prepared message. This action sends no email.</p><Button variant="outline" disabled={busy||!value.campaign_id} onClick={()=>void route()}>{routed===value.campaign_id?'Mailbox route saved':'Route selected campaign to this mailbox'}</Button><Link href="/settings/integrations" className="block text-xs text-primary underline">Gmail connection and sending approval</Link>{error&&<p role="alert" className="text-sm">{error}</p>}</section>}</div>;
}
