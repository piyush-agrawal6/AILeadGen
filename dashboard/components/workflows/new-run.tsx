"use client";
import {useState,useEffect} from "react";
import {useQuery} from "@tanstack/react-query";
import {useRouter} from "next/navigation";
import {request} from "@/lib/intelligence";
import {PlanForm} from "./mailbox-plan";
import {Metrics} from "@/components/operations/ui";
import {initialPlan,type Plan} from "./types";
import {SavedSearches} from './saved-searches';
import {applyTargeting,type TargetPreview} from './icp-targeting';
export function NewRun({kind}:{kind:"SCAN"|"OUTREACH"}){
 const router=useRouter();const [plan,setPlan]=useState<Plan>(()=>({...initialPlan(),kind})),[step,setStep]=useState(1),[eligible,setEligible]=useState<Record<string,number>|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
 useEffect(()=>{
  let active=true;
  const params=new URLSearchParams(window.location.search),campaign=params.get('campaign'),duplicate=params.get('duplicate'),icp=params.get('icp');
  async function load(){
   try{
    if(duplicate&&kind==='SCAN'){
     const result=await request<{configuration:Plan}>('/operations/campaigns/'+encodeURIComponent(duplicate));
     if(active)setPlan(p=>({...p,...Object.fromEntries(Object.entries(result.configuration).filter(([key])=>key in p)),kind,request_id:p.request_id,name:result.configuration.name+' copy',campaign_id:null}));
     return;
    }
    const saved=await request<Plan|null>('/workflow/defaults');
    const targeting=icp&&kind==='SCAN'?await request<TargetPreview>('/organization/icps/'+encodeURIComponent(icp)+'/discovery-preview'):null;
    if(active)setPlan(p=>{
     const base={...p,...(saved?Object.fromEntries(Object.entries(saved).filter(([key])=>key in p)):{})};
     const filtered=targeting?applyTargeting(base,targeting):base;
     return {...filtered,kind,request_id:p.request_id,name:'',campaign_id:campaign||null,outreach_mode:'UNCONTACTED',confirm_recontact:false,email_all_eligible:false,needs_owner_review:false};
    });
   }catch{
    if(!active)return;
    if(campaign)setPlan(p=>({...p,campaign_id:campaign}));
    if(icp)setError('The selected targeting profile could not be loaded. Choose a profile or review the filters before starting.');
   }
  }
  void load();return ()=>{active=false};
 },[kind]);
 const live=useQuery({queryKey:['campaign-plan',plan.campaign_id,plan.template_id,plan.outreach_mode,plan.confirm_recontact],queryFn:()=>request<Record<string,number>>('/workflow/eligible',{method:'POST',body:JSON.stringify(plan)}),enabled:kind==='OUTREACH'&&!!plan.campaign_id&&!!plan.template_id&&(plan.outreach_mode!=='RECONTACT'||plan.confirm_recontact)});
 async function review(){setBusy(true);setError("");try{if(kind==="SCAN"&&(!plan.countries.length||!plan.verticals.length)){throw new Error("Choose a supported industry and geography, or use Search with AI for a custom industry.")}if(kind==="OUTREACH"){const r=await request<Record<string,number>>("/workflow/eligible",{method:"POST",body:JSON.stringify(plan)});setEligible(r);}setStep(2);}catch(e){setError(e instanceof Error?e.message:"Could not prepare plan.");}finally{setBusy(false);}}
 async function create(){setBusy(true);setError("");try{const payload={...plan,name:plan.name};const r=await request<{id:string}>("/workflow/runs",{method:"POST",body:JSON.stringify(payload)});await request(`/workflow/runs/${r.id}/${kind==="SCAN"?"start":"prepare"}`,{method:"POST"});router.push('/runs/'+r.id);}catch(e){setError(e instanceof Error?e.message:"Run could not be started.");}finally{setBusy(false);}}
 return <main className="mx-auto max-w-4xl space-y-6"><header><p className="mb-2 text-xs text-primary">{step===1?"01 · Configure":"02 · Review"}</p><h1 className="text-3xl font-semibold">{kind==="SCAN"?"Find Leads":"Send Emails"}</h1><p className="mt-3 text-sm text-muted-foreground">{kind==="SCAN"?"Choose the businesses you want. Watch qualified leads arrive as each market is reviewed.":"Choose a campaign and your workspace email template. All eligible qualified leads become one reviewed outreach run."}</p></header>{step===1?<>{kind==='SCAN'&&<details className="rounded-xl border bg-card p-4"><summary className="cursor-pointer text-sm font-medium">Saved searches</summary><div className="mt-4"><SavedSearches value={plan} onChange={setPlan}/></div></details>}<PlanForm value={plan} onChange={setPlan}/>{kind==='OUTREACH'&&live.data&&<Metrics items={[["Qualified",live.data.qualified],["Email eligible",live.data.email_eligible],["Already contacted",live.data.already_contacted],["Manual contact",live.data.manual_contact],["Suppressed / DNC",live.data.suppressed],["Needs review",live.data.needs_review],["Will be queued",live.data.will_queue]]}/>}<p role="alert" className="text-xs text-destructive">{live.error?.message}</p></>:<section className="rounded-xl border bg-card p-6"><h2 className="text-lg font-semibold">{kind==="SCAN"?"Discovery plan":"Email run plan"}</h2><dl className="mt-5 space-y-3 text-sm"><div>Target: {kind==="SCAN"?`${plan.target} qualified leads`:`${eligible?.will_queue??0} eligible campaign emails`}</div>{kind==="SCAN"?<><div>Countries: {plan.countries.join(", ")}</div><div>Markets: {plan.cities.join(", ")||"Automatic rotation"}</div><div>Verticals: {plan.verticals.join(", ")}</div><div>Business size: {plan.business_scales.join(", ")}</div></>:<><Metrics items={[["Qualified",eligible?.qualified],["Email eligible",eligible?.email_eligible],["Previously contacted",eligible?.already_contacted],["Manual contact",eligible?.manual_contact],["Suppressed",eligible?.suppressed],["Needs review",eligible?.needs_review],["Will be queued",eligible?.will_queue]]}/><div>Template: {plan.template_id}</div><div>Daily maximum: {plan.max_day}</div><div>Maximum/hour: {plan.max_hour}</div><div>Minimum spacing: {Math.max(plan.spacing_minutes,60/plan.max_hour)} minutes</div><div>Send window: {plan.window_start} – {plan.window_end}</div><p className="text-muted-foreground">The next page prepares your exact messages. No email is sent until you review and start the run.</p></>}</dl></section>}<div className="flex flex-wrap gap-3"><button className="control" onClick={()=>step===1?router.push('/'):setStep(1)}>Cancel</button><button className="control border-primary text-primary" disabled={busy||(kind==="OUTREACH"&&(!plan.campaign_id||!plan.template_id||(plan.outreach_mode==="RECONTACT"&&!plan.confirm_recontact)))} onClick={()=>void(step===1?review():create())}>{busy?"Preparing…":step===1?"Review plan":kind==="SCAN"?"Start Discovery":"Review Emails"}</button></div>{error&&<p role="alert" className="text-destructive">{error}</p>}</main>;
}
