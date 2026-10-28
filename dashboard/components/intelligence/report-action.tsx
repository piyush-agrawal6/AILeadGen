"use client";
import { useEffect,useRef,useState } from "react";
import { useQuery,useQueryClient } from "@tanstack/react-query";
import { Download,FileText,LoaderCircle,RotateCw } from "lucide-react";
import { toast } from "sonner";
import { request,type ClientReport,type ReportStatus } from "@/lib/intelligence";
import { Button } from "@/components/ui/button";

export function ReportAction({id,name,reportId,status,readyReportId,reportVersion,detail=false,onChange}:{id:number;name:string;reportId?:string|null;status?:ReportStatus|null;readyReportId?:string|null;reportVersion?:number|null;detail?:boolean;onChange?:()=>void}){
 const cache=useQueryClient();const [created,setCreated]=useState<ClientReport|null>(null);const [submitting,setSubmitting]=useState(false);const [error,setError]=useState("");const wasPending=useRef(false);
 const local=created&&created.version>(reportVersion||0)?created:null;
 const activeId=local?.id||reportId;const activeStatus=local?.status||status;
 const pending=activeStatus==="QUEUED"||activeStatus==="GENERATING";
 const query=useQuery({queryKey:["client-report",activeId],queryFn:()=>request<ClientReport>("/client-reports/"+activeId),enabled:Boolean(activeId&&pending),refetchInterval:query=>["QUEUED","GENERATING"].includes(query.state.data?.status||activeStatus||"")?2000:false,retry:1});
 const current=query.data?.id===activeId?query.data:local;
 const currentStatus=current?.status||activeStatus;const busy=submitting||(!query.error&&(currentStatus==="QUEUED"||currentStatus==="GENERATING"));
 useEffect(()=>{if(busy)wasPending.current=true;if(wasPending.current&&currentStatus==="READY"){wasPending.current=false;toast.success("PDF report is ready");cache.invalidateQueries({queryKey:["intelligence-leads"]});cache.invalidateQueries({queryKey:["client-reports"]});onChange?.();}},[busy,currentStatus,cache,onChange]);
 const generate=async()=>{setSubmitting(true);setError("");try{const report=await request<ClientReport>(`/leads/${id}/pdf-reports`,{method:"POST"});setCreated(report);wasPending.current=true;onChange?.();}catch{setError("Report generation failed. Try again.");toast.error("Report generation failed. Try again.");}finally{setSubmitting(false);}};
 const failure=currentStatus==="FAILED"||Boolean(query.error)||Boolean(error);
 const downloadId=currentStatus==="READY"?activeId:readyReportId;
 return <div className={detail?"space-y-3":"report-cell"}>
  {busy?<Button variant="outline" disabled className={"gap-2 "+(detail?"w-full":"text-xs")} aria-label={"Generating PDF for "+name}><LoaderCircle className="h-3.5 w-3.5 animate-spin"/>{currentStatus==="QUEUED"?"Queued…":"Generating…"}</Button>:
   currentStatus==="READY"&&activeId?<a className={"pdf-download "+(detail?"w-full justify-center":"")} href={`/api/client-reports/${activeId}/download`}><Download className="h-3.5 w-3.5"/>{detail?"Download latest PDF":"Download PDF"}</a>:
   <Button variant={detail?"default":"outline"} className={"gap-2 "+(detail?"w-full":"text-xs")} onClick={generate}><FileText className="h-3.5 w-3.5"/>{failure?"Try again":detail?"Generate PDF Report":"Generate PDF"}</Button>}
  {!busy&&currentStatus==="READY"&&<button className={detail?"text-xs text-muted-foreground hover:text-primary":"report-regenerate"} onClick={generate} aria-label={"Regenerate PDF for "+name}><RotateCw className="h-3.5 w-3.5"/>{detail&&"Regenerate"}</button>}
  {failure&&<p role="alert" className="max-w-48 text-[11px] text-destructive">Report generation failed. Try again.</p>}
  {detail&&failure&&downloadId&&<a className="text-xs text-primary underline" href={`/api/client-reports/${downloadId}/download`}>Download previous PDF</a>}
 </div>;
}
