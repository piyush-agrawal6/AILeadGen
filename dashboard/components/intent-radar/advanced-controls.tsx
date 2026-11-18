"use client";
import {useState} from 'react';
import Link from 'next/link';
import {Check, Settings2, ShieldAlert} from 'lucide-react';
import type {IntentSearch,SourceId,IntentMonitor} from '@/lib/intent-radar';
import {useRadarCapabilities,useRadarRead,useRadarMutation} from './provider';
import {Field,ErrorState} from './ui';
import {ProviderLogo} from './provider-logo';
import {ChipInput} from './monitors';
import {SignalIntelligencePanel} from './signals/SignalIntelligencePanel';

type Feed={id:string;name:string;family:SourceId;enabled:boolean};
const GH_KINDS=['repositories','issues','discussions','pull_requests','releases'] as const;

const SOURCE_GROUPS: {label: string; ids: SourceId[]}[] = [
 {label: 'Developer & Technical', ids: ['stack_exchange', 'github', 'hacker_news']},
 {label: 'Social & Discussions', ids: ['bluesky', 'youtube', 'discourse']},
 {label: 'Feeds & Publications', ids: ['atom', 'rss']},
];

function sourceOptionSummary(id: SourceId, value: IntentSearch): string | null {
 if (id === 'hacker_news') {
  const feeds = value.hn_feeds || ['ask'];
  return `${feeds.join(', ')}${value.hn_comments ? ' + replies' : ''}`;
 }
 if (id === 'stack_exchange') {
  const sites = value.sites || ['stackoverflow'];
  const tags = value.tags || [];
  return `${sites.length} site${sites.length === 1 ? '' : 's'}${tags.length ? ` · ${tags.length} tag${tags.length === 1 ? '' : 's'}` : ''}`;
 }
 if (id === 'github') {
  const kinds = value.github_kinds || ['issues', 'discussions'];
  const repos = value.github_repos || [];
  return `${kinds.length} type${kinds.length === 1 ? '' : 's'}${repos.length ? ` · ${repos.length} repo${repos.length === 1 ? '' : 's'}` : ''}`;
 }
 if (id === 'youtube') {
  return `${value.youtube_mode || 'videos'}${value.youtube_comments === false ? '' : ' + comments'}`;
 }
 if (id === 'bluesky') {
  return `${value.bluesky_mode || 'search'}${value.bluesky_threads ? ' + threads' : ''}`;
 }
 if (id === 'rss' || id === 'discourse' || id === 'atom') {
  const count = (value.feed_ids || []).length;
  return count ? `${count} feed${count === 1 ? '' : 's'} selected` : 'All enabled feeds';
 }
 return null;
}

export function SourceOptionsEditor({
 sourceId,
 value,
 onChange,
}: {
 sourceId: SourceId;
 value: IntentSearch;
 onChange: (value: IntentSearch) => void;
}) {
 const access = useRadarCapabilities();
 const feeds = useRadarRead<{ items: Feed[] }>('/sources/configurations');
 const set = (patch: Partial<IntentSearch>) => onChange({ ...value, ...patch });
 const allSources = access.data?.sources || [];
 const sourceMap = Object.fromEntries(allSources.map(s => [s.id || 'hacker_news', s]));
 const seSites = sourceMap['stack_exchange']?.configured_sites || ['stackoverflow'];
 const ghConnected = sourceMap['github']?.state === 'Connected';
 const ytAiAuthorized = !!sourceMap['youtube']?.ai_analytics_authorized;

 if (sourceId === 'hacker_news') {
  return (
   <div className="space-y-3">
    <Field
     label="Hacker News feeds"
     hint="Official Firebase v0 feeds; bounded nested comments (depth ≤ 2) supported."
    >
     <div className="flex flex-wrap gap-1.5 pt-1">
      {['ask', 'show', 'new', 'top', 'best', 'jobs'].map(f => (
       <label
        className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 py-1 text-xs cursor-pointer"
        key={f}
       >
        <input
         type="checkbox"
         checked={(value.hn_feeds || ['ask']).includes(f)}
         onChange={e => {
          const old = value.hn_feeds || ['ask'];
          set({
           hn_feeds: e.target.checked
            ? [...old, f].slice(0, 6)
            : old.filter(x => x !== f),
          });
         }}
         className="accent-primary"
        />
        <span className="capitalize">{f}</span>
       </label>
      ))}
     </div>
    </Field>
    <label className="inline-flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
     <input
      type="checkbox"
      checked={!!value.hn_comments}
      onChange={e => set({ hn_comments: e.target.checked })}
      className="accent-primary"
     />
     Include bounded nested public replies (depth ≤ 2)
    </label>
   </div>
  );
 }

 if (sourceId === 'stack_exchange') {
  return (
   <div className="space-y-3">
    <Field
     label={`Stack Exchange communities (select up to 5 of ${seSites.length})`}
     hint="Bounded selection avoids wasteful fan-out across all communities."
    >
     <div className="flex flex-wrap gap-1.5 pt-1">
      {seSites.map(site => {
       const active = (value.sites || ['stackoverflow']).includes(site);
       return (
        <label
         className={
          'inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs cursor-pointer ' +
          (active
           ? 'border-primary bg-primary/10 text-foreground font-medium'
           : 'border-border bg-card text-muted-foreground')
         }
         key={site}
        >
         <input
          type="checkbox"
          checked={active}
          onChange={e => {
           const old = value.sites || ['stackoverflow'];
           if (e.target.checked) {
            if (old.length < 5) set({ sites: [...old, site] });
           } else if (old.length > 1) {
            set({ sites: old.filter(s => s !== site) });
           }
          }}
          className="accent-primary"
         />
         {site}
        </label>
       );
      })}
     </div>
    </Field>
    <ChipInput label="Stack Exchange tags" value={value.tags || []} onChange={tags => set({ tags })} />
    <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
     <label className="inline-flex items-center gap-2 cursor-pointer">
      <input
       type="checkbox"
       checked={!!value.se_include_answers}
       onChange={e => set({ se_include_answers: e.target.checked })}
       className="accent-primary"
      />
      Include top / accepted answers
     </label>
     <label className="inline-flex items-center gap-2 cursor-pointer">
      <input
       type="checkbox"
       checked={!!value.se_include_comments}
       onChange={e => set({ se_include_comments: e.target.checked })}
       className="accent-primary"
      />
      Include question comments
     </label>
    </div>
   </div>
  );
 }

 if (sourceId === 'github') {
  return (
   <div className="space-y-3">
    <Field
     label="GitHub content types"
     hint="Uses GitHub App REST & GraphQL APIs with installation-token auth."
    >
     <div className="flex flex-wrap gap-1.5 pt-1">
      {GH_KINDS.map(kind => {
       const current = value.github_kinds || ['issues', 'discussions'];
       return (
        <label
         className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 py-1 text-xs cursor-pointer"
         key={kind}
        >
         <input
          type="checkbox"
          checked={current.includes(kind)}
          onChange={e => {
           if (e.target.checked) set({ github_kinds: [...current, kind] });
           else if (current.length > 1) set({ github_kinds: current.filter(k => k !== kind) });
          }}
          className="accent-primary"
         />
         <span className="capitalize">{kind.replace('_', ' ')}</span>
        </label>
       );
      })}
     </div>
    </Field>
    <ChipInput
     label="Target repositories (optional owner/repo)"
     value={value.github_repos || []}
     onChange={github_repos => set({ github_repos })}
    />
    <div className="grid gap-3 sm:grid-cols-2 items-center">
     <Field
      label="GitHub access scope"
      hint="Private repository monitoring requires a workspace-connected GitHub App installation."
     >
      <select
       value={value.github_scope || 'public'}
       onChange={e => set({ github_scope: e.target.value as 'public' | 'connected' })}
      >
       <option value="public">Public GitHub discovery</option>
       <option value="connected" disabled={!ghConnected}>
        Workspace-connected repositories {!ghConnected ? '(Connect GitHub first)' : ''}
       </option>
      </select>
     </Field>
     <label className="inline-flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
      <input
       type="checkbox"
       checked={!!value.github_comments}
       onChange={e => set({ github_comments: e.target.checked })}
       className="accent-primary"
      />
      Include bounded issue &amp; discussion comments
     </label>
    </div>
   </div>
  );
 }

 if (sourceId === 'youtube') {
  return (
   <div className="space-y-3">
    <div className="grid gap-3 sm:grid-cols-2 items-center">
     <Field
      label="YouTube discovery mode"
      hint="Uses official YouTube Data API v3 with shared fair-usage quotas and 30-day retention."
     >
      <select
       value={value.youtube_mode || 'videos'}
       onChange={e => set({ youtube_mode: e.target.value as 'videos' | 'channels' | 'both' })}
      >
       <option value="videos">Videos &amp; public comments</option>
       <option value="channels">Channels</option>
       <option value="both">Videos &amp; channels</option>
      </select>
     </Field>
     <label className="inline-flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
      <input
       type="checkbox"
       checked={value.youtube_comments ?? true}
       onChange={e => set({ youtube_comments: e.target.checked })}
       className="accent-primary"
      />
      Collect public comment threads &amp; replies
     </label>
    </div>
    <ChipInput
     label="Optional YouTube channel IDs"
     value={value.youtube_channel_ids || []}
     onChange={youtube_channel_ids => set({ youtube_channel_ids })}
    />
    {!ytAiAuthorized && (
     <p className="flex items-start gap-1.5 text-[11px] text-amber-700 dark:text-amber-300">
      <ShieldAlert size={13} className="shrink-0 mt-0.5" aria-hidden="true" />
      <span>
       Policy note: YouTube retrieval and human review are enabled; derived AI sentiment/intent scoring remains gated pending YouTube API policy approval.
      </span>
     </p>
    )}
   </div>
  );
 }

 if (sourceId === 'bluesky') {
  return (
   <div className="space-y-3">
    <div className="grid gap-3 sm:grid-cols-2 items-center">
     <Field
      label="Bluesky discovery mode"
      hint="Uses official Bluesky Public API (api.bsky.app); Jetstream v2 runs on bounded scheduled monitoring."
     >
      <select
       value={value.bluesky_mode || 'search'}
       onChange={e => set({ bluesky_mode: e.target.value as 'search' | 'profiles' | 'feeds' })}
      >
       <option value="search">Public post search</option>
       <option value="feeds">Author public feeds</option>
       <option value="profiles">Profile search</option>
      </select>
     </Field>
     <label className="inline-flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
      <input
       type="checkbox"
       checked={!!value.bluesky_threads}
       onChange={e => set({ bluesky_threads: e.target.checked })}
       className="accent-primary"
      />
      Include bounded thread replies
     </label>
    </div>
    <ChipInput
     label="Optional Bluesky handles (e.g. bsky.app)"
     value={value.bluesky_handles || []}
     onChange={bluesky_handles => set({ bluesky_handles })}
    />
   </div>
  );
 }

 const matchingFeeds = (feeds.data?.items || []).filter(f => f.enabled && f.family === sourceId);
 return (
  <fieldset className="space-y-2">
   <legend className="text-xs font-semibold text-foreground">Approved feeds to search</legend>
   {matchingFeeds.length === 0 ? (
    <p className="text-xs text-muted-foreground">
     No enabled {sourceId.toUpperCase()} feeds yet.{' '}
     <Link href="/settings?category=integrations&tab=feeds" className="text-primary hover:underline">
      Manage custom feeds in Settings
     </Link>
    </p>
   ) : (
    <div className="flex flex-wrap gap-2">
     {matchingFeeds.map(f => (
      <label
       className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-1.5 text-xs cursor-pointer"
       key={f.id}
      >
       <input
        aria-label={f.name}
        type="checkbox"
        checked={(value.feed_ids || []).includes(f.id)}
        onChange={e =>
         set({
          feed_ids: e.target.checked
           ? [...(value.feed_ids || []), f.id]
           : (value.feed_ids || []).filter(x => x !== f.id),
         })
        }
        className="accent-primary"
       />
       <span>{f.name}</span>
      </label>
     ))}
    </div>
   )}
  </fieldset>
 );
}

export function SourceSelection({
 value,
 onChange,
 showAdvancedOptions = true,
 compactOptions = false,
 onConfigureSource,
}:{
 value:IntentSearch;
 onChange:(value:IntentSearch)=>void;
 showAdvancedOptions?: boolean;
 compactOptions?: boolean;
 onConfigureSource?: (sourceId: SourceId) => void;
}){
 const access=useRadarCapabilities(),feeds=useRadarRead<{items:Feed[]}>('/sources/configurations'),icps=useRadarRead<{items:{id:string;name:string}[]}>('/icps');
 const selected=value.sources??['hacker_news'];
 const set=(patch:Partial<IntentSearch>)=>onChange({...value,...patch});
 const allSources=access.data?.sources||[];
 const sourceMap=Object.fromEntries(allSources.map(s=>[s.id||'hacker_news',s]));
 const seSites=sourceMap['stack_exchange']?.configured_sites||['stackoverflow'];
 const ghConnected=sourceMap['github']?.state==='Connected';
 const ytAiAuthorized=!!sourceMap['youtube']?.ai_analytics_authorized;

 const grouped = SOURCE_GROUPS.map(g => ({
  label: g.label,
  items: g.ids.map(id => sourceMap[id]).filter(Boolean),
 })).filter(g => g.items.length > 0);

 const extraSources = allSources.filter(
  s => !SOURCE_GROUPS.some(g => g.ids.includes((s.id || 'hacker_news') as SourceId))
 );
 if (extraSources.length > 0) {
  grouped.push({label: 'Other Sources', items: extraSources});
 }

 const hasSelectedProviderOptions =
  selected.includes('hacker_news') ||
  selected.includes('stack_exchange') ||
  selected.includes('github') ||
  selected.includes('youtube') ||
  selected.includes('bluesky') ||
  selected.includes('rss') ||
  selected.includes('discourse') ||
  selected.includes('atom');

 return (
  <section className="space-y-4">
   <div className="space-y-4">
    {grouped.map(group => (
     <div key={group.label} className="space-y-2">
      <h4 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
       {group.label}
      </h4>
      <div className={compactOptions ? 'grid gap-2.5 sm:grid-cols-2' : 'grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3'}>
       {group.items.map(source => {
        const id = (source.id || 'hacker_news') as SourceId;
        const usable = source.state === 'Available' || source.state === 'Connected';
        const isChecked = selected.includes(id);
        return (
         <label
          key={source.name}
          className={
           'relative flex items-start gap-3 rounded-xl border p-3.5 transition-all ' +
           (!usable
            ? 'border-border/70 bg-muted/20 opacity-65 cursor-not-allowed'
            : isChecked
             ? 'border-primary bg-primary/[0.04] ring-1 ring-primary/25 cursor-pointer'
             : 'border-border bg-card hover:border-primary/45 cursor-pointer')
          }
         >
          <input
           type="checkbox"
           disabled={!usable}
           checked={isChecked}
           onChange={e => {
            set({
             sources: e.target.checked
              ? [...selected, id]
              : selected.filter(s => s !== id),
            });
           }}
           className="mt-1 accent-primary shrink-0"
          />
          <div className="min-w-0 flex-1 space-y-1">
           <div className="flex items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1.5 font-semibold text-xs text-foreground truncate">
             <span aria-hidden="true" className="inline-flex shrink-0">
              <ProviderLogo provider={source.name} size={16} />
             </span>
             <span className="truncate">{source.name}</span>
            </span>{" "}
            <span
             className={
              'rounded-full px-2 py-0.5 text-[10px] font-semibold shrink-0 ' +
              (source.state === 'Connected'
               ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
               : source.state === 'Available'
                ? 'bg-blue-500/10 text-blue-700 dark:text-blue-300'
                : 'bg-muted text-muted-foreground')
             }
            >
             {source.state}
            </span>
           </div>
           <p
            title={source.coverage}
            className="text-[11px] text-muted-foreground leading-snug line-clamp-2"
           >
            {source.coverage}
           </p>
           {compactOptions && isChecked && usable && onConfigureSource && (
            <div className="flex items-center justify-between gap-2 pt-1">
             <span className="text-[10px] text-muted-foreground truncate">
              {sourceOptionSummary(id, value)}
             </span>
             <button
              type="button"
              onClick={e => {
               e.preventDefault();
               e.stopPropagation();
               onConfigureSource(id);
              }}
              className="inline-flex items-center gap-1 rounded-md border border-border bg-background px-2 py-0.5 text-[11px] font-medium text-foreground hover:border-primary/60 hover:text-primary transition-colors cursor-pointer shrink-0"
             >
              <Settings2 size={11} aria-hidden="true" />
              Configure
             </button>
            </div>
           )}
           {!usable && (id === 'discourse' || id === 'atom' || id === 'rss') && (
            <Link
             href="/settings?category=integrations&tab=feeds"
             className="inline-flex items-center gap-1 text-[11px] font-medium text-primary hover:underline pt-0.5"
            >
             <Settings2 size={11} /> Enable feeds in Settings
            </Link>
           )}
          </div>
          {isChecked && (
           <Check
            size={13}
            className="text-primary shrink-0 mt-0.5 hidden sm:block"
            aria-hidden="true"
           />
          )}
         </label>
        );
       })}
      </div>
     </div>
    ))}
   </div>

   {/* Context-sensitive source-specific settings (ONLY for selected sources when not using compact drawer mode) */}
   {!compactOptions && hasSelectedProviderOptions && (
    <div className="space-y-3 rounded-xl border border-border/80 bg-muted/15 p-4">
     <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
      Selected source options
     </p>

     {selected.includes('hacker_news') && (
      <div className="space-y-2 border-b border-border/60 pb-3 last:border-b-0 last:pb-0">
       <Field
        label="Hacker News feeds"
        hint="Official Firebase v0 feeds; bounded nested comments (depth ≤ 2) supported."
       >
        <div className="flex flex-wrap gap-1.5 pt-1">
         {['ask', 'show', 'new', 'top', 'best', 'jobs'].map(f => (
          <label
           className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 py-1 text-xs cursor-pointer"
           key={f}
          >
           <input
            type="checkbox"
            checked={(value.hn_feeds || ['ask']).includes(f)}
            onChange={e => {
             const old = value.hn_feeds || ['ask'];
             set({
              hn_feeds: e.target.checked
               ? [...old, f].slice(0, 6)
               : old.filter(x => x !== f),
             });
            }}
            className="accent-primary"
           />
           <span className="capitalize">{f}</span>
          </label>
         ))}
        </div>
       </Field>
       <label className="inline-flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
        <input
         type="checkbox"
         checked={!!value.hn_comments}
         onChange={e => set({hn_comments: e.target.checked})}
         className="accent-primary"
        />
        Include bounded nested public replies (depth ≤ 2)
       </label>
      </div>
     )}

     {selected.includes('stack_exchange') && (
      <div className="space-y-2.5 border-b border-border/60 pb-3 last:border-b-0 last:pb-0">
       <Field
        label={`Stack Exchange communities (select up to 5 of ${seSites.length})`}
        hint="Bounded selection avoids wasteful fan-out across all communities."
       >
        <div className="flex flex-wrap gap-1.5 pt-1">
         {seSites.map(site => {
          const active = (value.sites || ['stackoverflow']).includes(site);
          return (
           <label
            className={
             'inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs cursor-pointer ' +
             (active
              ? 'border-primary bg-primary/10 text-foreground font-medium'
              : 'border-border bg-card text-muted-foreground')
            }
            key={site}
           >
            <input
             type="checkbox"
             checked={active}
             onChange={e => {
              const old = value.sites || ['stackoverflow'];
              if (e.target.checked) {
               if (old.length < 5) set({sites: [...old, site]});
              } else if (old.length > 1) {
               set({sites: old.filter(s => s !== site)});
              }
             }}
             className="accent-primary"
            />
            {site}
           </label>
          );
         })}
        </div>
       </Field>
       <ChipInput label="Stack Exchange tags" value={value.tags || []} onChange={tags => set({tags})} />
       <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
        <label className="inline-flex items-center gap-2 cursor-pointer">
         <input
          type="checkbox"
          checked={!!value.se_include_answers}
          onChange={e => set({se_include_answers: e.target.checked})}
          className="accent-primary"
         />
         Include top / accepted answers
        </label>
        <label className="inline-flex items-center gap-2 cursor-pointer">
         <input
          type="checkbox"
          checked={!!value.se_include_comments}
          onChange={e => set({se_include_comments: e.target.checked})}
          className="accent-primary"
         />
         Include question comments
        </label>
       </div>
      </div>
     )}

     {selected.includes('github') && (
      <div className="space-y-2.5 border-b border-border/60 pb-3 last:border-b-0 last:pb-0">
       <Field
        label="GitHub content types"
        hint="Uses GitHub App REST & GraphQL APIs with installation-token auth."
       >
        <div className="flex flex-wrap gap-1.5 pt-1">
         {GH_KINDS.map(kind => {
          const current = value.github_kinds || ['issues', 'discussions'];
          return (
           <label
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 py-1 text-xs cursor-pointer"
            key={kind}
           >
            <input
             type="checkbox"
             checked={current.includes(kind)}
             onChange={e => {
              if (e.target.checked) set({github_kinds: [...current, kind]});
              else if (current.length > 1) set({github_kinds: current.filter(k => k !== kind)});
             }}
             className="accent-primary"
            />
            <span className="capitalize">{kind.replace('_', ' ')}</span>
           </label>
          );
         })}
        </div>
       </Field>
       <ChipInput
        label="Target repositories (optional owner/repo)"
        value={value.github_repos || []}
        onChange={github_repos => set({github_repos})}
       />
       <div className="grid gap-3 sm:grid-cols-2 items-center">
        <Field
         label="GitHub access scope"
         hint="Private repository monitoring requires a workspace-connected GitHub App installation."
        >
         <select
          value={value.github_scope || 'public'}
          onChange={e => set({github_scope: e.target.value as 'public' | 'connected'})}
         >
          <option value="public">Public GitHub discovery</option>
          <option value="connected" disabled={!ghConnected}>
           Workspace-connected repositories {!ghConnected ? '(Connect GitHub first)' : ''}
          </option>
         </select>
        </Field>
        <label className="inline-flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
         <input
          type="checkbox"
          checked={!!value.github_comments}
          onChange={e => set({github_comments: e.target.checked})}
          className="accent-primary"
         />
         Include bounded issue &amp; discussion comments
        </label>
       </div>
      </div>
     )}

     {selected.includes('youtube') && (
      <div className="space-y-2.5 border-b border-border/60 pb-3 last:border-b-0 last:pb-0">
       <div className="grid gap-3 sm:grid-cols-2 items-center">
        <Field
         label="YouTube discovery mode"
         hint="Uses official YouTube Data API v3 with shared fair-usage quotas and 30-day retention."
        >
         <select
          value={value.youtube_mode || 'videos'}
          onChange={e => set({youtube_mode: e.target.value as 'videos' | 'channels' | 'both'})}
         >
          <option value="videos">Videos &amp; public comments</option>
          <option value="channels">Channels</option>
          <option value="both">Videos &amp; channels</option>
         </select>
        </Field>
        <label className="inline-flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
         <input
          type="checkbox"
          checked={value.youtube_comments ?? true}
          onChange={e => set({youtube_comments: e.target.checked})}
          className="accent-primary"
         />
         Collect public comment threads &amp; replies
        </label>
       </div>
       <ChipInput
        label="Optional YouTube channel IDs"
        value={value.youtube_channel_ids || []}
        onChange={youtube_channel_ids => set({youtube_channel_ids})}
       />
       {!ytAiAuthorized && (
        <p className="flex items-start gap-1.5 text-[11px] text-amber-700 dark:text-amber-300">
         <ShieldAlert size={13} className="shrink-0 mt-0.5" aria-hidden="true" />
         <span>
          Policy note: YouTube retrieval and human review are enabled; derived AI sentiment/intent scoring remains gated pending YouTube API policy approval.
         </span>
        </p>
       )}
      </div>
     )}

     {selected.includes('bluesky') && (
      <div className="space-y-2.5 border-b border-border/60 pb-3 last:border-b-0 last:pb-0">
       <div className="grid gap-3 sm:grid-cols-2 items-center">
        <Field
         label="Bluesky discovery mode"
         hint="Uses official Bluesky Public API (api.bsky.app); Jetstream v2 runs on bounded scheduled monitoring."
        >
         <select
          value={value.bluesky_mode || 'search'}
          onChange={e => set({bluesky_mode: e.target.value as 'search' | 'profiles' | 'feeds'})}
         >
          <option value="search">Public post search</option>
          <option value="feeds">Author public feeds</option>
          <option value="profiles">Profile search</option>
         </select>
        </Field>
        <label className="inline-flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
         <input
          type="checkbox"
          checked={!!value.bluesky_threads}
          onChange={e => set({bluesky_threads: e.target.checked})}
          className="accent-primary"
         />
         Include bounded thread replies
        </label>
       </div>
       <ChipInput
        label="Optional Bluesky handles (e.g. bsky.app)"
        value={value.bluesky_handles || []}
        onChange={bluesky_handles => set({bluesky_handles})}
       />
      </div>
     )}

     {(selected.includes('rss') || selected.includes('discourse') || selected.includes('atom')) && (
      <fieldset className="space-y-2 border-b border-border/60 pb-3 last:border-b-0 last:pb-0">
       <legend className="text-xs font-semibold text-foreground">Approved feeds to search</legend>
       <div className="flex flex-wrap gap-2">
        {feeds.data?.items
         .filter(f => f.enabled && selected.includes(f.family))
         .map(f => (
          <label
           className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-1.5 text-xs cursor-pointer"
           key={f.id}
          >
           <input
            aria-label={f.name}
            type="checkbox"
            checked={(value.feed_ids || []).includes(f.id)}
            onChange={e =>
             set({
              feed_ids: e.target.checked
               ? [...(value.feed_ids || []), f.id]
               : (value.feed_ids || []).filter(x => x !== f.id),
             })
            }
            className="accent-primary"
           />
           <span>{f.name}</span>
          </label>
         ))}
       </div>
      </fieldset>
     )}
    </div>
   )}

   {showAdvancedOptions && (
    <div className="space-y-3 pt-1">
     <Field
      label="Selected ICP"
      hint="No ideal customer profile selected? You can search without one."
     >
      <select
       value={value.icp_id || ''}
       onChange={e => set({icp_id: e.target.value || null})}
      >
       <option value="">No ICP selected — search without an ICP</option>
       {icps.data?.items.map(i => (
        <option key={i.id} value={i.id}>
         {i.name}
        </option>
       ))}
      </select>
     </Field>
     <label className="inline-flex items-center gap-2 text-xs text-foreground cursor-pointer">
      <input
       type="checkbox"
       checked={!!value.semantic}
       onChange={e => set({semantic: e.target.checked})}
       className="accent-primary"
      />
      Include ambiguous intent candidates for human-requested semantic analysis
     </label>
     <small className="block text-[11px] text-muted-foreground">
      Requires relevant offerings. Candidates are not verified semantic matches until evidence-grounded analysis succeeds.
     </small>
     {value.semantic && (
      <div className="ir-form-section">
       <ChipInput
        label="Positive semantic criteria"
        value={value.semantic_criteria || []}
        onChange={semantic_criteria => set({semantic_criteria})}
       />
       <ChipInput
        label="Semantic exclusions"
        value={value.semantic_exclusions || []}
        onChange={semantic_exclusions => set({semantic_exclusions})}
       />
       <Field label="Maximum candidates for bounded AI ranking">
        <input
         type="number"
         min={1}
         max={10}
         value={value.semantic_analysis_limit || 3}
         onChange={e =>
          set({
           semantic_analysis_limit: Math.max(1, Math.min(10, Number(e.target.value))),
          })
         }
        />
       </Field>
       <Field
        label="Source language for semantic matching"
        hint="Inferred from source evidence; unknown language is not admitted to a requested-language match."
       >
        <select
         value={value.language}
         onChange={e => set({language: e.target.value as IntentSearch['language']})}
        >
         {['Any / unverified', 'en', 'es', 'fr', 'de', 'pt', 'hi', 'ja'].map(language => (
          <option key={language}>{language}</option>
         ))}
        </select>
       </Field>
      </div>
     )}
    </div>
   )}
  </section>
 );
}

export function ScheduleControls({monitor:m}:{monitor:IntentMonitor}){
 const access=useRadarCapabilities(),mutation=useRadarMutation(),[frequency,setFrequency]=useState(m.schedule?.frequency||'Manual'),[zone,setZone]=useState(m.schedule?.timezone||'UTC'),[error,setError]=useState('');
 async function save(){try{await mutation.mutateAsync({path:'/monitors/'+m.id+'/schedule',method:'PUT',body:{frequency,timezone:zone,revision:m.revision}});setError('')}catch(e){setError((e as Error).message)}}
 return <section className="ir-form-section"><h3>Monitoring schedule</h3><div className="ir-form-grid"><Field label="Frequency"><select value={frequency} onChange={e=>setFrequency(e.target.value)}><option>Manual</option>{access.data?.usage.automatic_schedules_enabled&&['Daily','12 hours','6 hours'].filter(f=>f==='Daily'||Number(f.split(' ')[0])>=(access.data?.usage.minimum_schedule_hours||12)).map(f=><option key={f}>{f}</option>)}</select></Field><Field label="Schedule timezone"><input value={zone} onChange={e=>setZone(e.target.value)} maxLength={80}/></Field></div><p>Next scheduled run: {m.status!=='Active'?'Paused / inactive':m.next_run_at?new Date(m.next_run_at).toLocaleDateString()+' '+new Date(m.next_run_at).toISOString().slice(11,16)+' UTC':'Not scheduled'}. Fixed intervals use UTC across daylight-saving changes, with up to five minutes jitter.</p><button disabled={!access.data?.can_write||mutation.isPending||m.status!=='Active'} onClick={()=>void save()}>Save schedule</button>{!access.data?.usage.automatic_schedules_enabled&&<small>Recurring monitoring is disabled by the operator. Manual checks remain available.</small>}{error&&<ErrorState message={error}/>}</section>;
}

export function SignalIntelligence({id,monitorId}:{id:string;monitorId?:string}){
 return <SignalIntelligencePanel id={id} monitorId={monitorId}/>;
}
