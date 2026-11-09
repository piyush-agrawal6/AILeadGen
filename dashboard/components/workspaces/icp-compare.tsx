"use client";
import {useState} from 'react';
import {request} from '@/lib/intelligence';
import {Button} from '@/components/ui/button';
import {Input} from '@/components/ui/input';
type Difference={before_revision:number;after_revision:number;changes:Record<string,{before:unknown;after:unknown}>};
function label(value:string){return value.replaceAll('_',' ').replace(/^./,letter=>letter.toUpperCase())}
function cells(before:unknown,after:unknown,prefix=''): {field:string;before:string;after:string}[]{
 const object=(value:unknown):value is Record<string,unknown>=>!!value&&typeof value==='object'&&!Array.isArray(value);
 if(object(before)||object(after)){
  const left=object(before)?before:{},right=object(after)?after:{};
  return [...new Set([...Object.keys(left),...Object.keys(right)])].flatMap(key=>cells(left[key],right[key],prefix?prefix+' · '+label(key):label(key)));
 }
 if(JSON.stringify(before)===JSON.stringify(after))return [];
 const text=(value:unknown)=>Array.isArray(value)?value.join(', '):value===null||value===undefined||value===''?'Not specified':String(value);
 return [{field:prefix,before:text(before),after:text(after)}];
}
export function ICPCompare({profileId,revision}:{profileId:string;revision:number}){
 const [before,setBefore]=useState(Math.max(1,revision-1)),[after,setAfter]=useState(revision),[result,setResult]=useState<Difference|null>(null),[pending,setPending]=useState(false),[error,setError]=useState('');
 async function compare(event:React.FormEvent){event.preventDefault();if(pending||before>=after||before<1||after>revision||!Number.isInteger(before)||!Number.isInteger(after))return;setPending(true);setError('');setResult(null);try{setResult(await request<Difference>('/organization/icps/'+profileId+'/compare?before='+before+'&after='+after))}catch(reason){setError(reason instanceof Error?reason.message:'Saved versions could not be compared.')}finally{setPending(false)}}
 if(revision<2)return <p className="text-sm text-muted-foreground">Save another version to compare changes.</p>;
 const rows=result?Object.entries(result.changes).flatMap(([field,values])=>cells(values.before,values.after,label(field))):[];
 return <section aria-label="Compare profile versions" className="space-y-4 rounded-lg border p-4"><h3 className="font-medium">Compare saved versions</h3><form onSubmit={compare} className="flex flex-wrap items-end gap-3"><div className="space-y-2"><label htmlFor="icp-compare-before" className="text-sm">Earlier version</label><Input id="icp-compare-before" type="number" min={1} max={revision} required value={before} disabled={pending} onChange={event=>setBefore(Number(event.target.value))}/></div><div className="space-y-2"><label htmlFor="icp-compare-after" className="text-sm">Later version</label><Input id="icp-compare-after" type="number" min={1} max={revision} required value={after} disabled={pending} onChange={event=>setAfter(Number(event.target.value))}/></div><Button type="submit" disabled={pending||before>=after}>{pending?'Comparing…':'Compare versions'}</Button></form>
 {result&&<><p role="status" className="text-sm">{rows.length?`${rows.length} changed ${rows.length===1?'field':'fields'}`:'No differences'} between versions {result.before_revision} and {result.after_revision}.</p>{!!rows.length&&<div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b"><th className="p-2">Field</th><th className="p-2">Version {result.before_revision}</th><th className="p-2">Version {result.after_revision}</th></tr></thead><tbody>{rows.map(row=><tr key={row.field} className="border-b align-top"><th scope="row" className="max-w-48 break-words p-2 font-medium">{row.field}</th><td className="max-w-72 break-words p-2 text-muted-foreground">{row.before}</td><td className="max-w-72 break-words p-2">{row.after}</td></tr>)}</tbody></table></div>}</>}
 {error&&<p role="alert" className="text-sm text-destructive">{error}</p>}
 </section>;
}
