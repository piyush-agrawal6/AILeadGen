"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertCircle,
  ArrowLeft,
  Check,
  CheckCircle2,
  ChevronRight,
  ExternalLink,
  GitCompare,
  HelpCircle,
  Plus,
  Search,
  Sparkles,
  Star,
  Target,
} from "lucide-react";
import { toast } from "sonner";
import { request } from "@/lib/intelligence";
import { Button } from "@/components/ui/button";
import type { ICPProfile } from "./ICPDashboard";

interface CompareResult {
  items: {
    id: string;
    name: string;
    status: string;
    is_primary: boolean;
    industries: string[];
    job_titles: string[];
    pain_points_count: number;
    buying_signals_count: number;
    matched_signals: number;
    high_intent_matches: number;
    completeness_score: number;
    missing_fields: string[];
  }[];
  recommended_id: string | null;
  recommendation_reason: string;
  signals_evaluated: number;
}

export function ICPComparePage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  // Fetch all ICP profiles
  const profilesQuery = useQuery<{ items: ICPProfile[] }>({
    queryKey: ["ideal-customer-profiles-all"],
    queryFn: ({ signal }) =>
      request<{ items: ICPProfile[] }>("/organization/icps?page=1&status=ACTIVE", { signal }),
  });

  const profiles = profilesQuery.data?.items || [];

  // Selected profile IDs for comparison (default up to 3)
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Initialize selected IDs once profiles load
  useEffect(() => {
    if (profiles.length > 0 && selectedIds.length === 0) {
      setSelectedIds(profiles.slice(0, 3).map((p) => p.id));
    }
  }, [profiles, selectedIds.length]);

  // Compare query against backend
  const compareQuery = useQuery<CompareResult>({
    queryKey: ["icp-comparison", selectedIds],
    queryFn: ({ signal }) =>
      request<CompareResult>("/organization/icps/compare-profiles", {
        method: "POST",
        body: JSON.stringify({ profile_ids: selectedIds }),
        signal,
      }),
    enabled: selectedIds.length >= 1,
  });

  // Set Primary Mutation
  const setPrimaryMutation = useMutation({
    mutationFn: (id: string) =>
      request(`/organization/icps/${id}/set-primary`, { method: "POST" }),
    onSuccess: () => {
      toast.success("Primary ICP updated.");
      queryClient.invalidateQueries({ queryKey: ["ideal-customer-profiles"] });
      queryClient.invalidateQueries({ queryKey: ["icp-comparison"] });
    },
    onError: (err: Error) => {
      toast.error(err.message || "Could not set primary ICP.");
    },
  });

  function toggleProfile(id: string) {
    if (selectedIds.includes(id)) {
      if (selectedIds.length <= 1) {
        toast.error("Please select at least one profile to compare.");
        return;
      }
      setSelectedIds(selectedIds.filter((x) => x !== id));
    } else {
      if (selectedIds.length >= 5) {
        toast.error("You can compare up to 5 profiles simultaneously.");
        return;
      }
      setSelectedIds([...selectedIds, id]);
    }
  }

  const comparisonData = compareQuery.data;
  const comparedItems = comparisonData?.items || [];
  const recommendedItem = comparedItems.find((i) => i.id === comparisonData?.recommended_id);

  return (
    <div className="ir-page w-full min-w-0 space-y-6 pb-20">
      {/* 1. Breadcrumbs & Header */}
      <div className="flex items-center justify-between gap-3 border-b border-border/80 pb-3">
        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Link href="/intent-radar" className="hover:text-foreground transition-colors">
            PlaneByte
          </Link>
          <ChevronRight size={12} />
          <Link href="/intent-radar/ideal-customers" className="hover:text-foreground transition-colors">
            Ideal Customers
          </Link>
          <ChevronRight size={12} />
          <span className="font-medium text-foreground">Compare ICPs</span>
        </nav>

        <Link
          href="/intent-radar/ideal-customers"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft size={13} />
          <span>Back to Profiles</span>
        </Link>
      </div>

      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
            Compare Ideal Customers
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Compare your target customer segments using profile completeness and available research evidence.
          </p>
        </div>

        <Link
          href="/intent-radar/ideal-customers/new"
          className="ir-button ir-primary inline-flex h-8 items-center gap-1.5 text-xs font-semibold"
        >
          <Plus size={14} />
          <span>Create New ICP</span>
        </Link>
      </header>

      {/* 2. Profile Selection Multi-Picker */}
      <section className="rounded-xl border border-border bg-card p-3.5 space-y-2.5 shadow-xs">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-foreground">
            Select Profiles to Compare ({selectedIds.length} of {profiles.length})
          </span>
          <span className="text-[11px] text-muted-foreground">
            Pick 2 to 5 profiles to contrast evidence and targeting depth
          </span>
        </div>

        <div className="flex flex-wrap gap-2">
          {profiles.map((p) => {
            const isSelected = selectedIds.includes(p.id);
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => toggleProfile(p.id)}
                className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
                  isSelected
                    ? "border-primary bg-primary/10 text-primary font-semibold"
                    : "border-border bg-background text-foreground hover:bg-muted/50"
                }`}
              >
                <div
                  className={`h-3.5 w-3.5 rounded border flex items-center justify-center shrink-0 ${
                    isSelected ? "bg-primary border-primary text-white" : "border-border"
                  }`}
                >
                  {isSelected && <Check size={10} />}
                </div>
                <span>{p.name}</span>
                {p.is_primary && (
                  <span className="text-[10px] text-primary/80 font-normal">(Primary)</span>
                )}
              </button>
            );
          })}
        </div>
      </section>

      {/* 3. Recommendation Engine Callout */}
      {comparisonData && (
        <section
          aria-label="Targeting Recommendation"
          className="rounded-2xl border border-primary/25 bg-linear-to-b from-primary/5 to-card p-4 sm:p-5 shadow-xs space-y-2"
        >
          <div className="flex items-center gap-2 text-primary font-semibold text-xs">
            <Sparkles size={16} />
            <span>Prioritization Recommendation</span>
          </div>

          <h2 className="text-sm font-bold text-foreground">
            {recommendedItem
              ? `Recommended to prioritize: ${recommendedItem.name}`
              : "No single profile has sufficient evidence superiority"}
          </h2>

          <p className="text-xs text-muted-foreground leading-relaxed max-w-3xl">
            {comparisonData.recommendation_reason ||
              "Evaluation based on profile targeting completeness, pain-point clarity, and observed buying-intent conversations."}
          </p>

          <div className="text-[11px] text-muted-foreground flex items-center gap-4 pt-1">
            <span>
              <strong>{comparisonData.signals_evaluated}</strong> workspace conversations evaluated
            </span>
            <span>Completeness scores represent targeting clarity, not market size</span>
          </div>
        </section>
      )}

      {/* 4. Structured Comparison Table */}
      {compareQuery.isPending ? (
        <div className="h-64 rounded-xl border border-border bg-card p-6 flex items-center justify-center text-xs text-muted-foreground">
          <span>Calculating profile completeness and evaluating evidence matches…</span>
        </div>
      ) : comparedItems.length === 0 ? (
        <div className="p-8 text-center text-xs text-muted-foreground rounded-xl border border-border bg-card">
          Select at least one profile above to see comparison dimensions.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border bg-card shadow-xs">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-border bg-muted/40 text-[11px] uppercase tracking-wide text-muted-foreground select-none">
              <tr>
                <th className="px-4 py-3 font-semibold w-56">Dimension</th>
                {comparedItems.map((item) => (
                  <th key={item.id} className="px-4 py-3 font-semibold min-w-[200px]">
                    <div className="flex items-center gap-1.5">
                      <span className="text-foreground text-xs font-bold">{item.name}</span>
                      {item.is_primary && (
                        <span className="rounded-full bg-primary/10 text-primary px-1.5 py-0.2 text-[10px] font-semibold border border-primary/30">
                          Primary
                        </span>
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>

            <tbody className="divide-y divide-border text-xs">
              {/* Status */}
              <tr className="hover:bg-muted/20">
                <td className="px-4 py-2.5 font-medium text-muted-foreground">Status</td>
                {comparedItems.map((item) => (
                  <td key={item.id} className="px-4 py-2.5 font-medium text-foreground">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium border ${
                        item.status === "ACTIVE"
                          ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/20"
                          : "bg-muted text-muted-foreground border-border"
                      }`}
                    >
                      {item.status}
                    </span>
                  </td>
                ))}
              </tr>

              {/* Profile Completeness */}
              <tr className="hover:bg-muted/20">
                <td className="px-4 py-3 font-medium text-muted-foreground">
                  Profile Completeness
                </td>
                {comparedItems.map((item) => (
                  <td key={item.id} className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-24 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${Math.min(100, Math.max(10, item.completeness_score))}%` }}
                        />
                      </div>
                      <span className="font-bold text-foreground tabular-nums">
                        {item.completeness_score}%
                      </span>
                    </div>
                    {item.missing_fields && item.missing_fields.length > 0 && (
                      <div className="text-[10px] text-muted-foreground mt-1">
                        Missing: {item.missing_fields.slice(0, 2).join(", ")}
                      </div>
                    )}
                  </td>
                ))}
              </tr>

              {/* Target Industries */}
              <tr className="hover:bg-muted/20">
                <td className="px-4 py-3 font-medium text-muted-foreground">Target Industries</td>
                {comparedItems.map((item) => (
                  <td key={item.id} className="px-4 py-3">
                    {item.industries && item.industries.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {item.industries.map((ind, i) => (
                          <span
                            key={i}
                            className="rounded bg-muted/60 px-1.5 py-0.5 text-[11px] text-foreground font-medium"
                          >
                            {ind}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-muted-foreground italic">Any industry</span>
                    )}
                  </td>
                ))}
              </tr>

              {/* Buyer Job Titles */}
              <tr className="hover:bg-muted/20">
                <td className="px-4 py-3 font-medium text-muted-foreground">Buyer Job Titles</td>
                {comparedItems.map((item) => (
                  <td key={item.id} className="px-4 py-3">
                    {item.job_titles && item.job_titles.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {item.job_titles.map((title, i) => (
                          <span
                            key={i}
                            className="rounded bg-muted/60 px-1.5 py-0.5 text-[11px] text-foreground font-medium"
                          >
                            {title}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-muted-foreground italic">Unspecified</span>
                    )}
                  </td>
                ))}
              </tr>

              {/* Defined Pain Points */}
              <tr className="hover:bg-muted/20">
                <td className="px-4 py-2.5 font-medium text-muted-foreground">Customer Problems</td>
                {comparedItems.map((item) => (
                  <td key={item.id} className="px-4 py-2.5 text-foreground font-semibold tabular-nums">
                    {item.pain_points_count} {item.pain_points_count === 1 ? "problem defined" : "problems defined"}
                  </td>
                ))}
              </tr>

              {/* Buying Signals */}
              <tr className="hover:bg-muted/20">
                <td className="px-4 py-2.5 font-medium text-muted-foreground">Buying Triggers</td>
                {comparedItems.map((item) => (
                  <td key={item.id} className="px-4 py-2.5 text-foreground font-semibold tabular-nums">
                    {item.buying_signals_count} {item.buying_signals_count === 1 ? "trigger defined" : "triggers defined"}
                  </td>
                ))}
              </tr>

              {/* Evidence Matched Conversations */}
              <tr className="hover:bg-muted/20">
                <td className="px-4 py-3 font-medium text-muted-foreground">
                  Evidence Matches
                </td>
                {comparedItems.map((item) => (
                  <td key={item.id} className="px-4 py-3">
                    <div className="text-base font-bold text-foreground tabular-nums">
                      {item.matched_signals}
                    </div>
                    <div className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium mt-0.5">
                      {item.high_intent_matches} high-intent conversations
                    </div>
                  </td>
                ))}
              </tr>

              {/* Quick Actions */}
              <tr className="hover:bg-muted/20">
                <td className="px-4 py-3 font-medium text-muted-foreground">Actions</td>
                {comparedItems.map((item) => (
                  <td key={item.id} className="px-4 py-3 space-y-1.5">
                    {!item.is_primary && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setPrimaryMutation.mutate(item.id)}
                        className="h-7 text-xs w-full gap-1"
                      >
                        <Star size={11} />
                        <span>Set Primary</span>
                      </Button>
                    )}

                    <div className="flex gap-1.5">
                      <Link
                        href={`/intent-radar/ideal-customers/${item.id}`}
                        className="inline-flex h-7 flex-1 items-center justify-center rounded-lg border border-border bg-card text-xs font-semibold text-foreground hover:border-primary/50 hover:text-primary transition-colors"
                      >
                        View Details
                      </Link>

                      <Link
                        href={`/intent-radar/discover/new?icp_id=${item.id}`}
                        className="inline-flex h-7 items-center justify-center rounded-lg border border-border bg-card px-2 text-xs font-semibold text-foreground hover:border-primary/50 hover:text-primary transition-colors"
                        title="Start Discovery with this ICP"
                      >
                        <Search size={12} />
                      </Link>
                    </div>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
