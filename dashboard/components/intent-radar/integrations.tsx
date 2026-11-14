"use client";

import {useId, useState} from 'react';
import Link from 'next/link';
import * as Tabs from '@radix-ui/react-tabs';
import {useQuery} from '@tanstack/react-query';
import {ArrowRight, ArrowUpRight, BookOpen, Check, LockKeyhole, Radio, ShieldCheck, SlidersHorizontal} from 'lucide-react';
import {request} from '@/lib/intelligence';
import {useWorkspace} from '@/components/workspaces/use-workspace';
import {useRadarCapabilities} from './provider';
import {Badge, EmptyState, Field, Modal, PageHeading} from './ui';
import {ProviderLogo} from './provider-logo';
import './integrations.css';
import {SourceManagement} from './source-management';

const categories = ['Live Data Sources', 'AI Assistants & MCP', 'CRM & Sales Tools', 'Automation & Productivity', 'Notifications'] as const;
type Category = typeof categories[number];
type Entry = {id: string; name: string; category: Category; kind: 'source' | 'mcp' | 'planned' | 'native'; description: string; detail: string; highlights: string[]; documentation?: string};
type DeveloperStatus = {enabled: boolean; can_manage: boolean; mcp_available: boolean};
const tools = [
  ['search_intent_signals', 'Search stored public evidence; no discovery starts.'],
  ['list_intent_monitors', 'Review workspace monitors; no checks run.'],
  ['get_intent_signal', 'Retrieve the evidence behind an authorized signal.'],
  ['list_intent_opportunities', 'Read selected opportunities; no contacts or messages are created.'],
  ['list_intent_sources', 'Read the actual source catalog and configuration restrictions; no source is activated.'],
  ['get_intent_analysis', 'Read the latest valid signal interpretation and feedback; no AI call starts.'],
  ['get_intent_run', 'Inspect an owned discovery job and its per-source progress; no check is run.'],
  ['get_intent_source_health', 'Read persisted source errors, freshness and bounded request reservations.'],
  ['get_intent_workspace_context', 'Read reviewed workspace business context and its default ICP identifier; no credentials.'],
];
const growthTools=[['list_market_themes','Read stored themes with current-evidence checks.'],['get_growth_research','Read one authorized cited research snapshot.'],['get_market_overview','Read bounded collected-conversation metrics and coverage limits.'],['list_growth_watchlists','Read stored watchlists; no collection starts.']];
const entries: Entry[] = [
  {id: 'mcp', name: 'Intent Radar MCP', category: categories[1], kind: 'mcp', description: 'Bring source-backed workspace intelligence into your own MCP-capable tools.', detail: 'The shared PlaneByte MCP server exposes read-only Intent Radar tools, with additional Growth reads when enabled over Streamable HTTP. Server availability is separate from a successful client connection.', highlights: ['Scoped read-only tools', 'Workspace-scoped access']},
  {id: 'vscode', name: 'Visual Studio Code', category: categories[1], kind: 'mcp', description: 'Review stored intent evidence alongside your work in an MCP-capable editor.', detail: 'Visual Studio Code documents remote MCP servers. A client version and configuration that securely supports an Authorization header are required for PlaneByte’s scoped bearer keys. This workspace has no verified editor connection record.', highlights: ['Manual client setup', 'Connection not verified'], documentation: 'https://code.visualstudio.com/docs/agent-customization/mcp-servers'},
  {id: 'cursor', name: 'Cursor', category: categories[1], kind: 'mcp', description: 'Give your editor contextual access to authorized signals through the shared server.', detail: 'Cursor documents Streamable HTTP servers and Authorization header interpolation from environment variables. Use a personal configuration with securely stored credentials. No Cursor installation or successful tool call is verified here.', highlights: ['Streamable HTTP', 'Connection not verified'], documentation: 'https://cursor.com/docs/context/mcp'},
  {id: 'chatgpt', name: 'ChatGPT / OpenAI', category: categories[1], kind: 'planned', description: 'A potential conversational workflow for reviewing opportunities and public evidence.', detail: 'A dedicated ChatGPT connector has not been implemented or validated. PlaneByte currently provides scoped bearer-key MCP access; a compatible client authentication flow and end-to-end tool discovery must be verified before advertising ChatGPT setup.', highlights: ['Connector validation needed', 'No OAuth setup available']},
  {id: 'claude', name: 'Claude / Anthropic', category: categories[1], kind: 'planned', description: 'A potential assistant workflow for explaining the evidence behind saved signals.', detail: 'A Claude-specific connector and authentication handoff have not been validated. General MCP support does not establish compatibility with this bearer-key endpoint. A supported secure authentication path, tool discovery and workspace access tests are still needed.', highlights: ['Authentication validation needed', 'No client connection']},
  {id: 'hubspot', name: 'HubSpot', category: categories[2], kind: 'planned', description: 'Explore a future handoff from reviewed intent opportunities to your sales pipeline.', detail: 'The proposed workflow would link a reviewed opportunity to a workspace-owned CRM record and retain the public source citation. No HubSpot authorization, field mapping, deduplicated sync or Intent Radar export exists. An intent signal is not a verified contact or consent to outreach.', highlights: ['Reviewed opportunity handoff', 'Source citations retained']},
  {id: 'pipedrive', name: 'Pipedrive', category: categories[2], kind: 'planned', description: 'A future way to add reviewed market context to deals and sales activities.', detail: 'A future integration would need explicit record selection, deal-field mapping and idempotent workspace-scoped delivery. No Pipedrive credential flow or sync worker is implemented. It would not automatically create contacts or send messages.', highlights: ['Explicit record selection', 'No automatic outreach']},
  {id: 'sheets', name: 'Google Sheets', category: categories[3], kind: 'planned', description: 'A proposed export of selected signals for collaborative review in spreadsheets.', detail: 'Shared platform Sheets workflows are distinct from Intent Radar. Intent Radar has no Sheets export or customer connection contract. A future export would need a verified workspace-owned destination, bounded writes and source URLs alongside relevance explanations.', highlights: ['Selected-signal export', 'Destination access required']},
  {id: 'zapier', name: 'Zapier', category: categories[3], kind: 'planned', description: 'Explore future event-driven workflows for reviewed intent opportunities.', detail: 'No Intent Radar Zapier app, trigger, webhook event or delivery contract is implemented. A future workflow needs workspace authorization, event payload review, retry limits and duplicate-delivery protection. Shared platform webhooks do not establish Intent Radar event support.', highlights: ['Event contract needed', 'Bounded delivery required']},
  {id: 'alerts', name: 'Workspace notifications', category: categories[4], kind: 'native', description: 'Review Intent Radar alerts inside your workspace, with your existing alert preferences.', detail: 'Intent Radar stores workspace-owned alerts and provides read/unread controls. Alert preferences are managed in Intent Radar settings. This is in-app review, not email, Slack delivery or a guarantee of background scheduling.', highlights: ['In-app alerts', 'Workspace-owned history']},
  {id: 'slack', name: 'Slack', category: categories[4], kind: 'planned', description: 'A proposed channel digest to keep your team close to relevant public conversations.', detail: 'There is no Slack OAuth connection, channel selection or Intent Radar delivery worker. A future digest would need explicit channel authorization, relevance preferences, minimal source-backed payloads, cancellation and bounded retries.', highlights: ['Channel digest concept', 'Delivery not implemented']},
];

function MCPFlow() {
  return <ol className="ir-market-flow" aria-label="MCP access model">{['AI Client', 'Authenticated MCP', 'Intent Radar', 'Authorized Signals'].map((label, index) => <li key={label}><span className="ir-market-flow-number">{index + 1}</span><strong>{label}</strong>{index < 3 && <ArrowRight size={16} aria-hidden="true"/>}</li>)}</ol>;
}

function MCPDetails({entry, status}: {entry: Entry; status: string}) {
  const capabilities=useRadarCapabilities();
  return <>
    <div className="ir-market-notice"><ShieldCheck size={20}/><p><strong>{status}.</strong> Client connection is not verified. Use shared Developer access to review the current gates and available scopes.</p></div>
    <div className="ir-market-fields"><Field label="Backend endpoint path" hint="Your administrator must confirm the deployed HTTPS API origin and client reachability."><input readOnly value="/api/v1/mcp"/></Field><Field label="Required scopes" hint="A key is bound to one workspace and its issuing member’s current access."><input readOnly value="mcp:use + intent:read"/></Field></div>
    <h3>Set up a read-only client</h3>
    <ol className="ir-market-steps"><li>Ask a workspace owner or administrator to review Developer access. Both the developer API and MCP gates must be enabled, and the workspace must have Intent Radar access and completed onboarding. Only the enabled Intent Radar read scopes are needed for these tools.</li><li>Create an expiring scoped key in shared settings, selecting <code>mcp:use</code> and <code>intent:read</code> only when those scopes are offered. Store the one-time key securely in your client’s supported secret storage.</li><li>Configure a compatible Streamable HTTP client with the administrator-confirmed endpoint and an Authorization bearer header. This page does not provide an OAuth sign-in or collect credentials.</li><li>Discover the tools and verify a read call such as <code>list_intent_monitors</code>. Inspect the returned workspace data before treating the client as connected.</li></ol>
    <h3>Implemented read contracts</h3><dl className="ir-market-tools">{[...tools,...(capabilities.data?.growth_enabled?growthTools:[])].map(([name, explanation]) => <div key={name}><dt><code>{name}</code></dt><dd>{explanation}</dd></div>)}</dl>
    <p className="ir-market-muted">Each request checks credential expiry/revocation and active membership. Intent reads also require the workspace product grant and scopes. Public source text is untrusted evidence; relevance scores are interpretations, not verified purchasing events.</p>
    <div className="ir-market-dialog-actions"><Link className="ir-market-button ir-market-button-primary" href="/settings/developer">Shared developer settings <ArrowUpRight size={16}/></Link>{entry.documentation && <a className="ir-market-button" href={entry.documentation} target="_blank" rel="noopener noreferrer">Client documentation <ArrowUpRight size={16}/></a>}</div>
  </>;
}

export function IntegrationsPage() {
  const access = useRadarCapabilities();
  const workspace = useWorkspace();
  const organization = workspace.data?.active_organization_id;
  const developer = useQuery({queryKey: ['intent-radar-marketplace-developer', organization], queryFn: ({signal}) => request<DeveloperStatus>('/organization/developer/status', {signal}), enabled: !!organization && !!access.data && !access.isError, retry: false});
  const [category, setCategory] = useState<Category>(categories[0]);
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const searchId = useId();
  const sources: Entry[] = (access.data?.sources ?? []).map(source => ({id: `source:${source.name}`, name: source.name, category: categories[0], kind: 'source', description: source.coverage, detail: source.coverage, documentation: source.documentation, highlights: ['Public evidence', source.state]}));
  const catalog = [...sources, ...entries];
  const visible = catalog.filter(entry => entry.category === category && `${entry.name} ${entry.description}`.toLowerCase().includes(search.trim().toLowerCase()));
  const selected = catalog.find(entry => entry.id === selectedId);
  const mcpStatus = developer.isError ? 'MCP availability could not be verified' : !developer.data ? 'MCP availability not yet verified' : !developer.data.enabled ? 'Developer API disabled' : !developer.data.mcp_available ? 'Shared MCP disabled' : 'Shared MCP enabled';
  function status(entry: Entry) {
    if (entry.kind === 'planned') return 'Planned';
    if (entry.kind === 'mcp') return entry.id === 'mcp' ? mcpStatus : 'Manual setup';
    if (entry.kind === 'native') return access.data ? 'In-app' : 'Not verified';
    return access.data?.sources.find(source => source.name === entry.name)?.state ?? 'Not verified';
  }

  return <div className="ir-page ir-marketplace">
    <PageHeading title="Integrations & MCP" description="Your intelligence, in the right workflow. Explore public sources, secure AI access and the next connections on the roadmap." actions={<><Badge>Workspace integrations</Badge><Link className="ir-market-button" href="/settings/developer"><SlidersHorizontal size={16}/>Developer settings</Link></>}/>
    <section className="ir-market-hero" aria-labelledby="ir-market-hero-title"><div><span className="ir-market-kicker"><Radio size={16}/>FROM EVIDENCE TO CONTEXT</span><h2 id="ir-market-hero-title">Connect the dots.<br/>Keep the source.</h2><p>Discover recent public conversations, review their evidence and give your tools access to the signals your workspace authorizes.</p><button className="ir-market-button ir-market-button-primary" onClick={() => {setCategory(categories[1]); setSearch(''); setSelectedId('mcp');}}>Explore MCP access <ArrowRight size={16}/></button></div><div className="ir-market-hero-detail"><div className="ir-market-security"><LockKeyhole size={18}/><strong>One shared access model</strong><Badge>Read-only intent tools</Badge></div><MCPFlow/><p>Scoped credentials. Active membership. Authorized workspace data.</p><span className="ir-market-muted">Source availability and client connection status are distinct.</span></div></section>
    <Tabs.Root value={category} onValueChange={value => setCategory(value as Category)} className="ir-market-browser"><div className="ir-market-toolbar"><Tabs.List className="ir-market-tabs" aria-label="Integration categories">{categories.map(value => <Tabs.Trigger key={value} value={value} className="ir-market-tab">{value}</Tabs.Trigger>)}</Tabs.List><div className="ir-market-search"><label htmlFor={searchId}>Find an integration</label><input id={searchId} type="search" placeholder="Search this category…" value={search} onChange={event => setSearch(event.target.value)} maxLength={100}/></div></div>
      {categories.map(value => <Tabs.Content key={value} value={value} className="ir-market-tabpanel"><div className="ir-market-section-heading"><div><h2>{value}</h2><p>{value === categories[0] ? 'Availability comes from this workspace’s source catalog. No personal source account is connected.' : value === categories[1] ? 'Shared MCP is implemented. Named client setup and authentication compatibility require verification.' : value === categories[4] ? 'In-app alerts are implemented; external delivery is on the roadmap.' : 'Planned workflows — no export, sync or external action is available yet.'}</p></div><Badge>{visible.length} {visible.length === 1 ? 'integration' : 'integrations'}</Badge></div>
        {value === categories[0] && access.isPending ? <div className="ir-market-notice" role="status">Checking the workspace source catalog…</div> : value === categories[0] && access.isError ? <EmptyState title="Source availability could not be verified" description="The workspace catalog did not load. Retry to see authorized public sources." action={<button className="ir-market-button" onClick={() => void access.refetch()}>Retry source catalog</button>}/> : visible.length === 0 ? <EmptyState title={search ? 'No matching integrations' : 'No sources available in this workspace'} description={search ? 'Try a provider name or clear your search.' : 'The current source catalog contains no available providers.'} action={search ? <button className="ir-market-button" onClick={() => setSearch('')}>Clear search</button> : undefined}/> : <div className="ir-market-grid">{visible.map(entry => <article className="ir-market-card" key={entry.id} data-kind={entry.kind}><div className="ir-market-card-top">{entry.id === 'vscode' ? <a className="ir-market-logo-space" href="https://code.visualstudio.com" target="_blank" rel="noopener noreferrer" aria-label="Visit the Visual Studio Code website"><ProviderLogo provider={entry.name} size={36}/></a> : <div className="ir-market-logo-space"><ProviderLogo provider={entry.name} size={36}/></div>}<Badge>{status(entry)}</Badge></div><h3>{entry.name}</h3><p>{entry.description}</p><ul>{entry.highlights.map(highlight => <li key={highlight}><Check size={14} aria-hidden="true"/>{highlight}</li>)}</ul><footer><span>{entry.kind === 'source' ? 'Source adapter' : entry.kind === 'mcp' ? 'Shared developer access' : entry.kind === 'native' ? 'Native workspace workflow' : 'Roadmap candidate'}</span><button className="ir-market-card-action" aria-label={`${entry.kind === 'planned' ? 'Learn more about' : 'View details for'} ${entry.name}`} onClick={() => setSelectedId(entry.id)}>{entry.kind === 'planned' ? 'Learn more' : entry.kind === 'mcp' ? 'Setup details' : 'View details'}<ArrowUpRight size={16}/></button></footer></article>)}</div>}
      </Tabs.Content>)}
    </Tabs.Root>
    <SourceManagement/>
    <aside className="ir-market-bottom-note"><BookOpen size={20}/><p><strong>Evidence travels with the signal.</strong> Available sources describe coverage, not a connected customer account. Planned providers describe future workflows. Brand names identify third-party products and do not imply endorsement.</p></aside>
    <Modal open={!!selected} onOpenChange={open => {if (!open) setSelectedId(null);}} title={selected?.name ?? 'Integration details'} description={selected?.detail ?? 'Review source coverage and setup requirements.'}>
      {selected && <div className="ir-market-dialog"><div className="ir-market-dialog-status"><Badge>{status(selected)}</Badge><span>{selected.category}</span></div>
        {selected.kind === 'mcp' ? <MCPDetails entry={selected} status={mcpStatus}/> : selected.kind === 'source' ? <>
          <h3>Coverage & collection</h3><p>{selected.detail}</p>
          {selected.name === 'Hacker News' && <><dl className="ir-market-facts"><div><dt>Access</dt><dd>Official public v0 API. No HN account or key needed.</dd></div><div><dt>Check size</dt><dd>At most 22 requests across selected recent feeds and opt-in depth-one comments.</dd></div><div><dt>Matching</dt><dd>Local relevance filtering. Language is unverified; geography is unknown.</dd></div><div><dt>Excluded</dt><dd>No historical/full-text crawling, private profiles or external target-page collection.</dd></div></dl><h3>Use this source</h3><p>Create a bounded search or monitor. Date filters narrow recent feed snapshots. Checks require workspace write permission.</p></>}
          <div className="ir-market-dialog-actions">{access.data?.can_write && <Link className="ir-market-button ir-market-button-primary" href="/intent-radar/discover">Open signal search <ArrowRight size={16}/></Link>}{selected.documentation?.startsWith('https://') && <a className="ir-market-button" href={selected.documentation} target="_blank" rel="noopener noreferrer">Official source documentation <ArrowUpRight size={16}/></a>}</div>
        </> : selected.kind === 'native' ? <><h3>Review & preferences</h3><p>Open Alerts to inspect workspace notifications and mark them read. Administrators can manage alert preferences in Intent Radar settings.</p><div className="ir-market-dialog-actions"><Link className="ir-market-button ir-market-button-primary" href="/intent-radar/alerts">Review alerts <ArrowRight size={16}/></Link>{access.data?.can_manage && <Link className="ir-market-button" href="/intent-radar/settings">Alert preferences</Link>}</div></> : <><h3>What this would enable</h3><p>{selected.description}</p><h3>Current status</h3><p>{selected.detail}</p><div className="ir-market-notice"><LockKeyhole size={18}/><p>This is a roadmap candidate. There is no connection, credential collection or external action for this provider.</p></div></>}
        {selected.id === 'vscode' && <p className="ir-market-attribution">Visual Studio Code and its icon are trademarks of Microsoft Corporation. <a href="https://code.visualstudio.com/brand" target="_blank" rel="noopener noreferrer">Official icon usage guidelines</a>.</p>}
      </div>}
    </Modal>
  </div>;
}
