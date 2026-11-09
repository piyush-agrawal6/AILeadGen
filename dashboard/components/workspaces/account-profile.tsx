"use client";
import {useState} from 'react';
import {useQuery,useQueryClient} from '@tanstack/react-query';
import {request} from '@/lib/intelligence';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';

type Fields={display_name:string;job_title:string;phone:string;timezone:string;locale:string};
type Profile=Fields&{email:string;version:string};
const fields:[keyof Fields,string,number][]=[['display_name','Display name',120],['job_title','Job title',120],['phone','Phone number',50],['timezone','Your timezone',80],['locale','Language and region code',35]];
function Form({profile,onSaved,onReload}:{profile:Profile;onSaved:(value:Profile)=>void;onReload:()=>void}){
 const [values,setValues]=useState<Fields>({display_name:profile.display_name,job_title:profile.job_title,phone:profile.phone,timezone:profile.timezone,locale:profile.locale}),[pending,setPending]=useState(false),[error,setError]=useState('');
 async function save(event:React.FormEvent){event.preventDefault();if(pending)return;setPending(true);setError('');try{const result=await request<Profile>('/profile',{method:'PUT',body:JSON.stringify({...values,version:profile.version})});onSaved(result)}catch(reason){setError(reason instanceof Error?reason.message:'Your profile could not be saved.')}finally{setPending(false)}}
 return <form onSubmit={save} className="space-y-6"><div><p className="text-sm font-medium">Google account</p><p className="mt-1 break-all text-sm text-muted-foreground">{profile.email}</p><p className="mt-1 text-xs text-muted-foreground">Your sign-in email is verified by Google and cannot be changed here.</p></div><fieldset disabled={pending} className="grid gap-5 sm:grid-cols-2"><legend className="sr-only">Your personal profile</legend>{fields.map(([key,label,max])=><div className="space-y-2" key={key}><label htmlFor={'profile-'+key} className="text-sm font-medium">{label}</label><Input id={'profile-'+key} value={values[key]} maxLength={max} type={key==='phone'?'tel':'text'} required={['display_name','timezone','locale'].includes(key)} onChange={e=>setValues({...values,[key]:e.target.value})}/>{key==='timezone'&&<p className="text-xs text-muted-foreground">For example: Asia/Kolkata or Europe/London.</p>}{key==='locale'&&<p className="text-xs text-muted-foreground">For example: en, en-IN or fr-FR. This stores a preference; it does not translate the interface.</p>}</div>)}</fieldset><Button type="submit" disabled={pending}>{pending?'Saving…':'Save your profile'}</Button>{error&&<div className="space-y-3"><p role="alert" className="text-sm text-destructive">{error}</p><Button type="button" variant="outline" onClick={onReload}>Reload your profile</Button></div>}</form>;
}
export function AccountProfileSettings(){
 const client=useQueryClient(),[saved,setSaved]=useState(false);
 const profile=useQuery({queryKey:['personal-profile'],queryFn:()=>request<Profile>('/profile'),retry:false,refetchOnWindowFocus:false});
 return <section className="max-w-2xl space-y-6"><div><h1 className="text-2xl font-semibold">Your profile</h1><p className="mt-2 text-sm text-muted-foreground">Personal information for your account across workspaces. These preferences do not change company details, team roles or sending schedules.</p></div>{profile.isPending?<p role="status">Loading your profile…</p>:profile.isError?<div role="alert"><p>Your profile could not be loaded.</p><Button variant="outline" onClick={()=>void profile.refetch()}>Retry your profile</Button></div>:<Form key={profile.data.version} profile={profile.data} onReload={()=>{setSaved(false);void profile.refetch()}} onSaved={value=>{client.setQueryData(['personal-profile'],value);setSaved(true)}}/>}{saved&&<p role="status">Your profile has been saved.</p>}</section>;
}
