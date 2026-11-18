"use client";
import Link from 'next/link';
import {CommandCentre} from './command-centre';
import {Activity,Target,Radio,Bookmark,Bell,CheckCheck,Search,ArrowRight,ArrowUpRight,Radar} from 'lucide-react';
import type {IntentOverview,IntentSignal} from '@/lib/intent-radar';
import {useRadarRead,useRadarCapabilities,useRadarMutation} from './provider';
import {Badge,LoadingSkeleton,ErrorState} from './ui';
import {SignalScore} from './signals';
import {ProviderLogo} from './provider-logo';

type Summary=Pick<IntentOverview,'new_signals'|'reviewed_signals'|'high_relevance'|'active_monitors'|'saved_opportunities'|'unread_alerts'|'trends'>&{operations?:{backlog:number;scheduler_heartbeat_at:string|null;scheduler_heartbeat_fresh:boolean;worker_status_basis:string}};

export function OverviewDashboard(){
 const summary=useRadarRead<Summary>('/overview/summary'),details=useRadarRead<IntentOverview>('/overview',!!summary.data);
 if(!summary.data)return <div className="ir-page pb-home"><CommandCentre/>{summary.error?<ErrorState message={summary.error.message} retry={()=>void summary.refetch()}/>:<LoadingSkeleton/>}</div>;
 if(details.data)return <div className="ir-page pb-home"><CommandCentre/><OverviewContent d={{...details.data,...summary.data}}/></div>;
 const d=summary.data;
 const summaryMetrics=[['New Signals',d.new_signals,Activity,'/signals?status=New'],['High-Relevance Signals',d.high_relevance,Target,'/signals?min_score=85'],['Active Monitors',d.active_monitors,Radio,'/monitors'],['Saved Opportunities',d.saved_opportunities,Bookmark,'/opportunities'],['Reviewed Signals',d.reviewed_signals,CheckCheck,'/signals?status=Reviewed'],['Unread Alerts',d.unread_alerts,Bell,'/alerts']] as const;
 return <div className="ir-page pb-home"><CommandCentre/><div className="ir-section-heading"><h2>Workspace overview</h2><Link className="ir-link" href="/intent-radar/signals">Review signals →</Link></div><div className="pb-dash-metrics">{summaryMetrics.map(([name,value,Icon,href])=><Link className="pb-dash-metric-card" key={name} href={'/intent-radar'+href}><div className="pb-dash-metric-header"><span>{name}</span><Icon size={14}/></div><strong className="pb-dash-metric-value">{value}</strong></Link>)}</div>{details.error?<ErrorState message={details.error.message} retry={()=>void details.refetch()}/>:<section className="ir-panel text-center py-6" role="status"><p className="text-sm text-muted-foreground m-0">Your workspace totals are ready. Loading recent evidence and activity…</p></section>}</div>;
}

function OverviewContent({d}:{d:IntentOverview&Summary}){
 const fresh=!d.recent_signals.length&&!d.monitors.length&&!d.opportunities.length&&!d.alerts.length;
 const metrics=[['New Signals',d.new_signals,Activity,'/signals?status=New'],['High-Relevance Signals',d.high_relevance,Target,'/signals?min_score=85'],['Active Monitors',d.active_monitors,Radio,'/monitors'],['Saved Opportunities',d.saved_opportunities,Bookmark,'/opportunities'],['Reviewed Signals',d.reviewed_signals,CheckCheck,'/signals?status=Reviewed'],['Unread Alerts',d.unread_alerts,Bell,'/alerts']] as const;
 const trends=[...d.trends].reverse(),max=Math.max(1,...trends.map(t=>t.volume));
 const pendingOpportunities=d.opportunities.filter(o=>['New','Reviewing'].includes(o.status));
 const signalsToDisplay=[...d.recent_signals].sort((a,b)=>b.score-a.score).slice(0,10);

 if(fresh){
  return (
   <>
    <div className="pb-dash-metrics-section">
     <div className="ir-section-heading pb-metrics-heading">
      <h2>Workspace overview</h2>
      <Link className="ir-link" href="/intent-radar/discover">Start discovery <ArrowRight size={14}/></Link>
     </div>
     <div className="pb-dash-metrics">
      {metrics.map(([name,count,Icon,href])=>(
       <Link className="pb-dash-metric-card" key={name} href={'/intent-radar'+href}>
        <div className="pb-dash-metric-header"><span>{name}</span><Icon size={14}/></div>
        <strong className="pb-dash-metric-value">{count}</strong>
       </Link>
      ))}
     </div>
    </div>
    <section className="ir-panel ir-onboarding">
     <div>
      <p className="ir-eyebrow">GET STARTED</p>
      <h2>No signals collected yet</h2>
      <p>Run a discovery across your connected sources or create a monitor to start tracking buying intent automatically.</p>
      <div className="mt-3 flex flex-wrap gap-2">
       <Link className="ir-button ir-primary" href="/intent-radar/discover"><Search size={15}/>Discover Intent</Link>
       <Link className="ir-button" href="/intent-radar/monitors/new"><Radio size={15}/>Create Monitor</Link>
       <Link className="ir-button" href="/settings?category=integrations&tab=sources">Configure Sources</Link>
      </div>
     </div>
     <div className="ir-radar-mini" aria-hidden="true"><Radar size={36}/></div>
    </section>
   </>
  );
 }

 return (
  <>
   {/* Section B: Workspace Metrics Grid */}
   <div className="pb-dash-metrics-section">
    <div className="ir-section-heading pb-metrics-heading">
     <h2>Workspace overview</h2>
     <Link className="ir-link" href="/intent-radar/signals">Review all signals <ArrowRight size={14}/></Link>
    </div>
    <div className="pb-dash-metrics">
     {metrics.map(([name,count,Icon,href])=>(
      <Link className="pb-dash-metric-card" key={name} href={'/intent-radar'+href}>
       <div className="pb-dash-metric-header"><span>{name}</span><Icon size={14}/></div>
       <strong className="pb-dash-metric-value">{count}</strong>
      </Link>
     ))}
    </div>
   </div>

   {/* Section C: Monitoring and Activity Grid */}
   <div className="pb-dash-grid-row-1">
    {/* Card 1: Background Monitoring */}
    <section className="ir-panel pb-dash-card">
     <div>
      <div className="pb-dash-card-header">
       <div className="pb-dash-card-title">
        <Radio size={15} className="text-muted-foreground"/>
        <h3>Background monitoring</h3>
       </div>
       {d.active_monitors>0&&d.operations?.scheduler_heartbeat_fresh?(
        <span className="pb-status-badge is-active"><span className="pb-status-dot pulse"/>Active</span>
       ):d.active_monitors>0?(
        <span className="pb-status-badge is-idle"><span className="pb-status-dot"/>Scheduled</span>
       ):(
        <span className="pb-status-badge is-idle"><span className="pb-status-dot"/>Not configured</span>
       )}
      </div>
      <div className="pb-dash-stat-grid">
       <div className="pb-dash-stat-tile">
        <span className="pb-dash-stat-val">{d.active_monitors}</span>
        <span className="pb-dash-stat-lbl">Active monitors</span>
       </div>
       <div className="pb-dash-stat-tile">
        <span className="pb-dash-stat-val text-sm font-semibold truncate">
         {d.active_monitors===0?'None running':d.operations?.scheduler_heartbeat_fresh?'Healthy':'Standby'}
        </span>
        <span className="pb-dash-stat-lbl truncate">
         {d.active_monitors===0
          ?'0 queued checks'
          :d.operations?.backlog
           ?`${d.operations.backlog} queued check${d.operations.backlog===1?'':'s'}`
           :d.operations?.scheduler_heartbeat_at
            ?`Heartbeat ${new Date(d.operations.scheduler_heartbeat_at).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}`
            :'Ready for schedule'}
        </span>
       </div>
      </div>
      <p className="pb-dash-card-desc">
       {d.active_monitors===0
        ?'No active monitors in this workspace yet. Create a monitor to automate recurring checks.'
        :d.operations?.scheduler_heartbeat_fresh
         ?'Scheduler healthy. Active monitors run on their configured cadence.'
         :'Active monitors can be checked on demand or on their configured schedule.'}
      </p>
     </div>
     <div className="pb-dash-card-footer">
      <Link className="ir-link" href={d.active_monitors===0?'/intent-radar/monitors/new':'/intent-radar/monitors'}>
       {d.active_monitors===0?'Create your first monitor':'Manage monitors & runs'} <ArrowRight size={13}/>
      </Link>
     </div>
    </section>

    {/* Card 2: Monitor Activity */}
    <section className="ir-panel pb-dash-card">
     <div>
      <div className="pb-dash-card-header">
       <div className="pb-dash-card-title">
        <Radio size={15} className="text-muted-foreground"/>
        <h3>Monitor activity</h3>
       </div>
       <Link className="ir-link" href="/intent-radar/monitors">Manage <ArrowRight size={13}/></Link>
      </div>
      {d.monitors.length>0?(
       <div className="pb-dash-item-list">
        {d.monitors.slice(0,3).map(m=>(
         <Link className="pb-dash-item" key={m.id} href={'/intent-radar/monitors/'+m.id}>
          <div className="pb-dash-item-body">
           <strong className="truncate">{m.name}</strong>
           <small>{m.last_checked?'Checked '+new Date(m.last_checked).toLocaleDateString():'Ready for check'}</small>
          </div>
          <Badge>{m.status}</Badge>
         </Link>
        ))}
       </div>
      ):(
       <div className="pb-dash-card-empty">
        <Radio size={20}/>
        <p>No active monitors</p>
        <small>Save search topics to automate checks.</small>
       </div>
      )}
     </div>
     <div className="pb-dash-card-footer">
      <Link className="ir-link" href="/intent-radar/monitors/new">+ Create monitor <ArrowRight size={13}/></Link>
     </div>
    </section>

    {/* Card 3: Opportunities to Review */}
    <section className="ir-panel pb-dash-card">
     <div>
      <div className="pb-dash-card-header">
       <div className="pb-dash-card-title">
        <Target size={15} className="text-muted-foreground"/>
        <h3>Opportunities to review</h3>
       </div>
       <Link className="ir-link" href="/intent-radar/opportunities">View all <ArrowRight size={13}/></Link>
      </div>
      {pendingOpportunities.length>0?(
       <div className="pb-dash-item-list">
        {pendingOpportunities.slice(0,3).map(o=>(
         <Link className="pb-dash-item" key={o.id} href="/intent-radar/opportunities">
          <div className="pb-dash-item-body">
           <strong className="truncate">{o.next_action||'Review source evidence'}</strong>
           <small>{o.priority} priority · {o.status}</small>
          </div>
          <span className={'pb-priority-pill priority-'+o.priority.toLowerCase()}>{o.priority}</span>
         </Link>
        ))}
       </div>
      ):(
       <div className="pb-dash-card-empty">
        <Target size={20}/>
        <p>No pending opportunities</p>
        <small>Save promising signals to track next actions.</small>
       </div>
      )}
     </div>
     <div className="pb-dash-card-footer">
      <Link className="ir-link" href="/intent-radar/opportunities">Open opportunities <ArrowRight size={13}/></Link>
     </div>
    </section>
   </div>

   <div className="pb-dash-grid-row-2">
    {/* Card 4: Recent Activity */}
    <section className="ir-panel pb-dash-card">
     <div>
      <div className="pb-dash-card-header">
       <div className="pb-dash-card-title">
        <Bell size={15} className="text-muted-foreground"/>
        <h3>Recent activity</h3>
       </div>
       <Link className="ir-link" href="/intent-radar/alerts">All alerts <ArrowRight size={13}/></Link>
      </div>
      {d.alerts.length>0?(
       <div className="pb-dash-item-list">
        {d.alerts.slice(0,3).map(a=>(
         <Link key={a.id} className="pb-dash-item" href={a.signal_id?'/intent-radar/signals/'+a.signal_id:'/intent-radar/alerts'}>
          <div className="pb-dash-item-body">
           <strong className="truncate">{a.title}</strong>
           <small>{new Date(a.created_at).toLocaleString([],{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'})}</small>
          </div>
          {!a.read_at&&<span className="pb-unread-indicator" title="Unread alert"/>}
         </Link>
        ))}
       </div>
      ):(
       <div className="pb-dash-card-empty">
        <Bell size={20}/>
        <p>No recent alerts</p>
        <small>Monitor run notifications will appear here.</small>
       </div>
      )}
     </div>
     <div className="pb-dash-card-footer">
      <Link className="ir-link" href="/intent-radar/alerts">Alert preferences <ArrowRight size={13}/></Link>
     </div>
    </section>

    {/* Card 5: Signals Over Time */}
    <section className="ir-panel pb-dash-card">
     <div>
      <div className="pb-dash-card-header">
       <div className="pb-dash-card-title">
        <Activity size={15} className="text-muted-foreground"/>
        <div>
         <h3>Signals over time</h3>
         <p className="text-xs text-muted-foreground m-0">Public conversations observed · latest {trends.length} recorded days</p>
        </div>
       </div>
       <span className="text-xs text-muted-foreground font-mono">{trends.reduce((acc,t)=>acc+t.volume,0)} total</span>
      </div>
      {trends.length>0?(
       <div className="ir-trend" role="img" aria-label={trends.map(t=>`${t.day}: ${t.volume} signals`).join('; ')}>
        {trends.map(t=>(
         <div key={t.day} className="ir-trend-col">
          <small className="ir-trend-val">{t.volume}</small>
          <div className="ir-trend-bar-track">
           <span className="ir-trend-bar" style={{height:Math.max(8,(t.volume/max)*100)+'%'}} title={`${t.day}: ${t.volume} signals`}/>
          </div>
          <small className="ir-trend-label">{t.day.slice(5)}</small>
         </div>
        ))}
       </div>
      ):(
       <div className="pb-dash-card-empty">
        <Activity size={20}/>
        <p>No signal trends recorded yet</p>
       </div>
      )}
     </div>
    </section>
   </div>

   {/* Section 2: Latest Signals & Conversations Data Table */}
   <section className="pb-dashboard-table-card">
    <div className="pb-table-card-header">
     <div>
      <h2>Latest Signals & Conversations</h2>
      <p>Recent source-backed discussions identified by your monitors</p>
     </div>
     <Link className="ir-link" href="/intent-radar/signals">Review all signals <ArrowRight size={14}/></Link>
    </div>
    <DashboardSignalTable signals={signalsToDisplay}/>
   </section>
  </>
 );
}

function DashboardSignalTable({signals}:{signals:IntentSignal[]}){
 const mutation=useRadarMutation(),access=useRadarCapabilities();
 const disabled=!access.data?.can_write||mutation.isPending;

 if(!signals.length){
  return (
   <div className="pb-dash-table-empty">
    <Radar size={28} className="text-muted-foreground opacity-60" aria-hidden="true"/>
    <div>
     <h4>No signals recorded yet</h4>
     <p>Run a check from Monitors or start a discovery to collect relevant discussions.</p>
    </div>
    <Link href="/intent-radar/discover" className="ir-button ir-primary text-xs"><Search size={14}/>Start discovery</Link>
   </div>
  );
 }

 return (
  <>
   {/* Desktop & Tablet Table View */}
   <div className="pb-dash-table-wrap">
    <table className="pb-dash-table">
     <thead>
      <tr>
       <th scope="col" className="pb-col-conv">Conversation</th>
       <th scope="col" className="pb-col-source">Source</th>
       <th scope="col" className="pb-col-intent">Intent</th>
       <th scope="col" className="pb-col-rel">Relevance</th>
       <th scope="col" className="pb-col-status">Status</th>
       <th scope="col" className="pb-col-date">Detected</th>
       <th scope="col" className="pb-col-actions text-right">Actions</th>
      </tr>
     </thead>
     <tbody>
      {signals.map((s)=>{
       const detectedDate=s.observed_at?new Date(s.observed_at).toLocaleDateString([],{month:'short',day:'numeric',year:'numeric'}):'Unknown';
       return (
        <tr key={s.id} className="pb-dash-table-row">
         <td className="pb-cell-conv">
          <Link href={`/intent-radar/signals/${s.id}`} className="pb-signal-title truncate" title={s.title}>{s.title}</Link>
          {s.evidence?.matched_keywords?.length>0&&(
           <span className="pb-signal-sub truncate">{s.evidence.matched_keywords.slice(0,3).join(' · ')}</span>
          )}
         </td>
         <td className="pb-cell-source">
          <span className="pb-source-pill">
           <ProviderLogo provider={s.source} size={18}/>
           <span className="truncate">{s.source}</span>
          </span>
         </td>
         <td className="pb-cell-intent"><Badge>{s.category||'Uncertain'}</Badge></td>
         <td className="pb-cell-rel"><SignalScore score={s.score}/></td>
         <td className="pb-cell-status"><Badge data-tone={s.status==='New'?'brand':s.status==='Reviewed'?'success':undefined}>{s.status}</Badge></td>
         <td className="pb-cell-date whitespace-nowrap text-muted-foreground text-xs">{detectedDate}</td>
         <td className="pb-cell-actions text-right">
          <div className="pb-row-actions">
           <button
            type="button"
            disabled={disabled}
            className={`pb-btn-save ${s.saved?'is-saved':''}`}
            onClick={()=>mutation.mutate({path:`/saved/${s.id}`,method:s.saved?'DELETE':'POST'})}
            aria-label={s.saved?'Unsave signal':'Save signal'}
            title={s.saved?'Remove from saved':'Save signal'}
           >
            <Bookmark size={13} fill={s.saved?'currentColor':'none'}/>
            <span>{s.saved?'Saved':'Save'}</span>
           </button>
           <Link href={`/intent-radar/signals/${s.id}`} className="pb-btn-view" aria-label={`View details for ${s.title}`} title="View details">
            <span>View</span>
            <ArrowUpRight size={13}/>
           </Link>
          </div>
         </td>
        </tr>
       );
      })}
     </tbody>
    </table>
   </div>

   {/* Mobile Card View (<=767px) */}
   <div className="pb-dash-mobile-cards">
    {signals.map((s)=>{
     const detectedDate=s.observed_at?new Date(s.observed_at).toLocaleDateString([],{month:'short',day:'numeric',year:'numeric'}):'Unknown';
     return (
      <article key={s.id} className="pb-dash-mobile-card">
       <div className="pb-mobile-top">
        <span className="pb-source-pill">
         <ProviderLogo provider={s.source} size={16}/>
         <span className="truncate">{s.source}</span>
        </span>
        <div className="pb-mobile-top-right">
         <SignalScore score={s.score}/>
         <Badge data-tone={s.status==='New'?'brand':s.status==='Reviewed'?'success':undefined}>{s.status}</Badge>
        </div>
       </div>
       <Link href={`/intent-radar/signals/${s.id}`} className="pb-mobile-title">{s.title}</Link>
       <div className="pb-mobile-meta">
        <Badge>{s.category||'Uncertain'}</Badge>
        <span className="text-xs text-muted-foreground">{detectedDate}</span>
       </div>
       <div className="pb-mobile-actions">
        <button
         type="button"
         disabled={disabled}
         className={`pb-btn-save ${s.saved?'is-saved':''}`}
         onClick={()=>mutation.mutate({path:`/saved/${s.id}`,method:s.saved?'DELETE':'POST'})}
        >
         <Bookmark size={13} fill={s.saved?'currentColor':'none'}/>
         <span>{s.saved?'Saved':'Save'}</span>
        </button>
        <Link href={`/intent-radar/signals/${s.id}`} className="pb-btn-view">
         <span>View details</span>
         <ArrowUpRight size={13}/>
        </Link>
       </div>
      </article>
     );
    })}
   </div>
  </>
 );
}
