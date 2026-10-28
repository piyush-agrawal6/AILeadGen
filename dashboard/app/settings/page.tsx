"use client";
import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { getSettings, updateSettings } from "@/lib/api";
import { request,type User } from "@/lib/intelligence";
import type { AppSettingsSchema } from "@/types/api";
import { PageHeading,Loading,ErrorState } from "@/components/intelligence/common";
import { Button } from "@/components/ui/button";
export default function SettingsPage(){
 const query=useQuery({queryKey:["settings"],queryFn:getSettings});
 const users=useQuery({queryKey:["users"],queryFn:()=>request<User[]>("/users")});
 const limits=useQuery({queryKey:["limits"],queryFn:()=>request<Record<string,number|string>>("/system/limits")});
 const [pages,setPages]=useState<number|null>(null);const [lighthouse,setLighthouse]=useState<boolean|null>(null);const [busy,setBusy]=useState(false);const [error,setError]=useState("");
 const save=async(event:React.FormEvent)=>{event.preventDefault();if(!query.data)return;setBusy(true);try{const next:AppSettingsSchema={...query.data,crawler:{...query.data.crawler,max_pages:pages??query.data.crawler.max_pages},auditing:{...query.data.auditing,lighthouse_enabled:lighthouse??query.data.auditing.lighthouse_enabled}};await updateSettings(next);toast.success("Workspace preferences saved");query.refetch();setError("");}catch(e){setError(e instanceof Error?e.message:"Could not save preferences.");}finally{setBusy(false);}};
 return <div className="mx-auto max-w-5xl"><div className="mb-5 flex gap-4 text-sm text-primary"><Link href="/settings/email">Email connection</Link><Link href="/settings/templates">Email templates</Link></div><PageHeading title="Workspace preferences" description="Shared scan defaults for the team. Safety limits stay under deployment control."/>
 {query.isLoading?<Loading/>:query.error?<ErrorState error={query.error} retry={()=>query.refetch()}/>:query.data&&<div className="grid gap-10 lg:grid-cols-2"><form onSubmit={save} className="space-y-6 border-t pt-5"><h2 className="text-sm font-semibold">Scan preferences</h2><label className="field-label">Standard crawl pages<input type="number" min="1" max="30" className="control mt-2 w-full" value={pages??query.data.crawler.max_pages} onChange={e=>setPages(Number(e.target.value))}/><span className="mt-2 block text-xs font-normal leading-5">SEO campaigns may inspect up to 30 pages, reusing the shared crawl.</span></label><label className="flex items-start gap-3 text-sm"><input className="mt-1" type="checkbox" checked={lighthouse??query.data.auditing.lighthouse_enabled} onChange={e=>setLighthouse(e.target.checked)}/><span>Lighthouse performance audits<span className="mt-1 block text-xs leading-5 text-muted-foreground">Use a bounded browser audit for promising websites. Availability depends on worker configuration.</span></span></label>{error&&<p role="alert" className="text-xs text-destructive">{error}</p>}<Button disabled={busy} type="submit">{busy?"Saving…":"Save preferences"}</Button><div className="border-t pt-5"><h2 className="mb-3 text-sm font-semibold">Approved team</h2>{users.data?.map(user=><div className="border-b py-3" key={user.id}><p className="text-xs">{user.email}</p><p className="mt-1 text-[10px] text-muted-foreground">Administrator · Google sign-in</p></div>)}</div></form><section className="border-t pt-5"><h2 className="text-sm font-semibold">Workload protection</h2><p className="my-3 text-xs leading-6 text-muted-foreground">Read-only infrastructure limits. These keep a single campaign within the configured resource budget.</p><dl className="divide-y">{[["max_active_scans","Active scans"],["max_cities_per_scan","Cities per campaign"],["max_target_leads","Qualified lead target"],["max_raw_businesses","Raw businesses"],["max_lighthouse_audits","Lighthouse audits"],["max_scan_runtime_minutes","Runtime limit (minutes)"],["executor","Execution"]].map(([key,title])=><div className="flex justify-between py-3 text-xs" key={key}><dt className="text-muted-foreground">{title}</dt><dd>{limits.data?.[key]??"Checking…"}</dd></div>)}</dl></section></div>}
 </div>;
}

