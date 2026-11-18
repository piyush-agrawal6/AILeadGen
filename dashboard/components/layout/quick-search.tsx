"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import * as Dialog from "@radix-ui/react-dialog";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Bookmark,
  BookOpen,
  Building2,
  Clock,
  CreditCard,
  Gauge,
  KeyRound,
  LifeBuoy,
  Loader2,
  Network,
  Plug,
  Radio,
  RefreshCw,
  Search,
  Settings2,
  SlidersHorizontal,
  Sparkles,
  Target,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";
import { request } from "@/lib/intelligence";
import { useWorkspace } from "@/components/workspaces/use-workspace";
import { useProducts } from "@/components/workspaces/use-products";
import { Button } from "@/components/ui/button";

type CategoryTab = "all" | "pages" | "discoveries" | "monitors" | "sources" | "help";

interface PaletteItem {
  id: string;
  title: string;
  subtitle: string;
  href: string;
  group: string;
  type: string;
  badge?: string;
  updatedAt?: string | null;
  icon: LucideIcon;
  meta?: Record<string, unknown>;
}

interface BackendResult {
  id: string;
  type: string;
  title: string;
  subtitle: string;
  href: string;
  badge?: string;
  updated_at?: string | null;
  meta?: Record<string, unknown>;
  score?: number;
}

interface SearchApiResponse {
  query: string;
  organization_id: string | null;
  radar_enabled: boolean;
  growth_enabled: boolean;
  top?: BackendResult[];
  groups: {
    discoveries: BackendResult[];
    saved_searches: BackendResult[];
    signals: BackendResult[];
    opportunities: BackendResult[];
    monitors: BackendResult[];
    icps: BackendResult[];
    sources: BackendResult[];
    intelligence: BackendResult[];
    help: BackendResult[];
  };
  partial_errors: string[];
}

interface StaticNavEntry {
  id: string;
  title: string;
  subtitle: string;
  href: string;
  group: "Pages & Settings" | "Quick Actions";
  keywords: string[];
  icon: LucideIcon;
  requiresRadar?: boolean;
  requiresGrowth?: boolean;
}

const STATIC_ITEMS: StaticNavEntry[] = [
  { id: "nav-home", title: "Intent Radar Home", subtitle: "Workspace overview & recent activity", href: "/intent-radar", group: "Pages & Settings", keywords: ["home", "dashboard", "overview"], icon: Gauge, requiresRadar: true },
  { id: "nav-discover", title: "New Discovery", subtitle: "Search public conversations across approved sources", href: "/intent-radar/discover", group: "Quick Actions", keywords: ["discover", "search", "find", "new"], icon: Search, requiresRadar: true },
  { id: "nav-history", title: "Discovery History", subtitle: "Review past discovery runs & results", href: "/intent-radar/discover/history", group: "Pages & Settings", keywords: ["history", "runs", "discoveries"], icon: Clock, requiresRadar: true },
  { id: "nav-saved-searches", title: "Saved Searches", subtitle: "Reuse saved search configurations", href: "/intent-radar/discover/saved", group: "Pages & Settings", keywords: ["saved", "queries", "templates"], icon: Bookmark, requiresRadar: true },
  { id: "nav-signals", title: "Intent Signals", subtitle: "Triage & evaluate collected discussions", href: "/intent-radar/signals", group: "Pages & Settings", keywords: ["signals", "evidence", "intent"], icon: Activity, requiresRadar: true },
  { id: "nav-opportunities", title: "Opportunities", subtitle: "Track qualified buying opportunities", href: "/intent-radar/opportunities", group: "Pages & Settings", keywords: ["opportunities", "pipeline", "qualified"], icon: Target, requiresRadar: true },
  { id: "nav-monitors", title: "Monitoring & Schedules", subtitle: "Automated recurring signal checks", href: "/intent-radar/monitors", group: "Quick Actions", keywords: ["monitors", "alerts", "schedule", "watch"], icon: Radio, requiresRadar: true },
  { id: "nav-icp", title: "Ideal Customers (ICPs)", subtitle: "Manage buyer personas & targeting profiles", href: "/intent-radar/ideal-customers", group: "Pages & Settings", keywords: ["icp", "ideal customer", "persona", "target"], icon: Users, requiresRadar: true },
  { id: "nav-growth", title: "Growth Intelligence", subtitle: "Themes, research & competitor tracking", href: "/intent-radar/growth", group: "Pages & Settings", keywords: ["growth", "reports", "themes", "competitors"], icon: Sparkles, requiresRadar: true, requiresGrowth: true },
  { id: "nav-graph", title: "Intelligence Graph", subtitle: "Connected company, ICP & topic relationships", href: "/intent-radar/graph", group: "Pages & Settings", keywords: ["graph", "network", "map"], icon: Network, requiresRadar: true },
  { id: "nav-library", title: "Research Library", subtitle: "Bookmarked signals & curated collections", href: "/intent-radar/saved", group: "Pages & Settings", keywords: ["library", "bookmarks", "saved"], icon: Bookmark, requiresRadar: true },
  { id: "nav-assistant", title: "AI Assistant", subtitle: "Workspace-aware research & action assistant", href: "/intelligence/assistant", group: "Quick Actions", keywords: ["ai", "assistant", "chat", "copilot"], icon: Sparkles, requiresRadar: true, requiresGrowth: true },
  { id: "nav-sources", title: "Research Sources", subtitle: "GitHub App, YouTube, Bluesky, HN & Stack Exchange", href: "/settings?category=integrations&tab=sources", group: "Pages & Settings", keywords: ["sources", "github", "webhooks", "youtube", "bluesky", "hacker news", "integrations"], icon: Plug },
  { id: "nav-feeds", title: "Custom Feeds", subtitle: "Curated & custom Atom / Discourse feeds", href: "/settings?category=integrations&tab=feeds", group: "Pages & Settings", keywords: ["feeds", "rss", "atom", "discourse", "catalog"], icon: Radio },
  { id: "nav-dev", title: "Developer API & MCP", subtitle: "API keys, OpenAPI spec & MCP setup", href: "/settings?category=integrations&tab=developer", group: "Quick Actions", keywords: ["api", "mcp", "keys", "tokens", "developer"], icon: KeyRound },
  { id: "nav-billing", title: "Billing & Usage", subtitle: "Subscription status, usage limits & invoices", href: "/settings?category=billing&tab=overview", group: "Pages & Settings", keywords: ["billing", "plan", "usage", "trial", "creem", "invoices"], icon: CreditCard },
  { id: "nav-plans", title: "Compare Plans", subtitle: "Starter, Growth, Scale & Enterprise plans", href: "/settings?category=billing&tab=plans", group: "Pages & Settings", keywords: ["plans", "pricing", "upgrade"], icon: CreditCard },
  { id: "nav-prefs", title: "Research Preferences", subtitle: "Discovery defaults, notifications, retention & limits", href: "/settings?category=preferences&tab=discovery", group: "Pages & Settings", keywords: ["preferences", "defaults", "notifications", "alerts", "retention", "limits"], icon: SlidersHorizontal },
  { id: "nav-notif-prefs", title: "Notification Settings", subtitle: "Email alerts, quiet hours & alert threshold", href: "/settings?category=preferences&tab=notifications", group: "Pages & Settings", keywords: ["notifications", "email", "quiet hours", "alerts"], icon: Settings2 },
  { id: "nav-team", title: "Team & Access", subtitle: "Members, invitations, roles & audit log", href: "/settings?category=team&tab=members", group: "Pages & Settings", keywords: ["team", "members", "invite", "roles", "audit"], icon: Users },
  { id: "nav-company", title: "Organization Profile & Domains", subtitle: "Company context, AI website research & DNS domains", href: "/settings?category=company&tab=profile", group: "Pages & Settings", keywords: ["company", "profile", "domain", "dns", "website"], icon: Building2 },
  { id: "nav-workspaces", title: "Manage Workspaces", subtitle: "Switch, create, rename or leave workspaces", href: "/settings/workspaces", group: "Quick Actions", keywords: ["workspaces", "switch", "create workspace"], icon: Building2 },
  { id: "nav-help", title: "Help & Support", subtitle: "Knowledge base guides & contact support", href: "/help", group: "Pages & Settings", keywords: ["help", "support", "docs", "bug", "guide"], icon: LifeBuoy },
];

const SUGGESTED_QUERIES = [
  "GitHub webhooks",
  "Billing & usage",
  "Active monitors",
  "Notification settings",
];

function iconForType(type: string): LucideIcon {
  switch (type) {
    case "discovery":
      return Search;
    case "saved_search":
      return Bookmark;
    case "signal":
      return Activity;
    case "opportunity":
      return Target;
    case "monitor":
      return Radio;
    case "icp":
      return Users;
    case "source":
    case "feed":
      return Plug;
    case "report":
    case "research":
    case "competitor":
    case "library":
      return Sparkles;
    case "help":
      return BookOpen;
    default:
      return Search;
  }
}

function formatDateShort(iso?: string | null) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  } catch {
    return "";
  }
}

export function QuickSearchTrigger() {
  const router = useRouter();
  const workspace = useWorkspace();
  const products = useProducts();
  const orgId = workspace.data?.active_organization_id || "";
  const radarEnabled = Boolean(products.data?.intent_radar.enabled);
  const growthEnabled = Boolean(products.data?.intent_radar.growth_enabled);

  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<CategoryTab>("all");
  const [activeIndex, setActiveIndex] = useState(0);

  const [loading, setLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [apiData, setApiData] = useState<SearchApiResponse | null>(null);
  const [retryTick, setRetryTick] = useState(0);

  // Recent searches (strictly scoped by orgId)
  const [recentQueries, setRecentQueries] = useState<string[]>([]);

  // Explicit "Ask AI" inline state (ONLY invoked on explicit user click)
  const [aiBusy, setAiBusy] = useState(false);
  const [aiAnswer, setAiAnswer] = useState<{
    markdown: string;
    threadId: string | null;
    mode?: string;
    citations?: { label: string; url: string }[];
  } | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);

  const inputRef = useRef<HTMLInputElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Load workspace-scoped recent searches & clear stale state on org switch
  useEffect(() => {
    setApiData(null);
    setAiAnswer(null);
    setAiError(null);
    if (typeof window !== "undefined" && orgId) {
      try {
        const raw = window.sessionStorage.getItem(`pb_recent_searches:${orgId}`);
        setRecentQueries(raw ? (JSON.parse(raw) as string[]).slice(0, 5) : []);
      } catch {
        setRecentQueries([]);
      }
    } else {
      setRecentQueries([]);
    }
  }, [orgId]);

  function recordRecent(q: string) {
    const clean = q.trim();
    if (!clean || clean.length < 2 || !orgId) return;
    const next = [clean, ...recentQueries.filter((r) => r.toLowerCase() !== clean.toLowerCase())].slice(0, 5);
    setRecentQueries(next);
    try {
      window.sessionStorage.setItem(`pb_recent_searches:${orgId}`, JSON.stringify(next));
    } catch {
      // ignore
    }
  }

  // Global Cmd+K / Ctrl+K shortcut
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  // Debounced, AbortController-canceled backend search
  useEffect(() => {
    if (!open) return;
    const trimmed = query.trim();
    if (!trimmed && category === "pages") {
      setApiData(null);
      setLoading(false);
      setSearchError(null);
      return;
    }

    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    const timer = setTimeout(async () => {
      setLoading(true);
      setSearchError(null);
      try {
        const backendCat =
          category === "pages"
            ? "all"
            : category === "discoveries"
              ? "discoveries"
              : category === "monitors"
                ? "monitors"
                : category === "sources"
                  ? "sources"
                  : category === "help"
                    ? "help"
                    : "all";
        const res = await request<SearchApiResponse>(
          `/search?q=${encodeURIComponent(trimmed)}&category=${backendCat}&limit=6`,
          { signal: ctrl.signal }
        );
        if (!ctrl.signal.aborted) {
          setApiData(res);
        }
      } catch (err) {
        if (!ctrl.signal.aborted) {
          setSearchError(err instanceof Error ? err.message : "Workspace search failed.");
        }
      } finally {
        if (!ctrl.signal.aborted) {
          setLoading(false);
        }
      }
    }, trimmed ? 180 : 40);

    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
  }, [open, query, category, orgId, retryTick]);

  // Build unified filtered items list
  const items: PaletteItem[] = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list: PaletteItem[] = [];

    // 1. Pages & Settings / Quick Actions
    if (category === "all" || category === "pages") {
      for (const nav of STATIC_ITEMS) {
        if (nav.requiresRadar && !radarEnabled) continue;
        if (nav.requiresGrowth && !growthEnabled) continue;
        const hay = `${nav.title} ${nav.subtitle} ${nav.keywords.join(" ")}`.toLowerCase();
        if (!q || hay.includes(q) || q.split(/\s+/).every((t) => hay.includes(t))) {
          list.push({
            id: nav.id,
            title: nav.title,
            subtitle: nav.subtitle,
            href: nav.href,
            group: nav.group,
            type: nav.group === "Quick Actions" ? "action" : "page",
            icon: nav.icon,
          });
        }
      }
    }

    // 2. Live Workspace Records from /api/search
    if (apiData && category !== "pages") {
      const addGroup = (groupLabel: string, rows: BackendResult[] | undefined) => {
        for (const r of rows || []) {
          list.push({
            id: r.id,
            title: r.title,
            subtitle: r.subtitle || "",
            href: r.href,
            group: groupLabel,
            type: r.type,
            badge: r.badge,
            updatedAt: r.updated_at,
            icon: iconForType(r.type),
            meta: r.meta,
          });
        }
      };

      if (category === "all" || category === "discoveries") {
        addGroup("Discoveries & Saved Searches", [
          ...(apiData.groups.discoveries || []),
          ...(apiData.groups.saved_searches || []),
        ]);
        addGroup("Intent Signals", apiData.groups.signals);
      }
      if (category === "all" || category === "monitors") {
        addGroup("Monitors & Opportunities", [
          ...(apiData.groups.monitors || []),
          ...(apiData.groups.opportunities || []),
        ]);
      }
      if (category === "all" || category === "sources") {
        addGroup("Sources & Integrations", apiData.groups.sources);
      }
      if (category === "all") {
        addGroup("Intelligence & ICPs", [
          ...(apiData.groups.icps || []),
          ...(apiData.groups.intelligence || []),
        ]);
      }
      if (category === "all" || category === "help") {
        addGroup("Help & Documentation", apiData.groups.help);
      }
    }

    // Deduplicate by id
    const seen = new Set<string>();
    return list.filter((it) => {
      if (seen.has(it.id)) return false;
      seen.add(it.id);
      return true;
    });
  }, [query, category, radarEnabled, growthEnabled, apiData]);

  // Keep activeIndex in bounds
  const safeIndex = items.length ? Math.min(activeIndex, items.length - 1) : 0;
  const selectedItem = items[safeIndex] || null;

  // Group items preserving order for section headers
  const groupedSections = useMemo(() => {
    const map = new Map<string, { item: PaletteItem; flatIndex: number }[]>();
    items.forEach((item, idx) => {
      const arr = map.get(item.group) || [];
      arr.push({ item, flatIndex: idx });
      map.set(item.group, arr);
    });
    return Array.from(map.entries());
  }, [items]);

  function openItem(item: PaletteItem) {
    if (query.trim()) recordRecent(query);
    setOpen(false);
    setQuery("");
    setAiAnswer(null);
    router.push(item.href);
  }

  async function askAiInline() {
    const q = query.trim();
    if (!q || aiBusy) return;
    recordRecent(q);
    if (!growthEnabled) {
      setOpen(false);
      router.push(`/help?article=ai-assistant-icps`);
      return;
    }
    setAiBusy(true);
    setAiError(null);
    setAiAnswer(null);
    try {
      const resp = await fetch("/api/intent-radar/assistant/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: q,
          context_type: "overview",
          request_id: crypto.randomUUID(),
        }),
      });
      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData?.detail || `AI search unavailable (HTTP ${resp.status}).`);
      }
      const reader = resp.body?.getReader();
      if (!reader) throw new Error("Streaming response unavailable.");
      const decoder = new TextDecoder();
      let buffer = "";
      let accumulated = "";
      let threadId: string | null = null;
      let mode = "";
      let citations: { label: string; url: string }[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";
        for (const block of events) {
          const lines = block.split("\n");
          let eventName = "";
          let dataStr = "";
          for (const ln of lines) {
            if (ln.startsWith("event:")) eventName = ln.slice(6).trim();
            if (ln.startsWith("data:")) dataStr += ln.slice(5).trim();
          }
          if (!dataStr) continue;
          try {
            const payload = JSON.parse(dataStr);
            if (eventName === "status" && payload.thread_id) {
              threadId = payload.thread_id;
            } else if (eventName === "delta" && payload.text) {
              accumulated += payload.text;
              setAiAnswer({ markdown: accumulated, threadId, mode, citations });
            } else if (eventName === "cards" && Array.isArray(payload.citations)) {
              citations = payload.citations;
            } else if (eventName === "done" && payload.message) {
              accumulated = payload.message.markdown || accumulated;
              threadId = payload.message.thread_id || threadId;
              mode = payload.message.mode || "";
              citations = payload.message.citations || citations;
              setAiAnswer({ markdown: accumulated, threadId, mode, citations });
            }
          } catch {
            // ignore partial JSON chunks
          }
        }
      }
    } catch (err) {
      setAiError(err instanceof Error ? err.message : "Could not complete AI search.");
    } finally {
      setAiBusy(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((prev) => (items.length ? (prev + 1) % items.length : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((prev) => (items.length ? (prev - 1 + items.length) % items.length : 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (selectedItem) {
        openItem(selectedItem);
      } else if (query.trim()) {
        void askAiInline();
      }
    }
  }

  return (
    <>
      {/* Desktop + Mobile Search Trigger */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Universal search (⌘K)"
        className="inline-flex h-8 items-center gap-2 rounded-lg border border-border bg-muted/40 px-2.5 text-xs text-muted-foreground hover:border-primary/40 hover:bg-muted/70 hover:text-foreground transition-colors cursor-pointer"
      >
        <Search size={14} className="shrink-0" />
        <span className="hidden sm:inline">Search workspace…</span>
        <kbd className="hidden md:inline-flex items-center rounded border border-border bg-background px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
          ⌘K
        </kbd>
      </button>

      <Dialog.Root
        open={open}
        onOpenChange={(next) => {
          setOpen(next);
          if (!next) {
            setAiError(null);
          } else {
            setTimeout(() => inputRef.current?.focus(), 30);
          }
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/45 backdrop-blur-[2px]" />
          <Dialog.Content
            aria-label="Universal workspace search"
            className="fixed left-1/2 top-[10vh] z-50 flex max-h-[80vh] w-[calc(100%-1.5rem)] max-w-[820px] -translate-x-1/2 flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-2xl"
          >
            <Dialog.Title className="sr-only">Universal workspace search</Dialog.Title>
            <Dialog.Description className="sr-only">
              Search pages, settings, discoveries, signals, monitors, opportunities, sources, and help articles.
            </Dialog.Description>

            {/* Search Input Header */}
            <div className="flex items-center gap-2.5 border-b border-border px-4 py-3">
              {loading ? (
                <Loader2 size={17} className="shrink-0 animate-spin text-primary" />
              ) : (
                <Search size={17} className="shrink-0 text-muted-foreground" />
              )}
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setActiveIndex(0);
                  setAiAnswer(null);
                  setAiError(null);
                }}
                onKeyDown={handleKeyDown}
                placeholder="Search discoveries, signals, monitors, sources, settings, or ask a question…"
                aria-label="Search workspace"
                className="flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
              />
              {query && (
                <button
                  type="button"
                  onClick={() => {
                    setQuery("");
                    setAiAnswer(null);
                    setAiError(null);
                    inputRef.current?.focus();
                  }}
                  aria-label="Clear search"
                  className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground cursor-pointer"
                >
                  <X size={14} />
                </button>
              )}
              {query.trim() && growthEnabled && (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={aiBusy}
                  onClick={() => void askAiInline()}
                  className="h-7 px-2.5 text-[11px] gap-1 border-primary/30 text-primary hover:bg-primary/5 shrink-0"
                >
                  {aiBusy ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
                  Ask AI
                </Button>
              )}
            </div>

            {/* Category Filter Pills */}
            <div className="flex items-center gap-1 overflow-x-auto border-b border-border/70 bg-muted/20 px-4 py-2">
              {(
                [
                  { id: "all", label: "All" },
                  { id: "pages", label: "Pages & Settings" },
                  { id: "discoveries", label: "Discoveries & Signals" },
                  { id: "monitors", label: "Monitors & Opportunities" },
                  { id: "sources", label: "Sources & Integrations" },
                  { id: "help", label: "Help" },
                ] as { id: CategoryTab; label: string }[]
              ).map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => {
                    setCategory(tab.id);
                    setActiveIndex(0);
                  }}
                  className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors cursor-pointer ${
                    category === tab.id
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Inline AI Answer Panel (Only when explicitly triggered) */}
            {(aiBusy || aiAnswer || aiError) && (
              <div className="border-b border-primary/20 bg-primary/[0.03] px-4 py-3 space-y-2 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <span className="inline-flex items-center gap-1.5 font-semibold text-primary">
                    <Sparkles size={13} />
                    {aiBusy ? "Searching workspace with AI…" : "AI Workspace Answer"}
                    {aiAnswer?.mode && (
                      <span className="font-normal text-[10px] text-muted-foreground">
                        · {aiAnswer.mode}
                      </span>
                    )}
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      const target = aiAnswer?.threadId
                        ? `/intelligence/assistant?thread=${encodeURIComponent(aiAnswer.threadId)}`
                        : `/intelligence/assistant?prompt=${encodeURIComponent(query.trim())}&context=overview`;
                      setOpen(false);
                      router.push(target);
                    }}
                    className="inline-flex items-center gap-1 text-[11px] font-semibold text-primary hover:underline cursor-pointer"
                  >
                    Continue in AI Assistant <ArrowRight size={11} />
                  </button>
                </div>
                {aiError && <p className="text-destructive">{aiError}</p>}
                {aiAnswer && (
                  <div className="max-h-36 overflow-y-auto whitespace-pre-wrap text-foreground leading-relaxed">
                    {aiAnswer.markdown}
                  </div>
                )}
              </div>
            )}

            {/* Main Split Body: Results List + Optional Right Preview Panel */}
            <div className="grid min-h-0 flex-1 md:grid-cols-[minmax(0,1fr)_270px]">
              {/* Left: Scrollable Results */}
              <div className="overflow-y-auto p-3 space-y-3">
                {/* Recent & Suggested Queries (when input empty) */}
                {!query.trim() && (recentQueries.length > 0 || category === "all") && (
                  <div className="flex flex-wrap items-center gap-1.5 px-1">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mr-1">
                      {recentQueries.length > 0 ? "Recent" : "Try"}
                    </span>
                    {(recentQueries.length > 0 ? recentQueries : SUGGESTED_QUERIES).map((s) => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => {
                          setQuery(s);
                          setActiveIndex(0);
                        }}
                        className="rounded-md border border-border bg-muted/30 px-2 py-0.5 text-[11px] text-foreground hover:border-primary/40 hover:text-primary cursor-pointer"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                )}

                {/* Explicit Backend Error State (never silently shown as empty!) */}
                {searchError && (
                  <div
                    role="alert"
                    className="flex items-center justify-between gap-2 rounded-xl border border-destructive/25 bg-destructive/5 px-3 py-2 text-xs text-destructive"
                  >
                    <span className="flex items-center gap-1.5">
                      <AlertTriangle size={13} />
                      Workspace data search failed ({searchError}). Navigation links remain available.
                    </span>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setRetryTick((t) => t + 1)}
                      className="h-6 px-2 text-[11px] gap-1 shrink-0"
                    >
                      <RefreshCw size={11} /> Retry
                    </Button>
                  </div>
                )}

                {/* Grouped Results */}
                {groupedSections.length > 0 ? (
                  groupedSections.map(([groupName, entries]) => (
                    <div key={groupName} className="space-y-1">
                      <p className="px-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                        {groupName}
                      </p>
                      <div className="space-y-0.5">
                        {entries.map(({ item, flatIndex }) => {
                          const Icon = item.icon;
                          const isActive = flatIndex === safeIndex;
                          return (
                            <button
                              key={item.id}
                              type="button"
                              onMouseEnter={() => setActiveIndex(flatIndex)}
                              onClick={() => openItem(item)}
                              className={`flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors cursor-pointer ${
                                isActive
                                  ? "bg-primary/10 text-foreground"
                                  : "text-foreground hover:bg-muted/50"
                              }`}
                            >
                              <Icon
                                size={15}
                                className={`shrink-0 ${isActive ? "text-primary" : "text-muted-foreground"}`}
                              />
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-2">
                                  <span className="truncate text-xs font-medium">{item.title}</span>
                                  {item.badge && (
                                    <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                                      {item.badge}
                                    </span>
                                  )}
                                </div>
                                {item.subtitle && (
                                  <p className="truncate text-[11px] text-muted-foreground">
                                    {item.subtitle}
                                  </p>
                                )}
                              </div>
                              {item.updatedAt && (
                                <span className="shrink-0 text-[10px] text-muted-foreground tabular-nums">
                                  {formatDateShort(item.updatedAt)}
                                </span>
                              )}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))
                ) : !loading ? (
                  <div className="py-10 text-center space-y-2.5">
                    <p className="text-sm font-medium text-foreground">
                      No matching results for &ldquo;{query}&rdquo;
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Try another keyword or ask the PlaneByte AI Assistant.
                    </p>
                    {growthEnabled && query.trim() && (
                      <Button
                        size="sm"
                        onClick={() => void askAiInline()}
                        className="h-8 text-xs gap-1.5"
                      >
                        <Sparkles size={13} />
                        Ask AI about &ldquo;{query.slice(0, 32)}&rdquo;
                      </Button>
                    )}
                  </div>
                ) : null}
              </div>

              {/* Right: Contextual Preview Pane (Desktop md+) */}
              <aside className="hidden md:flex flex-col justify-between border-l border-border/70 bg-muted/15 p-4 text-xs">
                {selectedItem ? (
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <selectedItem.icon size={15} />
                      </span>
                      <div className="min-w-0">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                          {selectedItem.group}
                        </p>
                        {selectedItem.badge && (
                          <span className="text-[11px] font-medium text-primary">
                            {selectedItem.badge}
                          </span>
                        )}
                      </div>
                    </div>
                    <h3 className="text-sm font-semibold text-foreground leading-snug">
                      {selectedItem.title}
                    </h3>
                    {selectedItem.subtitle && (
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {selectedItem.subtitle}
                      </p>
                    )}
                    {selectedItem.updatedAt && (
                      <p className="text-[11px] text-muted-foreground">
                        Updated: <strong className="text-foreground">{formatDateShort(selectedItem.updatedAt)}</strong>
                      </p>
                    )}
                    <Button
                      size="sm"
                      onClick={() => openItem(selectedItem)}
                      className="w-full h-8 text-xs gap-1.5 mt-2"
                    >
                      <span>Open</span>
                      <ArrowRight size={13} />
                    </Button>
                  </div>
                ) : (
                  <div className="text-muted-foreground text-xs">
                    Select any result to preview details and open directly.
                  </div>
                )}

                <div className="border-t border-border/70 pt-3 text-[10px] text-muted-foreground flex items-center justify-between">
                  <span>↑↓ navigate · ↵ open</span>
                  <span>ESC close</span>
                </div>
              </aside>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}
