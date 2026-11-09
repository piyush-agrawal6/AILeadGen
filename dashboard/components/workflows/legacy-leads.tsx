"use client";
import { DeleteAction } from "@/components/intelligence/delete-action";
import { SocialIcons } from "@/components/intelligence/social-presence";
import { BulkActions } from "@/components/sales/workspace";
import { SavedViews } from "@/components/sales/saved-views";
import { Suspense,useEffect,useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpDown,Building2,ChevronLeft,ChevronRight,ExternalLink,Mail,Phone,Search,X } from "lucide-react";
import { request,label,type Campaign,type Country,type LeadPage,type Overview } from "@/lib/intelligence";
import { emailHref,phoneHref,safeWebsite } from "@/lib/lead-display";
import { PageHeading,Loading,ErrorState,Empty,Score } from "@/components/intelligence/common";
import { LeadFiltersPanel,type LeadFilters } from "@/components/intelligence/lead-filters";
import { StatusSelect } from "@/components/intelligence/status-select";
import { ReportAction } from "@/components/intelligence/report-action";
import { Button } from "@/components/ui/button";

function LeadExplorer(){
 const [selected,setSelected]=useState<number[]>([]);
 const initial=useSearchParams();const [filters,setFilters]=useState<LeadFilters>(()=>Object.fromEntries(initial.entries()));
 const page=Math.max(1,Number(filters.page)||1);
 const query=new URLSearchParams(Object.entries(filters).filter(([,value])=>value)).toString();
 useEffect(()=>{window.history.replaceState(null,"","/leads"+(query?"?"+query:""));},[query]);
 useEffect(()=>{setSelected([]);},[query]);
 const set=(key:string,value:string)=>setFilters(current=>({...current,[key]:value,page:key==="page"?value:"1"}));
 const data=useQuery({queryKey:["intelligence-leads",query],queryFn:()=>request<LeadPage>("/intelligence/leads?"+query),placeholderData:previous=>previous,refetchInterval:15000});
 const countries=useQuery({queryKey:["market-presets"],queryFn:()=>request<Country[]>("/markets/presets")});
 const verticals=useQuery({queryKey:["verticals"],queryFn:()=>request<{key:string;display_name:string}[]>("/verticals")});
 const campaigns=useQuery({queryKey:["campaigns-filter"],queryFn:()=>request<Campaign[]>("/campaigns?page_size=50")});
 const overview=useQuery({queryKey:["intelligence-overview"],queryFn:()=>request<Overview>("/intelligence/overview")});
 const sort=(key:string)=>setFilters(current=>({...current,sort_by:key,sort_dir:current.sort_by===key&&current.sort_dir!=="asc"?"asc":"desc",page:"1"}));
 const active=Object.entries(filters).filter(([key,value])=>value&&!["page","sort_by","sort_dir"].includes(key));
 const filterTitle=(key:string,value:string)=>{
  if(key==="business_scale")return "Business size: "+value.split(",").map(label).join(" + ");
  if(key==="campaign"){const campaign=campaigns.data?.find(item=>item.id===value);return "Campaign: "+(campaign?campaign.configuration.cities.map(city=>city.split(",")[0]).join(", "):"Selected campaign");}
  if(key.startsWith("min_"))return "Min "+(key==="min_seo"?"SEO":label(key.slice(4)))+": "+value;
  return label(key)+": "+(key==="opportunity"&&value==="SEO"?"SEO":label(value));
 };
 const progress=overview.data?.statuses.filter(row=>["CONTACTED","REPLIED","SHORTLISTED"].includes(row.lead_status)).reduce((sum,row)=>sum+row.count,0)??0;
 const won=overview.data?.statuses.find(row=>row.lead_status==="WON")?.count??0;
 const sortButton=(title:string,key:string)=><button type="button" aria-label={"Sort by "+title} aria-pressed={filters.sort_by===key} onClick={()=>sort(key)} className="inline-flex items-center gap-1 hover:text-foreground">{title}<ArrowUpDown className="h-3 w-3 opacity-60"/></button>;
 return <div className="mx-auto max-w-[1600px]">
  <PageHeading title="Lead workspace" description="Prioritize the opportunity. Keep every conversation in one shared place." action={<div className="flex divide-x rounded-lg border bg-card py-3 shadow-sm">{[["Known leads",overview.data?.total_leads],["In progress",progress],["Won",won]].map(([title,count])=><div className="px-5" key={title}><p className="text-lg font-semibold tabular-nums">{count==null?"—":Number(count).toLocaleString()}</p><p className="mt-0.5 text-[10px] text-muted-foreground">{title}</p></div>)}</div>}/>
  <div className="mb-4 flex flex-wrap items-center gap-3"><div className="relative min-w-64 flex-1"><Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground"/><input aria-label="Search businesses" className="control w-full pl-10" placeholder="Search business name, website or domain…" value={filters.search||""} onChange={event=>set("search",event.target.value)}/></div>
   <select aria-label="Opportunity type" className="control min-w-40" value={filters.opportunity||""} onChange={event=>set("opportunity",event.target.value)}><option value="">All opportunities</option><option value="WEBSITE">Website / Redesign</option><option value="SEO">SEO opportunity</option><option value="SECURITY">Basic Security</option></select>
   <SavedViews filters={filters} onApply={setFilters}/><LeadFiltersPanel value={filters} onApply={setFilters} countries={countries.data||[]} verticals={verticals.data||[]} campaigns={campaigns.data||[]}/>
  </div>
  {active.length>0&&<div aria-label="Active filters" className="mb-5 flex flex-wrap items-center gap-2">{active.map(([key,value])=><button key={key} className="inline-flex items-center gap-2 rounded-full border brand-filter-chip px-3 py-1.5 text-[11px]" onClick={()=>set(key,"")} aria-label={"Remove filter "+filterTitle(key,value)}>{filterTitle(key,value)}<X className="h-3 w-3"/></button>)}<button className="ml-2 text-xs font-medium text-primary" onClick={()=>setFilters({})}>Clear all</button></div>}
  <BulkActions ids={selected} onDone={()=>{setSelected([]);void data.refetch();}}/>
  {data.isLoading?<Loading rows={8}/>:data.error?<ErrorState error={data.error} retry={()=>data.refetch()}/>:!data.data?.items.length?<Empty title={active.length?"No leads match these filters":"Your next shortlist starts here"} detail={active.length?"Broaden a score range, change the opportunity type or clear your filters.":"Run a focused campaign to build your shared lead workspace."} href={active.length?undefined:"/scans/new"}/>:
   <><div className="overflow-x-auto rounded-lg border bg-card shadow-sm" aria-busy={data.isFetching}><table className="lead-table"><thead><tr>
    <th><input aria-label="Select all leads on page" type="checkbox" checked={!!data.data?.items.length&&selected.length===data.data.items.length} onChange={e=>setSelected(e.target.checked?data.data?.items.map(r=>r.id)||[]:[])}/></th><th className="w-[31%]">{sortButton("Business","name")}</th><th>Location</th><th>Vertical</th>
    <th className="min-w-[155px]"><span className="mb-2 block text-center">Opportunity scores</span><div className="grid grid-cols-3 gap-2">{sortButton("Website","website")}{sortButton("SEO","seo")}{sortButton("Security","security")}</div></th>
    <th>Primary</th><th>{sortButton("Commercial fit","commercial_fit")} / Contact</th><th>Status</th><th>Report</th>
   </tr></thead><tbody>{data.data.items.map(lead=>{
    const website=safeWebsite(lead.website);const email=emailHref(lead.public_email);const phone=phoneHref(lead.phone);
    return <tr key={lead.id}><td><input type="checkbox" aria-label={"Select "+lead.name} checked={selected.includes(lead.id)} onChange={e=>setSelected(e.target.checked?[...selected,lead.id]:selected.filter(x=>x!==lead.id))}/></td><td className="business-cell"><div className="flex items-start gap-3"><span className="mt-0.5 hidden h-8 w-8 shrink-0 place-items-center rounded-md bg-primary/10 text-primary xl:grid"><Building2 className="h-4 w-4"/></span><div className="min-w-0"><Link href={"/leads/"+lead.id} className="block truncate text-[13px] font-semibold hover:text-primary" title={lead.name}>{lead.name}</Link>
     {website?<a href={website} target="_blank" rel="noopener noreferrer" className="mt-1 inline-flex max-w-full items-center gap-1 text-[11px] text-primary hover:underline"><span className="truncate">{new URL(website).hostname.replace(/^www\./,"")}</span><ExternalLink className="h-2.5 w-2.5 shrink-0"/></a>:<p className="mt-1 text-[11px] text-muted-foreground">No official website found</p>}
     {(phone||email)&&<div className="contact-line">{phone&&<a href={phone}><Phone className="h-3 w-3 shrink-0"/>{lead.phone}</a>}{email&&<a href={email}><Mail className="h-3 w-3 shrink-0"/>{lead.public_email}</a>}</div>}
    <SocialIcons profiles={lead.social_profiles}/></div></div></td><td className="min-w-28"><p>{lead.city}</p><p className="mt-1 text-[10px] text-muted-foreground">{lead.country}</p></td><td className="max-w-32 text-[11px] text-muted-foreground">{label(lead.vertical)}</td>
    <td><div className="grid grid-cols-3 gap-2"><Score compact value={lead.website_opportunity_score}/><Score compact value={lead.seo_opportunity_score}/><Score compact value={lead.security_opportunity_score}/></div></td>
    <td className="text-[10px] font-medium">{lead.primary_opportunity?(lead.primary_opportunity==="WEBSITE"?"Website":lead.primary_opportunity==="SEO"?"SEO":"Security"):"Not assessed"}</td>
    <td>{lead.commercial_fit&&<p className="mb-1 text-[10px]" title="Based on public footprint and contact signals, not revenue or budget.">{label(lead.commercial_fit)} fit</p>}<span className={"text-[10px] font-medium "+(lead.contactability_level==="HIGH"?"contact-high":"text-muted-foreground")}>{lead.contactability_level?label(lead.contactability_level):"Unassessed"}</span></td>
    <td><StatusSelect id={lead.id} prospectId={lead.prospect_id} value={lead.lead_status} name={lead.name}/></td>
    <td><div className="flex items-center gap-2"><DeleteAction kind="lead" id={lead.id}/><ReportAction id={lead.id} name={lead.name} reportId={lead.latest_report_id} status={lead.latest_report_status} readyReportId={lead.ready_report_id} reportVersion={lead.report_version}/></div></td></tr>;
   })}</tbody></table></div>
   <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-[11px] text-muted-foreground"><p>{data.data.total.toLocaleString()} known leads · Higher score = stronger sales opportunity · — = not assessed</p><div className="flex items-center gap-3"><Button variant="ghost" size="icon" aria-label="Previous page" disabled={page<=1} onClick={()=>set("page",String(page-1))}><ChevronLeft className="h-4 w-4"/></Button><span>{page} / {data.data.total_pages}</span><Button variant="ghost" size="icon" aria-label="Next page" disabled={page>=data.data.total_pages} onClick={()=>set("page",String(page+1))}><ChevronRight className="h-4 w-4"/></Button></div></div></>}
 </div>;
}
export default function LeadsPage(){return <Suspense fallback={<Loading/>}><LeadExplorer/></Suspense>;}
