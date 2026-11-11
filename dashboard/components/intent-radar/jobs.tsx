"use client";
import Link from 'next/link';
import {useEffect,useRef} from 'react';
import type {IntentJob} from '@/lib/intent-radar';
import {useRadarRead,useRadarMutation,useRadarRefresh} from './provider';
import {Badge,ErrorState} from './ui';
export function JobPanel({id,onComplete}:{id:string;onComplete?:(job:IntentJob)=>void}){
 const query=useRadarRead<IntentJob>('/jobs/'+id),mutation=useRadarMutation(),refresh=useRadarRefresh(),started=useRef(0),complete=useRef('');
 const {refetch,dataUpdatedAt}=query;
 const active=query.data&&['QUEUED','RUNNING'].includes(query.data.status);
 useEffect(()=>{started.current=Date.now()},[id]);
 useEffect(()=>{if(active&&Date.now()-started.current<180000){const timer=setTimeout(()=>{void refetch()},2000);return()=>clearTimeout(timer)}},[active,dataUpdatedAt,refetch]);
 useEffect(()=>{if(active){complete.current='';return}if(query.data&&complete.current!==id){complete.current=id;refresh();onComplete?.(query.data)}},[query.data,active,id,refresh,onComplete]);
 if(query.error)return <ErrorState message={query.error.message}/>;
 if(!query.data)return <p className="ir-notice">Loading discovery job…</p>;
 const job=query.data,result=job.items[0]?.result;
 return <section className="ir-panel ir-job" aria-label="Discovery progress"><div className="ir-card-top"><h2>{active?'Checking public conversations':'Discovery check'}</h2><Badge>{job.status}</Badge></div>{active&&<div className="ir-job-progress" role="status" aria-label="Checking selected sources"><span/></div>}<p>{result?.coverage||'Bounded checks of selected authorized sources. Coverage updates as each provider completes.'}</p>
 {!!job.sources?.length&&<ul className="ir-source-limits">{job.sources.map(s=><li key={s.provider}><strong>{s.provider}</strong> — {s.status}: {s.coverage}{s.retry_at?' Retry after '+new Date(s.retry_at).toLocaleString():''}</li>)}</ul>}
 <div className="ir-job-metrics">{[[result?.scanned??0,'Items checked'],[result?.matched??0,'Matching signals'],[result?.requests??0,'Source requests']].map(([value,label])=><div key={label}><strong>{value}</strong><small>{label}</small></div>)}</div>{job.items.some(i=>i.error_code)&&<ErrorState message={'Source or authorization failure: '+job.items.find(i=>i.error_code)?.error_code+'. No substitute results were created.'}/>}
 <div className="ir-actions">{active&&<button disabled={mutation.isPending} onClick={()=>mutation.mutate({path:'/jobs/'+id+'/cancel'})}>Cancel check</button>}{['PARTIAL','FAILED'].includes(job.status)&&job.attempts<3&&<button disabled={mutation.isPending} onClick={()=>mutation.mutate({path:'/jobs/'+id+'/retry'})}>Retry bounded check</button>}<Link className="ir-link" href="/intent-radar/signals">Review stored signals</Link><button onClick={()=>{void query.refetch()}}>Refresh status</button></div></section>;
}
