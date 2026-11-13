"use client";
import Link from 'next/link';
import {useState} from 'react';
import {useRouter} from 'next/navigation';
import * as Menu from '@radix-ui/react-dropdown-menu';
import {Plus,Radio,Play,Pause,Copy,Archive,Pencil,MoreHorizontal,ArrowRight,BookOpen} from 'lucide-react';
import type {IntentMonitor,IntentJob,IntentPage,IntentSignal} from '@/lib/intent-radar';
import {useRadarRead,useRadarMutation,useRadarCapabilities} from './provider';
import {Badge,Field,Modal,PageHeading,EmptyState,ErrorState,LoadingSkeleton} from './ui';
import {MonitorWizard} from './wizard';
import {JobPanel} from './jobs';
import {SignalTable} from './signals';
import {ProviderLogo} from './provider-logo';
import {ScheduleControls} from './advanced-controls';

export function ManagedMonitorCard({monitor:m}:{monitor:IntentMonitor}){
 const mutation=useRadarMutation(),access=useRadarCapabilities(),[job,setJob]=useState<string|null>(null),[archive,setArchive]=useState(false),[error,setError]=useState('');
 const signals=useRadarRead<IntentPage<IntentSignal>>('/signals?monitor_id='+m.id+'&page_size=1');
 const disabled=!access.data?.can_write||mutation.isPending;
 async function status(value:IntentMonitor['status']){setError('');try{await mutation.mutateAsync({path:'/monitors/'+m.id,method:'PUT',body:{name:m.name,description:m.description,goal:m.goal,configuration:m.configuration,status:value,revision:m.revision}});setArchive(false)}catch(e){setError((e as Error).message)}}
 async function run(){setError('');try{const result=await mutation.mutateAsync({path:'/discover',body:{monitor_id:m.id,configuration:m.configuration,request_id:crypto.randomUUID()}}) as IntentJob;setJob(result.id)}catch(e){setError((e as Error).message)}}
  const selected=m.configuration.sources||['hacker_news'];
  const sourceNames=selected.map(id=>access.data?.sources.find(s=>s.id===id)?.name||id);
  return <article className="ir-panel ir-monitor"><div className="ir-card-top"><span className="ir-source">{sourceNames.map(name=><span key={name}><ProviderLogo provider={name} size={24}/>{name} </span>)}</span><Badge>{m.status}</Badge></div><h3><Link href={'/intent-radar/monitors/'+m.id}>{m.name}</Link></h3><p>{m.description||m.goal||'A saved search for relevant public conversations.'}</p><div className="ir-chips">{m.configuration.keywords.map(k=><span className="ir-chip" key={k}>{k}</span>)}</div><dl className="ir-review"><div><dt>Last checked</dt><dd>{m.last_checked?new Date(m.last_checked).toLocaleString():'Never'}</dd></div><div><dt>Signals found</dt><dd>{signals.data?.total??'—'} <Link className="ir-link" href={'/intent-radar/signals?monitor_id='+m.id}>View Signals</Link></dd></div><div><dt>Created</dt><dd>{new Date(m.created_at).toLocaleDateString()} · {m.schedule?.frequency||'Manual'} checks</dd></div></dl>
  <div className="ir-monitor-actions"><div className="ir-actions"><button className="ir-primary" aria-label="Run manual check" disabled={disabled||m.status!=='Active'} title={m.status!=='Active'?'Activate or resume this monitor to run a check.':undefined} onClick={()=>void run()}><Play size={14}/>Run Check</button><Link className="ir-button" href={'/intent-radar/monitors/'+m.id}><Pencil size={14}/>Edit</Link></div><Menu.Root><Menu.Trigger className="ir-icon-button" aria-label={'Actions for '+m.name}><MoreHorizontal size={18}/></Menu.Trigger><Menu.Portal><Menu.Content className="ir-menu" sideOffset={6} collisionPadding={12}><Menu.Item className="ir-menu-item" disabled={disabled} onSelect={()=>{void mutation.mutateAsync({path:'/monitors/'+m.id+'/duplicate',body:{request_id:crypto.randomUUID()}}).catch(()=>{})}}><Copy size={15}/>Duplicate</Menu.Item><Menu.Item className="ir-menu-item" disabled={disabled||m.status==='Archived'} onSelect={()=>void status(m.status==='Active'?'Paused':'Active')}>{m.status==='Active'?<Pause size={15}/>:<Play size={15}/>} {m.status==='Active'?'Pause':m.status==='Paused'?'Resume':'Activate'}</Menu.Item><Menu.Item className="ir-menu-item" disabled={disabled} onSelect={()=>m.status==='Archived'?void status('Draft'):setArchive(true)}><Archive size={15}/>{m.status==='Archived'?'Restore draft':'Archive'}</Menu.Item></Menu.Content></Menu.Portal></Menu.Root></div>
   <p>Sources: {(m.configuration.sources||['hacker_news']).join(', ')}</p><ScheduleControls monitor={m}/>
   {error&&<ErrorState message={error}/>}{job&&<JobPanel id={job}/>}{m.last_job_id&&!job&&<details><summary>Last-run status and history</summary><JobPanel id={m.last_job_id}/></details>}
  <Modal open={archive} onOpenChange={setArchive} title="Archive this monitor?" description="This removes the monitor from your current view. Its signals and history stay intact, and you can restore it later."><div className="ir-actions"><button onClick={()=>setArchive(false)}>Cancel</button><button className="ir-primary" disabled={mutation.isPending} onClick={()=>void status('Archived')}>Archive monitor</button></div></Modal>
 </article>;
}

function MonitorRunHistory({id}:{id:string}){
 const history=useRadarRead<{items:{id:string;created_at:string;provider:string|null;status:string|null;result:{requests?:number;scanned?:number;coverage?:string}}[]}>('/monitors/'+id+'/runs');
 return <section className="ir-panel"><h2>Monitor run history</h2>{history.error?<ErrorState message={history.error.message} retry={()=>void history.refetch()}/>:!history.data?<LoadingSkeleton/>:history.data.items.length?<ul className="ir-source-limits">{history.data.items.map((run,index)=><li key={run.id+':'+run.provider+':'+index}><strong>{new Date(run.created_at).toLocaleString()} · {run.provider||'Awaiting source dispatch'} · {run.status||'Pending'}</strong><p>{run.result.coverage||'No completed source coverage yet.'}</p><small>{run.result.scanned??'Unknown'} scanned · {run.result.requests??'Unknown'} requests</small></li>)}</ul>:<p>No monitor checks have been requested.</p>}<small>Latest 100 source-run records. Source health is available in Integrations & MCP.</small></section>;
}

export function MonitorsExperience({route}:{route:string}){
  const router=useRouter(),[tab,setTabValue]=useState('Current'),[search,setSearchValue]=useState(''),[learn,setLearn]=useState(false),[editing,setEditing]=useState(false),[page,setPage]=useState(1);
  const setTab=(value:string)=>{setTabValue(value);setPage(1)},setSearch=(value:string)=>{setSearchValue(value);setPage(1)};
  const query=useRadarRead<IntentPage<IntentMonitor>>('/monitors?page_size=20&page='+page+'&status='+tab+'&search='+encodeURIComponent(search));
 const id=route.startsWith('monitors/')&&route!=='monitors/new'?route.split('/')[1]:'';
 const detail=useRadarRead<IntentMonitor>('/monitors/'+id,!!id),related=useRadarRead<IntentPage<IntentSignal>>('/signals?monitor_id='+id,!!id),access=useRadarCapabilities();
 if(query.error||detail.error)return <ErrorState message={(query.error||detail.error)!.message} retry={()=>void query.refetch()}/>;
 if(!query.data||id&&!detail.data)return <LoadingSkeleton/>;
  const monitors=query.data.items;
 return <div className="ir-page"><PageHeading title={detail.data?.name||'Monitors'} description="Save the topics that matter. Run a controlled check whenever you need fresh conversations." actions={access.data?.can_write?<Link className="ir-button ir-primary" href="/intent-radar/monitors/new"><Plus size={16}/>Create Monitor</Link>:<Badge>Read-only access</Badge>}/>
  {id&&detail.data?<><ManagedMonitorCard monitor={detail.data}/><div className="ir-section-heading"><h2>Matched signals</h2><button disabled={!access.data?.can_write} onClick={()=>setEditing(true)}>Edit Monitor</button></div><SignalTable signals={related.data?.items||[]}/></>:<><div className="ir-toolbar"><div className="ir-tabs">{['Current','Archived'].map(t=><button key={t} aria-pressed={tab===t} onClick={()=>setTab(t)}>{t}</button>)}</div><Field label="Search monitors"><input type="search" value={search} placeholder="Find a monitor…" onChange={e=>setSearch(e.target.value)}/></Field><small>{monitors.length} monitors</small></div>
  {monitors.length?<div className="ir-cards">{monitors.map(m=><ManagedMonitorCard key={m.id} monitor={m}/>)}</div>:search||tab==='Archived'?<EmptyState title={search?'No monitors match your search':'No archived monitors'} description={search?'Try another monitor name or clear your search.':'Archived monitors appear here with their history preserved.'} action={search?<button onClick={()=>setSearch('')}>Clear search</button>:undefined} icon={Radio}/>:<div className="ir-split"><EmptyState title="Monitor the conversations that matter to your business" description="Save keywords and topics, then run controlled checks to discover new public discussions." icon={Radio} action={<><Link className="ir-button ir-primary" href="/intent-radar/monitors/new">Create Monitor <ArrowRight size={15}/></Link><button onClick={()=>setLearn(true)}><BookOpen size={15}/>Learn How Monitors Work</button></>}/><section className="ir-panel"><div className="ir-card-top"><Radio size={22}/><Badge>Illustrative preview</Badge></div><h3>Your next research monitor</h3><p>Example only — not a live monitor or discovered conversation.</p><div className="ir-chips"><span className="ir-chip">your topic</span><span className="ir-chip">recommendations</span></div><div className="ir-summary"><ProviderLogo provider="Hacker News" size={22}/><div><strong>Recent public discussions</strong><small>You choose when to check and what to save.</small></div></div></section></div>}</>}
  {(route==='monitors/new'||editing)&&<MonitorWizard existing={detail.data} open onClose={()=>{if(route==='monitors/new')router.push('/intent-radar/monitors');else setEditing(false)}}/>}
  {id&&<MonitorRunHistory id={id}/>}
  {!id&&query.data.total>20&&<nav className="ir-pagination" aria-label="Monitor pages"><span>Page {page} of {Math.ceil(query.data.total/20)}</span><button disabled={page<=1} onClick={()=>setPage(page-1)}>Previous</button><button disabled={page*20>=query.data.total} onClick={()=>setPage(page+1)}>Next</button></nav>}
  <Modal open={learn} onOpenChange={setLearn} title="How monitors work" description="A monitor is a saved set of keywords, topics and intent preferences."><ol className="ir-source-limits"><li>Create a monitor with at least one keyword.</li><li>Choose Run Check to retrieve a limited set of recent public stories.</li><li>Review matching evidence and save useful opportunities.</li></ol><p>Checks are manual. Saving, duplicating or editing a monitor does not start discovery.</p><Link className="ir-button ir-primary" href="/intent-radar/monitors/new">Create Monitor</Link></Modal>
 </div>;
}
