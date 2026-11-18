"use client";
import {useState} from 'react';
import {useRadarRead,useRadarMutation,useRadarCapabilities} from './provider';
import {Field,Badge,ErrorState} from './ui';

type Config={id?:string;name:string;family:'rss'|'discourse'|'atom';endpoint:string;policy_reference:string;attribution:string;retention_days:number;polling_minutes:number;enabled:boolean;ai_processing_authorized?:boolean};
type Preset={preset_id:string;name:string;family:'discourse'|'atom';endpoint:string;policy_reference:string;attribution:string;content_kind?:string;ai_processing_authorized:boolean;host_approved:boolean;configured:boolean;enabled:boolean};
type GitHubStatus={app_configured:boolean;oauth_configured:boolean;webhooks_configured:boolean;public_search_available:boolean;app_slug:string;status:string;installation_id:string|null;account_login:string|null;account_type:string|null;repositories:{id:number;full_name:string;private:boolean;selected:boolean}[];last_verified_at:string|null;last_error_code:string|null};
type HealthItem={provider:string;name?:string;availability?:string;state:string;last_success:string|null;last_error?:{code:string}|null;daily_requests_reserved?:number;daily_reservation_limit?:number;consecutive_failures?:number;stream_health?:{state:string;sequence:number;enabled:boolean;updated_at:string|null}};

const initial:Config={name:'',family:'rss',endpoint:'',policy_reference:'',attribution:'',retention_days:7,polling_minutes:60,enabled:false,ai_processing_authorized:false};

export function SourceManagement(){
 const access=useRadarCapabilities();
 const configs=useRadarRead<{items:Config[]}>('/sources/configurations');
 const presets=useRadarRead<{items:Preset[]}>('/sources/presets');
 const github=useRadarRead<GitHubStatus>('/sources/github/status');
 const health=useRadarRead<{items:HealthItem[]}>('/sources/health');
 const mutation=useRadarMutation();
 const [form,setForm]=useState<Config>(initial);
 const [repoSelection,setRepoSelection]=useState<number[]|null>(null);
 const [error,setError]=useState('');
 const [notice,setNotice]=useState('');

 async function save(){
  try{
   const {id,...body}=form;
   await mutation.mutateAsync({path:'/sources/configurations'+(id?'/'+id:''),method:id?'PUT':'POST',body});
   setForm(initial);setError('');setNotice('Feed configuration saved.');
  }catch(e){setError((e as Error).message);}
 }

 async function togglePreset(preset:Preset){
  setError('');setNotice('');
  try{
   await mutation.mutateAsync({path:`/sources/presets/${preset.preset_id}/enable`,method:'POST',body:{enabled:!preset.enabled}});
   setNotice(`${preset.name} ${preset.enabled?'disabled':'enabled'}.`);
  }catch(e){setError((e as Error).message);}
 }

 async function connectGitHub(mode:'oauth'|'install'){
  setError('');
  try{
   const res=await mutation.mutateAsync({path:'/sources/github/oauth/start',method:'POST',body:{}}) as {authorize_url:string;install_url:string};
   window.location.assign(mode==='install'?res.install_url:res.authorize_url);
  }catch(e){setError((e as Error).message);}
 }

 async function saveRepos(){
  if(!repoSelection)return;
  setError('');
  try{
   await mutation.mutateAsync({path:'/sources/github/repositories',method:'PUT',body:{repository_ids:repoSelection}});
   setRepoSelection(null);setNotice('Authorized GitHub repositories updated.');
  }catch(e){setError((e as Error).message);}
 }

 async function disconnectGitHub(){
  setError('');
  try{
   await mutation.mutateAsync({path:'/sources/github/disconnect',method:'POST',body:{}});
   setRepoSelection(null);setNotice('GitHub workspace connection disconnected.');
  }catch(e){setError((e as Error).message);}
 }

 async function pollJetstream(){
  setError('');setNotice('');
  try{
   const r=await mutation.mutateAsync({path:'/sources/bluesky/stream-poll',method:'POST',body:{}}) as {status:string;events:number;sequence:number};
   setNotice(`Bluesky Jetstream polled: ${r.status} (${r.events} events, seq ${r.sequence}).`);
  }catch(e){setError((e as Error).message);}
 }

 const gh=github.data;
 const selectedRepoIds=repoSelection??(gh?.repositories?.filter(r=>r.selected).map(r=>r.id)||[]);
 const bskyStream=health.data?.items?.find(i=>i.provider==='bluesky')?.stream_health;

 return <section className="ir-panel ir-form-section">
  <h2>Source health, connections & feed catalog</h2>
  <div className="ir-meta">
   {health.data?.items?.map(s=><div key={s.provider}>
    <strong>{s.name||s.provider}</strong> <Badge>{s.availability||s.state}</Badge> <Badge>{s.state}</Badge>
    <small>Last success: {s.last_success?new Date(s.last_success).toLocaleString():'Never'}</small>
    <small>{s.daily_requests_reserved??0} / {s.daily_reservation_limit??'unknown'} requests reserved today · {s.consecutive_failures??0} consecutive failures</small>
    {s.last_error&&<p role="status">Last error: {s.last_error.code}</p>}
   </div>)}
  </div>
  {health.error&&<ErrorState message={'Source health could not be loaded: '+health.error.message} retry={()=>void health.refetch()}/>}

  {gh&&<div className="ir-panel ir-form-section" style={{marginTop:12}}>
   <div className="ir-section-heading">
    <div><h3>GitHub workspace connection</h3><small>Public GitHub discovery works via the server GitHub App. Connect your workspace GitHub installation to monitor authorized repositories with strict tenant isolation.</small></div>
    <Badge>{gh.status}</Badge>
   </div>
   <div className="ir-meta">
    <small>Public search: {gh.public_search_available?'Available':'Disabled'}</small>
    <small>Customer OAuth: {gh.oauth_configured?'Configured':'Unavailable'}</small>
    <small>Webhooks: {gh.webhooks_configured?'Active (HMAC-SHA256)':'Pending GitHub App webhook secret'}</small>
    {gh.account_login&&<small>Connected account: {gh.account_login} ({gh.account_type}) · Installation #{gh.installation_id}</small>}
   </div>
   {access.data?.can_manage&&<div className="ir-actions">
    {gh.status!=='CONNECTED'?<>
     <button className="ir-primary" disabled={mutation.isPending||!gh.oauth_configured} onClick={()=>void connectGitHub('oauth')}>Connect GitHub Account</button>
     <button disabled={mutation.isPending||!gh.oauth_configured} onClick={()=>void connectGitHub('install')}>Install GitHub App</button>
    </>:<>
     <button disabled={mutation.isPending} onClick={()=>void connectGitHub('install')}>Manage Installation</button>
     <button disabled={mutation.isPending} onClick={()=>void disconnectGitHub()}>Disconnect GitHub</button>
    </>}
   </div>}
   {gh.status==='CONNECTED'&&gh.repositories.length>0&&<details>
    <summary>Authorized repositories ({selectedRepoIds.length} of {gh.repositories.length} selected)</summary>
    <div className="ir-choice-grid">{gh.repositories.map(r=><label className="ir-choice" key={r.id}><input type="checkbox" disabled={!access.data?.can_manage} checked={selectedRepoIds.includes(r.id)} onChange={e=>{const next=e.target.checked?[...selectedRepoIds,r.id]:selectedRepoIds.filter(id=>id!==r.id);setRepoSelection(next);}}/><span>{r.full_name} {r.private&&<Badge>Private</Badge>}</span></label>)}</div>
    {access.data?.can_manage&&repoSelection&&<div className="ir-actions"><button className="ir-primary" disabled={mutation.isPending} onClick={()=>void saveRepos()}>Save repository selection</button></div>}
   </details>}
  </div>}

  {bskyStream&&<div className="ir-summary">
   <div><strong>Bluesky Jetstream v2 Stream</strong> <Badge>{bskyStream.state}</Badge><small>Cursor seq: {bskyStream.sequence} · {bskyStream.updated_at?'Last poll '+new Date(bskyStream.updated_at).toLocaleString():'Not polled yet'}</small></div>
   {access.data?.can_manage&&bskyStream.enabled&&<button disabled={mutation.isPending} onClick={()=>void pollJetstream()}>Poll stream now</button>}
  </div>}

  {presets.data?.items&&presets.data.items.length>0&&<details>
   <summary>Curated Discourse RSS (10) & Atom (10) feeds</summary>
   <p>Enable approved public Discourse community feeds and release/research Atom 1.0 feeds. Atom releases and research papers are classified as market/technology intelligence, never fabricated buyers.</p>
   <div className="ir-stack">
    {presets.data.items.map(p=><div className="ir-summary" key={p.preset_id}>
     <div><strong>{p.name}</strong> <Badge>{p.family}</Badge> <Badge>{p.enabled?'Enabled':p.host_approved?'Available':'Host approval required'}</Badge>{!p.ai_processing_authorized&&<Badge>AI gated</Badge>}<small>{p.endpoint}</small></div>
     {access.data?.can_manage&&<button disabled={mutation.isPending||!p.host_approved} onClick={()=>void togglePreset(p)}>{p.enabled?'Disable':'Enable'}</button>}
    </div>)}
   </div>
  </details>}

  {configs.data?.items?.map(config=><div className="ir-summary" key={config.id}><div><strong>{config.name}</strong> <Badge>{config.family}</Badge><small>{config.endpoint} · {config.enabled?'Enabled':'Disabled'} · {config.polling_minutes}m minimum polling</small></div>{access.data?.can_manage&&<button onClick={()=>setForm(config)}>Edit source</button>}</div>)}

  {access.data?.can_manage&&<details><summary>{form.id?'Edit approved feed':'Configure a custom approved public feed'}</summary><p>Only platform-approved HTTPS hosts are accepted. Record the publisher’s permission/terms and required attribution. Discourse supports specifically permitted RSS/Atom endpoints.</p><div className="ir-form-grid"><Field label="Feed name"><input value={form.name} maxLength={120} onChange={e=>setForm(f=>({...f,name:e.target.value}))}/></Field><Field label="Source family"><select value={form.family} onChange={e=>setForm(f=>({...f,family:e.target.value as Config['family']}))}><option value="rss">RSS / Atom</option><option value="discourse">Approved Discourse</option><option value="atom">Atom Feeds</option></select></Field></div><Field label="Permitted feed endpoint"><input value={form.endpoint} maxLength={1000} onChange={e=>setForm(f=>({...f,endpoint:e.target.value}))}/></Field><Field label="Usage permission / terms reference"><input value={form.policy_reference} maxLength={1000} onChange={e=>setForm(f=>({...f,policy_reference:e.target.value}))}/></Field><Field label="Required source attribution"><input value={form.attribution} maxLength={300} onChange={e=>setForm(f=>({...f,attribution:e.target.value}))}/></Field><div className="ir-form-grid"><Field label="Retention days"><input type="number" min={1} max={30} value={form.retention_days} onChange={e=>setForm(f=>({...f,retention_days:Number(e.target.value)}))}/></Field><Field label="Polling interval (minutes)"><input type="number" min={60} max={1440} value={form.polling_minutes} onChange={e=>setForm(f=>({...f,polling_minutes:Number(e.target.value)}))}/></Field></div><label><input type="checkbox" checked={form.enabled} onChange={e=>setForm(f=>({...f,enabled:e.target.checked}))}/> Enable this approved source</label><div className="ir-actions"><button className="ir-primary" disabled={mutation.isPending} onClick={()=>void save()}>Save source configuration</button><button onClick={()=>setForm(initial)}>Clear source form</button></div></details>}
  {notice&&<p role="status">{notice}</p>}
  {error&&<ErrorState message={error}/>}
 </section>;
}
