"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  TrendingUp,
  Search,
  Sparkles,
  ExternalLink,
  Plus,
  Bookmark,
  BookmarkCheck,
  ArrowUpRight,
  ChevronRight,
  ArrowLeft,
  Calendar,
  Layers,
  Radio,
  FileText,
  SlidersHorizontal,
} from "lucide-react";
import { useRadarRead, useRadarMutation, useRadarCapabilities } from "../provider";
import { LoadingSkeleton, ErrorState, EmptyState, Badge } from "../ui";
import { ProviderLogo } from "../provider-logo";
import { SearchInput } from "@/components/ui/search-input";
import type { GrowthPage, GrowthTheme, GrowthCitation } from "@/lib/growth";

interface GrowthThemesPageProps {
  themeId?: string;
  onNavigateTab?: (tabId: string) => void;
}

export function GrowthThemesPage({ themeId, onNavigateTab }: GrowthThemesPageProps) {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [savedOnly, setSavedOnly] = useState(false);
  const [sortBy, setSortBy] = useState<"mentions" | "recent" | "name">("mentions");

  const query = useRadarRead<GrowthPage<GrowthTheme>>(
    `/growth/themes?page=${page}&saved=${savedOnly}&search=${encodeURIComponent(search)}`
  );
  const mutation = useRadarMutation();
  const capabilities = useRadarCapabilities();

  // If a themeId is provided, render the Theme Detail View
  if (themeId) {
    return <ThemeDetailView themeId={themeId} onBack={() => router.push("/intent-radar/growth/themes")} />;
  }

  const items = query.data?.items || [];
  const total = query.data?.total || 0;

  // Client-side sort if needed
  const sortedItems = [...items].sort((a, b) => {
    if (sortBy === "name") return a.name.localeCompare(b.name);
    if (sortBy === "recent") return (b.saved_at || "").localeCompare(a.saved_at || "");
    const aCount = a.citations?.length || 0;
    const bCount = b.citations?.length || 0;
    return bCount - aCount;
  });

  return (
    <div className="w-full min-w-0 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-foreground">Market Themes & Trends</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Repeated customer problems, buyer objections, and emerging product demand synthesized from public conversations.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {onNavigateTab && (
            <button
              type="button"
              onClick={() => onNavigateTab("research")}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-colors shadow-xs cursor-pointer"
            >
              <Sparkles size={13} />
              <span>Discover New Themes</span>
            </button>
          )}
        </div>
      </div>

      {/* Filter & Search Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 rounded-xl border border-border bg-card p-2.5">
        <div className="flex flex-wrap items-center gap-2 flex-1 min-w-[260px]">
          <SearchInput
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            onClear={() => {
              setSearch("");
              setPage(1);
            }}
            placeholder="Search market themes, problems, keywords…"
            wrapperClassName="flex-1 min-w-[220px]"
          />

          {/* Saved Filter Toggle */}
          <button
            type="button"
            onClick={() => {
              setSavedOnly(!savedOnly);
              setPage(1);
            }}
            className={`inline-flex h-8 items-center gap-1.5 rounded-lg border px-2.5 text-xs font-medium transition-colors cursor-pointer ${
              savedOnly
                ? "border-primary/50 bg-primary/10 text-primary font-semibold"
                : "border-border bg-background text-foreground hover:bg-muted"
            }`}
          >
            {savedOnly ? <BookmarkCheck size={13} /> : <Bookmark size={13} />}
            <span>Saved Themes</span>
          </button>

          {/* Sort Dropdown */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground focus:border-primary focus:outline-none"
          >
            <option value="mentions">Sort by Evidence Volume</option>
            <option value="recent">Sort by Most Recent</option>
            <option value="name">Sort by Name</option>
          </select>
        </div>
      </div>

      {/* 7-Column Themes Table */}
      {query.error ? (
        <ErrorState message={query.error.message} retry={() => void query.refetch()} />
      ) : query.isLoading ? (
        <LoadingSkeleton />
      ) : sortedItems.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border bg-card/50 p-12 text-center space-y-3">
          <TrendingUp className="mx-auto h-8 w-8 text-muted-foreground/60" />
          <h3 className="text-sm font-semibold text-foreground">No market themes match your filters</h3>
          <p className="text-xs text-muted-foreground max-w-md mx-auto">
            {search || savedOnly
              ? "Try clearing your filters or search keywords to see all recorded market themes."
              : "Discover recurring demand patterns and problem themes across collected customer conversations."}
          </p>
          {onNavigateTab && (
            <button
              type="button"
              onClick={() => onNavigateTab("research")}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors shadow-xs"
            >
              <Sparkles size={12} />
              <span>Generate Themes from Evidence</span>
            </button>
          )}
        </div>
      ) : (
        <div className="rounded-xl border border-border bg-card overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                  <th className="py-3 px-4 min-w-[280px]">Theme & Description</th>
                  <th className="py-3 px-3 text-center min-w-[90px]">Evidence</th>
                  <th className="py-3 px-3 min-w-[120px]">Method</th>
                  <th className="py-3 px-3 min-w-[110px]">Comparison</th>
                  <th className="py-3 px-3 min-w-[90px]">Status</th>
                  <th className="py-3 px-3 text-right sticky right-0 bg-muted/95 backdrop-blur-xs min-w-[170px]">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {sortedItems.map((theme) => {
                  const citationCount = theme.citations?.length || 0;
                  const isSaved = Boolean(theme.saved_at);
                  const comparison = theme.comparison;

                  return (
                    <tr
                      key={theme.id}
                      className="group hover:bg-muted/30 transition-colors"
                    >
                      {/* 1. Theme Name & Description */}
                      <td className="py-3 px-4">
                        <Link
                          href={`/intent-radar/growth/themes/${theme.id}`}
                          className="font-semibold text-foreground group-hover:text-primary transition-colors block text-xs"
                        >
                          {theme.name}
                        </Link>
                        <p className="text-[11px] text-muted-foreground line-clamp-1 mt-0.5">
                          {theme.description}
                        </p>
                      </td>

                      {/* 2. Evidence Count */}
                      <td className="py-3 px-3 text-center">
                        <span className="inline-flex items-center justify-center rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-bold text-primary">
                          {citationCount} citations
                        </span>
                      </td>

                      {/* 3. Method */}
                      <td className="py-3 px-3 text-[11px] text-muted-foreground">
                        <span className="rounded bg-muted px-1.5 py-0.5 font-medium text-foreground">
                          {theme.method}
                        </span>
                      </td>

                      {/* 4. Comparison */}
                      <td className="py-3 px-3 text-[11px]">
                        {comparison ? (
                          <div className="space-y-0.5">
                            <span className="text-foreground font-medium">{comparison.state}</span>
                            <div className="text-[10px] text-muted-foreground">
                              {comparison.current} cur · {comparison.previous} prev
                            </div>
                          </div>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>

                      {/* 5. Status / Saved */}
                      <td className="py-3 px-3 text-[11px]">
                        {isSaved ? (
                          <span className="inline-flex items-center gap-1 text-emerald-600 font-medium">
                            <BookmarkCheck size={12} />
                            <span>Saved</span>
                          </span>
                        ) : (
                          <span className="text-muted-foreground">Unsaved</span>
                        )}
                      </td>

                      {/* 6. Actions */}
                      <td className="py-3 px-3 text-right sticky right-0 bg-card group-hover:bg-muted/30 transition-colors">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            type="button"
                            onClick={() =>
                              mutation.mutate({
                                path: `/growth/themes/${theme.id}`,
                                method: "PATCH",
                                body: {
                                  revision: theme.revision,
                                  saved: !isSaved,
                                },
                              })
                            }
                            className={`p-1.5 rounded-lg border text-muted-foreground hover:text-foreground transition-colors cursor-pointer ${
                              isSaved
                                ? "border-primary/40 text-primary bg-primary/5"
                                : "border-border hover:bg-muted"
                            }`}
                            title={isSaved ? "Unsave theme" : "Save theme"}
                          >
                            <Bookmark size={12} className={isSaved ? "fill-primary" : ""} />
                          </button>

                          <Link
                            href={`/intent-radar/monitors/new?prompt=${encodeURIComponent(
                              `Monitor customer discussions about ${theme.name}: ${theme.description}`
                            )}`}
                            className="inline-flex h-7 items-center gap-1 rounded-md border border-border bg-background px-2 text-[11px] font-medium text-foreground hover:border-primary/40 hover:text-primary transition-colors"
                            title="Create Monitor from Theme"
                          >
                            <Plus size={11} />
                            <span>Monitor</span>
                          </Link>

                          <Link
                            href={`/intent-radar/growth/themes/${theme.id}`}
                            className="inline-flex h-7 items-center gap-1 rounded-md bg-muted px-2 text-[11px] font-medium text-foreground hover:bg-muted/80 transition-colors"
                          >
                            <span>Details</span>
                            <ChevronRight size={11} />
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {total > 25 && (
            <div className="flex items-center justify-between border-t border-border px-4 py-3 text-xs text-muted-foreground">
              <span>Showing {sortedItems.length} of {total} themes</span>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="rounded border border-border px-2 py-1 disabled:opacity-40"
                >
                  Previous
                </button>
                <span className="px-2 font-medium text-foreground">{page}</span>
                <button
                  type="button"
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page * 25 >= total}
                  className="rounded border border-border px-2 py-1 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Subcomponent: Full-page Theme Detail View with direct citations
function ThemeDetailView({ themeId, onBack }: { themeId: string; onBack: () => void }) {
  const query = useRadarRead<GrowthTheme>(`/growth/themes/${themeId}`);
  const mutation = useRadarMutation();
  const theme = query.data;

  if (query.error) {
    return <ErrorState message={query.error.message} retry={() => void query.refetch()} />;
  }
  if (!theme) {
    return <LoadingSkeleton />;
  }

  const isSaved = Boolean(theme.saved_at);
  const citations = theme.citations || [];

  return (
    <div className="w-full min-w-0 space-y-6 pb-20">
      {/* Back button & Breadcrumb */}
      <div className="flex items-center justify-between gap-3 border-b border-border pb-3">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
        >
          <ArrowLeft size={13} />
          <span>Back to Themes</span>
        </button>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() =>
              mutation.mutate({
                path: `/growth/themes/${theme.id}`,
                method: "PATCH",
                body: {
                  revision: theme.revision,
                  saved: !isSaved,
                },
              })
            }
            className={`inline-flex h-8 items-center gap-1.5 rounded-lg border px-3 text-xs font-medium transition-colors cursor-pointer ${
              isSaved
                ? "border-primary/40 text-primary bg-primary/5"
                : "border-border hover:bg-muted text-foreground"
            }`}
          >
            <Bookmark size={13} className={isSaved ? "fill-primary" : ""} />
            <span>{isSaved ? "Saved" : "Save Theme"}</span>
          </button>

          <Link
            href={`/intent-radar/monitors/new?prompt=${encodeURIComponent(
              `Monitor customer discussions about ${theme.name}: ${theme.description}`
            )}`}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-colors shadow-xs"
          >
            <Plus size={13} />
            <span>Create Monitor from Theme</span>
          </Link>
        </div>
      </div>

      {/* Theme Overview Card */}
      <div className="rounded-2xl border border-border bg-card p-6 space-y-4 shadow-xs">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-bold text-primary">
            {theme.method}
          </span>
          {theme.comparison && (
            <span className="rounded bg-muted px-2 py-0.5 text-xs font-medium text-foreground">
              {theme.comparison.state}
            </span>
          )}
        </div>

        <div className="space-y-1.5">
          <h1 className="text-xl font-bold tracking-tight text-foreground">{theme.name}</h1>
          <p className="text-xs text-muted-foreground leading-relaxed max-w-3xl">{theme.description}</p>
        </div>

        {theme.comparison && (
          <div className="rounded-lg border border-border/70 bg-muted/20 p-3 text-xs space-y-1">
            <div className="font-semibold text-foreground">Timeline Comparison</div>
            <p className="text-muted-foreground">
              {theme.comparison.current} current sample mentions vs {theme.comparison.previous} previous sample mentions.
            </p>
            {theme.comparison.limitation && (
              <p className="text-[11px] text-muted-foreground/80 italic">{theme.comparison.limitation}</p>
            )}
          </div>
        )}
      </div>

      {/* Verifiable Evidence Citations */}
      <div className="rounded-2xl border border-border bg-card p-6 space-y-4 shadow-xs">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Verifiable Customer Evidence</h3>
            <p className="text-xs text-muted-foreground">
              Direct excerpts and citations from public customer discussions underpinning this theme.
            </p>
          </div>
          <span className="text-xs font-semibold text-primary">
            {citations.length} verified citations
          </span>
        </div>

        {citations.length === 0 ? (
          <div className="py-8 text-center text-xs text-muted-foreground border border-dashed border-border rounded-lg">
            No direct citations recorded for this theme.
          </div>
        ) : (
          <div className="space-y-3">
            {citations.map((c, idx) => (
              <div
                key={c.signal_id || idx}
                className="rounded-xl border border-border/80 bg-background p-4 space-y-2 hover:border-primary/40 transition-colors"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                    Citation #{idx + 1}
                  </span>
                  {c.signal?.source && (
                    <div className="flex items-center gap-1.5">
                      <ProviderLogo provider={c.signal.source} size={14} />
                      <span className="text-[11px] text-foreground font-medium capitalize">
                        {c.signal.source}
                      </span>
                    </div>
                  )}
                </div>

                <blockquote className="border-l-2 border-primary/50 pl-3 text-xs text-foreground italic leading-relaxed">
                  &ldquo;{c.quote}&rdquo;
                </blockquote>

                {c.signal?.source_url && (
                  <div className="pt-1 flex items-center justify-end">
                    <a
                      href={c.signal.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[11px] text-primary hover:underline inline-flex items-center gap-1 font-medium"
                    >
                      <span>View original source discussion</span>
                      <ExternalLink size={10} />
                    </a>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
