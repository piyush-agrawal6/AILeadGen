"use client";

import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertCircle,
  Check,
  CheckCircle2,
  Copy,
  Edit3,
  Eye,
  GitCompare,
  Plus,
  Radio,
  Search,
  Sparkles,
  Star,
  Target,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { request } from "@/lib/intelligence";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SlideOverDrawer } from "@/components/intent-radar/integrations/SlideOverDrawer";
import { CriteriaTerms } from "@/components/workspaces/criteria-terms";
import {
  ICPRefinement,
  ICPSuggestions,
  type ReviewedDraft,
  type Suggestions,
} from "@/components/workspaces/icp-suggestions";
import { ICPAssistant } from "@/components/workspaces/icp-assistant";
import { ICPCompare } from "@/components/workspaces/icp-compare";

type Group = "company" | "contact" | "intent";
type Value = string[] | number | string | null;
type Criteria = Record<Group, Record<string, Value>> & { weights?: Record<string, number> };

export type ICPProfile = {
  id: string;
  name: string;
  description: string;
  status: "ACTIVE" | "INACTIVE" | "ARCHIVED";
  revision: number;
  is_primary?: boolean;
  related_counts?: { discoveries?: number; monitors?: number };
  criteria: Criteria;
  generation_source?: string;
  created_at?: string;
  updated_at?: string;
};

type ICPPage = {
  items: ICPProfile[];
  total: number;
  can_edit: boolean;
};

type RelatedResponse = {
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

type CompareResponse = {
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
};

const SECTIONS: { key: Group; title: string; subtitle: string; fields: [string, string][] }[] = [
  {
    key: "company",
    title: "Company & Market Profile",
    subtitle: "Industries, geography, size, stage, business model, and tech stack.",
    fields: [
      ["industries", "Target industries"],
      ["sub_industries", "Sub-industries"],
      ["countries", "Target countries"],
      ["regions", "Target regions"],
      ["company_sizes", "Company size"],
      ["maturity", "Company maturity / stage"],
      ["business_models", "Business model"],
      ["technologies", "Relevant technologies"],
      ["languages", "Languages"],
    ],
  },
  {
    key: "contact",
    title: "Decision-Makers & Stakeholders",
    subtitle: "Job titles, departments, seniority, and responsibilities.",
    fields: [
      ["job_titles", "Target job titles"],
      ["departments", "Relevant departments"],
      ["seniority", "Seniority"],
      ["job_functions", "Job functions"],
      ["responsibilities", "Key responsibilities"],
    ],
  },
  {
    key: "intent",
    title: "Pain Points, Triggers & Search Strategy",
    subtitle: "Buying signals, competitors, search terms, preferred sources, and exclusions.",
    fields: [
      ["pain_points", "Business pain points"],
      ["buying_signals", "Buying triggers & intent indicators"],
      ["business_needs", "Products / services being evaluated"],
      ["competitors", "Competitor or alternative products"],
      ["search_terms", "Search terminology & phrases"],
      ["preferred_sources", "Preferred research sources"],
      ["relevant_services", "Relevant offerings"],
      ["budget_indicators", "Budget indicators"],
      ["exclusions", "Excluded customer types"],
      ["custom_criteria", "Additional custom criteria"],
    ],
  },
];

function prettify(key: string): string {
  return key.replaceAll("_", " ").replace(/^./, (v) => v.toUpperCase());
}

function asStrings(val: Value | undefined): string[] {
  return Array.isArray(val) ? val : [];
}

function emptyCriteria(): Criteria {
  return {
    company: { revenue_currency: "USD" },
    contact: {},
    intent: {},
  };
}

function ICPEditorForm({
  profile,
  initialDraft,
  canEdit,
  onSaved,
  onCancel,
}: {
  profile: ICPProfile | null;
  initialDraft: ReviewedDraft | null;
  canEdit: boolean;
  onSaved: (saved: ICPProfile) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(profile?.name || initialDraft?.name || "");
  const [description, setDescription] = useState(
    profile?.description || initialDraft?.description || ""
  );
  const [status, setStatus] = useState<string>(
    profile?.status || initialDraft?.status || "ACTIVE"
  );
  const [criteria, setCriteria] = useState<Criteria>(
    profile?.criteria || initialDraft?.criteria || emptyCriteria()
  );
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [aiDraft, setAiDraft] = useState<ReviewedDraft | null>(initialDraft || null);
  const [changes, setChanges] = useState<string[]>([]);
  const [confirmReplace, setConfirmReplace] = useState(false);
  const requestIdRef = useRef<string | null>(null);

  const aiStatus = useQuery({
    queryKey: ["icp-ai-status"],
    queryFn: () =>
      request<{ enabled: boolean; configured: boolean; can_generate: boolean }>(
        "/organization/icps/ai-status"
      ),
    enabled: canEdit,
    retry: false,
  });

  function updateField(group: Group, field: string, value: Value) {
    setCriteria((prev) => ({
      ...prev,
      [group]: { ...prev[group], [field]: value },
    }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (pending || !canEdit) return;
    if (profile?.status === "ACTIVE" && !confirmReplace) {
      setError("Confirm replacing the active ICP before saving.");
      return;
    }
    setPending(true);
    setError("");
    requestIdRef.current ??= crypto.randomUUID();

    try {
      const cleanedCriteria = Object.fromEntries(
        Object.entries(criteria).map(([grp, vals]) => {
          if (grp === "weights") return [grp, vals];
          return [
            grp,
            Object.fromEntries(
              Object.entries((vals as Record<string, Value>) || {}).map(([k, v]) => [
                k,
                Array.isArray(v) ? v.map((s) => s.trim()).filter(Boolean) : v,
              ])
            ),
          ];
        })
      );

      const saved = await request<ICPProfile>(
        `/organization/icps${profile ? `/${profile.id}` : ""}`,
        {
          method: profile ? "PUT" : "POST",
          body: JSON.stringify({
            name: name.trim(),
            description: description.trim(),
            status,
            ...(aiDraft?.proposal_id ? { ai_proposal_id: aiDraft.proposal_id } : {}),
            criteria: cleanedCriteria,
            ...(profile ? { revision: profile.revision } : { request_id: requestIdRef.current }),
          }),
        }
      );
      toast.success(profile ? `Updated ICP "${saved.name}".` : `Created ICP "${saved.name}".`);
      onSaved(saved);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save ideal customer profile.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-5 text-xs">
      {profile && !aiDraft && aiStatus.data?.enabled && aiStatus.data.configured && aiStatus.data.can_generate && (
        <div className="flex items-center justify-between gap-2 rounded-xl border border-primary/25 bg-primary/5 px-3.5 py-2.5">
          <span className="text-foreground font-medium">
            Want stronger buying triggers or sharper keywords?
          </span>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={pending}
            onClick={async () => {
              setPending(true);
              setError("");
              try {
                const res = await request<Suggestions>(
                  `/organization/icps/${profile.id}/prepare-refinement`,
                  { method: "POST", body: JSON.stringify({ revision: profile.revision }) }
                );
                setAiDraft({
                  ...res.candidates[0].draft,
                  proposal_id: res.proposal_id,
                  candidate_index: 0,
                });
              } catch (err) {
                setError(
                  err instanceof Error ? err.message : "AI refinement unavailable right now."
                );
              } finally {
                setPending(false);
              }
            }}
            className="h-7 text-xs gap-1 shrink-0"
          >
            <Sparkles size={12} /> Refine with AI
          </Button>
        </div>
      )}

      {aiDraft && (
        <ICPRefinement
          draft={{ ...aiDraft, name, description, status: "INACTIVE", criteria }}
          onRefined={(val, fields) => {
            setName(val.name);
            setDescription(val.description);
            setCriteria(val.criteria as Criteria);
            setAiDraft(val);
            setChanges(fields);
            requestIdRef.current = null;
          }}
        />
      )}

      {changes.length > 0 && (
        <p role="status" className="rounded-xl bg-primary/5 border border-primary/20 px-3.5 py-2 text-foreground">
          AI refinement ready to review. Updated: {changes.map((c) => prettify(c.replaceAll(".", " · "))).join(", ")}.
        </p>
      )}

      {aiDraft?.assumptions && aiDraft.assumptions.length > 0 && (
        <details className="rounded-xl border border-border bg-muted/20 p-3">
          <summary className="cursor-pointer font-medium text-foreground">
            AI assumptions to review before saving ({aiDraft.assumptions.length})
          </summary>
          <ul className="mt-2 list-disc pl-4 space-y-1 text-muted-foreground">
            {aiDraft.assumptions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </details>
      )}

      <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
        <fieldset disabled={pending || !canEdit} className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="sm:col-span-2 space-y-1">
              <label htmlFor="icp-ws-name" className="block font-medium text-foreground">
                ICP name
              </label>
              <Input
                id="icp-ws-name"
                required
                minLength={2}
                maxLength={120}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. US Series A SaaS needing AI workflow automation"
              />
            </div>

            <div className="space-y-1">
              <label htmlFor="icp-ws-status" className="block font-medium text-foreground">
                Status
              </label>
              <select
                id="icp-ws-status"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="w-full rounded-lg border border-border bg-card px-2.5 py-2 text-xs text-foreground"
              >
                <option value="ACTIVE">Active</option>
                <option value="INACTIVE">Draft / Inactive</option>
                <option value="ARCHIVED">Archived</option>
              </select>
            </div>
          </div>

          <div className="space-y-1">
            <label htmlFor="icp-ws-desc" className="block font-medium text-foreground">
              Description &amp; positioning rationale
            </label>
            <textarea
              id="icp-ws-desc"
              maxLength={1000}
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Briefly describe who this customer segment is and why they buy."
              className="w-full rounded-lg border border-border bg-card px-3 py-2 text-xs text-foreground"
            />
          </div>

          {SECTIONS.map((sec, idx) => (
            <details
              key={sec.key}
              open={idx === 0 || sec.key === "intent"}
              className="rounded-xl border border-border bg-card p-3.5"
            >
              <summary className="cursor-pointer font-semibold text-sm text-foreground">
                {sec.title}
              </summary>
              <p className="text-[11px] text-muted-foreground mt-1 mb-3">
                {sec.subtitle} Leave unknown fields empty — never invent attributes.
              </p>

              <div className="grid gap-3.5 sm:grid-cols-2">
                {sec.fields.map(([fieldKey, label]) => (
                  <CriteriaTerms
                    key={fieldKey}
                    id={`icp-ws-${sec.key}-${fieldKey}`}
                    label={label}
                    value={asStrings(criteria[sec.key]?.[fieldKey])}
                    onChange={(items) => updateField(sec.key, fieldKey, items)}
                    suggestions={
                      fieldKey === "company_sizes"
                        ? ["1-10", "11-50", "51-200", "201-500", "501-1000"]
                        : fieldKey === "countries"
                          ? ["United States", "United Kingdom", "Canada", "Germany", "India", "Australia"]
                          : fieldKey === "preferred_sources"
                            ? ["GitHub", "Hacker News", "Stack Exchange", "Bluesky", "YouTube"]
                            : []
                    }
                  />
                ))}
              </div>

              {sec.key === "company" && (
                <div className="mt-3.5 grid gap-3 sm:grid-cols-2 border-t border-border/60 pt-3">
                  {(["employee_min", "employee_max", "revenue_min", "revenue_max"] as const).map(
                    (numKey) => (
                      <div key={numKey} className="space-y-1">
                        <label htmlFor={`icp-ws-${numKey}`} className="block text-[11px] font-medium text-muted-foreground">
                          {prettify(numKey)}
                        </label>
                        <Input
                          id={`icp-ws-${numKey}`}
                          type="number"
                          min={0}
                          value={(criteria.company?.[numKey] as number) ?? ""}
                          onChange={(e) =>
                            updateField(
                              "company",
                              numKey,
                              e.target.value === "" ? null : Number(e.target.value)
                            )
                          }
                        />
                      </div>
                    )
                  )}
                </div>
              )}
            </details>
          ))}
        </fieldset>

        {profile?.status === "ACTIVE" && canEdit && (
          <label className="flex items-start gap-2 rounded-xl border border-amber-500/30 bg-amber-500/5 p-3 text-xs cursor-pointer">
            <input
              type="checkbox"
              checked={confirmReplace}
              onChange={(e) => setConfirmReplace(e.target.checked)}
              className="accent-primary mt-0.5"
            />
            <span className="text-foreground">
              I reviewed these edits and want to update this active ICP. Historical discoveries remain preserved.
            </span>
          </label>
        )}

        {error && (
          <div
            role="alert"
            className="rounded-xl border border-destructive/25 bg-destructive/5 px-3.5 py-2.5 text-destructive flex items-start gap-2"
          >
            <AlertCircle size={14} className="shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border">
          {canEdit && (
            <Button type="submit" size="sm" disabled={pending}>
              {pending ? "Saving…" : profile ? "Save ICP changes" : "Create ICP"}
            </Button>
          )}
          <Button type="button" size="sm" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}

export function IdealCustomersWorkspace() {
  const client = useQueryClient();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [drawerMode, setDrawerMode] = useState<"detail" | "edit" | "ai" | "compare" | null>(null);
  const [activeProfile, setActiveProfile] = useState<ICPProfile | null>(null);
  const [aiDraft, setAiDraft] = useState<ReviewedDraft | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<ICPProfile | null>(null);
  const [showVersions, setShowVersions] = useState(false);

  const listQuery = useQuery({
    queryKey: ["icps", "workspace", statusFilter],
    queryFn: () =>
      request<ICPPage>(
        `/organization/icps?page=1${statusFilter ? `&status=${statusFilter}` : ""}`
      ),
    retry: false,
  });

  const relatedQuery = useQuery({
    queryKey: ["icp-related", activeProfile?.id],
    queryFn: () => request<RelatedResponse>(`/organization/icps/${activeProfile!.id}/related`),
    enabled: drawerMode === "detail" && !!activeProfile?.id,
    retry: false,
  });

  const compareQuery = useQuery({
    queryKey: ["icp-compare-profiles"],
    queryFn: () =>
      request<CompareResponse>("/organization/icps/compare-profiles", {
        method: "POST",
        body: JSON.stringify({ profile_ids: [] }),
      }),
    enabled: drawerMode === "compare",
    retry: false,
  });

  const items = useMemo(() => listQuery.data?.items || [], [listQuery.data?.items]);
  const canEdit = listQuery.data?.can_edit === true;

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return items;
    return items.filter((p) => {
      const hay = [
        p.name,
        p.description,
        ...asStrings(p.criteria?.company?.industries),
        ...asStrings(p.criteria?.contact?.job_titles),
        ...asStrings(p.criteria?.intent?.pain_points),
        ...asStrings(p.criteria?.intent?.buying_signals),
      ]
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }, [items, search]);

  const primaryIcp = items.find((p) => p.is_primary) || null;
  const activeCount = items.filter((p) => p.status === "ACTIVE").length;
  const linkedTotal = items.reduce(
    (sum, p) => sum + (p.related_counts?.discoveries || 0) + (p.related_counts?.monitors || 0),
    0
  );

  async function refreshAll() {
    await Promise.all([
      client.invalidateQueries({ queryKey: ["icps"] }),
      client.invalidateQueries({ queryKey: ["intent-radar"] }),
    ]);
  }

  async function handleSetPrimary(profile: ICPProfile) {
    setBusyId(`primary:${profile.id}`);
    try {
      await request<ICPProfile>(`/organization/icps/${profile.id}/set-primary`, {
        method: "POST",
      });
      toast.success(`"${profile.name}" set as your primary ICP.`);
      await refreshAll();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not set primary ICP.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDuplicate(profile: ICPProfile) {
    setBusyId(`dup:${profile.id}`);
    try {
      const copy = await request<ICPProfile>(`/organization/icps/${profile.id}/duplicate`, {
        method: "POST",
        body: JSON.stringify({
          name: `${profile.name} (Copy)`.slice(0, 120),
          request_id: crypto.randomUUID(),
        }),
      });
      toast.success(`Duplicated "${profile.name}" as "${copy.name}".`);
      await refreshAll();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not duplicate ICP.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(profile: ICPProfile) {
    setBusyId(`del:${profile.id}`);
    try {
      await request<{ deleted: boolean }>(`/organization/icps/${profile.id}`, {
        method: "DELETE",
      });
      toast.success(`Deleted ICP "${profile.name}". Historical discoveries remain intact.`);
      setConfirmDelete(null);
      if (activeProfile?.id === profile.id) {
        setDrawerMode(null);
        setActiveProfile(null);
      }
      await refreshAll();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not delete ICP.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Target size={20} className="text-primary" aria-hidden="true" />
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Ideal Customers (ICP)
            </h1>
          </div>
          <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
            Define, refine, and prioritize your target customer segments. ICPs power AI Discovery strategies, signal relevance scoring, and recurring monitors across PlaneByte.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {items.length >= 2 && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => setDrawerMode("compare")}
              className="gap-1.5"
            >
              <GitCompare size={14} /> Compare &amp; Prioritize
            </Button>
          )}
          {canEdit && (
            <>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setActiveProfile(null);
                  setAiDraft(null);
                  setDrawerMode("ai");
                }}
                className="gap-1.5"
              >
                <Sparkles size={14} className="text-primary" /> Generate with AI
              </Button>
              <Button
                size="sm"
                onClick={() => {
                  setActiveProfile(null);
                  setAiDraft(null);
                  setDrawerMode("edit");
                }}
                className="gap-1.5"
              >
                <Plus size={14} /> Create ICP
              </Button>
            </>
          )}
        </div>
      </div>

      {/* KPI Summary Strip */}
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4" aria-label="ICP overview">
        <div className="rounded-xl border border-border bg-card px-4 py-3">
          <p className="text-[11px] font-medium text-muted-foreground">Total ICPs</p>
          <p className="text-xl font-bold text-foreground mt-0.5 tabular-nums">{items.length}</p>
          <p className="text-[11px] text-muted-foreground">{activeCount} active for targeting</p>
        </div>
        <div className="rounded-xl border border-border bg-card px-4 py-3">
          <p className="text-[11px] font-medium text-muted-foreground">Primary ICP</p>
          <p className="text-sm font-bold text-foreground mt-1 truncate">
            {primaryIcp ? primaryIcp.name : "Not set"}
          </p>
          <p className="text-[11px] text-muted-foreground">Default in Discover &amp; AI</p>
        </div>
        <div className="rounded-xl border border-border bg-card px-4 py-3">
          <p className="text-[11px] font-medium text-muted-foreground">Linked research</p>
          <p className="text-xl font-bold text-foreground mt-0.5 tabular-nums">{linkedTotal}</p>
          <p className="text-[11px] text-muted-foreground">Discoveries &amp; monitors</p>
        </div>
        <div className="rounded-xl border border-border bg-card px-4 py-3">
          <p className="text-[11px] font-medium text-muted-foreground">AI Assistant</p>
          <Link
            href="/intelligence/assistant?context=icp&prompt=Compare+my+ICPs+and+recommend+which+segment+has+the+strongest+signals+this+month."
            className="mt-1 inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
          >
            <Sparkles size={12} /> Ask AI about ICP fit →
          </Link>
          <p className="text-[11px] text-muted-foreground mt-0.5">Grounded in workspace signals</p>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="flex flex-wrap items-center gap-2.5">
        <div className="relative flex-1 min-w-[220px] max-w-md">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
          />
          <input
            type="search"
            aria-label="Search ICPs"
            placeholder="Search by ICP name, industry, title, or buying trigger…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ paddingLeft: "2.25rem" }}
            className="w-full rounded-xl border border-border bg-card pr-3 py-2 text-xs text-foreground"
          />
        </div>

        <select
          aria-label="Filter ICP status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ width: "auto" }}
          className="w-auto shrink-0 rounded-xl border border-border bg-card px-3 py-2 text-xs text-foreground"
        >
          <option value="">All statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="INACTIVE">Draft / Inactive</option>
          <option value="ARCHIVED">Archived</option>
        </select>
      </div>

      {/* Delete Confirmation Banner */}
      {confirmDelete && (
        <div
          role="alertdialog"
          aria-label="Confirm delete ICP"
          className="rounded-2xl border border-destructive/30 bg-destructive/5 p-4 flex flex-wrap items-center justify-between gap-3 text-xs"
        >
          <p className="text-foreground">
            <strong>Delete “{confirmDelete.name}”?</strong> Existing discovery runs and collected signals will remain intact.
          </p>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="destructive"
              disabled={busyId !== null}
              onClick={() => void handleDelete(confirmDelete)}
            >
              Confirm delete
            </Button>
            <Button size="sm" variant="outline" onClick={() => setConfirmDelete(null)}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Main Scalable ICP Table / Cards */}
      {listQuery.isPending ? (
        <div className="space-y-3" role="status" aria-label="Loading ideal customer profiles">
          {[1, 2, 3].map((n) => (
            <div key={n} className="h-20 rounded-2xl border border-border bg-muted/30 animate-pulse" />
          ))}
        </div>
      ) : listQuery.isError ? (
        <div role="alert" className="rounded-2xl border border-destructive/25 bg-destructive/5 p-5 space-y-2">
          <p className="text-sm font-semibold text-destructive">Ideal customer profiles could not be loaded.</p>
          <Button size="sm" variant="outline" onClick={() => void listQuery.refetch()}>
            Retry
          </Button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border bg-muted/15 p-10 text-center space-y-3">
          <Target size={26} className="mx-auto text-muted-foreground" aria-hidden="true" />
          <h2 className="text-base font-semibold text-foreground">
            {items.length === 0 ? "No Ideal Customer Profiles yet" : "No ICPs match your search"}
          </h2>
          <p className="text-xs text-muted-foreground max-w-md mx-auto">
            {items.length === 0
              ? "Generate 3–5 tailored ICPs from your company profile using AI, or build your first customer segment manually."
              : "Try clearing your search or status filter."}
          </p>
          {items.length === 0 && canEdit && (
            <div className="flex justify-center gap-2 pt-1">
              <Button size="sm" onClick={() => setDrawerMode("ai")} className="gap-1.5">
                <Sparkles size={13} /> Generate with AI
              </Button>
              <Button size="sm" variant="outline" onClick={() => setDrawerMode("edit")}>
                Create manually
              </Button>
            </div>
          )}
        </div>
      ) : (
        <>
          {/* Desktop Table */}
          <div className="hidden lg:block overflow-x-auto rounded-2xl border border-border bg-card">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-border bg-muted/35 text-[11px] font-semibold text-muted-foreground">
                  <th className="px-4 py-2.5">Ideal Customer Profile</th>
                  <th className="px-3 py-2.5">Status</th>
                  <th className="px-3 py-2.5">Target Segment</th>
                  <th className="px-3 py-2.5">Linked Research</th>
                  <th className="px-4 py-2.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filtered.map((icp) => {
                  const industries = asStrings(icp.criteria?.company?.industries).slice(0, 3);
                  const titles = asStrings(icp.criteria?.contact?.job_titles).slice(0, 2);
                  const triggers = asStrings(icp.criteria?.intent?.buying_signals).length;

                  return (
                    <tr key={icp.id} className="hover:bg-muted/20 transition-colors">
                      <td className="px-4 py-3.5 max-w-[300px]">
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              setActiveProfile(icp);
                              setShowVersions(false);
                              setDrawerMode("detail");
                            }}
                            className="font-semibold text-sm text-foreground hover:text-primary text-left truncate cursor-pointer"
                          >
                            {icp.name}
                          </button>
                          {icp.is_primary && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/25 px-2 py-0.5 text-[10px] font-semibold text-primary shrink-0">
                              <Star size={10} /> Primary
                            </span>
                          )}
                        </div>
                        {icp.description && (
                          <p className="text-[11px] text-muted-foreground truncate mt-0.5">
                            {icp.description}
                          </p>
                        )}
                      </td>

                      <td className="px-3 py-3.5 whitespace-nowrap">
                        <span
                          className={
                            "rounded-full border px-2 py-0.5 text-[10px] font-semibold " +
                            (icp.status === "ACTIVE"
                              ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                              : "border-border bg-muted text-muted-foreground")
                          }
                        >
                          {icp.status === "ACTIVE"
                            ? "Active"
                            : icp.status === "ARCHIVED"
                              ? "Archived"
                              : "Draft"}
                        </span>
                        <p className="text-[10px] text-muted-foreground mt-1">v{icp.revision}</p>
                      </td>

                      <td className="px-3 py-3.5 max-w-[260px]">
                        <p className="text-foreground truncate">
                          {industries.length ? industries.join(", ") : "Industries not set"}
                        </p>
                        <p className="text-[11px] text-muted-foreground truncate mt-0.5">
                          {titles.length ? titles.join(", ") : "Titles not set"} · {triggers} buying trigger{triggers === 1 ? "" : "s"}
                        </p>
                      </td>

                      <td className="px-3 py-3.5 whitespace-nowrap text-muted-foreground">
                        <p className="tabular-nums">
                          {icp.related_counts?.discoveries || 0} discoveries · {icp.related_counts?.monitors || 0} monitors
                        </p>
                      </td>

                      <td className="px-4 py-3.5 text-right whitespace-nowrap">
                        <div className="inline-flex items-center gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              setActiveProfile(icp);
                              setShowVersions(false);
                              setDrawerMode("detail");
                            }}
                            className="h-7 px-2 text-[11px] gap-1"
                          >
                            <Eye size={12} /> Details
                          </Button>
                          {canEdit && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                setActiveProfile(icp);
                                setAiDraft(null);
                                setDrawerMode("edit");
                              }}
                              className="h-7 px-2 text-[11px] gap-1"
                            >
                              <Edit3 size={11} /> Edit
                            </Button>
                          )}
                          {canEdit && !icp.is_primary && (
                            <Button
                              size="sm"
                              variant="ghost"
                              disabled={busyId !== null}
                              onClick={() => void handleSetPrimary(icp)}
                              className="h-7 px-2 text-[11px]"
                              title="Set as primary ICP"
                            >
                              Set Primary
                            </Button>
                          )}
                          <Link
                            href={`/intent-radar/discover?icp=${icp.id}`}
                            className="inline-flex h-7 items-center gap-1 rounded-md border border-border bg-card px-2 text-[11px] font-medium text-foreground hover:border-primary/40"
                          >
                            <Search size={11} /> Discover
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Mobile / Tablet Compact Cards */}
          <div className="lg:hidden grid gap-3 sm:grid-cols-2">
            {filtered.map((icp) => (
              <article
                key={icp.id}
                className="rounded-2xl border border-border bg-card p-4 space-y-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <h3 className="text-sm font-semibold text-foreground truncate">{icp.name}</h3>
                      {icp.is_primary && (
                        <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
                          Primary
                        </span>
                      )}
                    </div>
                    {icp.description && (
                      <p className="text-xs text-muted-foreground line-clamp-2 mt-0.5">
                        {icp.description}
                      </p>
                    )}
                  </div>
                  <span className="rounded-full border border-border bg-muted px-2 py-0.5 text-[10px] font-medium shrink-0">
                    {icp.status}
                  </span>
                </div>

                <div className="flex flex-wrap gap-1.5 pt-1">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setActiveProfile(icp);
                      setShowVersions(false);
                      setDrawerMode("detail");
                    }}
                    className="h-7 text-xs"
                  >
                    Details
                  </Button>
                  {canEdit && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setActiveProfile(icp);
                        setAiDraft(null);
                        setDrawerMode("edit");
                      }}
                      className="h-7 text-xs"
                    >
                      Edit
                    </Button>
                  )}
                  <Link
                    href={`/intent-radar/discover?icp=${icp.id}`}
                    className="inline-flex h-7 items-center rounded-md border border-border px-2.5 text-xs font-medium text-foreground"
                  >
                    Discover
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </>
      )}

      {/* =================================================================
          DRAWER 1: ICP DETAILS + RELATED DISCOVERIES / SIGNALS / MONITORS
      ================================================================== */}
      <SlideOverDrawer
        open={drawerMode === "detail" && !!activeProfile}
        onClose={() => setDrawerMode(null)}
        title={activeProfile?.name || "ICP Details"}
        subtitle={activeProfile?.description || "Structured targeting profile and linked Intent Radar research."}
        icon={<Target size={18} className="text-primary" />}
        widthClass="max-w-2xl"
      >
        {activeProfile && (
          <div className="space-y-5 text-xs">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-700 dark:text-emerald-300">
                  {activeProfile.status}
                </span>
                {activeProfile.is_primary && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-0.5 text-[11px] font-semibold text-primary">
                    <Star size={11} /> Primary ICP
                  </span>
                )}
                <span className="text-muted-foreground">Version {activeProfile.revision}</span>
              </div>

              <div className="flex flex-wrap items-center gap-1.5">
                <Link
                  href={`/intent-radar/discover?icp=${activeProfile.id}`}
                  className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground"
                >
                  <Search size={12} /> Discover Signals
                </Link>
                <Link
                  href={`/intelligence/assistant?context=icp&entityId=${activeProfile.id}&prompt=${encodeURIComponent(`Improve my "${activeProfile.name}" ICP by suggesting stronger buying triggers and search terms.`)}`}
                  className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-medium text-foreground hover:border-primary/40"
                >
                  <Sparkles size={12} className="text-primary" /> Ask AI
                </Link>
              </div>
            </div>

            {/* Structured Criteria Breakdown */}
            <div className="space-y-3">
              {SECTIONS.map((sec) => {
                const populated = sec.fields.filter(
                  ([key]) => asStrings(activeProfile.criteria?.[sec.key]?.[key]).length > 0
                );
                if (populated.length === 0) return null;
                return (
                  <div key={sec.key} className="rounded-xl border border-border bg-muted/15 p-4 space-y-2.5">
                    <h4 className="font-semibold text-sm text-foreground">{sec.title}</h4>
                    <dl className="grid gap-2.5 sm:grid-cols-2">
                      {populated.map(([fieldKey, label]) => (
                        <div key={fieldKey}>
                          <dt className="text-[11px] text-muted-foreground">{label}</dt>
                          <dd className="mt-1 flex flex-wrap gap-1">
                            {asStrings(activeProfile.criteria?.[sec.key]?.[fieldKey]).map((v) => (
                              <span
                                key={v}
                                className="rounded-md border border-border bg-card px-2 py-0.5 text-[11px] text-foreground"
                              >
                                {v}
                              </span>
                            ))}
                          </dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                );
              })}
            </div>

            {/* Related Discoveries, Monitors & Matching Signals */}
            <div className="rounded-xl border border-border bg-card p-4 space-y-3">
              <h4 className="font-semibold text-sm text-foreground flex items-center gap-1.5">
                <Activity size={14} className="text-primary" /> Related Workspace Research
              </h4>
              {relatedQuery.isPending ? (
                <div className="h-16 rounded-lg bg-muted/30 animate-pulse" />
              ) : relatedQuery.data ? (
                <div className="space-y-3">
                  <div className="grid gap-2.5 sm:grid-cols-3 text-center">
                    <div className="rounded-lg bg-muted/30 p-2.5">
                      <p className="text-base font-bold text-foreground tabular-nums">
                        {relatedQuery.data.discoveries.length}
                      </p>
                      <p className="text-[11px] text-muted-foreground">Discoveries</p>
                    </div>
                    <div className="rounded-lg bg-muted/30 p-2.5">
                      <p className="text-base font-bold text-foreground tabular-nums">
                        {relatedQuery.data.monitors.length}
                      </p>
                      <p className="text-[11px] text-muted-foreground">Monitors</p>
                    </div>
                    <div className="rounded-lg bg-muted/30 p-2.5">
                      <p className="text-base font-bold text-foreground tabular-nums">
                        {relatedQuery.data.signals.length}
                      </p>
                      <p className="text-[11px] text-muted-foreground">Matching Signals</p>
                    </div>
                  </div>

                  {relatedQuery.data.signals.length > 0 && (
                    <div className="space-y-1.5">
                      <p className="text-[11px] font-semibold text-muted-foreground">
                        Recent matching signals
                      </p>
                      {relatedQuery.data.signals.slice(0, 5).map((sig) => (
                        <Link
                          key={sig.id}
                          href={`/intent-radar/signals/${sig.id}`}
                          className="flex items-center justify-between gap-2 rounded-lg border border-border/70 px-3 py-2 hover:border-primary/40"
                        >
                          <span className="truncate font-medium text-foreground">{sig.title}</span>
                          <span className="shrink-0 text-[11px] text-muted-foreground">
                            {sig.source} · {sig.score}
                          </span>
                        </Link>
                      ))}
                    </div>
                  )}

                  {relatedQuery.data.monitors.length > 0 && (
                    <div className="space-y-1.5">
                      <p className="text-[11px] font-semibold text-muted-foreground">
                        Linked monitors
                      </p>
                      {relatedQuery.data.monitors.map((m) => (
                        <Link
                          key={m.id}
                          href={`/intent-radar/monitors/${m.id}`}
                          className="flex items-center justify-between gap-2 rounded-lg border border-border/70 px-3 py-2 hover:border-primary/40"
                        >
                          <span className="inline-flex items-center gap-1.5 font-medium text-foreground">
                            <Radio size={12} className="text-primary" /> {m.name}
                          </span>
                          <span className="text-[11px] text-muted-foreground">{m.status}</span>
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              ) : null}
            </div>

            {/* Version Comparison Toggle */}
            <div className="space-y-2">
              <button
                type="button"
                onClick={() => setShowVersions((v) => !v)}
                className="text-xs font-medium text-primary hover:underline cursor-pointer"
              >
                {showVersions ? "Hide version comparison" : "Compare saved revisions"}
              </button>
              {showVersions && (
                <ICPCompare
                  key={`${activeProfile.id}:${activeProfile.revision}`}
                  profileId={activeProfile.id}
                  revision={activeProfile.revision}
                />
              )}
            </div>

            {/* Lifecycle Actions */}
            {canEdit && (
              <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border pt-4">
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setAiDraft(null);
                      setDrawerMode("edit");
                    }}
                    className="gap-1"
                  >
                    <Edit3 size={12} /> Edit
                  </Button>
                  {!activeProfile.is_primary && (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={busyId !== null}
                      onClick={() => void handleSetPrimary(activeProfile)}
                      className="gap-1"
                    >
                      <Star size={12} /> Set Primary
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={busyId !== null}
                    onClick={() => void handleDuplicate(activeProfile)}
                    className="gap-1"
                  >
                    <Copy size={12} /> Duplicate
                  </Button>
                </div>

                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setConfirmDelete(activeProfile)}
                  className="text-destructive hover:text-destructive gap-1"
                >
                  <Trash2 size={12} /> Delete
                </Button>
              </div>
            )}
          </div>
        )}
      </SlideOverDrawer>

      {/* =================================================================
          DRAWER 2: CREATE / EDIT ICP
      ================================================================== */}
      <SlideOverDrawer
        open={drawerMode === "edit"}
        onClose={() => {
          setDrawerMode(null);
          setAiDraft(null);
        }}
        title={activeProfile ? `Edit ${activeProfile.name}` : "Create Ideal Customer Profile"}
        subtitle="Define structured company, buyer, and intent criteria. Unknown fields stay empty."
        widthClass="max-w-2xl"
      >
        <ICPEditorForm
          key={activeProfile ? `${activeProfile.id}:${activeProfile.revision}` : `new:${aiDraft?.proposal_id || "manual"}`}
          profile={activeProfile}
          initialDraft={aiDraft}
          canEdit={canEdit}
          onSaved={async (saved) => {
            await refreshAll();
            setActiveProfile(saved);
            setAiDraft(null);
            setDrawerMode("detail");
          }}
          onCancel={() => {
            setDrawerMode(null);
            setAiDraft(null);
          }}
        />
      </SlideOverDrawer>

      {/* =================================================================
          DRAWER 3: GENERATE WITH AI (3-5 Suggestions + Natural Language)
      ================================================================== */}
      <SlideOverDrawer
        open={drawerMode === "ai"}
        onClose={() => setDrawerMode(null)}
        title="AI ICP Generator"
        subtitle="Generate 3–5 tailored ICP suggestions from your company context or describe a segment in natural language. Proposals are reviewed before saving."
        icon={<Sparkles size={18} className="text-primary" />}
        widthClass="max-w-2xl"
      >
        <div className="space-y-5">
          <ICPSuggestions
            onChoose={(draft) => {
              setActiveProfile(null);
              setAiDraft(draft);
              setDrawerMode("edit");
              toast.info("AI ICP proposal loaded for review. Click Create ICP to save.");
            }}
          />
          <ICPAssistant
            onGenerated={(draft) => {
              setActiveProfile(null);
              setAiDraft(draft);
              setDrawerMode("edit");
              toast.info("AI ICP draft ready for review. Click Create ICP to save.");
            }}
          />
        </div>
      </SlideOverDrawer>

      {/* =================================================================
          DRAWER 4: COMPARE & PRIORITIZE ICPs
      ================================================================== */}
      <SlideOverDrawer
        open={drawerMode === "compare"}
        onClose={() => setDrawerMode(null)}
        title="Compare & Prioritize ICPs"
        subtitle="Evaluates your saved ICPs against actual collected workspace signals and highlights missing targeting information."
        icon={<GitCompare size={18} className="text-primary" />}
        widthClass="max-w-2xl"
      >
        {compareQuery.isPending ? (
          <div className="h-32 rounded-xl bg-muted/30 animate-pulse" />
        ) : compareQuery.data ? (
          <div className="space-y-4 text-xs">
            <div className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 p-4 space-y-1">
              <p className="font-semibold text-emerald-800 dark:text-emerald-200 flex items-center gap-1.5">
                <CheckCircle2 size={14} /> Prioritization Recommendation
              </p>
              <p className="text-foreground leading-relaxed">
                {compareQuery.data.recommendation_reason}
              </p>
              <p className="text-[11px] text-muted-foreground">
                Evaluated against {compareQuery.data.signals_evaluated} stored workspace signals.
              </p>
            </div>

            <div className="space-y-3">
              {compareQuery.data.items.map((row) => {
                const isRec = row.id === compareQuery.data?.recommended_id;
                return (
                  <div
                    key={row.id}
                    className={
                      "rounded-xl border p-4 space-y-2 " +
                      (isRec ? "border-primary bg-primary/[0.03]" : "border-border bg-card")
                    }
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <h4 className="font-semibold text-sm text-foreground">{row.name}</h4>
                        {isRec && (
                          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
                            Recommended Priority
                          </span>
                        )}
                        {row.is_primary && (
                          <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                            Primary
                          </span>
                        )}
                      </div>
                      <span className="font-semibold text-foreground tabular-nums">
                        {row.completeness_score}% complete
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-3 text-[11px] text-muted-foreground">
                      <span>
                        <strong className="text-foreground">{row.high_intent_matches}</strong> high-relevance signal matches
                      </span>
                      <span>
                        <strong className="text-foreground">{row.matched_signals}</strong> total signal matches
                      </span>
                      <span>
                        <strong className="text-foreground">{row.buying_signals_count}</strong> buying triggers
                      </span>
                    </div>

                    {row.missing_fields.length > 0 && (
                      <p className="text-[11px] text-amber-700 dark:text-amber-300">
                        Missing targeting details: {row.missing_fields.join(", ")}
                      </p>
                    )}

                    {canEdit && !row.is_primary && (
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={busyId !== null}
                        onClick={() => {
                          const target = items.find((i) => i.id === row.id);
                          if (target) void handleSetPrimary(target);
                        }}
                        className="h-7 text-[11px] gap-1"
                      >
                        <Check size={11} /> Make Primary ICP
                      </Button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}
      </SlideOverDrawer>
    </div>
  );
}
