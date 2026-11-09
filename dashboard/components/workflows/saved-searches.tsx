"use client";
import {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {request} from '@/lib/intelligence';
import type {Plan} from './types';
type Saved={id:string;name:string;revision:number;configuration:Partial<Plan>};
export function SavedSearches({value,onChange}:{value:Plan;onChange:(plan:Plan)=>void}){
 const [page,setPage]=useState(1),[selected,setSelected]=useState<Saved|null>(null),[name,setName]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false);
 const q=useQuery({queryKey:['discovery-saved-searches',page],queryFn:()=>request<{items:Saved[];total:number}>('/discovery/searches?page='+page)});
 const me=useQuery({queryKey:['my-role'],queryFn:()=>request<{role:string}>('/foundation/me')});
 const writable=me.data?.role!=='VIEWER';
 function load(saved:Saved){setSelected(saved);setName(saved.name);setMessage('Search loaded as a draft. Review it before starting.');onChange({...value,...saved.configuration,kind:'SCAN',name:saved.name,request_id:crypto.randomUUID(),email_all_eligible:false});}
 async function action(kind:'save'|'update'|'duplicate'|'archive'){
  setBusy(true);setMessage('');try{
   if(kind==='archive'&&selected){await request('/discovery/searches/'+selected.id+'/archive',{method:'POST',body:JSON.stringify({revision:selected.revision})});setSelected(null);setName('');setMessage('Search archived. Runs and company history are preserved.');}
   else {const path=kind==='update'&&selected?'/discovery/searches/'+selected.id:kind==='duplicate'&&selected?'/discovery/searches/'+selected.id+'/duplicate':'/discovery/searches';const saved=await request<Saved>(path,{method:kind==='update'?'PUT':'POST',body:JSON.stringify({name:name.trim(),configuration:value,request_id:crypto.randomUUID(),revision:kind==='update'?selected?.revision:undefined})});setSelected(saved);setName(saved.name);setMessage('Search saved. No discovery was started.');}
   await q.refetch();
  }catch(error){setMessage(error instanceof Error?error.message:'Search could not be saved.');}finally{setBusy(false);}
 }
 return <section className="rounded-xl border bg-card p-5 space-y-4" aria-label="Saved discovery searches"><div><h2 className="font-semibold">Saved searches</h2><p className="mt-1 text-xs text-muted-foreground">Reuse targeting and ICP settings. Loading or saving never starts a job.</p></div>{q.error&&<p role="alert">{q.error.message}</p>}<label className="field-label block">Load saved search<select aria-label="Load saved search" className="control mt-2 w-full" value={selected?.id||''} onChange={e=>{const item=q.data?.items.find(item=>item.id===e.target.value);if(item)load(item);else{setSelected(null);setName('')}}}><option value="">Choose a saved search</option>{q.data?.items.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select></label>{q.data&&q.data.total>25&&<div className="flex items-center gap-3 text-xs"><button className="control" disabled={page===1} onClick={()=>setPage(page-1)}>Previous searches</button><span>Page {page} · {q.data.total} searches</span><button className="control" disabled={page*25>=q.data.total} onClick={()=>setPage(page+1)}>Next searches</button></div>}<div className="flex flex-wrap gap-2"><label className="field-label min-w-40 flex-1">Search name<input aria-label="Search name" className="control mt-2 w-full" maxLength={120} value={name} onChange={e=>setName(e.target.value)}/></label><button type="button" className="control self-end" disabled={busy||!name.trim()||!writable} onClick={()=>void action('save')}>Save as new search</button>{selected&&<><button type="button" className="control self-end" disabled={busy||!name.trim()||!writable} onClick={()=>void action('update')}>Update search</button><button type="button" className="control self-end" disabled={busy||!name.trim()||!writable} onClick={()=>void action('duplicate')}>Duplicate search</button><button type="button" className="control self-end" disabled={busy||!writable} onClick={()=>void action('archive')}>Archive search</button></>}</div>{message&&<p role="status" className="text-sm">{message}</p>}</section>;
}
