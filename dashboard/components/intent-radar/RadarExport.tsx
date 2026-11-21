"use client";
import {useState} from 'react';
import {Button} from '@/components/ui/button';
import {RadarSheets} from './integrations/RadarSheets';

export type ExportSelection={dataset:'discovery'|'signals'|'opportunities'|'monitor'|'saved'|'growth';ids?:string[];parent?:string;search?:string;source?:string;status?:string;list_filters?:Record<string,string>};
export function RadarExport({selection:current,matchingQuery}:{selection:ExportSelection;matchingQuery?:string}) {
  const [all,setAll]=useState(false);
  const params=new URLSearchParams(matchingQuery);params.delete('page');params.delete('page_size');
  const selection=all&&matchingQuery!==undefined?{dataset:current.dataset,list_filters:Object.fromEntries(params)}:current;
  const [format,setFormat]=useState('csv'),[busy,setBusy]=useState(false),[message,setMessage]=useState('');
  async function download(){
    if(busy)return;
    if(selection.ids&&selection.ids.length>100){setMessage('Select at most 100 records.');return;}
    setBusy(true);setMessage('Preparing export…');
    try{
      const res=await fetch('/api/intent-radar/exports/'+(format==='Copy summary'?'json':format),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(selection),cache:'no-store'});
      if(!res.ok){const error=await res.json().catch(()=>null);throw new Error(typeof error?.detail==='string'?error.detail:'Export unavailable for this selection or workspace.');}
      if(format==='Copy summary'){const {records}=await res.json() as {records:{title:string;excerpt:string;source:string;source_url:string;attribution?:string}[]};await navigator.clipboard.writeText(records.map(r=>[r.title,r.excerpt,r.source,r.source_url,r.attribution].filter(Boolean).join('\n')).join('\n\n'));setMessage('Copied authorized summaries and source links.');return;}
      const url=URL.createObjectURL(await res.blob());const a=document.createElement('a');a.href=url;a.download=`planebyte-${selection.dataset}.${format}`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);setMessage('Download prepared.');
    }catch(error){setMessage(error instanceof Error?error.message:'Download failed.');}finally{setBusy(false);}
  }
  return <div className="flex flex-wrap items-center gap-2">{matchingQuery!==undefined&&<select aria-label="Export scope" value={all?'all':'page'} onChange={e=>setAll(e.target.value==='all')}><option value="page">Selection / current page</option><option value="all">All matching results</option></select>}<select aria-label="Export format" value={format} onChange={e=>setFormat(e.target.value)} className="rounded border bg-background p-1">{['csv','xlsx','json','pdf','Google Sheets','Copy summary'].map(f=><option key={f} value={f}>{f.includes(' ')?f:f.toUpperCase()}</option>)}</select>{format==='Google Sheets'?<RadarSheets selection={selection}/>:<Button variant="outline" size="sm" disabled={busy||selection.ids?.length===0} onClick={download}>Export</Button>}<small>Up to 100 eligible records</small><small role="status">{message}</small></div>;
}
