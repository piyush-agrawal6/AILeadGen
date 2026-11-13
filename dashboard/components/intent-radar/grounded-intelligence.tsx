"use client";
import {useState} from 'react';
import {useRadarRead,useRadarMutation,useRadarCapabilities} from './provider';
import {ErrorState,LoadingSkeleton,Field} from './ui';

type Citation={quote:string;interpretation:string;translation?:string;target?:string;kind:string};
type GroundedAnalysis={source_url?:string;summary_language?:string|null;interpretation:{categories:string[];summary?:Citation|null;buyer_problem?:Citation|null;business_relevance?:Citation|null;detected_language?:string;language_evidence?:string;claims:{kind:string;quote:string;interpretation:string;translation?:string}[];icp_assessments?:{criterion:string;status:string;quote:string;explanation:string;basis:string}[]}|null};
export function GroundedIntelligence({analysis}:{analysis:GroundedAnalysis}){
 const data=analysis.interpretation;
 const sections:[string,Citation|null|undefined][]=[['Conversation summary',data?.summary],['Described buyer problem',data?.buyer_problem],['Why this may matter to your business',data?.business_relevance]];
 return <section className="ir-form-section"><h3>Grounded research summary</h3>
  {sections.map(([title,citation])=><div key={title}><h4>{title}</h4>{citation?<><p>{citation.interpretation}</p><blockquote>{citation.quote}</blockquote>{citation.translation&&<p>Requested translation ({analysis.summary_language||'specified language'}): {citation.translation}</p>}{analysis.source_url&&<a className="ir-link" href={analysis.source_url} target="_blank" rel="noopener noreferrer">Original evidence</a>}</>:<p>No source-supported {title.toLowerCase()} was returned. Review the original evidence.</p>}</div>)}
  <p>Detected language: {data?.detected_language||'unknown'} (AI interpretation, not geographic attribution).</p>{data?.language_evidence&&<blockquote>{data.language_evidence}</blockquote>}
  <h4>Non-buying, contradictory or excluded evidence</h4>{data?.claims.filter(c=>['contradiction','exclusion'].includes(c.kind)).map((c,index)=><div key={index}><blockquote>{c.quote}</blockquote><p>{c.interpretation}</p></div>)}
  {!!data?.icp_assessments?.length&&<section><h4>Selected ICP criteria</h4>{data.icp_assessments.map(item=><div key={item.criterion}><strong>{item.criterion}: {item.status}</strong><p>{item.explanation}</p>{item.quote&&<blockquote>{item.quote}</blockquote>}<small>{item.basis}</small></div>)}</section>}
  <small>Original source text is retained. Translations and interpretations require review; they do not establish identity, authority or purchase probability.</small>
 </section>;
}

type Usage={month:string;requests:number;requests_today:number;input_tokens_reported:number;output_tokens_reported:number;unreported_requests:number;estimated_cost_usd:string|null;complete:boolean;basis:string};
export function ProviderUsage(){
 const query=useRadarRead<Usage>('/usage/provider');
 if(query.error)return <ErrorState message={query.error.message} retry={()=>void query.refetch()}/>;
 if(!query.data)return <LoadingSkeleton/>;
 const usage=query.data;
 return <section className="ir-panel ir-form-section"><h2>AI provider usage</h2><dl className="ir-review"><div><dt>Requests this month</dt><dd>{usage.requests}</dd></div><div><dt>Requests today</dt><dd>{usage.requests_today}</dd></div><div><dt>Reported input / output tokens</dt><dd>{usage.input_tokens_reported} / {usage.output_tokens_reported}</dd></div><div><dt>Calls without provider usage</dt><dd>{usage.unreported_requests}</dd></div><div><dt>Estimated USD using approved pricing</dt><dd>{usage.estimated_cost_usd===null?'Unavailable — verified model pricing or usage not supplied':usage.estimated_cost_usd}</dd></div></dl><small>{usage.basis}{!usage.complete?' Totals are a bounded partial sample; full request count is shown.':''}</small></section>;
}

export function TranslatedAnalysis({id,icp,monitorId,onResult}:{id:string;icp:string;monitorId?:string;onResult:(result:unknown)=>void}){
 const [language,setLanguage]=useState('en'),[error,setError]=useState(''),mutation=useRadarMutation(),access=useRadarCapabilities();
 async function translate(){try{onResult(await mutation.mutateAsync({path:'/signals/'+id+'/analysis',body:{icp_id:icp||null,monitor_id:monitorId||null,summary_language:language}}));setError('')}catch(e){setError((e as Error).message)}}
 return <div className="ir-form-section"><Field label="Optional translated evidence summary" hint="Translation is requested explicitly, uses the same bounded AI budget and preserves original source quotes."><select value={language} onChange={e=>setLanguage(e.target.value)}>{['en','es','fr','de','pt','hi','ja'].map(lang=><option key={lang}>{lang}</option>)}</select></Field><button disabled={!access.data?.can_manage||mutation.isPending} onClick={()=>void translate()}>Analyze with requested translation</button>{error&&<ErrorState message={error}/>}</div>;
}

export function FeedbackExplanation({id}:{id:string}){
 const [note,setNote]=useState(''),[label,setLabel]=useState('Not relevant'),[error,setError]=useState(''),mutation=useRadarMutation(),access=useRadarCapabilities();
 async function save(){try{await mutation.mutateAsync({path:'/signals/'+id+'/feedback',method:'PUT',body:{label,note,active:true}});setError('')}catch(e){setError((e as Error).message)}}
  return <div className="ir-form-section"><Field label="Explain a relevance correction"><select value={label} onChange={e=>setLabel(e.target.value)}>{['Relevant','Not relevant','Wrong intent category','Not a target customer','Too old','Duplicate','Incorrect AI summary'].map(value=><option key={value}>{value}</option>)}</select><textarea aria-label="Feedback explanation" maxLength={1000} value={note} onChange={e=>setNote(e.target.value)}/></Field><button disabled={!access.data?.can_write||mutation.isPending} onClick={()=>void save()}>Save feedback with explanation</button>{error&&<ErrorState message={error}/>}</div>;
}
