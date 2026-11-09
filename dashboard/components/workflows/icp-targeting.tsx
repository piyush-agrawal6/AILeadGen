"use client";
import Link from 'next/link';
import {useQuery} from '@tanstack/react-query';
import {request} from '@/lib/intelligence';
import type {Plan,SearchCriteria} from './types';
import {Button} from '@/components/ui/button';
export type TargetPreview={profile:{id:string;name:string;revision:number;criteria:{company:Record<string,string[]|number|null>;contact:Record<string,string[]>}};filters:{countries:string[];cities:string[];verticals:string[];search_criteria:SearchCriteria};warnings:string[];post_discovery:{field:string;mode:string}[];requires_city_review:boolean};
export function applyTargeting(plan:Plan,preview:TargetPreview):Plan{
 return {...plan,icp_id:preview.profile.id,countries:preview.filters.countries.length?preview.filters.countries:plan.countries,cities:[],locations:[],verticals:preview.filters.verticals,search_criteria:{...plan.search_criteria,...preview.filters.search_criteria}};
}
export function ICPTargeting({value,onChange}:{value:Plan;onChange:(value:Plan)=>void}){
 const query=useQuery({queryKey:['icp-discovery-preview',value.icp_id],queryFn:()=>request<TargetPreview>('/organization/icps/'+value.icp_id+'/discovery-preview'),enabled:!!value.icp_id,retry:false});
 if(!value.icp_id)return null;
 return <section className="rounded-xl border bg-primary/5 p-4 text-sm">{query.isPending?<p role="status">Loading profile targeting…</p>:query.error?<p role="alert">{query.error.message}</p>:query.data&&<><h3 className="font-semibold">{query.data.profile.name}<span className="ml-2 text-xs font-normal text-muted-foreground">Version {query.data.profile.revision}</span></h3><p className="mt-2 text-muted-foreground">{[query.data.filters.countries.join(', '),query.data.filters.verticals.map(v=>v.replaceAll('_',' ')).join(', ')].filter(Boolean).join(' · ')||'Review your search geography and industry below.'}</p><Button className="mt-3" type="button" size="sm" variant="outline" onClick={()=>onChange(applyTargeting(value,query.data!))}>Apply profile filters</Button><p className="mt-3 text-xs text-muted-foreground">Additional criteria are checked after discovery using available evidence. Unmeasured criteria remain unknown.</p>{query.data.post_discovery.length>0&&<details className="mt-3"><summary className="cursor-pointer text-xs">Criteria requiring evidence ({query.data.post_discovery.length})</summary><ul className="mt-2 list-disc pl-4 text-xs">{query.data.post_discovery.map(item=><li key={item.field}>{item.field.replaceAll('_',' ').replace('.',': ')}</li>)}</ul></details>}{query.data.warnings.map((text,i)=><p className="mt-2 text-xs" key={i}>{text}</p>)}{query.data.requires_city_review&&<p className="mt-2 text-xs">Preferred cities: {query.data.filters.cities.join(', ')}. Select their explicit location results below to confirm geography.</p>}<Link className="mt-3 inline-block text-xs text-primary underline" href="/settings/icp">Review targeting profiles</Link></>}</section>;
}
