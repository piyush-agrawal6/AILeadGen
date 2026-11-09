"use client";
import {useRef,useState} from 'react';
import {request} from '@/lib/intelligence';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';

export function CreateWorkspace({onCreated}:{onCreated?:()=>void}){
 const [name,setName]=useState(''),[pending,setPending]=useState(false),[error,setError]=useState(''),[reused,setReused]=useState(false);
 const requestId=useRef<string|null>(null);
 async function submit(event:React.FormEvent){
  event.preventDefault();if(pending)return;setPending(true);setError('');
  requestId.current??=crypto.randomUUID();
  try{const result=await request<{reused:boolean}>('/organization/workspaces',{method:'POST',body:JSON.stringify({name:name.trim(),request_id:requestId.current})});if(result.reused){setReused(true);return}if(onCreated)onCreated();else window.location.assign('/onboarding')}
  catch(reason){setError(reason instanceof Error?reason.message:'Workspace could not be created. Retry with the same company name.')}
  finally{setPending(false)}
 }
 return <section className="max-w-xl space-y-6"><div><h1 className="text-2xl font-semibold">Create a workspace</h1><p className="mt-2 text-sm text-muted-foreground">Create a separate workspace for your company. You become its owner and can complete its company profile next.</p></div>{reused?<p role="status">This workspace was already created. Select it from the workspace menu to continue; your current selection has been preserved.</p>:<form onSubmit={submit} className="space-y-5"><div className="space-y-2"><label htmlFor="new-workspace-name" className="text-sm font-medium">Company name</label><Input id="new-workspace-name" required minLength={2} maxLength={120} value={name} disabled={pending} onChange={event=>{setName(event.target.value);requestId.current=null}}/></div><p className="text-sm text-muted-foreground">Your existing workspaces and records stay available through the workspace selector. Discovery and outreach remain unavailable in the new workspace until onboarding is complete.</p><Button type="submit" disabled={pending||!name.trim()}>{pending?'Creating workspace…':'Create workspace'}</Button>{error&&<p role="alert" className="text-sm text-destructive">{error}</p>}</form>}</section>;
}
