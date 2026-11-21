"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Check,
  CheckCircle2,
  ChevronRight,
  Clock,
  Copy,
  Edit3,
  ExternalLink,
  GitCompare,
  History,
  MoreHorizontal,
  Plus,
  Radio,
  Search,
  Sparkles,
  Star,
  Target,
  Trash2,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import { request } from "@/lib/intelligence";
import { Button } from "@/components/ui/button";
import { PrimaryTabs } from "@/components/ui/tabs";
import type { ICPProfile } from "./ICPDashboard";

type RelatedData = {
  icp_id: string;
  discoveries: { id: string; title: string; status: string; created_at: string }[];
  monitors: { id: string; name: string; status: string; last_checked: string | null }[];
  signals: {
    id: string;
    title: string;
    source: string;
    score: number;
    category: string;
    observed_at: string;
    matched_terms: string[];
  }[];
};

type VersionData = {
  items: {
    revision: number;
    name: string;
    description: string;
    updated_at: string;
    updated_by_email?: string;
  }[];
  total: number;
};

export function ICPDetailPage({ id }: { id: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("overview");

  // Fetch ICP Profile
  const profileQuery = useQuery<ICPProfile>({
    queryKey: ["ideal-customer-profile", id],
    queryFn: ({ signal }) =>
      request<ICPProfile>(`/organization/icps/${id}`, { signal }),
  });

  // Fetch Related Discoveries, Monitors, Signals
  const relatedQuery = useQuery<RelatedData>({
    queryKey: ["ideal-customer-profile-related", id],
    queryFn: ({ signal }) =>
      request<RelatedData>(`/organization/icps/${id}/related`, { signal }),
    enabled: Boolean(id),
  });

  // Fetch Version History
  const versionsQuery = useQuery<VersionData>({
    queryKey: ["ideal-customer-profile-versions", id],
    queryFn: ({ signal }) =>
      request<VersionData>(`/organization/icps/${id}/versions`, { signal }),
    enabled: activeTab === "activity",
  });

  // Set Primary Mutation
  const setPrimaryMutation = useMutation({
    mutationFn: () =>
      request(`/organization/icps/${id}/set-primary`, { method: "POST" }),
    onSuccess: () => {
      toast.success("Set as primary ICP.");
      queryClient.invalidateQueries({ queryKey: ["ideal-customer-profile", id] });
      queryClient.invalidateQueries({ queryKey: ["ideal-customer-profiles"] });
    },
    onError: (err: Error) => {
      toast.error(err.message || "Failed to set as primary.");
    },
  });

  // Duplicate Mutation
  const duplicateMutation = useMutation({
    mutationFn: () =>
      request<{id:string}>(`/organization/icps/${id}/duplicate`, {
        method: "POST",
        body: JSON.stringify({
          name: `${profileQuery.data?.name || "Profile"} (Copy)`,
          request_id: crypto.randomUUID(),
        }),
      }),
    onSuccess: (newP) => {
      toast.success("Profile duplicated.");
      if (newP?.id) {
        router.push(`/intent-radar/ideal-customers/${newP.id}`);
      }
    },
    onError: (err: Error) => {
      toast.error(err.message || "Could not duplicate profile.");
    },
  });

  if (profileQuery.isPending) {
    return (
      <div className="ir-page space-y-6">
        <div className="h-6 w-48 bg-muted rounded animate-pulse" />
        <div className="h-10 w-96 bg-muted rounded animate-pulse" />
        <div className="h-48 rounded-2xl border border-border bg-card p-6 animate-pulse" />
      </div>
    );
  }

  if (profileQuery.isError || !profileQuery.data) {
    return (
      <div className="ir-page space-y-4">
        <div role="alert" className="rounded-xl border border-destructive/25 bg-destructive/5 p-5 text-xs text-destructive">
          Failed to load Ideal Customer Profile: {profileQuery.error?.message || "Not found."}
        </div>
        <Link href="/intent-radar/ideal-customers" className="ir-button text-xs">
          Back to Profiles
        </Link>
      </div>
    );
  }

  const p = profileQuery.data;
  const company = p.criteria?.company || {};
  const contact = p.criteria?.contact || {};
  const intent = p.criteria?.intent || {};

  const industries: string[] = Array.isArray(company.industries) ? company.industries : [];
  const sizes: string[] = Array.isArray(company.size) ? company.size : [];
  const geographies: string[] = Array.isArray(company.geographies) ? company.geographies : [];
  const jobTitles: string[] = Array.isArray(contact.job_titles) ? contact.job_titles : [];
  const painPoints: string[] = Array.isArray(intent.pain_points) ? intent.pain_points : [];
  const triggers: string[] = Array.isArray(intent.buying_triggers) ? intent.buying_triggers : [];
  const exclusions: string[] = Array.isArray(company.exclusions) ? company.exclusions : [];

  const related = relatedQuery.data;

  return (
    <div className="ir-page w-full min-w-0 space-y-6 pb-20">
      {/* 1. Breadcrumbs */}
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
          <span className="font-medium text-foreground truncate max-w-[200px]">{p.name}</span>
        </nav>

        <Link
          href="/intent-radar/ideal-customers"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft size={13} />
          <span>Back to Profiles</span>
        </Link>
      </div>

      {/* 2. Detail Header */}
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1.5 max-w-2xl">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
              {p.name}
            </h1>

            <span
              className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium border ${
                p.status === "ACTIVE"
                  ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/20"
                  : "bg-muted text-muted-foreground border-border"
              }`}
            >
              {p.status}
            </span>

            {p.is_primary ? (
              <span className="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">
                <Star size={11} className="fill-primary" /> Primary ICP
              </span>
            ) : (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setPrimaryMutation.mutate()}
                className="h-6 text-[11px] text-muted-foreground hover:text-primary gap-1"
              >
                <Star size={11} />
                <span>Set as Primary</span>
              </Button>
            )}
          </div>

          <p className="text-xs text-muted-foreground leading-relaxed">
            {p.description || "No description provided."}
          </p>
        </div>

        {/* Header Actions */}
        <div className="flex items-center gap-2">
          <Link
            href={`/intent-radar/ideal-customers/compare`}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-semibold text-foreground hover:border-primary/50 hover:text-primary transition-colors"
          >
            <GitCompare size={13} />
            <span>Compare</span>
          </Link>

          <Link
            href={`/intent-radar/ideal-customers/${id}/edit`}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-semibold text-foreground hover:border-primary/50 hover:text-primary transition-colors"
          >
            <Edit3 size={13} />
            <span>Edit ICP</span>
          </Link>

          <Link
            href={`/intent-radar/discover/new?icp_id=${id}`}
            className="ir-button ir-primary inline-flex h-8 items-center gap-1.5 text-xs font-semibold"
          >
            <Search size={13} />
            <span>Start Discovery</span>
          </Link>
        </div>
      </header>

      {/* 3. Tab Navigation */}
      <PrimaryTabs
        items={[
          { id: "overview", label: "Overview" },
          { id: "targeting", label: "Targeting Criteria" },
          {
            id: "research",
            label: "Linked Research & Signals",
            count: (related?.discoveries?.length || 0) + (related?.monitors?.length || 0),
          },
          { id: "activity", label: "Version History" },
        ]}
        activeId={activeTab}
        onChange={setActiveTab}
      />

      {/* TAB 1: Overview */}
      {activeTab === "overview" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Target Companies Card */}
            <article className="rounded-2xl border border-border bg-card p-4 space-y-3 shadow-xs">
              <span className="text-[11px] font-semibold text-primary uppercase tracking-wide flex items-center gap-1.5">
                <Target size={13} />
                <span>Target Companies</span>
              </span>
              <div className="space-y-2 text-xs">
                <div>
                  <span className="text-muted-foreground block text-[11px]">Industries:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {industries.length > 0 ? (
                      industries.map((ind, i) => (
                        <span key={i} className="rounded bg-muted/60 px-1.5 py-0.5 text-foreground font-medium">
                          {ind}
                        </span>
                      ))
                    ) : (
                      <span className="text-muted-foreground italic">Any industry</span>
                    )}
                  </div>
                </div>

                <div>
                  <span className="text-muted-foreground block text-[11px]">Company Size:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {sizes.length > 0 ? (
                      sizes.map((s, i) => (
                        <span key={i} className="rounded bg-muted/60 px-1.5 py-0.5 text-foreground font-medium">
                          {s}
                        </span>
                      ))
                    ) : (
                      <span className="text-muted-foreground italic">All sizes</span>
                    )}
                  </div>
                </div>

                <div>
                  <span className="text-muted-foreground block text-[11px]">Geographies:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {geographies.length > 0 ? (
                      geographies.map((g, i) => (
                        <span key={i} className="rounded bg-muted/60 px-1.5 py-0.5 text-foreground font-medium">
                          {g}
                        </span>
                      ))
                    ) : (
                      <span className="text-muted-foreground italic">Worldwide</span>
                    )}
                  </div>
                </div>
              </div>
            </article>

            {/* Buyer Personas Card */}
            <article className="rounded-2xl border border-border bg-card p-4 space-y-3 shadow-xs">
              <span className="text-[11px] font-semibold text-primary uppercase tracking-wide flex items-center gap-1.5">
                <Users size={13} />
                <span>Decision Makers &amp; Roles</span>
              </span>
              <div className="space-y-2 text-xs">
                <div className="flex flex-wrap gap-1 mt-1">
                  {jobTitles.length > 0 ? (
                    jobTitles.map((t, i) => (
                      <span key={i} className="rounded bg-primary/10 text-primary border border-primary/20 px-2 py-0.5 font-medium">
                        {t}
                      </span>
                    ))
                  ) : (
                    <span className="text-muted-foreground italic">Any decision maker</span>
                  )}
                </div>
                {company.product_service && (
                  <div className="pt-2 border-t border-border/70 text-[11px]">
                    <span className="text-muted-foreground">Associated Product: </span>
                    <strong className="text-foreground">{company.product_service}</strong>
                  </div>
                )}
              </div>
            </article>

            {/* Customer Problems Card */}
            <article className="rounded-2xl border border-border bg-card p-4 space-y-3 shadow-xs">
              <span className="text-[11px] font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wide flex items-center gap-1.5">
                <AlertCircle size={13} />
                <span>Customer Problems &amp; Frustrations</span>
              </span>
              <div className="space-y-1.5 text-xs">
                {painPoints.length > 0 ? (
                  painPoints.map((pt, i) => (
                    <div key={i} className="flex items-start gap-1.5 text-foreground">
                      <span className="text-amber-500 font-bold">•</span>
                      <span>{pt}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-muted-foreground italic">No specific pain points defined.</p>
                )}
              </div>
            </article>

            {/* Buying Triggers Card */}
            <article className="rounded-2xl border border-border bg-card p-4 space-y-3 shadow-xs">
              <span className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wide flex items-center gap-1.5">
                <Sparkles size={13} />
                <span>High-Intent Buying Signals</span>
              </span>
              <div className="space-y-1.5 text-xs">
                {triggers.length > 0 ? (
                  triggers.map((trig, i) => (
                    <div key={i} className="flex items-start gap-1.5 text-foreground">
                      <span className="text-emerald-500 font-bold">✓</span>
                      <span>{trig}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-muted-foreground italic">No custom triggers defined.</p>
                )}
              </div>
            </article>
          </div>

          {/* Exclusions Strip */}
          {exclusions.length > 0 && (
            <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5 space-y-1.5 text-xs">
              <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">
                Targeting Exclusions
              </span>
              <div className="flex flex-wrap gap-1">
                {exclusions.map((ex, i) => (
                  <span key={i} className="rounded border border-border bg-background px-2 py-0.5 text-muted-foreground">
                    ✕ {ex}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Targeting Details */}
      {activeTab === "targeting" && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-border bg-card p-5 space-y-4">
            <h2 className="text-sm font-bold text-foreground">Full Targeting Criteria JSON</h2>
            <p className="text-xs text-muted-foreground">
              These structured attributes are evaluated during intent ranking and keyword expansion.
            </p>
            <pre className="p-4 rounded-xl bg-muted/40 border border-border/80 text-[11px] font-mono overflow-x-auto text-foreground">
              {JSON.stringify(p.criteria, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* TAB 3: Linked Research & Signals */}
      {activeTab === "research" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Linked Discoveries */}
            <article className="rounded-2xl border border-border bg-card p-4 space-y-3">
              <h2 className="text-xs font-semibold text-foreground flex items-center justify-between">
                <span>Associated Discoveries ({related?.discoveries?.length || 0})</span>
                <Link
                  href={`/intent-radar/discover/new?icp_id=${id}`}
                  className="text-primary hover:underline font-normal text-[11px]"
                >
                  + New Discovery
                </Link>
              </h2>
              {related?.discoveries && related.discoveries.length > 0 ? (
                <div className="space-y-2 text-xs">
                  {related.discoveries.map((d) => (
                    <div key={d.id} className="p-2 rounded-lg border border-border flex items-center justify-between">
                      <span className="font-medium text-foreground">{d.title}</span>
                      <span className="text-[10px] text-muted-foreground">{d.status}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground italic">No linked discovery searches yet.</p>
              )}
            </article>

            {/* Linked Monitors */}
            <article className="rounded-2xl border border-border bg-card p-4 space-y-3">
              <h2 className="text-xs font-semibold text-foreground flex items-center justify-between">
                <span>Associated Monitors ({related?.monitors?.length || 0})</span>
                <Link
                  href={`/intent-radar/monitors/new?icp_id=${id}`}
                  className="text-primary hover:underline font-normal text-[11px]"
                >
                  + New Monitor
                </Link>
              </h2>
              {related?.monitors && related.monitors.length > 0 ? (
                <div className="space-y-2 text-xs">
                  {related.monitors.map((m) => (
                    <div key={m.id} className="p-2 rounded-lg border border-border flex items-center justify-between">
                      <span className="font-medium text-foreground">{m.name}</span>
                      <span className="text-[10px] text-muted-foreground">{m.status}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground italic">No linked monitors yet.</p>
              )}
            </article>
          </div>

          {/* Matched Conversations */}
          <article className="rounded-2xl border border-border bg-card p-4 space-y-3">
            <h2 className="text-xs font-semibold text-foreground">
              Matched Evidence Conversations ({related?.signals?.length || 0})
            </h2>
            {related?.signals && related.signals.length > 0 ? (
              <div className="space-y-2 text-xs">
                {related.signals.map((sig) => (
                  <div key={sig.id} className="p-3 rounded-xl border border-border bg-background space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <Link
                        href={`/intent-radar/signals/${sig.id}`}
                        className="font-semibold text-foreground hover:text-primary transition-colors"
                      >
                        {sig.title}
                      </Link>
                      <span className="rounded bg-primary/10 text-primary px-1.5 py-0.2 text-[10px] font-semibold shrink-0">
                        Score {sig.score}
                      </span>
                    </div>
                    <div className="text-[11px] text-muted-foreground flex items-center gap-3">
                      <span>Source: {sig.source}</span>
                      {sig.matched_terms?.length > 0 && (
                        <span>Matched terms: {sig.matched_terms.join(", ")}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground italic">
                No conversations have matched this profile yet. Run a Discovery or setup Monitoring.
              </p>
            )}
          </article>
        </div>
      )}

      {/* TAB 4: Activity / History */}
      {activeTab === "activity" && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-border bg-card p-5 space-y-3">
            <h2 className="text-sm font-bold text-foreground">Revision History</h2>
            <p className="text-xs text-muted-foreground">
              Track changes made to this targeting profile over time.
            </p>
            {versionsQuery.isPending ? (
              <div className="p-4 text-xs text-muted-foreground">Loading revision history…</div>
            ) : versionsQuery.data?.items?.length ? (
              <div className="space-y-2 text-xs">
                {versionsQuery.data.items.map((v) => (
                  <div key={v.revision} className="p-3 rounded-xl border border-border bg-background flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-foreground">Revision #{v.revision}</span>
                      <p className="text-[11px] text-muted-foreground mt-0.5">{v.name}</p>
                    </div>
                    <span className="text-[11px] text-muted-foreground">
                      {new Date(v.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground italic">Current version is Revision #{p.revision}.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
