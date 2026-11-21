'use client';
import {useState} from 'react';
import {Button} from '@/components/ui/button';
import {request} from '@/lib/intelligence';
type Brief={mode:string;source:string;limitation:string|null;summary:{summary?:string;problem?:string;topic_relevance?:string;recommended_next_step?:string;source_statements:string[];unknowns:string[]}};
export function ActionBrief({op}:{op:string}){
 const [brief,setBrief]=useState<Brief|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 return <section className="rounded-lg border p-4 space-y-2"><h2 className="font-semibold">Opportunity brief</h2><Button variant="outline" disabled={busy} onClick={async()=>{setBusy(true);setError('');try{setBrief(await request<Brief>('/intent-radar/actions/brief/'+op,{method:'POST'}))}catch(e){setBrief(null);setError((e as Error).message)}finally{setBusy(false)}}}>{busy?'Preparing…':'Generate evidence brief'}</Button>{error&&<p role="alert">{error}</p>}{brief&&<div className="space-y-2 break-words text-sm"><p>{brief.mode} · <a className="underline" href={brief.source} rel="noreferrer" target="_blank">Original discussion</a></p>{brief.limitation&&<p>{brief.limitation}</p>}{brief.summary.source_statements?.map((s,i)=><blockquote className="border-l-2 pl-2" key={i}>{s}</blockquote>)}{brief.summary.summary&&<p><strong>Interpretation:</strong> {brief.summary.summary}</p>}{brief.summary.topic_relevance&&<p>Relevance: {brief.summary.topic_relevance}</p>}<p>Suggested follow-up: {brief.summary.recommended_next_step||'Review the original discussion.'}</p>{brief.summary.unknowns?.length>0&&<p>Unverified: {brief.summary.unknowns.join('; ')}</p>}</div>}</section>;
}
