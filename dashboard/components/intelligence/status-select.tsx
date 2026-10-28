"use client";
import { useState } from "react";
import { useMutation,useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { LoaderCircle } from "lucide-react";
import { STATUSES,label,request,type LeadStatus,type LeadPage,type Workspace } from "@/lib/intelligence";
import { STATUS_STYLES } from "@/lib/lead-display";

export function StatusSelect({id,prospectId,value,name,onSaved}:{id:number;prospectId?:string|null;value:LeadStatus;name:string;onSaved?:()=>void}){
 const cache=useQueryClient();const [optimistic,setOptimistic]=useState<LeadStatus|null>(null);
 const updateCached=(status:LeadStatus)=>cache.setQueriesData<LeadPage>({queryKey:["intelligence-leads"]},data=>data?{...data,items:data.items.map(row=>row.id===id||(prospectId&&row.prospect_id===prospectId)?{...row,lead_status:status}:row)}:data);
 const mutation=useMutation({mutationFn:(status:LeadStatus)=>request<Workspace>(`/leads/${id}/workflow`,{method:"PATCH",body:JSON.stringify({lead_status:status})}),
  onMutate:status=>{setOptimistic(status);updateCached(status);return {previous:value};},
  onSuccess:workspace=>{updateCached(workspace.lead_status);cache.setQueryData<Workspace>(["workspace",id],current=>current?{...current,lead_status:workspace.lead_status}:workspace);toast.success("Status updated to "+label(workspace.lead_status));onSaved?.();},
  onError:(_error,_status,context)=>{if(context)updateCached(context.previous);toast.error("Could not save the status. Your previous status was restored.");},
  onSettled:()=>{setOptimistic(null);cache.invalidateQueries({queryKey:["workspace",id]});cache.invalidateQueries({queryKey:["intelligence-leads"]});cache.invalidateQueries({queryKey:["sales",id]});cache.invalidateQueries({queryKey:["outreach"]});cache.invalidateQueries({queryKey:["outreach-indicator"]});}
 });
 const current=optimistic||value;
 return <span className={"status-control "+STATUS_STYLES[current]} data-status={current}><span className="status-dot"/>
  <select aria-label={"Lead status for "+name} value={current} disabled={mutation.isPending} aria-busy={mutation.isPending} onChange={event=>mutation.mutate(event.target.value as LeadStatus)}>{STATUSES.map(status=><option key={status} value={status}>{label(status)}</option>)}</select>
  {mutation.isPending&&<LoaderCircle className="pointer-events-none h-3 w-3 animate-spin" aria-label="Saving status"/>}
 </span>;
}
