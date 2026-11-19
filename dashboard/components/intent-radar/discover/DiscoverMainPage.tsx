"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  Calendar,
  CheckCircle2,
  Clock,
  Compass,
  Copy,
  Edit3,
  ExternalLink,
  Eye,
  Filter,
  History,
  Loader2,
  MoreHorizontal,
  Play,
  Plus,
  Radio,
  RotateCcw,
  Search,
  SlidersHorizontal,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { toast } from "sonner";
import type {
  DiscoveryRun,
  IntentJob,
  IntentPage,
  SavedSearch,
  SourceId,
} from "@/lib/intent-radar";
import { Button } from "@/components/ui/button";
import { SearchInput } from "@/components/ui/search-input";
import { StatusFilterTabs } from "@/components/ui/tabs";
import { Menu, MenuContent } from "@/components/ui/menu";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "../provider";
import { ProviderLogo } from "../provider-logo";
import { EmptyState, ErrorState, LoadingSkeleton } from "../ui";
import { DiscoveryHistoryView } from "./DiscoveryHistoryView";
import { SavedSearchesView } from "./SavedSearchesView";

type MainTab = "history" | "saved";

export function DiscoverMainPage({
  initialTab = "history",
}: {
  initialTab?: MainTab;
}) {
  let router: any = null;
  try {
    router = useRouter();
  } catch {
    // ignore in test environments without next router
  }

  let urlTab: string | null = null;
  try {
    const sp = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
    urlTab = sp?.get("tab") || null;
  } catch {
    // ignore
  }
  const access = useRadarCapabilities();
  const canWrite = Boolean(access.data?.can_write);

  // Tab state: history or saved searches
  const [activeTab, setActiveTab] = useState<MainTab>(
    urlTab === "saved" || initialTab === "saved" ? "saved" : "history"
  );

  // Fetch discoveries stats
  const discoveriesQuery = useRadarRead<IntentPage<DiscoveryRun>>("/discoveries?page=1&page_size=50");
  const savedSearchesQuery = useRadarRead<IntentPage<SavedSearch>>("/saved-searches?page=1&page_size=50");

  const runs = discoveriesQuery.data?.items || [];
  const savedItems = savedSearchesQuery.data?.items || [];

  // Calculate 4 summary metrics
  const stats = useMemo(() => {
    const totalRuns = discoveriesQuery.data?.total ?? runs.length;
    const totalSignals = runs.reduce((acc, r) => acc + (r.matched_count || 0), 0);
    const totalSaved = savedSearchesQuery.data?.total ?? savedItems.length;
    const attentionRuns = runs.filter(
      (r) => r.status === "FAILED" || r.status === "PARTIAL" || r.status === "ERROR"
    ).length;

    return {
      totalRuns,
      totalSignals,
      totalSaved,
      attentionRuns,
      hasData: totalRuns > 0 || totalSaved > 0,
    };
  }, [discoveriesQuery.data, runs, savedSearchesQuery.data, savedItems]);

  const handleTabChange = (tab: MainTab) => {
    setActiveTab(tab);
    const sp = new URLSearchParams(window.location.search);
    if (tab === "saved") {
      sp.set("tab", "saved");
    } else {
      sp.delete("tab");
    }
    const qs = sp.toString();
    const nextUrl = `/intent-radar/discover${qs ? `?${qs}` : ""}`;
    window.history.replaceState({}, "", nextUrl);
  };

  return (
    <div className="ir-page w-full min-w-0 space-y-5">
      {/* 1. Page Header */}
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
        <div className="space-y-0.5">
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
            Discover Conversations
          </h1>
          <p className="text-xs text-muted-foreground">
            Search public conversations, review discoveries, and save research for later.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/help?article=intent-radar-overview"
            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-medium text-foreground hover:border-primary/40 transition-colors"
          >
            <BookOpen size={13} className="text-muted-foreground" />
            <span>Guide</span>
          </Link>

          {canWrite ? (
            <Link
              href="/intent-radar/discover/new"
              className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground shadow-xs hover:bg-primary/90 transition-colors"
            >
              <Plus size={14} />
              <span>Create Discovery</span>
            </Link>
          ) : (
            <span className="text-xs text-muted-foreground border border-border rounded-lg px-2.5 py-1">
              Read-only access
            </span>
          )}
        </div>
      </header>

      {/* 2. Summary Overview Cards (4 Real Metrics) */}
      <section aria-label="Discover overview metrics" className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div
          onClick={() => handleTabChange("history")}
          className="rounded-xl border border-border bg-card p-3.5 space-y-1 cursor-pointer hover:border-primary/40 transition-colors"
        >
          <span className="text-[11px] font-medium text-muted-foreground block">
            Total Discovery Runs
          </span>
          <div className="flex items-baseline gap-1.5">
            <span className="text-xl font-bold text-foreground tabular-nums">
              {stats.totalRuns}
            </span>
            <span className="text-[11px] text-muted-foreground">executed</span>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-3.5 space-y-1">
          <span className="text-[11px] font-medium text-muted-foreground block">
            Conversations Found
          </span>
          <div className="flex items-baseline gap-1.5">
            <span className="text-xl font-bold text-foreground tabular-nums">
              {stats.totalSignals}
            </span>
            <span className="text-[11px] text-muted-foreground">total signals</span>
          </div>
        </div>

        <div
          onClick={() => handleTabChange("saved")}
          className="rounded-xl border border-border bg-card p-3.5 space-y-1 cursor-pointer hover:border-primary/40 transition-colors"
        >
          <span className="text-[11px] font-medium text-muted-foreground block">
            Saved Searches
          </span>
          <div className="flex items-baseline gap-1.5">
            <span className="text-xl font-bold text-foreground tabular-nums">
              {stats.totalSaved}
            </span>
            <span className="text-[11px] text-muted-foreground">configurations</span>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-3.5 space-y-1">
          <span className="text-[11px] font-medium text-muted-foreground block">
            Runs Requiring Attention
          </span>
          <div className="flex items-baseline gap-1.5">
            <span
              className={`text-xl font-bold tabular-nums ${
                stats.attentionRuns > 0 ? "text-amber-600 dark:text-amber-400" : "text-foreground"
              }`}
            >
              {stats.attentionRuns}
            </span>
            <span className="text-[11px] text-muted-foreground">partial / failed</span>
          </div>
        </div>
      </section>

      {/* 3. Navigation Tabs: Only TWO tabs (Discovery History | Saved Searches) */}
      <div className="border-b border-border">
        <div className="flex items-center gap-1" role="tablist" aria-label="Discover workspace views">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "history"}
            onClick={() => handleTabChange("history")}
            className={`inline-flex items-center gap-2 border-b-2 px-3.5 py-2.5 text-xs font-medium transition-colors cursor-pointer ${
              activeTab === "history"
                ? "border-primary text-primary font-semibold"
                : "border-transparent text-muted-foreground hover:border-border hover:text-foreground"
            }`}
          >
            <History size={14} />
            <span>Discovery History</span>
            <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground">
              {stats.totalRuns}
            </span>
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "saved"}
            onClick={() => handleTabChange("saved")}
            className={`inline-flex items-center gap-2 border-b-2 px-3.5 py-2.5 text-xs font-medium transition-colors cursor-pointer ${
              activeTab === "saved"
                ? "border-primary text-primary font-semibold"
                : "border-transparent text-muted-foreground hover:border-border hover:text-foreground"
            }`}
          >
            <BookmarkIcon size={14} />
            <span>Saved Searches</span>
            <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground">
              {stats.totalSaved}
            </span>
          </button>
        </div>
      </div>

      {/* 4. Active Tab Content */}
      <div className="pt-1">
        {activeTab === "history" ? (
          <DiscoveryHistoryView embeddedInMain />
        ) : (
          <SavedSearchesView embeddedInMain />
        )}
      </div>
    </div>
  );
}

function BookmarkIcon({ size = 14, className }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z" />
    </svg>
  );
}
