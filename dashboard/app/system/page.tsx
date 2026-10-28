"use client";
import { useQuery } from "@tanstack/react-query";
import { request } from "@/lib/intelligence";
import { PageHeading,Loading,ErrorState } from "@/components/intelligence/common";
import { Button } from "@/components/ui/button";
interface Health {environment:string;checks:{name:string;status:string;details:string}[]}
export default function SystemPage(){
 const query=useQuery({queryKey:["hosted-health"],queryFn:()=>request<Health>("/system/hosted-health"),retry:false});
 return <div className="mx-auto max-w-5xl"><PageHeading title="System health" description="Live checks for the services behind your shared workspace." action={<Button variant="outline" disabled={query.isFetching} onClick={()=>query.refetch()}>{query.isFetching?"Checking…":"Run checks"}</Button>}/>
 {query.isLoading?<Loading rows={8}/>:query.error?<ErrorState error={query.error} retry={()=>query.refetch()}/>:<><div className="mb-5 flex items-center justify-between border-y py-4"><span className="text-sm">Dashboard</span><span className="text-xs text-primary">Connected to authenticated API</span></div><div className="divide-y">{query.data?.checks.map((check,index)=><div className="grid gap-2 py-4 sm:grid-cols-[200px_110px_minmax(0,1fr)]" key={check.name+index}><p className="text-sm font-medium">{check.name}</p><p className={"text-xs capitalize "+(check.status==="ready"?"text-primary":check.status==="error"?"text-destructive":"text-muted-foreground")}>{check.status}</p><p className="text-xs leading-5 text-muted-foreground">{check.details}</p></div>)}</div><p className="mt-5 border-t pt-4 text-xs text-muted-foreground">Environment: {query.data?.environment}. Configuration checks do not establish successful worker execution; a canary verifies that separately.</p></>}
 </div>;
}

