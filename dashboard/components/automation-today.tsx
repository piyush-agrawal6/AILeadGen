"use client";
import Link from "next/link";
import {useQuery} from "@tanstack/react-query";
import {request} from "@/lib/intelligence";
export function AutomationToday(){
 const q=useQuery({queryKey:['automation-today'],queryFn:()=>request<{today:{qualified:number;sent:number;replies:number;bounces:number;queued:number;manual:number};environment:{daily_lead_target:number;daily_email_target:number}}>('/automation/summary'),refetchInterval:30000});
 if(!q.data)return null;
 const d=q.data;
 return <section className="my-6 rounded-lg border bg-card p-5"><div className="mb-4 flex justify-between"><h2 className="text-sm font-semibold">Automation today</h2><Link className="text-xs text-primary" href="/automation">Status and controls</Link></div><div className="grid grid-cols-2 gap-4 md:grid-cols-6">{[['New qualified',d.today.qualified+' / '+d.environment.daily_lead_target],['Emails sent',d.today.sent+' / '+d.environment.daily_email_target],['Queued',d.today.queued],['Replies',d.today.replies],['Manual contact',d.today.manual],['Bounce signals',d.today.bounces]].map(([name,value])=><div key={name}><p className="text-xs text-muted-foreground">{name}</p><p className="mt-2 text-lg font-semibold tabular-nums">{value}</p></div>)}</div></section>;
}
