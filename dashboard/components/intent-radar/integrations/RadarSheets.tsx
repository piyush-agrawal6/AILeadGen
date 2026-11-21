"use client";
import {useState} from 'react';
import {useRadarRead} from '../provider';
import {useWorkspace} from '@/components/workspaces/use-workspace';
import {request} from '@/lib/intelligence';
import type {ExportSelection} from '../RadarExport';

export type SheetStatus={configured:boolean;health:string;connection:null|{id:string;connected_by:string;status:string;scopes:string[];last_success_at:string|null}};
type Review={id:string;fingerprint:string;row_count:number;target_range:string;spreadsheet_id:string;status:string;last_error_code:string|null;columns?:string[];existing_cells?:number;existing_preview?:(string|number|boolean)[][];preview?:string[][]};
export function RadarSheets({selection}:{selection?:ExportSelection}){
  const org=useWorkspace().data?.active_organization_id;
  return org?<Management key={org} selection={selection}/>:<p>Select a workspace.</p>;
}
function Management({selection}:{selection?:ExportSelection}){
  const state=useRadarRead<SheetStatus>('/sheets'),history=useRadarRead<{items:Review[]}>('/sheets/history',!!state.data?.configured);
  const [sid,setSid]=useState(''),[tabs,setTabs]=useState<string[]>([]),[tab,setTab]=useState(''),[dataset,setDataset]=useState<ExportSelection['dataset']>('signals'),[search,setSearch]=useState(''),[review,setReview]=useState<Review|null>(null),[busy,setBusy]=useState(false),[notice,setNotice]=useState('');
  const [startRow,setStartRow]=useState(1);
  const conn=state.data?.connection;
  async function run(fn:()=>Promise<void>){if(busy)return;setBusy(true);setNotice('');try{await fn();await Promise.all([state.refetch(),history.refetch()]);}catch(e){setNotice(e instanceof Error?e.message:'Request failed.');}finally{setBusy(false);}}
  const post=<T,>(path:string,body?:unknown)=>request<T>('/intent-radar/sheets/'+path,{method:'POST',body:body===undefined?undefined:JSON.stringify(body)});
  async function connect(){const {authorization_url}=await post<{authorization_url:string}>('authorize');const u=new URL(authorization_url);if(u.origin!=='https://accounts.google.com'||!u.searchParams.get('state'))throw Error('Invalid Google authorization response.');location.assign(u.href);}
  if(!state.data||state.isError||!state.data.configured)return <p role="status">{state.isLoading?'Checking Sheets availability…':'Sheets is unavailable for this workspace or requires server configuration.'}</p>;
  return <section className="rounded-lg border bg-card p-4 space-y-3"><h2>Google Sheets · Manual export</h2><p>{state.data.health}{conn?.connected_by&&` · Authorized by ${conn.connected_by}`} {conn?.last_success_at&&` · Last verified ${conn.last_success_at}`}</p><small>Google account email is not requested. Authorization requires the spreadsheets scope.</small>
    <fieldset disabled={busy} className="space-y-3"><button className="control" onClick={()=>void run(connect)}>Authorize Google Sheets writes</button>
    {conn&&conn.status!=='DISCONNECTED'&&<><button className="control" onClick={()=>void run(async()=>{await request('/intent-radar/sheets/connections/'+conn.id,{method:'DELETE'});setReview(null);setTabs([]);setNotice('Disconnected locally. Manage Google grants in your Google account.');})}>Disconnect</button>
    <label>Existing spreadsheet URL or ID <input value={sid} onChange={e=>{setSid(e.target.value);setTabs([]);setReview(null);}}/></label><button className="control" onClick={()=>void run(async()=>{const m=await post<{tabs:{title:string}[]}>('connections/'+conn.id+'/inspect',{spreadsheet:sid});setTabs(m.tabs.map(t=>t.title));setTab(m.tabs[0]?.title||'');})}>Check access and load worksheets</button>
    {tabs.length>0&&<><label>Worksheet <select value={tab} onChange={e=>{setTab(e.target.value);setReview(null);}}>{tabs.map(t=><option key={t}>{t}</option>)}</select></label>
    {selection?<p>Selected {selection.dataset} records</p>:<><label>Dataset <select value={dataset} onChange={e=>{setDataset(e.target.value as ExportSelection['dataset']);setReview(null);}}>{['signals','opportunities','saved'].map(x=><option key={x}>{x}</option>)}</select></label><label>Filter by evidence text <input value={search} onChange={e=>{setSearch(e.target.value);setReview(null);}}/></label></>}
    <label>Start row <input type="number" min={1} max={100000} value={startRow} onChange={e=>{setStartRow(Number(e.target.value));setReview(null)}}/></label>
    <button className="control" onClick={()=>void run(async()=>setReview(await post<Review>('connections/'+conn.id+'/exports',{selection:selection||{dataset,search},spreadsheet:sid,sheet:tab,start_row:startRow,request_id:crypto.randomUUID()})))}>Preview write (100 records maximum)</button></>}
    {review&&<div><p>{review.row_count} records → {review.spreadsheet_id} / {review.target_range}</p><p>Existing nonempty cells in this range: {review.existing_cells}</p>{!!review.existing_cells&&<details><summary>Existing values (first five rows)</summary><div className="overflow-auto"><table><tbody>{review.existing_preview?.map((r,i)=><tr key={i}>{r.map((v,j)=><td key={j}>{String(v)}</td>)}</tr>)}</tbody></table></div></details>}<div className="overflow-auto"><table><tbody>{[review.columns||[],...(review.preview||[])].map((r,i)=><tr key={i}>{r.map((v,j)=><td key={j}>{v}</td>)}</tr>)}</tbody></table></div><button className="control" onClick={()=>void run(async()=>{await post('exports/'+review.id+'/approve',{review_digest:review.fingerprint,confirmation:'OVERWRITE_REVIEWED_RANGE'});setReview(null);setNotice('Approved. Refresh history to check the write outcome.');})}>Approve overwriting this exact range</button></div>}
    </>}
    <button className="control" onClick={()=>void history.refetch()}>Refresh export history</button>{history.data?.items.map(j=><div key={j.id}>{j.target_range} · {j.status} {j.last_error_code} {['FAILED','UNCERTAIN','RUNNING','QUEUED'].includes(j.status)&&<button onClick={()=>void run(async()=>{await post('exports/'+j.id+'/'+(j.status==='QUEUED'?'approve':'retry'),{review_digest:j.fingerprint,confirmation:'OVERWRITE_REVIEWED_RANGE'});})}>Confirm repeat overwrite of {j.spreadsheet_id} {j.target_range}</button>}{['DRAFT','QUEUED','FAILED','UNCERTAIN'].includes(j.status)&&<button onClick={()=>void run(async()=>{await post('exports/'+j.id+'/cancel');})}>Cancel</button>}</div>)}</fieldset><p role="status">{notice}</p></section>;
}
