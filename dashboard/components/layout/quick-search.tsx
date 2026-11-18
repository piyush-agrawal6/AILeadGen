"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import * as Dialog from "@radix-ui/react-dialog";
import {
  Activity,
  Bell,
  Bookmark,
  CreditCard,
  Gauge,
  KeyRound,
  LifeBuoy,
  Network,
  Plug,
  Radio,
  Search,
  Settings2,
  Sparkles,
  Target,
  Users,
  X,
} from "lucide-react";

type QuickItem = {
  id: string;
  title: string;
  subtitle: string;
  href: string;
  group: "Workspace" | "Intelligence" | "Settings & Tools";
  keywords: string[];
  icon: typeof Search;
};

const QUICK_ITEMS: QuickItem[] = [
  { id: "home", title: "Home", subtitle: "Intent Radar overview & KPIs", href: "/intent-radar", group: "Workspace", keywords: ["dashboard", "overview", "summary"], icon: Gauge },
  { id: "discover", title: "Discover", subtitle: "Search public conversations & intent", href: "/intent-radar/discover", group: "Workspace", keywords: ["search", "find", "new discovery"], icon: Search },
  { id: "discover-history", title: "Discovery History", subtitle: "Past discovery runs & matched threads", href: "/intent-radar/discover/history", group: "Workspace", keywords: ["runs", "past searches"], icon: Search },
  { id: "signals", title: "Intent Signals", subtitle: "Review, score & triage collected signals", href: "/intent-radar/signals", group: "Workspace", keywords: ["discussions", "conversations", "leads"], icon: Activity },
  { id: "opportunities", title: "Opportunities", subtitle: "Tracked high-intent opportunities", href: "/intent-radar/opportunities", group: "Workspace", keywords: ["pipeline", "deals", "qualified"], icon: Target },
  { id: "monitors", title: "Monitoring", subtitle: "Scheduled monitors & watch rules", href: "/intent-radar/monitors", group: "Workspace", keywords: ["alerts", "watch", "schedule"], icon: Radio },
  { id: "ai-assistant", title: "AI Assistant", subtitle: "Full-page AI workspace copilot", href: "/intelligence/assistant", group: "Intelligence", keywords: ["copilot", "chat", "ask ai", "agent"], icon: Sparkles },
  { id: "icps", title: "Ideal Customers", subtitle: "Manage, compare & prioritize ICPs", href: "/intent-radar/ideal-customers", group: "Intelligence", keywords: ["icp", "target", "persona", "profiles"], icon: Users },
  { id: "growth", title: "Growth Intelligence", subtitle: "Themes, trends, competitors & reports", href: "/intent-radar/growth", group: "Intelligence", keywords: ["reports", "themes", "competitors"], icon: Sparkles },
  { id: "graph", title: "Intelligence Graph", subtitle: "Connected signals, topics & entities", href: "/intent-radar/graph", group: "Intelligence", keywords: ["network", "connections"], icon: Network },
  { id: "library", title: "Research Library", subtitle: "Saved bookmarks & search templates", href: "/intent-radar/saved", group: "Intelligence", keywords: ["bookmarks", "saved"], icon: Bookmark },
  { id: "notifications", title: "Notifications", subtitle: "Workspace alerts & email preferences", href: "/notifications", group: "Settings & Tools", keywords: ["bell", "inbox", "email"], icon: Bell },
  { id: "sources", title: "Integrations & Sources", subtitle: "Connected sources, custom feeds & GitHub", href: "/settings?category=integrations&tab=sources", group: "Settings & Tools", keywords: ["feeds", "rss", "youtube", "discourse", "github"], icon: Plug },
  { id: "api-keys", title: "API Keys & MCP", subtitle: "Developer credentials & MCP server", href: "/settings?category=integrations&tab=api-keys", group: "Settings & Tools", keywords: ["developer", "token", "mcp", "claude"], icon: KeyRound },
  { id: "billing", title: "Billing & Usage", subtitle: "Plan, trial status & monthly allowances", href: "/settings?category=billing&tab=overview", group: "Settings & Tools", keywords: ["plan", "subscription", "quota", "creem", "upgrade"], icon: CreditCard },
  { id: "settings", title: "Workspace Settings", subtitle: "Company profile, preferences & team", href: "/settings", group: "Settings & Tools", keywords: ["company", "team", "preferences"], icon: Settings2 },
  { id: "help", title: "Help & Support", subtitle: "Documentation & troubleshooting", href: "/help", group: "Settings & Tools", keywords: ["docs", "support"], icon: LifeBuoy },
];

export function QuickSearchTrigger() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const router = useRouter();

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((prev) => !prev);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return QUICK_ITEMS;
    return QUICK_ITEMS.filter(
      (item) =>
        item.title.toLowerCase().includes(q) ||
        item.subtitle.toLowerCase().includes(q) ||
        item.keywords.some((kw) => kw.includes(q)),
    );
  }, [query]);

  function navigate(href: string) {
    setOpen(false);
    setQuery("");
    router.push(href);
  }

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <button
          type="button"
          aria-label="Quick search (⌘K)"
          className="hidden sm:inline-flex items-center gap-2 rounded-lg border border-border bg-muted/40 px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <Search size={14} aria-hidden="true" />
          <span className="hidden lg:inline">Quick jump…</span>
          <kbd className="rounded border border-border bg-background px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
            ⌘K
          </kbd>
        </button>
      </Dialog.Trigger>

      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs" />
        <Dialog.Content className="fixed left-1/2 top-[15%] z-50 w-[92vw] max-w-lg -translate-x-1/2 overflow-hidden rounded-2xl border border-border bg-card shadow-2xl">
          <Dialog.Title className="sr-only">Quick navigation</Dialog.Title>
          <Dialog.Description className="sr-only">
            Jump quickly to any PlaneByte workspace page, tool, or setting.
          </Dialog.Description>
          <div className="flex items-center gap-2.5 border-b border-border px-4 py-3">
            <Search size={16} className="shrink-0 text-muted-foreground" />
            <input
              type="text"
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && filtered[0]) {
                  e.preventDefault();
                  navigate(filtered[0].href);
                }
              }}
              placeholder="Jump to Discover, Signals, Ideal Customers, AI Assistant, Billing…"
              className="w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
            />
            <Dialog.Close asChild>
              <button
                type="button"
                aria-label="Close quick search"
                className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <X size={15} />
              </button>
            </Dialog.Close>
          </div>
          <div className="max-h-80 overflow-y-auto p-2">
            {filtered.length === 0 ? (
              <p className="px-3 py-6 text-center text-sm text-muted-foreground">
                No matching destinations. Press Esc to close or ask the{" "}
                <button
                  type="button"
                  onClick={() => navigate(`/intelligence/assistant?prompt=${encodeURIComponent(query)}`)}
                  className="font-medium text-primary underline"
                >
                  AI Assistant
                </button>
                .
              </p>
            ) : (
              (["Workspace", "Intelligence", "Settings & Tools"] as const).map((group) => {
                const items = filtered.filter((item) => item.group === group);
                if (!items.length) return null;
                return (
                  <div key={group} className="mb-2 last:mb-0">
                    <p className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                      {group}
                    </p>
                    <ul className="space-y-0.5">
                      {items.map((item) => {
                        const Icon = item.icon;
                        return (
                          <li key={item.id}>
                            <button
                              type="button"
                              onClick={() => navigate(item.href)}
                              className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors hover:bg-muted"
                            >
                              <Icon size={16} className="shrink-0 text-primary" />
                              <span className="min-w-0 flex-1">
                                <span className="block truncate text-sm font-medium text-foreground">
                                  {item.title}
                                </span>
                                <span className="block truncate text-xs text-muted-foreground">
                                  {item.subtitle}
                                </span>
                              </span>
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                );
              })
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
