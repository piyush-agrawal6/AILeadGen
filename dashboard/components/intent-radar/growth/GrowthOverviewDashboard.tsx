"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  MessageSquare,
  Sparkles,
  Users,
  Target,
  ArrowUpRight,
  TrendingUp,
  RefreshCw,
  Search,
  ExternalLink,
  Plus,
  Compass,
  Radar,
  FileText,
  Building2,
  Calendar,
  Layers,
} from "lucide-react";
import { useRadarRead, useRadarCapabilities } from "../provider";
import { LoadingSkeleton, ErrorState, Badge } from "../ui";
import {
  emptyGrowthScope,
  growthQuery,
  type GrowthOverview,
  type GrowthScope,
  type GrowthSignal,
} from "@/lib/growth";
import { ProviderLogo } from "../provider-logo";
import { SearchInput } from "@/components/ui/search-input";

interface GrowthOverviewDashboardProps {
  onNavigateTab: (tabId: string) => void;
}

export function GrowthOverviewDashboard({ onNavigateTab }: GrowthOverviewDashboardProps) {
  const [scope, setScope] = useState<GrowthScope>(emptyGrowthScope);
  const [selectedDay, setSelectedDay] = useState<string | null>(null);

  const query = useRadarRead<GrowthOverview>("/growth/overview?" + growthQuery(scope));
  const capabilities = useRadarCapabilities();

  const data = query.data;

  return (
    <div className="w-full min-w-0 space-y-6">
      {/* Header with Title and Filter Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-foreground">Market & Demand Intelligence</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Evidence-backed market signals, problem trends, and customer conversations collected across active sources.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void query.refetch()}
            disabled={query.isFetching}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 text-xs font-medium text-foreground hover:bg-muted transition-colors cursor-pointer"
            title="Refresh overview data"
          >
            <RefreshCw size={13} className={query.isFetching ? "animate-spin text-primary" : ""} />
            <span>Refresh</span>
          </button>

          <button
            type="button"
            onClick={() => onNavigateTab("research")}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-colors shadow-xs cursor-pointer"
          >
            <Sparkles size={13} />
            <span>AI Research</span>
          </button>
        </div>
      </div>

      {/* Scope Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 rounded-xl border border-border bg-card p-2.5">
        <div className="flex flex-wrap items-center gap-2 flex-1 min-w-[260px]">
          <SearchInput
            value={scope.search}
            onChange={(e) => setScope((prev) => ({ ...prev, search: e.target.value }))}
            onClear={() => setScope((prev) => ({ ...prev, search: "" }))}
            placeholder="Filter evidence by keyword or problem…"
            wrapperClassName="flex-1 min-w-[200px]"
          />

          {/* Time Window */}
          <select
            value={scope.days}
            onChange={(e) =>
              setScope((prev) => ({
                ...prev,
                days: Number(e.target.value) as GrowthScope["days"],
              }))
            }
            className="h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground focus:border-primary focus:outline-none"
          >
            <option value={0}>All available evidence</option>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>

          {/* Source Filter */}
          <select
            value={scope.sources[0] || ""}
            onChange={(e) =>
              setScope((prev) => ({
                ...prev,
                sources: e.target.value ? [e.target.value] : [],
              }))
            }
            className="h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground focus:border-primary focus:outline-none"
          >
            <option value="">All Sources</option>
            {(capabilities.data?.sources || []).map((s) => (
              <option key={s.id || s.name} value={s.id || s.name}>
                {s.name}
              </option>
            ))}
          </select>

          {/* ICP Context */}
          {data?.filter_options?.icps && data.filter_options.icps.length > 0 && (
            <select
              value={scope.icp_id || ""}
              onChange={(e) =>
                setScope((prev) => ({
                  ...prev,
                  icp_id: e.target.value || null,
                }))
              }
              className="h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground focus:border-primary focus:outline-none max-w-[160px] truncate"
            >
              <option value="">All ICPs</option>
              {data.filter_options.icps.map((icp) => (
                <option key={icp.id} value={icp.id}>
                  {icp.name}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      {query.error ? (
        <ErrorState message={query.error.message} retry={() => void query.refetch()} />
      ) : !data ? (
        <LoadingSkeleton />
      ) : (
        <div className="space-y-6">
          {/* 1. 4 Primary Metric KPIs */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
            <div className="rounded-xl border border-border bg-card p-4 space-y-1 shadow-xs hover:border-primary/30 transition-colors">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-xs font-medium">Conversations Analyzed</span>
                <MessageSquare size={16} className="text-primary" />
              </div>
              <div className="text-2xl font-bold tracking-tight text-foreground">{data.sample_size}</div>
              <p className="text-[11px] text-muted-foreground flex items-center gap-1">
                <span className="text-foreground font-semibold">{data.daily.reduce((acc, d) => acc + d.conversations, 0)}</span> in publication sample
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card p-4 space-y-1 shadow-xs hover:border-primary/30 transition-colors">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-xs font-medium">Active Recurring Themes</span>
                <TrendingUp size={16} className="text-primary" />
              </div>
              <div className="text-2xl font-bold tracking-tight text-foreground">
                {data.theme_count ?? data.themes.length}
              </div>
              <button
                type="button"
                onClick={() => onNavigateTab("themes")}
                className="text-[11px] text-primary hover:underline font-medium inline-flex items-center gap-0.5"
              >
                Explore themes & trends <ArrowUpRight size={11} />
              </button>
            </div>

            <div className="rounded-xl border border-border bg-card p-4 space-y-1 shadow-xs hover:border-primary/30 transition-colors">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-xs font-medium">Monitored Topics</span>
                <Radar size={16} className="text-primary" />
              </div>
              <div className="text-2xl font-bold tracking-tight text-foreground">{data.monitored_topics}</div>
              <Link
                href="/intent-radar/monitors"
                className="text-[11px] text-primary hover:underline font-medium inline-flex items-center gap-0.5"
              >
                Manage active monitors <ArrowUpRight size={11} />
              </Link>
            </div>

            <div className="rounded-xl border border-border bg-card p-4 space-y-1 shadow-xs hover:border-primary/30 transition-colors">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="text-xs font-medium">Emerging Opportunities</span>
                <Target size={16} className="text-emerald-500" />
              </div>
              <div className="text-2xl font-bold tracking-tight text-foreground">{data.opportunity_candidates}</div>
              <Link
                href="/intent-radar/opportunities"
                className="text-[11px] text-primary hover:underline font-medium inline-flex items-center gap-0.5"
              >
                Review candidate signals <ArrowUpRight size={11} />
              </Link>
            </div>
          </div>

          {/* 2. Key Intelligence Findings & Evidence Summary */}
          <div className="rounded-xl border border-border bg-card p-5 space-y-4 shadow-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-primary" />
                <h3 className="text-sm font-semibold text-foreground">Key Market Insights</h3>
              </div>
              <span className="text-[11px] text-muted-foreground">
                {data.comparison.state} · Updated {data.as_of ? new Date(data.as_of).toLocaleDateString() : "recently"}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 pt-1">
              <div className="rounded-lg border border-border/70 bg-muted/20 p-3.5 space-y-1.5">
                <span className="text-[11px] font-semibold text-primary uppercase tracking-wider">Demand Trends</span>
                <p className="text-xs text-foreground leading-relaxed">
                  {data.comparison.percentage_change !== null
                    ? `${Math.abs(data.comparison.percentage_change)}% ${
                        data.comparison.percentage_change >= 0 ? "increase" : "decrease"
                      } in collected discussion mentions compared to the previous period.`
                    : "Sufficient comparative timeline established; monitoring recurring conversation volume."}
                </p>
                <div className="text-[11px] text-muted-foreground pt-1">
                  {data.comparison.current} current mentions vs {data.comparison.previous} previous
                </div>
              </div>

              <div className="rounded-lg border border-border/70 bg-muted/20 p-3.5 space-y-1.5">
                <span className="text-[11px] font-semibold text-primary uppercase tracking-wider">Top Intent Channels</span>
                <p className="text-xs text-foreground leading-relaxed">
                  Discussions predominantly observed across{" "}
                  <span className="font-medium text-foreground">
                    {Object.keys(data.sources).slice(0, 3).join(", ") || "configured sources"}
                  </span>
                  .
                </p>
                <div className="flex flex-wrap gap-1 pt-1">
                  {Object.entries(data.sources).map(([src, count]) => (
                    <span
                      key={src}
                      className="inline-flex items-center gap-1 rounded bg-background px-2 py-0.5 text-[10px] text-muted-foreground border border-border"
                    >
                      <ProviderLogo provider={src} size={14} />
                      <span>{src}: {count}</span>
                    </span>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-border/70 bg-muted/20 p-3.5 space-y-1.5">
                <span className="text-[11px] font-semibold text-primary uppercase tracking-wider">Active Problem Categories</span>
                <p className="text-xs text-foreground leading-relaxed">
                  Highest customer activity centered around{" "}
                  <span className="font-medium text-foreground">
                    {Object.keys(data.categories).slice(0, 2).join(" and ") || "commercial topics"}
                  </span>
                  .
                </p>
                <div className="flex flex-wrap gap-1 pt-1">
                  {Object.entries(data.categories).map(([cat, count]) => (
                    <span
                      key={cat}
                      className="rounded bg-background px-2 py-0.5 text-[10px] text-muted-foreground border border-border"
                    >
                      {cat}: {count}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* 3. Conversation Activity Over Time Chart */}
          <div className="rounded-xl border border-border bg-card p-5 space-y-3 shadow-xs">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-foreground">Conversation Activity Timeline</h3>
                <p className="text-xs text-muted-foreground">
                  Published customer discussions by date. Click any bar to inspect specific volume.
                </p>
              </div>
              {selectedDay && (
                <button
                  type="button"
                  onClick={() => setSelectedDay(null)}
                  className="text-[11px] text-primary hover:underline font-medium"
                >
                  Clear date selection
                </button>
              )}
            </div>

            {data.daily.length === 0 ? (
              <div className="py-12 text-center text-xs text-muted-foreground">
                No conversation history recorded in this time window. Activity populates as discovery and monitors run.
              </div>
            ) : (
              <div className="space-y-2 pt-2">
                <div
                  className="flex items-end gap-1.5 h-36 border-b border-border pb-1 overflow-x-auto pt-4"
                  role="group"
                  aria-label="Collected conversations by publication day"
                >
                  {(() => {
                    const maxCount = Math.max(...data.daily.map((d) => d.conversations), 1);
                    return data.daily.map((item) => {
                      const heightPercent = Math.max(10, Math.round((item.conversations / maxCount) * 100));
                      const isSelected = selectedDay === item.day;
                      return (
                        <button
                          key={item.day}
                          type="button"
                          onClick={() => setSelectedDay(isSelected ? null : item.day)}
                          aria-label={`${item.day}: ${item.conversations} discussions`}
                          aria-pressed={isSelected}
                          className="group flex-1 min-w-[28px] max-w-[48px] flex flex-col items-center gap-1.5 focus:outline-none cursor-pointer"
                        >
                          <div className="w-full flex items-end justify-center h-28">
                            <div
                              style={{ height: `${heightPercent}%` }}
                              className={`w-full rounded-t-sm transition-all duration-200 ${
                                isSelected
                                  ? "bg-primary shadow-xs"
                                  : "bg-primary/40 group-hover:bg-primary/70"
                              }`}
                            />
                          </div>
                          <span
                            className={`text-[10px] truncate ${
                              isSelected ? "text-primary font-bold" : "text-muted-foreground"
                            }`}
                          >
                            {item.day.slice(5)}
                          </span>
                        </button>
                      );
                    });
                  })()}
                </div>

                <div className="text-[11px] text-muted-foreground text-center">
                  {selectedDay ? (
                    <span className="text-foreground font-semibold">
                      {selectedDay}: {data.daily.find((d) => d.day === selectedDay)?.conversations || 0} collected conversations
                    </span>
                  ) : (
                    "Select a day above to inspect daily activity."
                  )}
                </div>
              </div>
            )}
          </div>

          {/* 4. Active Recurring Themes Snapshot & Recent Evidence */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
            {/* Left: Active Recurring Themes */}
            <div className="rounded-xl border border-border bg-card p-5 space-y-4 shadow-xs">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-foreground">Recurring Themes</h3>
                  <p className="text-xs text-muted-foreground">Market patterns identified from repeated buyer discussions.</p>
                </div>
                <button
                  type="button"
                  onClick={() => onNavigateTab("themes")}
                  className="text-xs text-primary hover:underline font-medium inline-flex items-center gap-0.5"
                >
                  View all ({data.theme_count ?? data.themes.length}) <ArrowUpRight size={12} />
                </button>
              </div>

              {data.themes.length === 0 ? (
                <div className="py-8 text-center text-xs text-muted-foreground border border-dashed border-border rounded-lg">
                  No recurring themes detected yet. Generate themes from the Trends & Themes tab.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {data.themes.slice(0, 5).map((theme) => (
                    <Link
                      key={theme.id}
                      href={`/intent-radar/growth/themes/${theme.id}`}
                      className="block rounded-lg border border-border/80 bg-background p-3 hover:border-primary/40 hover:bg-muted/10 transition-colors"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-semibold text-foreground truncate">{theme.name}</span>
                        <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                          {theme.method}
                        </span>
                      </div>
                      <p className="text-[11px] text-muted-foreground line-clamp-2 mt-1">{theme.description}</p>
                    </Link>
                  ))}
                </div>
              )}
            </div>

            {/* Right: Recent Source Evidence with Citations */}
            <div className="rounded-xl border border-border bg-card p-5 space-y-4 shadow-xs">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-foreground">Verifiable Source Evidence</h3>
                  <p className="text-xs text-muted-foreground">Recent discussions supporting these market insights.</p>
                </div>
                <Link
                  href="/intent-radar/signals"
                  className="text-xs text-primary hover:underline font-medium inline-flex items-center gap-0.5"
                >
                  Inspect Signals <ArrowUpRight size={12} />
                </Link>
              </div>

              {data.signals.length === 0 ? (
                <div className="py-8 text-center text-xs text-muted-foreground border border-dashed border-border rounded-lg">
                  No recent signals matching filters. Run Discovery or check Monitoring to collect new signals.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {data.signals.slice(0, 5).map((sig) => (
                    <div
                      key={sig.id}
                      className="rounded-lg border border-border/80 bg-background p-3 space-y-1.5 hover:border-primary/40 transition-colors"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-1.5 min-w-0">
                          <ProviderLogo provider={sig.source} size={14} />
                          <span className="text-xs font-medium text-foreground truncate">{sig.title}</span>
                        </div>
                        <span className="text-[10px] font-semibold text-emerald-600 bg-emerald-500/10 px-1.5 py-0.5 rounded shrink-0">
                          {sig.score}% match
                        </span>
                      </div>

                      {sig.excerpt && (
                        <p className="text-[11px] text-muted-foreground italic line-clamp-2 border-l-2 border-primary/30 pl-2">
                          &ldquo;{sig.excerpt}&rdquo;
                        </p>
                      )}

                      <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-0.5">
                        <span>{new Date(sig.observed_at).toLocaleDateString()}</span>
                        {sig.source_url && (
                          <a
                            href={sig.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline inline-flex items-center gap-1"
                          >
                            <span>Original Discussion</span>
                            <ExternalLink size={10} />
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* 5. Recommended Next Actions */}
          <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-0.5">
              <h4 className="text-xs font-bold text-foreground flex items-center gap-1.5">
                <Compass size={14} className="text-primary" />
                <span>Next Growth Actions</span>
              </h4>
              <p className="text-[11px] text-muted-foreground">
                Turn market signals into automated pipeline: set up monitors for recurring problem themes or conduct deep-dive research.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Link
                href="/intent-radar/monitors/new"
                className="inline-flex h-8 items-center gap-1 rounded-lg border border-border bg-card px-2.5 text-xs font-medium text-foreground hover:bg-muted transition-colors"
              >
                <Plus size={12} />
                <span>Create Monitor</span>
              </Link>
              <button
                type="button"
                onClick={() => onNavigateTab("research")}
                className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-colors shadow-xs cursor-pointer"
              >
                <Sparkles size={12} />
                <span>Generate Intelligence Report</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
