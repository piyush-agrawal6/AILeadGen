"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { request, label, type Campaign } from "@/lib/intelligence";
import { getScans } from "@/lib/api";
import { PageHeading, Loading, ErrorState, Empty, State } from "@/components/intelligence/common";
import { Button } from "@/components/ui/button";
export default function ScansPage() {
  const campaigns=useQuery({queryKey:["campaigns"],queryFn:()=>request<Campaign[]>("/campaigns"),refetchInterval:10000});
  const runs=useQuery({queryKey:["scans"],queryFn:()=>getScans({page_size:50}),refetchInterval:10000});
  return <div className="mx-auto max-w-6xl"><PageHeading title="Campaigns & scans" description="Shared discovery history, live progress and every result your team has found." action={<Link href="/scans/new"><Button>New scan ↗</Button></Link>}/>
    {campaigns.isLoading?<Loading/>:campaigns.error?<ErrorState error={campaigns.error} retry={()=>campaigns.refetch()}/>:!campaigns.data?.length?<Empty title="No campaigns yet" detail="Create a focused campaign with several cities and verticals. Existing individual scans are listed below." href="/scans/new"/>:<div className="divide-y border-y">{campaigns.data.map(c=><Link key={c.id} href={"/campaigns/"+c.id} className="flex flex-wrap items-center justify-between gap-5 py-5 hover:bg-muted/20"><div><p className="text-sm font-medium">{c.configuration.cities.map(city=>city.split(",")[0]).join(", ")}</p><p className="mt-2 text-xs text-muted-foreground">{c.configuration.verticals.map(label).join(" · ")} · {c.runs.length} child scans</p></div><div className="flex items-center gap-6"><p className="text-xs text-muted-foreground">{c.counters.qualified} qualified</p><State value={c.status}/><span className="text-xs text-muted-foreground">↗</span></div></Link>)}</div>}
    <section className="mt-10"><h2 className="mb-4 text-sm font-semibold">Individual & historical runs</h2>{runs.isLoading?<Loading rows={3}/>:runs.error?<ErrorState error={runs.error} retry={()=>runs.refetch()}/>:!runs.data?.length?<p className="text-sm text-muted-foreground">Individual runs will appear here when a campaign starts.</p>:<div className="overflow-x-auto border-y"><table className="w-full min-w-[650px] text-left text-xs"><thead className="border-b text-muted-foreground"><tr>{["Run","Market","Vertical","Status","Qualified","Started"].map(title=><th className="py-3 pr-4 font-normal" key={title}>{title}</th>)}</tr></thead><tbody className="divide-y">{runs.data.map(run=><tr key={run.id}><td className="py-4 pr-4"><Link className="text-primary" href={"/scans/"+run.id}>#{run.id} ↗</Link></td><td className="py-4 pr-4">{run.market}</td><td className="py-4 pr-4 text-muted-foreground">{label(run.vertical)}</td><td className="py-4 pr-4"><State value={run.status}/></td><td className="py-4 pr-4">{run.qualified}</td><td className="py-4 pr-4 text-muted-foreground">{run.started_at?new Date(run.started_at).toLocaleDateString():"Queued"}</td></tr>)}</tbody></table></div>}</section>
  </div>;
}

