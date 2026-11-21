"use client";
import {useState} from 'react';
import Link from 'next/link';
import {Braces,Download,FileSpreadsheet,Network,Webhook} from 'lucide-react';
import {SearchInput} from '@/components/ui/search-input';
import {useRadarRead} from '../provider';
import type {SheetStatus} from './RadarSheets';
import type {CrmState} from './HubSpotConnection';

export function CustomerIntegrationsCatalog(){
  const destinations=useRadarRead<{files:boolean;developer:boolean;mcp:boolean;webhooks:boolean}>('/destinations');
  const sheets=useRadarRead<SheetStatus>('/sheets');
  const crm=useRadarRead<CrmState>('/hubspot');
  const [query,setQuery]=useState(''),[category,setCategory]=useState('All');
  const state=destinations.isError?undefined:destinations.data;
  const sheet=state?.files && !sheets.isError && sheets.data?.configured?sheets.data:undefined;
  const rows=[
    ...(crm.data?.configured&&!crm.isError?[{name:'HubSpot',icon:Network,category:'CRM',description:'Manage your workspace CRM connection.',status:crm.data.connection?.status==='CONNECTED'?'Connected':crm.data.connection?.status==='REAUTH_REQUIRED'?'Reconnect required':'Not connected',href:'/intent-radar/integrations/hubspot',action:crm.data.connection?.status==='CONNECTED'?'Manage':'Connect'}]:[]),
    {name:'Google Sheets',icon:FileSpreadsheet,category:'Spreadsheets & Export',description:'Write reviewed records to an approved range.',status:sheet?.health||'Restricted',href:sheet?'/intent-radar/integrations/sheets':null,action:sheet?.health==='Not Connected'?'Connect':'Manage'},
    {name:'File exports',icon:Download,category:'Spreadsheets & Export',description:'Download CSV, Excel, PDF or JSON.',status:state?.files?'Available':'Restricted',href:state?.files?'/intent-radar/discover':null,action:'Select records'},
    {name:'Webhooks',icon:Webhook,category:'Automation',description:'Deliver signed events to an authorized endpoint.',status:state?.webhooks?'Available':'Restricted',href:state?.webhooks?'/intent-radar/integrations/webhooks':null,action:'Configure'},
    {name:'REST API',icon:Braces,category:'Developer',description:'Read workspace data with scoped keys.',status:state?.developer?'Available':'Restricted',href:state?.developer?'/settings?category=developer&tab=keys':null,action:'Manage keys'},
    {name:'MCP',icon:Network,category:'Developer',description:'Connect an authorized research client.',status:state?.mcp?'Available':'Restricted',href:state?.mcp?'/settings?category=developer&tab=mcp':null,action:'Configure'},
  ];
  const matches=(name:string,cat:string,desc='')=>(category==='All'||category===cat)&&`${name} ${desc}`.toLowerCase().includes(query.trim().toLowerCase());
  const visible=rows.filter(r=>matches(r.name,r.category,r.description));const planned=rows.some(r=>r.name==='HubSpot')?[]:['HubSpot'].filter(n=>matches(n,'CRM'));
  return <main className="mx-auto w-full max-w-5xl space-y-5 pb-8">
    <header><h1 className="text-2xl font-semibold tracking-tight">Integrations</h1><p className="mt-1 text-sm text-muted-foreground">Connect tools and manage workspace destinations.</p></header>
    <div className="flex flex-wrap items-end gap-3"><div className="min-w-0 grow"><SearchInput value={query} onChange={e=>setQuery(e.target.value)} onClear={()=>setQuery('')} aria-label="Search integrations" placeholder="Search integrations"/></div><label className="text-xs text-muted-foreground">Category<select className="control mt-1 block max-w-full" value={category} onChange={e=>setCategory(e.target.value)}>{['All','CRM','Spreadsheets & Export','Automation','Developer'].map(c=><option key={c}>{c}</option>)}</select></label></div>
    {destinations.isError&&<p role="status" className="text-sm">Workspace destinations could not be loaded. <button className="underline" onClick={()=>void destinations.refetch()}>Retry</button></p>}
    {(['Connected','Available','Restricted'] as const).map(group=>{const items=visible.filter(r=>(r.status==='Connected'?'Connected':r.href?'Available':'Restricted')===group);return items.length>0&&<section key={group}><h2 className="mb-2 text-sm font-semibold">{group}</h2><ul className="divide-y rounded-lg border bg-card">{items.map(r=><li key={r.name} className="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 py-3"><r.icon size={18} aria-hidden="true" className="text-muted-foreground"/><div className="min-w-0 flex-1 basis-44"><h3 className="text-sm font-medium">{r.name}</h3><p className="text-xs text-muted-foreground">{r.description}</p></div>{r.href&&<Link className="control text-xs" href={r.href} aria-label={`${r.action}: ${r.name}`}>{r.action}</Link>}{r.name==='Google Sheets'&&sheet&&sheet.health!=='Connected'&&<span className="text-xs text-muted-foreground">{sheet.health}</span>}</li>)}</ul></section>})}
    {planned.length>0&&<details className="rounded-lg border px-4 py-3 text-sm"><summary className="cursor-pointer font-medium">Other integrations</summary><p className="mt-2 text-muted-foreground">HubSpot · Not available</p></details>}
    {!visible.length&&!planned.length&&<p role="status">No matching integrations.</p>}
  </main>;
}
