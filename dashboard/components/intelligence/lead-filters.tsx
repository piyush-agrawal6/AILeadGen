"use client";
import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { SlidersHorizontal, X } from "lucide-react";
import { STATUSES, label, type Country, type Campaign } from "@/lib/intelligence";
import { Button } from "@/components/ui/button";

export type LeadFilters = Record<string,string>;
interface Props { value:LeadFilters; onApply:(value:LeadFilters)=>void; countries:Country[]; verticals:{key:string;display_name:string}[]; campaigns:Campaign[] }
export function LeadFiltersPanel({value,onApply,countries,verticals,campaigns}:Props){
 const [open,setOpen]=useState(false);const [draft,setDraft]=useState<LeadFilters>({});
 const count=Object.entries(value).filter(([key,val])=>val&&!["page","sort_by","sort_dir","search","opportunity"].includes(key)).length;
 const set=(key:string,val:string)=>setDraft(current=>({...current,[key]:val}));
 const select=(key:string,title:string,options:{value:string;title:string}[])=> <label className="field-label" key={key} htmlFor={"lead-filter-"+key}>{title}<select id={"lead-filter-"+key} className="control mt-2 w-full" value={draft[key]||""} onChange={event=>set(key,event.target.value)}><option value="">All</option>{options.map(option=><option key={option.value} value={option.value}>{option.title}</option>)}</select></label>;
 return <Dialog.Root open={open} onOpenChange={next=>{if(next)setDraft({...value});setOpen(next);}}>
  <Dialog.Trigger asChild><Button variant="outline" className="gap-2"><SlidersHorizontal className="h-3.5 w-3.5"/>More filters{count>0&&<span className="filter-count">{count}</span>}</Button></Dialog.Trigger>
  <Dialog.Portal><Dialog.Overlay className="filter-overlay" onClick={()=>setOpen(false)}/><Dialog.Content className="filter-panel">
   <div className="flex items-center justify-between border-b px-6 py-5"><div><Dialog.Title className="text-base font-semibold">Filters</Dialog.Title><Dialog.Description className="mt-1 text-xs text-muted-foreground">Narrow your workspace to the next useful conversation.</Dialog.Description></div><Dialog.Close asChild><button type="button" aria-label="Close filters" className="rounded p-2 text-muted-foreground hover:bg-muted"><X className="h-4 w-4"/></button></Dialog.Close></div>
   <form onSubmit={event=>{event.preventDefault();onApply({...draft,page:"1"});setOpen(false);}}>
    <div className="grid grid-cols-1 gap-x-5 gap-y-5 px-6 py-5 sm:grid-cols-2">
     {select("country","Country",countries.map(c=>({value:c.country,title:c.country})))}
     <label className="field-label" htmlFor="lead-filter-city">City<input id="lead-filter-city" className="control mt-2 w-full" placeholder="Enter city name" value={draft.city||""} onChange={event=>set("city",event.target.value)}/></label>
     {select("primary","Primary opportunity",["WEBSITE","SEO","SECURITY"].map(key=>({value:key,title:key==="WEBSITE"?"Website / Redesign":key==="SEO"?"SEO":"Basic Security"})))}
     {select("vertical","Vertical",verticals.map(v=>({value:v.key,title:v.display_name})))}
     {select("status","Lead status",STATUSES.map(key=>({value:key,title:label(key)})))}
     {select("contactability","Contactability",["HIGH","MEDIUM","LOW"].map(key=>({value:key,title:label(key)})))}
     {select("commercial_fit","Commercial fit",["HIGH","MEDIUM","LOW","UNKNOWN"].map(key=>({value:key,title:label(key)})))}
     {select("results","Seen before",[{value:"new",title:"New leads only"},{value:"previous",title:"Previously seen"}])}
     <fieldset className="sm:col-span-2"><legend className="field-label mb-2">Business size</legend><div className="grid grid-cols-2 gap-2 sm:grid-cols-3">{["LOCAL","SMALL_GROUP","MID_MARKET","REGIONAL","ENTERPRISE","KNOWN_CHAIN"].map(key=><label key={key} className="flex items-center gap-2 text-xs"><input type="checkbox" checked={(draft.business_scale||"").split(",").includes(key)} onChange={e=>{const values=(draft.business_scale||"").split(",").filter(Boolean);set("business_scale",(e.target.checked?[...values,key]:values.filter(v=>v!==key)).join(","));}}/>{label(key)}</label>)}</div></fieldset>
     {(["website","seo","security"] as const).map(kind=><label className="field-label" key={kind} htmlFor={"lead-filter-min-"+kind}>Minimum {kind==="seo"?"SEO":label(kind)} score<input id={"lead-filter-min-"+kind} className="control mt-2 w-full" type="number" min={0} max={100} placeholder="e.g. 70" value={draft["min_"+kind]||""} onChange={event=>set("min_"+kind,event.target.value)}/></label>)}
     {select("campaign","Campaign",campaigns.map(c=>({value:c.id,title:c.configuration.cities.map(city=>city.split(",")[0]).join(", ")+" · "+c.configuration.verticals.map(label).join(", ")})))}
    </div>
    <div className="flex items-center justify-between border-t px-6 py-4"><button type="button" className="text-xs font-medium text-primary hover:underline" onClick={()=>setDraft({})}>Clear all</button><Button type="submit">Apply filters</Button></div>
   </form>
  </Dialog.Content></Dialog.Portal>
 </Dialog.Root>;
}
