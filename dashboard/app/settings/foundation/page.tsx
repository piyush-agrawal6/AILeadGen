"use client";
import {useEffect,useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {request} from '@/lib/intelligence';
type Pitch={enabled:boolean;minimum_score:number;minimum_findings:number;required_evidence:string[]};
type Config={reuse_windows:Record<string,number>;sender:Record<string,string>;report:{company_description:string;why_planebyte:string[];cta:string;signature_tagline:string;service_labels:Record<string,string>;include_seo:boolean;include_security:boolean;include_validation:boolean};pitches:Record<string,Pitch>};
export default function Foundation(){
 const q=useQuery({queryKey:['foundation-settings'],queryFn:()=>request<Config>('/foundation/settings')}),me=useQuery({queryKey:['my-role'],queryFn:()=>request<{role:string}>('/foundation/me')});
 const [value,setValue]=useState<Config|null>(null),[message,setMessage]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>{if(q.data)setValue(q.data)},[q.data]);
 if(!value)return <p role={q.error?'alert':'status'}>{q.error?.message||'Loading approved settings…'}</p>;
 const sender=(k:string,v:string)=>setValue({...value,sender:{...value.sender,[k]:v}});
 async function save(){setBusy(true);setMessage('');try{await request('/foundation/settings',{method:'PUT',body:JSON.stringify(value)});setMessage('Settings saved. Existing campaign snapshots are preserved; no automation was activated.');await q.refetch()}catch(e){setMessage(e instanceof Error?e.message:'Settings could not be saved.')}finally{setBusy(false)}}
 return <main className="space-y-8"><header><h1 className="text-2xl font-semibold">Foundation Settings</h1><p className="mt-2 text-sm text-muted-foreground">Internal sender settings and company-information reuse defaults. Credentials remain in server configuration.</p></header>
 <section id="analysis" className="space-y-4"><h2 className="text-lg font-semibold">Analysis Reuse</h2><p className="text-xs text-muted-foreground">A fresh result is reused only when lightweight evidence and relevant analyzer settings also match. New campaigns capture these windows permanently.</p><div className="grid gap-4 sm:grid-cols-3">{Object.entries(value.reuse_windows).filter(([key])=>['contacts','crawl'].includes(key)).map(([k,n])=><label className="text-xs" key={k}>{k} · days<input type="number" min={1} max={90} className="control mt-2 w-full" value={n} onChange={e=>setValue({...value,reuse_windows:{...value.reuse_windows,[k]:Number(e.target.value)}})}/></label>)}</div></section>
 <section id="sender" className="space-y-4"><h2 className="text-lg font-semibold">Sender Identity</h2><div className="grid gap-4 sm:grid-cols-2">{Object.entries(value.sender).map(([k,v])=><label className="text-xs" key={k}>{k.replaceAll('_',' ')}<input className="control mt-2 w-full" value={v} readOnly={k==='company'} maxLength={k==='website'?500:254} onChange={e=>sender(k,e.target.value)}/></label>)}</div><p className="text-xs text-muted-foreground">The SMTP account and sender address are unchanged by these fields.</p></section>
 <button type="button" className="control ops-primary" disabled={busy||me.data?.role!=='OWNER'} onClick={()=>void save()}>{busy?'Saving…':'Save Approved Settings'}</button>{me.data?.role!=='OWNER'&&<p className="text-xs">These critical settings require the workspace owner.</p>}{message&&<p role="status" className="text-sm">{message}</p>}</main>
}
