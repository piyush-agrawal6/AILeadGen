"use client";
import {useRef,useState} from 'react';
import {useQuery,useQueryClient} from '@tanstack/react-query';
import {request} from '@/lib/intelligence';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
import {CompanyAutofill} from './company-autofill';
import {companyDraft,companyFieldLabels,type CompanyFields,type CompanyProfile} from './company-profile-types';
const fields:[keyof Pick<CompanyFields,'name'|'website'|'industry'|'company_size'|'country'|'city'|'timezone'|'contact_email'>,string][]=[['name','text'],['website','url'],['industry','text'],['company_size','text'],['country','text'],['city','text'],['timezone','text'],['contact_email','email']];
function ProfileForm({profile,onSaved,onDirty,onReload}:{profile:CompanyProfile;onSaved:(value:CompanyProfile)=>void;onDirty:(dirty:boolean)=>void;onReload:()=>void}){
 const [values,setValues]=useState<CompanyFields>(()=>companyDraft(profile)),[review,setReview]=useState<{review_id:string;reviewed_fields:string[]}|null>(null);
 const [pending,setPending]=useState(false),[error,setError]=useState<string|null>(null),form=useRef<HTMLFormElement>(null);
 function edit(patch:Partial<CompanyFields>){setValues(previous=>({...previous,...patch}));onDirty(true)}
 async function save(event:React.FormEvent){
  event.preventDefault();if(pending||!profile.can_edit)return;setPending(true);setError(null);
  try{const result=await request<CompanyProfile>('/organization/profile',{method:'PUT',body:JSON.stringify({...values,countries_served:values.countries_served.filter(Boolean),target_customers:values.target_customers.filter(Boolean),target_industries:values.target_industries.filter(Boolean),specialties:values.specialties.filter(Boolean),version:profile.version,...review})});onDirty(false);onSaved(result)}
  catch(reason){setError(reason instanceof Error?reason.message:'Company profile could not be saved.')}
  finally{setPending(false)}
 }
 return <><CompanyAutofill initialWebsite={profile.website} canEdit={profile.can_edit&&!pending} onManual={()=>form.current?.querySelector<HTMLInputElement>('#company-name')?.focus()} onApply={(patch,id,selected)=>{edit(patch);setReview({review_id:id,reviewed_fields:selected});form.current?.scrollIntoView({behavior:'smooth',block:'start'})}}/>
 <form ref={form} onSubmit={save} aria-label="Company profile" className="company-profile-form space-y-6">
  <div><h2 className="text-lg font-semibold">Company information</h2><p className="mt-2 text-sm text-muted-foreground">Review your details and save when ready. Domain ownership is verified separately.</p></div>
  {!profile.can_edit&&<p className="text-sm text-muted-foreground">You can view this profile. An owner or administrator can edit it.</p>}
  <fieldset disabled={pending||!profile.can_edit} className="grid gap-5 sm:grid-cols-2">
   <legend className="sr-only">Company information</legend>
   {fields.map(([key,type])=><div key={key} className="min-w-0 space-y-2"><label className="text-sm font-medium" htmlFor={'company-'+key}>{companyFieldLabels[key]}</label><Input id={'company-'+key} type={type} value={values[key]} required={key==='name'||key==='timezone'} minLength={key==='name'?2:undefined} maxLength={key==='website'?600:key==='contact_email'?254:key==='company_size'?60:key==='timezone'?80:key==='name'?120:100} onChange={e=>edit({[key]:e.target.value})}/></div>)}
   {(['description','positioning'] as const).map(key=><div key={key} className="space-y-2 sm:col-span-2"><label htmlFor={'company-'+key} className="text-sm font-medium">{companyFieldLabels[key]}</label><textarea id={'company-'+key} className="control min-h-28 w-full" maxLength={1000} value={values[key]} onChange={e=>edit({[key]:e.target.value})}/></div>)}
   {(['countries_served','target_customers','target_industries','specialties'] as const).map(key=><div key={key} className="space-y-2 sm:col-span-2"><label htmlFor={'company-'+key} className="text-sm font-medium">{companyFieldLabels[key]}</label><Input id={'company-'+key} value={values[key].join(', ')} onChange={e=>edit({[key]:e.target.value.split(',').map(value=>value.trim())})}/><p className="text-xs text-muted-foreground">Separate entries with commas.{key==='countries_served'?' These are your service regions, not prospect-targeting filters.':''}</p></div>)}
   <section className="space-y-4 sm:col-span-2" aria-label="Company products and services"><h3 className="text-sm font-medium">Products and services</h3><p className="text-xs text-muted-foreground">Describe your own offerings. These are shared with company setup; they do not change prospect qualification rules.</p>{values.products_services.map((service,index)=><div key={index} className="company-service-fields"><label className="field-group">Product or service name<Input value={service.name} required minLength={2} maxLength={120} onChange={e=>edit({products_services:values.products_services.map((item,i)=>i===index?{...item,name:e.target.value}:item)})}/></label><label className="field-group">Service category<Input value={service.category} maxLength={100} onChange={e=>edit({products_services:values.products_services.map((item,i)=>i===index?{...item,category:e.target.value}:item)})}/></label><label className="field-group sm:col-span-2">Service description<textarea className="control min-h-20" maxLength={1000} value={service.description} onChange={e=>edit({products_services:values.products_services.map((item,i)=>i===index?{...item,description:e.target.value}:item)})}/></label><Button type="button" variant="outline" onClick={()=>edit({products_services:values.products_services.filter((_,i)=>i!==index)})}>Remove offering {index+1}</Button></div>)}{profile.can_edit&&<Button type="button" variant="outline" disabled={values.products_services.length>=20} onClick={()=>edit({products_services:[...values.products_services,{name:'',category:'',description:''}]})}>Add offering</Button>}</section>
  </fieldset>
  {error&&<div className="space-y-2"><p role="alert" className="text-sm text-destructive">{error}</p><Button type="button" variant="outline" onClick={onReload}>Reload saved profile</Button></div>}
  {profile.can_edit&&<Button type="submit" disabled={pending}>{pending?'Saving…':'Save company profile'}</Button>}
 </form></>;
}
export function CompanyProfileSettings({embedded=false,onSaved,onDirty}:{embedded?:boolean;onSaved?:(value:CompanyProfile)=>void;onDirty?:(dirty:boolean)=>void}){
 const client=useQueryClient();const [saved,setSaved]=useState(false);
 const profile=useQuery({queryKey:['organization-profile'],queryFn:()=>request<CompanyProfile>('/organization/profile'),retry:false,refetchOnWindowFocus:false});
 return <section className="space-y-7">{!embedded&&<header><p className="page-eyebrow">Company settings</p><h1 className="mt-2 text-2xl font-semibold tracking-tight">Company profile</h1><p className="mt-2 max-w-2xl text-sm text-muted-foreground">Keep your company information, services and positioning together. Review every suggested change before saving.</p></header>}
  {profile.isPending?<p role="status">Loading company profile…</p>:profile.isError?<div role="alert"><p>Company information could not be loaded. Select a workspace or retry.</p><Button variant="outline" onClick={()=>profile.refetch()}>Retry profile</Button></div>:profile.data&&<ProfileForm key={profile.data.version||'new'} profile={profile.data} onDirty={dirty=>{if(dirty)setSaved(false);onDirty?.(dirty)}} onReload={()=>{onDirty?.(false);void profile.refetch()}} onSaved={value=>{client.setQueryData(['organization-profile'],value);void client.invalidateQueries({queryKey:['account-workspaces']});void client.invalidateQueries({queryKey:['onboarding-progress']});setSaved(true);onSaved?.(value)}}/>}
  {saved&&<p role="status" className="text-sm text-primary">Company profile saved.</p>}
 </section>;
}
