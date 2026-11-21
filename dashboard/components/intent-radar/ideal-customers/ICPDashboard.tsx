"use client";

import { useMemo, useRef, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  Copy,
  Edit3,
  ExternalLink,
  GitCompare,
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
import { SearchInput } from "@/components/ui/search-input";
import { StatusFilterTabs } from "@/components/ui/tabs";

export type ICPProfile = {
  id: string;
  name: string;
  description: string;
  status: "ACTIVE" | "INACTIVE" | "ARCHIVED";
  revision: number;
  is_primary?: boolean;
  related_counts?: { discoveries?: number; monitors?: number };
  criteria: {
    company?: Partial<Record<'industries'|'size'|'geographies'|'technologies'|'exclusions',string[]> & Record<'business_objective'|'product_service',string>>;
    contact?: Partial<Record<'job_titles',string[]>>;
    intent?: Partial<Record<'keywords'|'pain_points'|'buying_triggers'|'negative_keywords',string[]>>;
  };
  generation_source?: string;
  created_at?: string;
  updated_at?: string;
};

type ICPPageResponse = {
  items: ICPProfile[];
  total: number;
  can_edit: boolean;
};

type StatusTab = "all" | "ACTIVE" | "INACTIVE" | "ARCHIVED";

const STATUS_TABS: { key: StatusTab; label: string }[] = [
  { key: "all", label: "All Profiles" },
  { key: "ACTIVE", label: "Active" },
  { key: "INACTIVE", label: "Drafts" },
  { key: "ARCHIVED", label: "Archived" },
];

export function ICPDashboard() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [statusTab, setStatusTab] = useState<StatusTab>("all");
  const [search, setSearch] = useState("");
  const [industryFilter, setIndustryFilter] = useState("");
  const [sortBy, setSortBy] = useState<"updated" | "name_asc" | "name_desc">("updated");
  const [page, setPage] = useState(1);
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!activeMenuId) return;
    function onDocClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setActiveMenuId(null);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [activeMenuId]);

  // Fetch all ICPs (active, inactive, archived)
  const listQuery = useQuery<ICPPageResponse>({
    queryKey: ["ideal-customer-profiles", page, statusTab],
    queryFn: ({ signal }) =>
      request<ICPPageResponse>(
        `/organization/icps?page=${page}${statusTab !== "all" ? `&status=${statusTab}` : ""}`,
        { signal }
      ),
  });

  const profiles = listQuery.data?.items || [];
  const canEdit = listQuery.data?.can_edit ?? true;

  // Set Primary Mutation
  const setPrimaryMutation = useMutation({
    mutationFn: (id: string) =>
      request(`/organization/icps/${id}/set-primary`, { method: "POST" }),
    onSuccess: () => {
      toast.success("Primary ICP updated.");
      queryClient.invalidateQueries({ queryKey: ["ideal-customer-profiles"] });
    },
    onError: (err: Error) => {
      toast.error(err.message || "Could not set primary ICP.");
    },
  });

  // Duplicate Mutation
  const duplicateMutation = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) =>
      request<{id:string}>(`/organization/icps/${id}/duplicate`, {
        method: "POST",
        body: JSON.stringify({
          name: `${name} (Copy)`,
          request_id: crypto.randomUUID(),
        }),
      }),
    onSuccess: (newProfile) => {
      toast.success("Profile duplicated.");
      queryClient.invalidateQueries({ queryKey: ["ideal-customer-profiles"] });
      if (newProfile?.id) {
        router.push(`/intent-radar/ideal-customers/${newProfile.id}`);
      }
    },
    onError: (err: Error) => {
      toast.error(err.message || "Could not duplicate profile.");
    },
  });

  // Archive / Delete Mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      request(`/organization/icps/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      toast.success("Profile archived.");
      queryClient.invalidateQueries({ queryKey: ["ideal-customer-profiles"] });
    },
    onError: (err: Error) => {
      toast.error(err.message || "Could not archive profile.");
    },
  });

  // Client-side filtering & sorting on the current page items
  const filteredProfiles = useMemo(() => {
    let result = [...profiles];

    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.description?.toLowerCase().includes(q) ||
          JSON.stringify(p.criteria || {}).toLowerCase().includes(q)
      );
    }

    if (industryFilter) {
      result = result.filter((p) => {
        const ind = p.criteria?.company?.industries;
        if (Array.isArray(ind)) {
          return ind.some((i) => String(i).toLowerCase().includes(industryFilter.toLowerCase()));
        }
        return false;
      });
    }

    if (sortBy === "name_asc") {
      result.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortBy === "name_desc") {
      result.sort((a, b) => b.name.localeCompare(a.name));
    } else {
      result.sort(
        (a, b) =>
          new Date(b.updated_at || 0).getTime() - new Date(a.updated_at || 0).getTime()
      );
    }

    return result;
  }, [profiles, search, industryFilter, sortBy]);

  // Compute 4 genuine Overview KPIs
  const totalProfiles = listQuery.data?.total ?? profiles.length;
  const activeProfilesCount = profiles.filter((p) => p.status === "ACTIVE").length;
  const primaryProfile = profiles.find((p) => p.is_primary);
  const totalLinkedResearch = profiles.reduce(
    (acc, p) => acc + (p.related_counts?.discoveries || 0) + (p.related_counts?.monitors || 0),
    0
  );

  // Available industry list for filter
  const allIndustries = useMemo(() => {
    const set = new Set<string>();
    profiles.forEach((p) => {
      const ind = p.criteria?.company?.industries;
      if (Array.isArray(ind)) {
        ind.forEach((i) => set.add(String(i)));
      }
    });
    return Array.from(set);
  }, [profiles]);

  return (
    <div className="ir-page w-full min-w-0 space-y-5">
      {/* 1. Header with Title, Subtitle, and Primary Actions */}
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-border/80 pb-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
            Ideal Customers
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Define and manage your target customers to discover more relevant conversations and opportunities.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            href="/intent-radar/ideal-customers/compare"
            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-semibold text-foreground hover:border-primary/50 hover:text-primary transition-colors"
          >
            <GitCompare size={13} />
            <span>Compare ICPs</span>
          </Link>

          <Link
            href="/intent-radar/ideal-customers/new"
            className="ir-button ir-primary inline-flex h-8 items-center gap-1.5 text-xs font-semibold shadow-xs"
          >
            <Plus size={14} />
            <span>Create ICP</span>
          </Link>
        </div>
      </header>

      {/* 2. 4 Overview Metric Cards */}
      <section aria-label="ICP Metrics Overview" className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <article className="rounded-xl border border-border/70 bg-card p-3.5 shadow-xs space-y-1">
          <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
            Total ICPs
          </span>
          <div className="text-2xl font-bold text-foreground tabular-nums">
            {listQuery.isPending ? "…" : totalProfiles}
          </div>
          <p className="text-[11px] text-muted-foreground">Target market segments</p>
        </article>

        <article className="rounded-xl border border-border/70 bg-card p-3.5 shadow-xs space-y-1">
          <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
            Active Profiles
          </span>
          <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">
            {listQuery.isPending ? "…" : activeProfilesCount}
          </div>
          <p className="text-[11px] text-muted-foreground">Targeting public conversations</p>
        </article>

        <article className="rounded-xl border border-border/70 bg-card p-3.5 shadow-xs space-y-1">
          <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
            Primary Target
          </span>
          <div className="text-sm font-semibold text-foreground truncate mt-1">
            {listQuery.isPending
              ? "…"
              : primaryProfile
              ? primaryProfile.name
              : "None set"}
          </div>
          <p className="text-[11px] text-muted-foreground">Default ranking context</p>
        </article>

        <article className="rounded-xl border border-border/70 bg-card p-3.5 shadow-xs space-y-1">
          <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
            Linked Research
          </span>
          <div className="text-2xl font-bold text-primary tabular-nums">
            {listQuery.isPending ? "…" : totalLinkedResearch}
          </div>
          <p className="text-[11px] text-muted-foreground">Discoveries &amp; monitors</p>
        </article>
      </section>

      {/* 3. Status Tabs */}
      <StatusFilterTabs
        items={STATUS_TABS.map((t) => ({
          id: t.key,
          label: t.label,
          count:
            t.key === "all"
              ? totalProfiles
              : t.key === "ACTIVE"
              ? profiles.filter((p) => p.status === "ACTIVE").length
              : t.key === "INACTIVE"
              ? profiles.filter((p) => p.status === "INACTIVE").length
              : profiles.filter((p) => p.status === "ARCHIVED").length,
        }))}
        activeId={statusTab}
        onChange={(id) => {
          setStatusTab(id as StatusTab);
          setPage(1);
        }}
      />

      {/* 4. Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 rounded-xl border border-border bg-card p-2.5 shadow-xs">
        <div className="flex flex-wrap items-center gap-2 flex-1 min-w-[240px]">
          <SearchInput
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onClear={() => setSearch("")}
            placeholder="Search profiles by name, keywords, or criteria…"
            wrapperClassName="flex-1 min-w-[220px]"
          />

          {allIndustries.length > 0 && (
            <select
              aria-label="Filter by industry"
              value={industryFilter}
              onChange={(e) => setIndustryFilter(e.target.value)}
              className="h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground cursor-pointer focus:border-primary focus:outline-none"
            >
              <option value="">All Industries</option>
              {allIndustries.map((ind) => (
                <option key={ind} value={ind}>
                  {ind}
                </option>
              ))}
            </select>
          )}
        </div>

        <div className="flex items-center gap-2">
          <select
            aria-label="Sort ICPs"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
            className="h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground cursor-pointer focus:border-primary focus:outline-none"
          >
            <option value="updated">Sort: Recently Updated</option>
            <option value="name_asc">Sort: Name (A–Z)</option>
            <option value="name_desc">Sort: Name (Z–A)</option>
          </select>

          {(search || industryFilter) && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setSearch("");
                setIndustryFilter("");
              }}
              className="h-8 text-xs text-muted-foreground hover:text-foreground"
            >
              Reset
            </Button>
          )}
        </div>
      </div>

      {/* 5. Main ICP Table */}
      {listQuery.isPending ? (
        <div role="status" className="overflow-x-auto rounded-xl border border-border bg-card shadow-xs animate-pulse">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-border bg-muted/30 text-[11px] uppercase tracking-wide text-muted-foreground select-none">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Ideal Customer Profile</th>
                <th className="px-3 py-2.5 font-semibold">Status</th>
                <th className="px-3 py-2.5 font-semibold">Target Market</th>
                <th className="px-3 py-2.5 font-semibold">Buyer Roles</th>
                <th className="px-3 py-2.5 font-semibold">Linked Research</th>
                <th className="px-4 py-2.5 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {[1, 2, 3, 4].map((idx) => (
                <tr key={idx} className="h-16">
                  <td className="px-4 py-3">
                    <div className="h-3.5 w-44 rounded bg-muted/60 mb-1.5" />
                    <div className="h-2.5 w-64 rounded bg-muted/40" />
                  </td>
                  <td className="px-3 py-3">
                    <div className="h-4 w-16 rounded-full bg-muted/50" />
                  </td>
                  <td className="px-3 py-3">
                    <div className="h-3 w-32 rounded bg-muted/40" />
                  </td>
                  <td className="px-3 py-3">
                    <div className="h-3 w-28 rounded bg-muted/40" />
                  </td>
                  <td className="px-3 py-3">
                    <div className="h-3 w-20 rounded bg-muted/40" />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="h-7 w-16 rounded bg-muted/50 ml-auto" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <span className="sr-only">Loading ICP profiles…</span>
        </div>
      ) : listQuery.isError ? (
        <div role="alert" className="rounded-xl border border-destructive/25 bg-destructive/5 p-5 text-xs text-destructive flex items-center justify-between">
          <span>{listQuery.error?.message || "Could not load ICP profiles."}</span>
          <Button size="sm" variant="outline" onClick={() => void listQuery.refetch()}>
            Retry
          </Button>
        </div>
      ) : filteredProfiles.length === 0 ? (
        <div className="rounded-2xl border border-border bg-card p-10 text-center space-y-3">
          <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Target size={20} />
          </div>
          <h2 className="text-base font-semibold text-foreground">
            {search || industryFilter ? "No profiles match your filters" : "No Ideal Customer Profiles yet"}
          </h2>
          <p className="text-xs text-muted-foreground max-w-md mx-auto">
            {search || industryFilter
              ? "Try clearing your search terms or changing your status tab."
              : "Define target industries, buyer roles, customer pain points, and buying signals to automatically rank public conversations."}
          </p>
          <div className="pt-2">
            {search || industryFilter ? (
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setSearch("");
                  setIndustryFilter("");
                }}
              >
                Clear Filters
              </Button>
            ) : (
              <Link
                href="/intent-radar/ideal-customers/new"
                className="ir-button ir-primary inline-flex h-8 items-center gap-1.5 text-xs font-semibold"
              >
                <Plus size={14} />
                <span>Create Your First ICP</span>
              </Link>
            )}
          </div>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border bg-card shadow-xs">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-border bg-muted/30 text-[11px] uppercase tracking-wide text-muted-foreground select-none">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Ideal Customer Profile</th>
                <th className="px-3 py-2.5 font-semibold">Status</th>
                <th className="px-3 py-2.5 font-semibold">Target Market</th>
                <th className="px-3 py-2.5 font-semibold">Buyer Roles</th>
                <th className="px-3 py-2.5 font-semibold">Linked Research</th>
                <th className="px-4 py-2.5 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredProfiles.map((p) => {
                const industries = (p.criteria?.company?.industries as string[]) || [];
                const companySize = (p.criteria?.company?.size as string[]) || [];
                const buyerTitles = (p.criteria?.contact?.job_titles as string[]) || [];
                const discCount = p.related_counts?.discoveries || 0;
                const monCount = p.related_counts?.monitors || 0;

                return (
                  <tr key={p.id} className="hover:bg-muted/30 transition-colors group">
                    {/* ICP Name & Description */}
                    <td className="px-4 py-3 max-w-[280px]">
                      <div className="flex items-center gap-2">
                        <Link
                          href={`/intent-radar/ideal-customers/${p.id}`}
                          className="font-semibold text-foreground hover:text-primary transition-colors truncate"
                        >
                          {p.name}
                        </Link>
                        {p.is_primary && (
                          <span className="inline-flex items-center gap-0.5 rounded-full border border-primary/30 bg-primary/10 px-1.5 py-0.2 text-[10px] font-semibold text-primary shrink-0">
                            <Star size={9} className="fill-primary" /> Primary
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-muted-foreground truncate mt-0.5">
                        {p.description || "No description provided."}
                      </p>
                    </td>

                    {/* Status */}
                    <td className="px-3 py-3">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium border ${
                          p.status === "ACTIVE"
                            ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/20"
                            : p.status === "ARCHIVED"
                            ? "bg-muted text-muted-foreground border-border"
                            : "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/20"
                        }`}
                      >
                        {p.status === "ACTIVE"
                          ? "Active"
                          : p.status === "ARCHIVED"
                          ? "Archived"
                          : "Draft"}
                      </span>
                    </td>

                    {/* Target Market */}
                    <td className="px-3 py-3 max-w-[200px]">
                      <div className="truncate font-medium text-foreground">
                        {industries.length > 0 ? industries.slice(0, 2).join(", ") : "Any industry"}
                        {industries.length > 2 ? ` +${industries.length - 2}` : ""}
                      </div>
                      <div className="text-[11px] text-muted-foreground truncate">
                        {companySize.length > 0 ? companySize.join(", ") : "All sizes"}
                      </div>
                    </td>

                    {/* Buyer Roles */}
                    <td className="px-3 py-3 max-w-[180px]">
                      <div className="truncate text-foreground">
                        {buyerTitles.length > 0
                          ? buyerTitles.slice(0, 2).join(", ")
                          : "Any decision maker"}
                        {buyerTitles.length > 2 ? ` +${buyerTitles.length - 2}` : ""}
                      </div>
                      <div className="text-[11px] text-muted-foreground">
                        {buyerTitles.length} {buyerTitles.length === 1 ? "role defined" : "roles defined"}
                      </div>
                    </td>

                    {/* Linked Research */}
                    <td className="px-3 py-3">
                      <div className="flex items-center gap-1.5 text-[11px]">
                        <span className="rounded bg-muted/60 px-1.5 py-0.5 text-foreground font-medium">
                          {discCount} {discCount === 1 ? "search" : "searches"}
                        </span>
                        <span className="rounded bg-muted/60 px-1.5 py-0.5 text-foreground font-medium">
                          {monCount} {monCount === 1 ? "monitor" : "monitors"}
                        </span>
                      </div>
                    </td>

                    {/* Row Actions */}
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1.5 relative">
                        <Link
                          href={`/intent-radar/ideal-customers/${p.id}`}
                          className="inline-flex h-7 items-center rounded-lg border border-border bg-card px-2 text-[11px] font-semibold text-foreground hover:border-primary/50 hover:text-primary transition-colors"
                        >
                          Open
                        </Link>

                        <div className="relative" ref={activeMenuId === p.id ? menuRef : undefined}>
                          <button
                            type="button"
                            onClick={() => setActiveMenuId(activeMenuId === p.id ? null : p.id)}
                            className="flex h-7 w-7 items-center justify-center rounded-lg border border-border bg-card text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors cursor-pointer"
                            aria-label="More actions"
                          >
                            <MoreHorizontal size={13} />
                          </button>

                          {activeMenuId === p.id && (
                            <div className="absolute right-0 top-full mt-1 z-50 w-44 rounded-xl border border-border bg-card p-1.5 shadow-xl text-xs space-y-0.5 text-left animate-in fade-in-50">
                              <Link
                                href={`/intent-radar/ideal-customers/${p.id}/edit`}
                                onClick={() => setActiveMenuId(null)}
                                className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-foreground hover:bg-muted/50 transition-colors"
                              >
                                <Edit3 size={13} />
                                <span>Edit ICP</span>
                              </Link>

                              {!p.is_primary && p.status === "ACTIVE" && canEdit && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setActiveMenuId(null);
                                    setPrimaryMutation.mutate(p.id);
                                  }}
                                  className="w-full flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-foreground hover:bg-muted/50 transition-colors cursor-pointer text-left"
                                >
                                  <Star size={13} />
                                  <span>Set as Primary</span>
                                </button>
                              )}

                              {canEdit && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setActiveMenuId(null);
                                    duplicateMutation.mutate({ id: p.id, name: p.name });
                                  }}
                                  className="w-full flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-foreground hover:bg-muted/50 transition-colors cursor-pointer text-left"
                                >
                                  <Copy size={13} />
                                  <span>Duplicate</span>
                                </button>
                              )}

                              <div className="my-1 border-t border-border/70" />

                              <Link
                                href={`/intent-radar/discover/new?icp_id=${p.id}`}
                                onClick={() => setActiveMenuId(null)}
                                className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-foreground hover:bg-muted/50 transition-colors"
                              >
                                <Search size={13} />
                                <span>Start Discovery</span>
                              </Link>

                              <Link
                                href={`/intent-radar/monitors/new?icp_id=${p.id}`}
                                onClick={() => setActiveMenuId(null)}
                                className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-foreground hover:bg-muted/50 transition-colors"
                              >
                                <Activity size={13} />
                                <span>Create Monitor</span>
                              </Link>

                              {canEdit && p.status !== "ARCHIVED" && (
                                <>
                                  <div className="my-1 border-t border-border/70" />
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setActiveMenuId(null);
                                      deleteMutation.mutate(p.id);
                                    }}
                                    className="w-full flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-destructive hover:bg-destructive/10 transition-colors cursor-pointer text-left"
                                  >
                                    <Trash2 size={13} />
                                    <span>Archive Profile</span>
                                  </button>
                                </>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
