"use client";

import { useQuery } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import { request } from "@/lib/intelligence";
import { useRadarCapabilities } from "@/components/intent-radar/provider";
import { DeveloperSettings } from "@/components/workspaces/developer-settings";
import { SourceManagement } from "@/components/intent-radar/source-management";

export function IntegrationsSection({ activeTab }: { activeTab: string }) {
  if (activeTab === "developer") {
    return <DeveloperSettings />;
  }

  if (activeTab === "feeds") {
    return <CustomFeedsTab />;
  }

  return <ApprovedSourcesTab />;
}

interface SourceHealthItem {
  provider: string;
  name: string;
  availability: string;
  state: string;
  last_success: string | null;
  consecutive_failures?: number;
  daily_requests_reserved?: number;
  daily_reservation_limit?: number;
}

function getSourceStatus(providerKey: string, healthItems?: SourceHealthItem[]) {
  const item = healthItems?.find(
    (h) => h.provider === providerKey || h.provider.replace("_", "") === providerKey.replace("_", "")
  );
  if (!item) {
    // If not monitored in telemetry, report as Available/Standby
    return {
      status: "Available",
      badgeClass: "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20",
      info: "Adapter active; queries run on demand",
    };
  }
  if (item.consecutive_failures && item.consecutive_failures > 0) {
    return {
      status: "Warning",
      badgeClass: "bg-destructive/10 text-destructive border-destructive/20",
      info: `${item.consecutive_failures} consecutive failure(s)`,
    };
  }
  if (item.availability === "Available") {
    if (item.state === "COMPLETE") {
      return {
        status: "Active",
        badgeClass: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20",
        info: item.last_success ? `Last synced ${new Date(item.last_success).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : "Telemetry verified",
      };
    }
    return {
      status: "Available",
      badgeClass: "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20",
      info: item.state === "Never checked" ? "Ready (standby)" : `State: ${item.state}`,
    };
  }
  if (item.availability === "Not configured") {
    return {
      status: "Not configured",
      badgeClass: "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20",
      info: "Requires endpoint setup or feed allowlist",
    };
  }
  return {
    status: item.availability || "Standby",
    badgeClass: "bg-muted text-muted-foreground border-border",
    info: item.state || "Unchecked",
  };
}

function ApprovedSourcesTab() {
  const access = useRadarCapabilities();
  const health = useRadarReadHealth();

  const sources = [
    {
      id: "hacker_news",
      name: "Hacker News",
      type: "Official Public API",
      coverage: "Recent Ask HN and Show HN submissions with opt-in discussion excerpts.",
      limit: "Up to 20 stories per manual/scheduled check.",
      docUrl: "https://github.com/HackerNews/API",
    },
    {
      id: "reddit",
      name: "Reddit Discussions",
      type: "Structured Feed Adapter",
      coverage: "Targeted subreddits focusing on SaaS, developer tools, and technology comparisons.",
      limit: "Permitted public RSS/JSON feeds with rate compliance.",
      docUrl: "https://www.reddit.com/dev/api",
    },
    {
      id: "github",
      name: "GitHub Discussions",
      type: "Public GraphQL Reader",
      coverage: "Open repository discussion threads, issue request discussions, and tool migrations.",
      limit: "Bounded requests respecting GitHub rate ceilings.",
      docUrl: "https://docs.github.com/en/graphql",
    },
    {
      id: "stack_exchange",
      name: "Stack Exchange Network",
      type: "Public API v2.3",
      coverage: "Stack Overflow and Server Fault recommendation and tool comparison topics.",
      limit: "Platform key required for continuous polling.",
      docUrl: "https://api.stackexchange.com",
    },
    {
      id: "rss",
      name: "Custom RSS & Atom Feeds",
      type: "Direct Feed Parser",
      coverage: "Verified technical blogs, engineering publications, and industry updates.",
      limit: "Manage approved endpoints in Custom Feeds tab.",
      docUrl: "https://en.wikipedia.org/wiki/RSS",
    },
    {
      id: "discourse",
      name: "Approved Discourse Forums",
      type: "Permitted Forum Reader",
      coverage: "Open software communities and developer forum topics.",
      limit: "Configured via admin feed allowlist.",
      docUrl: "https://meta.discourse.org/t/discourse-api-documentation/22706",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="border-b pb-4">
        <h2 className="text-xl font-semibold tracking-tight">Approved Research Sources</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Public discussion channels monitored for buying intent, tool evaluations, and customer pain points.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sources.map((src) => {
          const telemetry = getSourceStatus(src.id, health.data);
          return (
            <div key={src.id} className="flex flex-col justify-between rounded-xl border bg-card p-5 space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="font-semibold text-sm">{src.name}</h3>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium border ${telemetry.badgeClass}`}>
                    {telemetry.status}
                  </span>
                </div>
                <p className="text-xs font-medium text-muted-foreground">{src.type}</p>
                <p className="text-xs text-muted-foreground leading-relaxed">{src.coverage}</p>
                <p className="text-[11px] text-muted-foreground/80 font-mono pt-1">{telemetry.info}</p>
              </div>

              <div className="border-t pt-3 flex items-center justify-between text-xs text-muted-foreground">
                <span className="truncate max-w-[170px]">{src.limit}</span>
                <a
                  href={src.docUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-primary hover:underline"
                >
                  Docs <ExternalLink size={12} />
                </a>
              </div>
            </div>
          );
        })}
      </div>

      {health.data && health.data.length > 0 && (
        <div className="rounded-xl border bg-card p-5 space-y-3">
          <h3 className="text-sm font-semibold">Live Source Health Telemetry</h3>
          <div className="divide-y text-xs">
            {health.data.map((item) => (
              <div key={item.provider} className="flex flex-wrap items-center justify-between py-2.5 gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-medium capitalize">{item.name || item.provider.replaceAll("_", " ")}</span>
                  <span className="text-muted-foreground">· state: {item.state}</span>
                  <span className="rounded bg-muted px-1.5 py-0.5 text-[11px] font-medium">{item.availability}</span>
                </div>
                <div className="flex items-center gap-4 text-muted-foreground">
                  <span>Reserved: {item.daily_requests_reserved ?? 0}</span>
                  <span>Failures: {item.consecutive_failures ?? 0}</span>
                  <span>Last success: {item.last_success ? new Date(item.last_success).toLocaleTimeString() : "None"}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function useRadarReadHealth() {
  return useQuery({
    queryKey: ["source-health-summary"],
    queryFn: () =>
      request<{ items: SourceHealthItem[] }>(
        "/intent-radar/sources/health"
      ).then((res) => res.items).catch(() => []),
    staleTime: 15000,
  });
}

function CustomFeedsTab() {
  return (
    <div className="space-y-6">
      <div className="border-b pb-4">
        <h2 className="text-xl font-semibold tracking-tight">Approved Feeds & Community Endpoints</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Configure custom RSS/Atom feeds and Discourse forum endpoints authorized for monitoring.
        </p>
      </div>
      <SourceManagement />
    </div>
  );
}
