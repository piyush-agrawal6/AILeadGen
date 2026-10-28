"use client";
import { DeleteAction } from "@/components/intelligence/delete-action";
import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { request, label, type Campaign } from "@/lib/intelligence";
import { PageHeading, Loading, ErrorState, State } from "@/components/intelligence/common";
import { Button } from "@/components/ui/button";
export default function CampaignPage() {
  const id=String(useParams().campaignId); const [busy,setBusy]=useState(false); const [error,setError]=useState("");
  const query=useQuery({queryKey:["campaign",id],queryFn:()=>request<Campaign>("/campaigns/"+id),refetchInterval:q=>["COMPLETED","FAILED","CANCELLED"].includes(q.state.data?.status||"")?false:2000});
  const act=async(action:string)=>{setBusy(true);try{setError("");await request("/campaigns/"+id+"/"+action,{method:"POST"});query.refetch();}catch(e){setError(e instanceof Error?e.message:"Unable to update campaign.");}finally{setBusy(false);}};
  if(query.isLoading)return <Loading/>;
  if(query.error||!query.data)return <ErrorState error={query.error} retry={()=>query.refetch()}/>;
  const c=query.data;
  return <div className="mx-auto max-w-6xl"><PageHeading eyebrow="Discovery / Campaign" title={c.configuration.cities.map(city=>city.split(",")[0]).join(" · ")} description={c.configuration.verticals.map(label).join(" / ")} action={<div className="flex gap-2"><DeleteAction kind="campaign" id={id} redirect="/scans"/>{["RUNNING","QUEUED"].includes(c.status)?<Button variant="outline" disabled={busy} onClick={()=>act("cancel")}>Cancel campaign</Button>:c.status!=="COMPLETED"&&<Button variant="outline" disabled={busy} onClick={()=>act("resume")}>Resume campaign</Button>}<Link href={"/leads?campaign="+id}><Button>View results ↗</Button></Link></div>}/>
    <div className="flex flex-wrap items-center gap-4 border-y py-4"><State value={c.status}/><p className="text-xs text-muted-foreground">{c.progress.completed} of {c.runs.length} complete · {c.progress.running} running · {c.progress.queued} queued</p><p className="ml-auto text-xs text-muted-foreground">Created by {c.created_by.split("@")[0]}</p></div>
    {error&&<p role="alert" className="my-4 text-xs text-destructive">{error}</p>}
    <div className="my-7 grid grid-cols-2 gap-5 sm:grid-cols-5">{[["Discovered",c.counters.raw_found],["Qualified",c.counters.qualified],["Website",c.opportunities.website],["SEO",c.opportunities.seo],["Security",c.opportunities.security]].map(([name,value])=><div key={name}><p className="text-xs text-muted-foreground">{name}</p><p className="mt-2 text-3xl font-medium tabular-nums">{value}</p></div>)}</div>
    <section className="mt-9"><h2 className="mb-4 text-sm font-semibold">City × vertical runs</h2><div className="overflow-x-auto border-y"><table className="w-full min-w-[600px] text-left text-xs"><thead className="border-b text-[10px] text-muted-foreground"><tr>{["Location","Vertical","Status","Discovered","Qualified",""].map((title,i)=><th key={i} className="px-3 py-3 font-medium first:pl-0">{title}</th>)}</tr></thead><tbody className="divide-y">{c.runs.map(run=><tr key={run.id}><td className="py-4 pr-3 font-medium">{run.market}</td><td className="px-3 py-4 text-muted-foreground">{label(run.vertical)}</td><td className="px-3 py-4"><State value={run.status}/></td><td className="px-3 py-4 tabular-nums">{run.raw_found}</td><td className="px-3 py-4 tabular-nums">{run.qualified}</td><td className="px-3 py-4"><Link className="text-primary" href={"/scans/"+run.id}>Live detail ↗</Link></td></tr>)}</tbody></table></div></section>
    <div className="mt-7 grid gap-7 border-t pt-5 sm:grid-cols-2"><div><h2 className="mb-3 text-sm font-semibold">Campaign configuration</h2><p className="text-xs leading-6 text-muted-foreground">{c.configuration.opportunities.map(label).join(" + ")}<br/>{label(c.configuration.quality)} quality · {c.configuration.business_scales.map(label).join(" + ")}<br/>Target: {c.target_total} qualified leads across {c.runs.length} child scans.</p></div><div><h2 className="mb-3 text-sm font-semibold">Activity</h2><p className="text-xs leading-6 text-muted-foreground">Started {new Date(c.created_at).toLocaleString()}{c.completed_at&&<><br/>Finished {new Date(c.completed_at).toLocaleString()}</>}</p>{c.runs.filter(run=>run.error_message).map(run=><p className="mt-3 text-xs text-destructive" key={run.id}>{run.market}: {run.error_message}</p>)}</div></div>
  </div>;
}

