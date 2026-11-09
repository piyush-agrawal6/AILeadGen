"use client";
import {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {request} from '@/lib/intelligence';
import {Button} from '@/components/ui/button';

export type ICPProposal={name:string;description:string;status:'INACTIVE';criteria:Record<'company'|'contact'|'intent',Record<string,string[]|number|string|null>>&{weights?:Record<string,number>}};
type AIStatus={enabled:boolean;configured:boolean;can_generate:boolean;requests_used_today:number;daily_limit:number;period_timezone:string};
export function ICPAssistant({onGenerated}:{onGenerated:(value:ICPProposal)=>void}){
 const [prompt,setPrompt]=useState(''),[pending,setPending]=useState(false),[error,setError]=useState('');
 const status=useQuery({queryKey:['icp-ai-status'],queryFn:()=>request<AIStatus>('/organization/icps/ai-status'),retry:false});
 if(!status.data?.enabled||!status.data.configured||!status.data.can_generate)return null;
 async function generate(event:React.FormEvent){event.preventDefault();if(pending)return;setPending(true);setError('');try{const result=await request<{draft:ICPProposal;proposal_id?:string;review_required:true}>('/organization/icps/interpret',{method:'POST',body:JSON.stringify({prompt})});await status.refetch();onGenerated({...result.draft,...(result.proposal_id?{proposal_id:result.proposal_id}:{})})}catch(reason){setError(reason instanceof Error?reason.message:'AI criteria could not be generated. The manual builder remains available.');void status.refetch()}finally{setPending(false)}}
 return <details className="rounded-lg border p-4"><summary className="cursor-pointer font-medium">Describe your ideal customers</summary><form onSubmit={generate} className="mt-4 space-y-4"><p className="text-sm text-muted-foreground">Turn your request into an editable draft. Review every field before saving. Generating criteria does not create a profile or start a search.</p><label className="block text-sm" htmlFor="icp-ai-prompt">Your targeting instructions</label><textarea id="icp-ai-prompt" className="control min-h-28 w-full" required minLength={10} maxLength={2000} value={prompt} disabled={pending} onChange={e=>setPrompt(e.target.value)}/><p className="text-xs text-muted-foreground">Draft requests today: {status.data.requests_used_today}/{status.data.daily_limit} ({status.data.period_timezone}). Failed requests also count; identical cached requests are reused.</p><Button type="submit" disabled={pending||prompt.trim().length<10}>{pending?'Preparing draft…':'Generate criteria draft'}</Button>{error&&<p role="alert" className="text-sm text-destructive">{error}</p>}</form></details>;
}
