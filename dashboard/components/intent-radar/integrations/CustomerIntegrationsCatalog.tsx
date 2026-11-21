"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Blocks,
  CheckCircle2,
  Clock,
  Code2,
  Database,
  Download,
  ExternalLink,
  FileSpreadsheet,
  Layers,
  Network,
  Plug,
  Search,
  Send,
  Share2,
  Sparkles,
  Terminal,
  Workflow,
  X,
} from "lucide-react";
import { SearchInput } from "@/components/ui/search-input";
import {useRadarRead} from '../provider';
import type {SheetStatus} from './RadarSheets';

export type IntegrationCategory =
  | "all"
  | "crm"
  | "spreadsheets"
  | "automation"
  | "collaboration"
  | "developer";

export interface IntegrationItem {
  id: string;
  name: string;
  category: "crm" | "spreadsheets" | "automation" | "collaboration" | "developer";
  description: string;
  status: "coming_soon" | "available";
  statusLabel: string;
  capabilities: string[];
  configHref?: string;
  brandColor: string;
  initials: string;
  iconType: "crm" | "sheet" | "zap" | "chat" | "code" | "csv";
}

export const INTEGRATION_CATEGORIES: { id: IntegrationCategory; label: string }[] = [
  { id: "all", label: "All Integrations" },
  { id: "crm", label: "CRM" },
  { id: "spreadsheets", label: "Spreadsheets & Export" },
  { id: "automation", label: "Automation" },
  { id: "collaboration", label: "Notifications & Collaboration" },
  { id: "developer", label: "Developer Tools" },
];

export const INTEGRATION_CATALOG: IntegrationItem[] = [
  // CRM
  {
    id: "hubspot",
    name: "HubSpot",
    category: "crm",
    description: "Send qualified opportunities and contact signals directly into your HubSpot CRM.",
    status: "coming_soon",
    statusLabel: "Coming Soon",
    capabilities: ["Two-way Sync", "Deals & Contacts", "Activity Logging"],
    brandColor: "bg-[#FF7A59]/10 text-[#FF7A59] border-[#FF7A59]/20",
    initials: "HS",
    iconType: "crm",
  },
  {
    id: "salesforce",
    name: "Salesforce",
    category: "crm",
    description: "Sync high-intent accounts and verified buyer conversations with Salesforce Leads.",
    status: "coming_soon",
    statusLabel: "Coming Soon",
    capabilities: ["Enterprise CRM", "Lead Routing", "Custom Objects"],
    brandColor: "bg-[#00A1E0]/10 text-[#00A1E0] border-[#00A1E0]/20",
    initials: "SF",
    iconType: "crm",
  },
  {
    id: "pipedrive",
    name: "Pipedrive",
    category: "crm",
    description: "Automatically create visual pipeline deals from detected high-intent buyer discussions.",
    status: "coming_soon",
    statusLabel: "Coming Soon",
    capabilities: ["Deal Creation", "Stage Progression", "Notes Sync"],
    brandColor: "bg-[#017737]/10 text-[#017737] border-[#017737]/20",
    initials: "PD",
    iconType: "crm",
  },
  {
    id: "zoho-crm",
    name: "Zoho CRM",
    category: "crm",
    description: "Route verified sales opportunities into Zoho CRM modules and deal stages.",
    status: "coming_soon",
    statusLabel: "Coming Soon",
    capabilities: ["Modules Sync", "Lead Conversion", "Account Tagging"],
    brandColor: "bg-[#D8232A]/10 text-[#D8232A] border-[#D8232A]/20",
    initials: "ZH",
    iconType: "crm",
  },
  {
    id: "freshsales",
    name: "Freshsales",
    category: "crm",
    description: "Turn Intent Radar signals into actionable Freshworks contacts and sales sequences.",
    status: "coming_soon",
    statusLabel: "Coming Soon",
    capabilities: ["Contact Timeline", "Deal Pipeline", "Account Context"],
    brandColor: "bg-[#F38020]/10 text-[#F38020] border-[#F38020]/20",
    initials: "FS",
    iconType: "crm",
  },

  // Spreadsheets & Data
  {
    id: "google-sheets",
    name: "Google Sheets",
    category: "spreadsheets",
    description: "Review a one-way workspace export to an existing spreadsheet.",
    status: "available",
    statusLabel: "Available",
    configHref: "/intent-radar/integrations/sheets",
    capabilities: ["Reviewed range", "Explicit approval"],
    brandColor: "bg-[#0F9D58]/10 text-[#0F9D58] border-[#0F9D58]/20",
    initials: "GS",
    iconType: "sheet",
  },
  {
    id: "microsoft-excel",
    name: "Microsoft Excel Online",
    category: "spreadsheets",
    description: "Export market intelligence and discussion datasets directly into Excel Online or desktop.",
    status: "coming_soon",
    statusLabel: "Coming Soon",
    capabilities: ["Office 365", "Workbook Export", "Structured Tables"],
    brandColor: "bg-[#107C41]/10 text-[#107C41] border-[#107C41]/20",
    initials: "XL",
    iconType: "sheet",
  },
  {
    id: "csv-export",
    name: "CSV Export",
    category: "spreadsheets",
    description: "Download up to 100 export-permitted records from discovery results.",
    status: "available",
    statusLabel: "Available in Tables",
    capabilities: ["Instant Download", "Grounded Columns", "Custom Reporting"],
    brandColor: "bg-primary/10 text-primary border-primary/20",
    initials: "CSV",
    iconType: "csv",
    configHref: "/intent-radar/discover",
  },
  {
    id: "airtable",
    name: "Airtable",
    category: "spreadsheets",
    description: "Send market discussions, signals, and buyer context into custom Airtable bases.",
    status: "coming_soon",
    statusLabel: "Coming Soon",
    capabilities: ["Base Sync", "Custom Views", "Relational Records"],
    brandColor: "bg-[#2D7FF9]/10 text-[#2D7FF9] border-[#2D7FF9]/20",
    initials: "AT",
    iconType: "sheet",
  },

  // Automation
  {
    id: "zapier",
    name: "Zapier",
    category: "automation",
    description: "Connect Intent Radar triggers with 5,000+ business apps without writing code.",
    status: "coming_soon",
    statusLabel: "Coming Soon",
    capabilities: ["Trigger on Signal", "New Opportunity Zap", "Filter by Score"],
    brandColor: "bg-[#FF4A00]/10 text-[#FF4A00] border-[#FF4A00]/20",
    initials: "ZP",
    iconType: "zap",
  },
  {
    id: "make",
    name: "Make (Integromat)",
    category: "automation",
    description: "Build visual multi-step workflows triggered by new opportunities and monitor alerts.",
    status: "coming_soon",
    statusLabel: "Coming Soon",
    capabilities: ["Scenario Routing", "Data Transformation", "Multi-branch"],
    brandColor: "bg-[#6D3AEC]/10 text-[#6D3AEC] border-[#6D3AEC]/20",
    initials: "MK",
    iconType: "zap",
  },
  {
    id: "n8n",
    name: "n8n",
    category: "automation",
    description: "Self-host or cloud-automate data pipelines using n8n node-based workflows.",
    status: "coming_soon",
    statusLabel: "Coming Soon",
    capabilities: ["Self-hosted Nodes", "Community Workflows", "API Polling"],
    brandColor: "bg-[#EA4B71]/10 text-[#EA4B71] border-[#EA4B71]/20",
    initials: "N8",
    iconType: "zap",
  },

  // Communication & Collaboration
  {
    id: "slack",
    name: "Slack",
    category: "collaboration",
    description: "Receive important Intent Radar signal alerts directly in your team's Slack channels.",
    status: "coming_soon",
    statusLabel: "Coming Soon",
    capabilities: ["Channel Broadcasts", "Score Badges", "One-click Triage"],
    brandColor: "bg-[#4A154B]/10 text-[#4A154B] dark:text-[#E01E5A] border-[#4A154B]/20",
    initials: "SL",
    iconType: "chat",
  },
  {
    id: "microsoft-teams",
    name: "Microsoft Teams",
    category: "collaboration",
    description: "Deliver high-relevance intent alerts into Microsoft Teams channels with rich adaptive cards.",
    status: "coming_soon",
    statusLabel: "Coming Soon",
    capabilities: ["Teams Webhooks", "Channel Alerts", "Interactive Cards"],
    brandColor: "bg-[#5059C9]/10 text-[#5059C9] border-[#5059C9]/20",
    initials: "MT",
    iconType: "chat",
  },
  {
    id: "notion",
    name: "Notion",
    category: "collaboration",
    description: "Save curated research findings, competitor themes, and market dossiers to Notion pages.",
    status: "coming_soon",
    statusLabel: "Coming Soon",
    capabilities: ["Database Append", "Research Notes", "Dossier Sync"],
    brandColor: "bg-slate-900/10 text-slate-900 dark:text-slate-100 border-slate-900/20",
    initials: "NT",
    iconType: "chat",
  },

  // Developer Tools
  ...(['xlsx','json','pdf'] as const).map(format=>({id:format,name:format==='xlsx'?'Excel (.xlsx)':format.toUpperCase(),category:'spreadsheets' as const,description:'Download permitted workspace evidence. No external account required.',status:'available' as const,statusLabel:'Available',capabilities:['Manual download'],brandColor:'bg-primary/10 text-primary',initials:format,iconType:'sheet' as const,configHref:'/intent-radar/discover'})),
  {id:'mcp',name:'MCP',category:'developer',description:'Read permitted workspace evidence from a compatible client.',status:'available',statusLabel:'Available',capabilities:['Scoped bearer key'],brandColor:'bg-primary/10 text-primary',initials:'MCP',iconType:'code',configHref:'/settings?category=developer&tab=mcp'},
  {
    id: "developer-api",
    name: "REST API",
    category: "developer",
    description: "Read authorized signals, monitors, opportunities and discovery history with a scoped workspace key.",
    status: "available",
    statusLabel: "Available",
    capabilities: ["Scoped API Keys", "OpenAPI Spec", "Rate-limited"],
    brandColor: "bg-blue-600/10 text-blue-600 border-blue-600/20",
    initials: "API",
    iconType: "code",
    configHref: "/settings?category=developer&tab=keys",
  },
  {
    id: "webhooks",
    name: "Webhooks",
    category: "developer",
    description: "Manage signed, identifier-only deliveries for supported event topics.",
    status: "available",
    statusLabel: "Available",
    capabilities: ["Event Subscriptions", "HMAC Signatures", "Retry Delivery"],
    brandColor: "bg-indigo-600/10 text-indigo-600 border-indigo-600/20",
    initials: "WH",
    iconType: "code",
    configHref: "/intent-radar/integrations/webhooks",
  },
];

function CategoryIcon({ type }: { type: IntegrationItem["iconType"] }) {
  switch (type) {
    case "crm":
      return <Network size={18} />;
    case "sheet":
      return <FileSpreadsheet size={18} />;
    case "csv":
      return <Download size={18} />;
    case "zap":
      return <Workflow size={18} />;
    case "chat":
      return <Share2 size={18} />;
    case "code":
      return <Terminal size={18} />;
    default:
      return <Plug size={18} />;
  }
}

export function CustomerIntegrationsCatalog() {
  const sheets=useRadarRead<SheetStatus>('/sheets');
  const availability=useRadarRead<{files:boolean;developer:boolean;mcp:boolean;webhooks:boolean}>('/destinations');
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<IntegrationCategory>("all");

  const filtered = useMemo(() => {
    return INTEGRATION_CATALOG.filter((item) => {
      const matchCat = category === "all" || item.category === category;
      const q = search.trim().toLowerCase();
      const matchSearch =
        !q ||
        item.name.toLowerCase().includes(q) ||
        item.description.toLowerCase().includes(q) ||
        item.capabilities.some((c) => c.toLowerCase().includes(q));
      return matchCat && matchSearch;
    });
  }, [category, search]);

  const countForCategory = (catId: IntegrationCategory) => {
    if (catId === "all") return INTEGRATION_CATALOG.length;
    return INTEGRATION_CATALOG.filter((i) => i.category === catId).length;
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Page Header */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <Plug size={22} className="text-primary" />
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Integrations</h1>
        </div>
        <p className="text-sm text-muted-foreground max-w-3xl">
          Connect your favorite tools and bring Intent Radar insights into your existing workflow.
        </p>
      </div>

      {/* Distinction Info Callout */}
      <div className="flex items-start gap-3 rounded-2xl border border-border/80 bg-muted/20 p-4 text-xs text-muted-foreground">
        <Sparkles size={16} className="text-primary shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <p className="font-semibold text-foreground">
            Customer Workflow &amp; Destination Tools
          </p>
          <p className="leading-relaxed">
            This catalog connects PlaneByte insights to your CRMs, spreadsheets, and automation tools.
            To configure where PlaneByte gathers research evidence (Hacker News, GitHub, YouTube, etc.),
            visit{" "}
            <Link
              href="/settings?category=sources&tab=sources"
              className="font-medium text-primary hover:underline"
            >
              Settings &rsaquo; Sources &amp; Tools
            </Link>
            . To manage API keys and MCP servers, visit{" "}
            <Link
              href="/settings?category=developer&tab=keys"
              className="font-medium text-primary hover:underline"
            >
              Settings &rsaquo; Developer &amp; API
            </Link>
            .
          </p>
        </div>
      </div>

      {/* Search and Category Filter Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        {/* Category Tabs */}
        <div
          role="tablist"
          aria-label="Integration categories"
          className="flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0"
        >
          {INTEGRATION_CATEGORIES.map((cat) => {
            const isSelected = category === cat.id;
            const count = countForCategory(cat.id);
            return (
              <button
                key={cat.id}
                role="tab"
                aria-selected={isSelected}
                onClick={() => setCategory(cat.id)}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-colors cursor-pointer ${
                  isSelected
                    ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                    : "bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
              >
                <span>{cat.label}</span>
                <span
                  className={`rounded-full px-1.5 py-0.2 text-[10px] tabular-nums ${
                    isSelected ? "bg-primary-foreground/20 text-primary-foreground" : "bg-background/80 text-muted-foreground"
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Search Input */}
        <div className="w-full sm:w-64 shrink-0">
          <SearchInput
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onClear={() => setSearch("")}
            placeholder="Search integrations…"
            aria-label="Search customer integrations"
          />
        </div>
      </div>

      {/* Integrations Grid */}
      {filtered.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((item) => {
            const state=availability.isError?undefined:availability.data;
            const isAvailable = item.status === 'available' && !!(item.id==='google-sheets'?state?.files&&!sheets.isError&&sheets.data?.configured:item.id==='developer-api'?state?.developer:item.id==='webhooks'?state?.webhooks:item.id==='mcp'?state?.mcp:state?.files);
            const badge=isAvailable?'Available':item.status==='available'?'Unavailable':'Coming Soon';
            return (
              <div
                key={item.id}
                className="group flex flex-col justify-between rounded-2xl border border-border/80 bg-card p-5 shadow-xs hover:border-primary/40 hover:shadow-sm transition-all"
              >
                <div className="space-y-3.5">
                  {/* Top Bar: Icon + Status */}
                  <div className="flex items-start justify-between gap-2">
                    <div
                      className={`flex h-11 w-11 items-center justify-center rounded-xl border font-bold text-sm shadow-xs ${item.brandColor}`}
                      aria-hidden="true"
                    >
                      <CategoryIcon type={item.iconType} />
                    </div>

                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium border ${
                        isAvailable
                          ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/25"
                          : "bg-muted text-muted-foreground border-border/80"
                      }`}
                    >
                      {isAvailable ? <CheckCircle2 size={11} /> : <Clock size={11} />}
                      <span>{badge}</span>
                      {item.id==='google-sheets'&&isAvailable&&<span> · {sheets.data?.health}</span>}
                    </span>
                  </div>

                  {/* Title & Description */}
                  <div>
                    <h3 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors">
                      {item.name}
                    </h3>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                      {item.description}
                    </p>
                  </div>

                  {/* Capabilities Tags */}
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {item.capabilities.map((cap) => (
                      <span
                        key={cap}
                        className="rounded-md border border-border/70 bg-muted/30 px-2 py-0.5 text-[10px] text-muted-foreground font-medium"
                      >
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Bottom Action Area */}
                <div className="pt-4 mt-4 border-t border-border/60">
                  {isAvailable && item.configHref ? (
                    <Link
                      href={item.configHref}
                      className="inline-flex h-8 w-full items-center justify-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 text-primary text-xs font-semibold hover:bg-primary/20 transition-colors"
                    >
                      <span>Configure &rarr;</span>
                    </Link>
                  ) : (
                    <button
                      type="button"
                      disabled
                      aria-disabled="true"
                      className="inline-flex h-8 w-full items-center justify-center gap-1.5 rounded-lg border border-border/60 bg-muted/40 text-muted-foreground text-xs font-medium cursor-not-allowed opacity-80"
                    >
                      <span>{badge}</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-border bg-card p-12 text-center space-y-3">
          <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl bg-muted text-muted-foreground">
            <Search size={18} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">No integrations match &quot;{search}&quot;</h3>
            <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
              Try adjusting your search terms or select another category filter.
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              setSearch("");
              setCategory("all");
            }}
            className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline cursor-pointer"
          >
            <span>Reset filters</span>
            <X size={12} />
          </button>
        </div>
      )}
    </div>
  );
}
