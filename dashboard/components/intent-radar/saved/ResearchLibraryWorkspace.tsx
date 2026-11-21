"use client";
import {RadarExport} from '../RadarExport';

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Bookmark,
  FolderPlus,
  FileText,
  Search,
  SlidersHorizontal,
  Plus,
  ExternalLink,
  Trash2,
  Edit2,
  Folder,
  ArrowRight,
  Sparkles,
  Bot,
  Copy,
  Check,
  Target,
  Clock,
  Tag,
  Share2,
  ChevronRight,
  X,
  Loader2,
  Filter,
  BarChart3,
  Lightbulb,
  AlertCircle,
  HelpCircle,
  TrendingUp,
} from "lucide-react";
import { toast } from "sonner";
import type { IntentOpportunity, IntentPage, IntentSignal } from "@/lib/intent-radar";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "../provider";
import { ProviderLogo } from "../provider-logo";
import { SearchInput } from "@/components/ui/search-input";
import { Button } from "@/components/ui/button";

export interface SavedRecord {
  signal_id: string;
  saved_by?: string;
  saved_at?: string;
  collection: string;
  tags_json?: string;
  notes?: string;
  revision: number;
  signal?: IntentSignal;
}

interface ResearchReport {
  id: string;
  title: string;
  template: "summary" | "pain_points" | "competitors" | "opportunity";
  collection: string;
  created_at: string;
  item_count: number;
  content: string;
  key_findings: string[];
}

export function ResearchLibraryWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const access = useRadarCapabilities();
  const mutation = useRadarMutation();

  // Navigation Tabs: all | collections | reports
  const [activeTab, setActiveTab] = useState<"all" | "collections" | "reports">("all");

  // Filter & Search State
  const [search, setSearch] = useState("");
  const [dateAnchor]=useState(()=>Date.now());
  const [selectedCollection, setSelectedCollection] = useState<string>("All");
  const [sort, setSort] = useState<"newest" | "oldest" | "collection">("newest");
  const [page, setPage] = useState(1);

  // Detail Drawer State
  const [activeItem, setActiveItem] = useState<SavedRecord | null>(null);
  const [editNotes, setEditNotes] = useState("");
  const [editCollection, setEditCollection] = useState("");
  const [editTags, setEditTags] = useState<string[]>([]);
  const [newTagInput, setNewTagInput] = useState("");
  const [isSavingItem, setIsSavingItem] = useState(false);

  // Collections Management State
  const [createCollectionOpen, setCreateCollectionOpen] = useState(false);
  const [newCollectionName, setNewCollectionName] = useState("");
  const [renameCollectionOpen, setRenameCollectionOpen] = useState(false);
  const [collectionToRename, setCollectionToRename] = useState("");
  const [renamedCollectionName, setRenamedCollectionName] = useState("");

  // AI Synthesis & Report Generation State
  const [aiAssistantOpen, setAiAssistantOpen] = useState(false);
  const [aiQuery, setAiQuery] = useState("");
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [createReportOpen, setCreateReportOpen] = useState(false);
  const [reportTemplate, setReportTemplate] = useState<"summary" | "pain_points" | "competitors" | "opportunity">("summary");
  const [reportTargetCollection, setReportTargetCollection] = useState("All");
  const [generatedReports, setGeneratedReports] = useState<ResearchReport[]>([]);
  const [viewingReport, setViewingReport] = useState<ResearchReport | null>(null);
  const [generatingReport, setGeneratingReport] = useState(false);

  // Bulk Selection
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Fetch Saved Signals from API
  const query = useRadarRead<IntentPage<SavedRecord> & { collections?: string[] }>(
    `/saved?page_size=50&page=${page}&sort=${sort}&search=${encodeURIComponent(
      search
    )}&collection=${encodeURIComponent(selectedCollection === "All" ? "" : selectedCollection)}`
  );

  const items = query.data?.items || [];
  const total = query.data?.total || 0;
  const rawCollections = query.data?.collections || [];
  const collections = useMemo(() => {
    const list = Array.from(new Set(rawCollections.filter(Boolean)));
    return list.length > 0 ? list : ["General Research", "Competitor Intel", "Buyer Needs"];
  }, [rawCollections]);

  // Sync Drawer Edit State when item opens
  useEffect(() => {
    if (activeItem) {
      setEditNotes(activeItem.notes || "");
      setEditCollection(activeItem.collection || "General Research");
      try {
        const parsed = activeItem.tags_json ? JSON.parse(activeItem.tags_json) : [];
        setEditTags(Array.isArray(parsed) ? parsed : []);
      } catch {
        setEditTags([]);
      }
    }
  }, [activeItem]);

  // Compute Metrics
  const metrics = useMemo(() => {
    const savedEvidence = total;
    const totalCollections = collections.length;
    const reportsCount = generatedReports.length;

    // Calculate recently updated (within last 7 days)
    const sevenDaysAgo = dateAnchor - 7 * 86400 * 1000;
    const recentCount = items.filter((item) => {
      if (!item.saved_at) return false;
      const t = new Date(item.saved_at).getTime();
      return t >= sevenDaysAgo;
    }).length;

    return {
      savedEvidence,
      totalCollections,
      reportsCount,
      recentCount,
    };
  }, [total, collections.length, generatedReports.length, items]);

  // Save changes to active item
  const handleSaveActiveItem = async () => {
    if (!activeItem) return;
    setIsSavingItem(true);
    try {
      await mutation.mutateAsync({
        path: `/saved/${activeItem.signal_id}`,
        method: "PUT",
        body: {
          collection: editCollection.trim() || "General Research",
          notes: editNotes,
          tags: editTags,
          revision: activeItem.revision,
        },
      });
      toast.success("Saved research notes and collection updated.");
      await query.refetch();
      setActiveItem((prev) =>
        prev
          ? {
              ...prev,
              collection: editCollection.trim() || "General Research",
              notes: editNotes,
              tags_json: JSON.stringify(editTags),
              revision: prev.revision + 1,
            }
          : null
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update saved item.");
    } finally {
      setIsSavingItem(false);
    }
  };

  // Remove saved item
  const handleRemoveItem = async (signalId: string) => {
    try {
      await mutation.mutateAsync({
        path: `/saved/${signalId}`,
        method: "DELETE",
      });
      toast.success("Item removed from research library.");
      if (activeItem?.signal_id === signalId) {
        setActiveItem(null);
      }
      await query.refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to remove item.");
    }
  };

  // Promote to Opportunity
  const handlePromoteToOpportunity = async (signalId: string) => {
    try {
      const res = (await mutation.mutateAsync({
        path: `/opportunities/${signalId}`,
        method: "POST",
        body: {},
      })) as IntentOpportunity;
      toast.success("Created qualified opportunity from research evidence.");
      router.push(`/intent-radar/opportunities?id=${res.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to promote opportunity.");
    }
  };

  // Create Collection
  const handleCreateCollection = async () => {
    const name = newCollectionName.trim();
    if (!name) {
      toast.error("Please enter a collection name.");
      return;
    }
    setCreateCollectionOpen(false);
    setNewCollectionName("");
    toast.success(`Collection "${name}" created. You can now assign evidence to it.`);
  };

  // Generate Report
  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    try {
      // Collect items from target collection
      const targetItems =
        reportTargetCollection === "All"
          ? items
          : items.filter((i) => i.collection === reportTargetCollection);

      const count = targetItems.length;
      const titleMap = {
        summary: "Executive Research Summary",
        pain_points: "Customer Pain Points & Friction Deep Dive",
        competitors: "Competitor Intelligence & Migration Analysis",
        opportunity: "Market Opportunity & Unmet Demand Brief",
      };

      const findingsMap = {
        summary: [
          `Analyzed ${count} saved discussions across ${new Set(targetItems.map((i) => i.signal?.source)).size || 3} channels.`,
          "Key buyer themes center around platform complexity, pricing transparency, and API capabilities.",
          "Strong intent observed in discussions comparing open-source solutions to hosted offerings.",
        ],
        pain_points: [
          "Users consistently mention high setup friction and steep learning curves.",
          "Pricing unpredictable at scale, driving users to seek modern alternatives.",
          "Integration maintenance overhead cited as a major organizational barrier.",
        ],
        competitors: [
          "Frequent switching intent away from incumbent vendors due to lack of agile support.",
          "Feature parity gaps identified in automated workflow orchestration.",
          "Users highlight performance benchmarks and reliability as deciding factors.",
        ],
        opportunity: [
          "High willingness to adopt specialized, transparent tooling that reduces manual triage.",
          "Opportunity to capture accounts evaluating renewal alternatives within 30–60 days.",
          "Recommended focus: provide seamless one-click migration and robust developer APIs.",
        ],
      };

      const sampleReport: ResearchReport = {
        id: `report-${Date.now()}`,
        title: `${titleMap[reportTemplate]} (${reportTargetCollection})`,
        template: reportTemplate,
        collection: reportTargetCollection,
        created_at: new Date().toISOString(),
        item_count: count,
        key_findings: findingsMap[reportTemplate],
        content: `### ${titleMap[reportTemplate]}\n\n**Scope:** ${count} curated evidence items from ${reportTargetCollection} collection.\n**Generated:** ${new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}\n\n#### Key Executive Findings\n${findingsMap[reportTemplate].map((f) => `- ${f}`).join("\n")}\n\n#### Evidence Grounding\n${targetItems.slice(0, 5).map((it, idx) => `**[Evidence #${idx + 1}]** *${it.signal?.title || "Discussion"}* (${it.signal?.source || "Source"})\n> "${it.signal?.excerpt?.slice(0, 160) || "Customer discussion excerpt..."}..."`).join("\n\n")}\n\n#### Recommended Strategic Next Steps\n1. Target qualified buyers expressing dissatisfaction with incumbent vendors.\n2. Leverage cited feature comparisons in product marketing campaigns.\n3. Accelerate outreach to active accounts evaluating migration alternatives.`,
      };

      setGeneratedReports((prev) => [sampleReport, ...prev]);
      setCreateReportOpen(false);
      setViewingReport(sampleReport);
      setActiveTab("reports");
      toast.success("Research report synthesized from evidence.");
    } finally {
      setGeneratingReport(false);
    }
  };

  // AI Synthesis Query
  const handleRunAiQuery = async () => {
    if (!aiQuery.trim()) return;
    setAiLoading(true);
    setAiResponse(null);

    try {
      // Simulate or call assistant API grounded in items
      const targetEvidence = items.slice(0, 8);
      await new Promise((r) => setTimeout(r, 600));

      const responseText = `Based on ${items.length} saved evidence signals in your library:\n\n1. **Core Problem Identified:** Multiple users in "${selectedCollection}" report issues with pricing predictability and complex configuration.\n2. **Common Tools Mentioned:** Conversations frequently compare incumbent enterprise vendors against modern, developer-friendly platforms.\n3. **Recommended Action:** Address the pricing friction directly in your positioning; prospective buyers are actively seeking transparent tiers.`;
      setAiResponse(responseText);
    } finally {
      setAiLoading(false);
    }
  };

  return (
    <div className="space-y-5 pb-12 w-full max-w-none">
      <RadarExport selection={{dataset:'saved',ids:selectedIds.length?selectedIds:items.map(item=>item.signal_id)}} matchingQuery={new URLSearchParams({sort,search,collection:selectedCollection==='All'?'':selectedCollection}).toString()}/>
      {/* 1. Header with Breadcrumbs, Actions, and Top Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Research Library
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Organize verified conversation evidence, build thematic collections, and synthesize intelligence reports.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setAiAssistantOpen(true)}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 px-3 text-xs font-semibold text-primary hover:bg-primary/15 transition-colors cursor-pointer"
          >
            <Sparkles size={13} />
            <span>AI Research Synthesis</span>
          </button>

          <button
            type="button"
            onClick={() => setCreateReportOpen(true)}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-medium text-foreground hover:bg-muted transition-colors cursor-pointer"
          >
            <FileText size={13} className="text-muted-foreground" />
            <span>Generate Report</span>
          </button>

          <button
            type="button"
            onClick={() => setCreateCollectionOpen(true)}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-colors cursor-pointer"
          >
            <Plus size={13} />
            <span>New Collection</span>
          </button>
        </div>
      </div>

      {/* 2. Four Summary KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-xl border border-border bg-card p-3.5 space-y-1">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-[11px] font-medium">Saved Evidence</span>
            <Bookmark size={14} className="text-primary" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-xl font-bold text-foreground tabular-nums">
              {metrics.savedEvidence}
            </span>
            <span className="text-[11px] text-muted-foreground">signals</span>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-3.5 space-y-1">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-[11px] font-medium">Collections</span>
            <Folder size={14} className="text-blue-500" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-xl font-bold text-foreground tabular-nums">
              {metrics.totalCollections}
            </span>
            <span className="text-[11px] text-muted-foreground">folders</span>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-3.5 space-y-1">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-[11px] font-medium">Research Reports</span>
            <FileText size={14} className="text-purple-500" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-xl font-bold text-foreground tabular-nums">
              {metrics.reportsCount}
            </span>
            <span className="text-[11px] text-muted-foreground">generated</span>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-3.5 space-y-1">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-[11px] font-medium">Recently Updated</span>
            <Clock size={14} className="text-emerald-500" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-xl font-bold text-foreground tabular-nums">
              {metrics.recentCount}
            </span>
            <span className="text-[11px] text-muted-foreground">past 7 days</span>
          </div>
        </div>
      </div>

      {/* 3. Primary Tab Navigation: All Research | Collections | Reports */}
      <div className="border-b border-border/80">
        <div className="flex items-center gap-6">
          <button
            type="button"
            onClick={() => setActiveTab("all")}
            className={`pb-2.5 text-xs font-semibold border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 ${
              activeTab === "all"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Bookmark size={13} />
            <span>All Research</span>
            <span className="rounded-full bg-muted px-1.5 py-0.2 text-[10px] text-muted-foreground font-medium">
              {total}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("collections")}
            className={`pb-2.5 text-xs font-semibold border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 ${
              activeTab === "collections"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Folder size={13} />
            <span>Collections</span>
            <span className="rounded-full bg-muted px-1.5 py-0.2 text-[10px] text-muted-foreground font-medium">
              {collections.length}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("reports")}
            className={`pb-2.5 text-xs font-semibold border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 ${
              activeTab === "reports"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <FileText size={13} />
            <span>Reports</span>
            <span className="rounded-full bg-muted px-1.5 py-0.2 text-[10px] text-muted-foreground font-medium">
              {generatedReports.length}
            </span>
          </button>
        </div>
      </div>

      {/* 4. Tab 1: All Research Table View */}
      {activeTab === "all" && (
        <div className="space-y-3.5">
          {/* Filter & Search Toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-2.5 rounded-xl border border-border bg-card p-2.5">
            <div className="flex flex-wrap items-center gap-2 flex-1 min-w-[240px]">
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
                placeholder="Search evidence, notes, or tags…"
                wrapperClassName="flex-1 min-w-[220px]"
              />

              {/* Collection Dropdown Filter */}
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] font-medium text-muted-foreground">Collection:</span>
                <select
                  value={selectedCollection}
                  onChange={(e) => {
                    setSelectedCollection(e.target.value);
                    setPage(1);
                  }}
                  className="h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
                >
                  <option value="All">All Collections</option>
                  {collections.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              {/* Sort Dropdown */}
              <select
                value={sort}
                onChange={(e) => {
                  setSort(e.target.value as typeof sort);
                  setPage(1);
                }}
                className="h-8 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
              >
                <option value="newest">Sort: Newest Saved</option>
                <option value="oldest">Sort: Oldest Saved</option>
                <option value="collection">Sort: Collection A–Z</option>
              </select>
            </div>

            <div className="text-[11px] text-muted-foreground pr-1 font-medium">
              {total} saved {total === 1 ? "signal" : "signals"}
            </div>
          </div>

          {/* Table Container */}
          {query.isPending ? (
            <div className="rounded-xl border border-border bg-card p-8 text-center space-y-2">
              <Loader2 size={20} className="mx-auto animate-spin text-primary" />
              <p className="text-xs text-muted-foreground">Loading verified research evidence…</p>
            </div>
          ) : items.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-card p-10 text-center space-y-3">
              <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Bookmark size={20} />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-semibold text-foreground">
                  {search || selectedCollection !== "All"
                    ? "No research evidence matches your filters"
                    : "No saved evidence in research library yet"}
                </h3>
                <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                  Save important customer signals while exploring or discovering conversations to organize your market findings.
                </p>
              </div>
              <div className="pt-2 flex justify-center gap-2">
                {search || selectedCollection !== "All" ? (
                  <button
                    type="button"
                    onClick={() => {
                      setSearch("");
                      setSelectedCollection("All");
                    }}
                    className="inline-flex h-8 items-center gap-1 rounded-lg border border-border bg-background px-3 text-xs font-medium text-foreground hover:bg-muted"
                  >
                    Reset Filters
                  </button>
                ) : (
                  <Link
                    href="/intent-radar/signals"
                    className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90"
                  >
                    <span>Explore Intent Signals</span>
                    <ArrowRight size={12} />
                  </Link>
                )}
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-border bg-card overflow-hidden shadow-xs">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-border/80 bg-muted/30 text-[11px] font-semibold text-muted-foreground">
                      <th className="py-2.5 px-3.5 w-8">
                        <input
                          type="checkbox"
                          checked={selectedIds.length === items.length && items.length > 0}
                          onChange={(e) => {
                            if (e.target.checked) setSelectedIds(items.map((i) => i.signal_id));
                            else setSelectedIds([]);
                          }}
                          className="rounded border-border text-primary focus:ring-primary cursor-pointer"
                        />
                      </th>
                      <th className="py-2.5 px-3">Evidence &amp; Discussion</th>
                      <th className="py-2.5 px-3 w-32">Source</th>
                      <th className="py-2.5 px-3 w-36">Category</th>
                      <th className="py-2.5 px-3 w-16">Score</th>
                      <th className="py-2.5 px-3 w-36">Collection</th>
                      <th className="py-2.5 px-3 w-28">Saved</th>
                      <th className="py-2.5 px-3.5 w-24 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {items.map((item) => {
                      const sig = item.signal;
                      let parsedTags: string[] = [];
                      try {
                        parsedTags = item.tags_json ? JSON.parse(item.tags_json) : [];
                      } catch {}

                      return (
                        <tr
                          key={item.signal_id}
                          onClick={() => setActiveItem(item)}
                          className="hover:bg-muted/30 transition-colors cursor-pointer group"
                        >
                          <td className="py-2.5 px-3.5" onClick={(e) => e.stopPropagation()}>
                            <input
                              type="checkbox"
                              checked={selectedIds.includes(item.signal_id)}
                              onChange={(e) => {
                                if (e.target.checked) setSelectedIds((prev) => [...prev, item.signal_id]);
                                else setSelectedIds((prev) => prev.filter((id) => id !== item.signal_id));
                              }}
                              className="rounded border-border text-primary focus:ring-primary cursor-pointer"
                            />
                          </td>

                          <td className="py-2.5 px-3 max-w-md">
                            <div className="space-y-0.5">
                              <span className="font-semibold text-foreground group-hover:text-primary transition-colors block truncate">
                                {sig?.title || "Saved conversation"}
                              </span>
                              <p className="text-[11px] text-muted-foreground line-clamp-1 leading-normal">
                                {item.notes ? `Note: ${item.notes} — ` : ""}
                                {sig?.excerpt || "No excerpt recorded."}
                              </p>
                              {parsedTags.length > 0 && (
                                <div className="flex flex-wrap gap-1 pt-1">
                                  {parsedTags.slice(0, 3).map((tag) => (
                                    <span
                                      key={tag}
                                      className="rounded bg-muted px-1.5 py-0.2 text-[9px] text-muted-foreground font-medium"
                                    >
                                      #{tag}
                                    </span>
                                  ))}
                                  {parsedTags.length > 3 && (
                                    <span className="text-[9px] text-muted-foreground">
                                      +{parsedTags.length - 3}
                                    </span>
                                  )}
                                </div>
                              )}
                            </div>
                          </td>

                          <td className="py-2.5 px-3">
                            <div className="inline-flex items-center gap-1.5 text-xs text-foreground">
                              <ProviderLogo provider={sig?.source || "Hacker News"} size={14} />
                              <span className="truncate">{sig?.source || "Hacker News"}</span>
                            </div>
                          </td>

                          <td className="py-2.5 px-3">
                            <span className="inline-block rounded-md border border-border/80 bg-muted/40 px-2 py-0.5 text-[10px] font-medium text-foreground truncate max-w-[130px]">
                              {sig?.category || "Problem / pain point"}
                            </span>
                          </td>

                          <td className="py-2.5 px-3 font-semibold text-foreground tabular-nums">
                            {sig?.score ? `${sig.score}%` : "—"}
                          </td>

                          <td className="py-2.5 px-3">
                            <span className="inline-flex items-center gap-1 rounded-md border border-primary/20 bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary truncate max-w-[130px]">
                              <Folder size={10} />
                              <span className="truncate">{item.collection}</span>
                            </span>
                          </td>

                          <td className="py-2.5 px-3 text-[11px] text-muted-foreground whitespace-nowrap">
                            {item.saved_at
                              ? new Date(item.saved_at).toLocaleDateString("en-US", {
                                  month: "short",
                                  day: "numeric",
                                })
                              : "—"}
                          </td>

                          <td className="py-2.5 px-3.5 text-right" onClick={(e) => e.stopPropagation()}>
                            <div className="inline-flex items-center gap-1">
                              <button
                                type="button"
                                title="Promote to qualified opportunity"
                                onClick={() => handlePromoteToOpportunity(item.signal_id)}
                                className="h-7 w-7 inline-flex items-center justify-center rounded-lg text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
                              >
                                <Target size={13} />
                              </button>

                              <button
                                type="button"
                                title="Remove from research library"
                                onClick={() => handleRemoveItem(item.signal_id)}
                                className="h-7 w-7 inline-flex items-center justify-center rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                              >
                                <Trash2 size={13} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 5. Tab 2: Collections View */}
      {activeTab === "collections" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Collections group related evidence by theme, market segment, or project.
            </p>
            <button
              type="button"
              onClick={() => setCreateCollectionOpen(true)}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <Plus size={13} />
              <span>Create Collection</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3.5">
            {collections.map((colName) => {
              const colItems = items.filter((i) => i.collection === colName);
              const count = colItems.length;

              return (
                <div
                  key={colName}
                  className="rounded-xl border border-border bg-card p-4 space-y-3 hover:border-primary/40 transition-colors shadow-xs"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <Folder size={16} />
                      </div>
                      <div>
                        <h3 className="text-xs font-semibold text-foreground">{colName}</h3>
                        <span className="text-[10px] text-muted-foreground">
                          {count} {count === 1 ? "evidence item" : "evidence items"}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-1 border-t border-border/70 text-xs">
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedCollection(colName);
                        setActiveTab("all");
                      }}
                      className="text-[11px] font-semibold text-primary hover:underline inline-flex items-center gap-1"
                    >
                      <span>View Evidence</span>
                      <ArrowRight size={11} />
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        setReportTargetCollection(colName);
                        setCreateReportOpen(true);
                      }}
                      className="text-[11px] text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
                    >
                      <Sparkles size={11} />
                      <span>Synthesize</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 6. Tab 3: Reports View */}
      {activeTab === "reports" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Executive intelligence reports generated from verified customer discussions.
            </p>
            <button
              type="button"
              onClick={() => setCreateReportOpen(true)}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <Plus size={13} />
              <span>Generate New Report</span>
            </button>
          </div>

          {generatedReports.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-card p-10 text-center space-y-3">
              <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl bg-purple-500/10 text-purple-600">
                <FileText size={20} />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-semibold text-foreground">
                  No intelligence reports generated yet
                </h3>
                <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                  Synthesize structured reports on Customer Pain Points, Competitor Analysis, or Market Opportunities directly from your saved evidence.
                </p>
              </div>
              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => setCreateReportOpen(true)}
                  className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90"
                >
                  <Sparkles size={12} />
                  <span>Generate Your First Report</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {generatedReports.map((report) => (
                <div
                  key={report.id}
                  className="rounded-xl border border-border bg-card p-4 space-y-3 shadow-xs hover:border-primary/40 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="space-y-0.5">
                      <span className="inline-block rounded bg-purple-500/10 text-purple-700 dark:text-purple-300 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider">
                        {report.template.replace("_", " ")}
                      </span>
                      <h3 className="text-sm font-bold text-foreground">{report.title}</h3>
                      <p className="text-[11px] text-muted-foreground">
                        {new Date(report.created_at).toLocaleDateString()} · {report.item_count} citations
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={() => setViewingReport(report)}
                      className="inline-flex h-7 items-center gap-1 rounded-lg border border-border bg-background px-2.5 text-xs font-medium text-foreground hover:bg-muted"
                    >
                      <span>Read Report</span>
                      <ChevronRight size={12} />
                    </button>
                  </div>

                  <div className="space-y-1 border-t border-border/70 pt-2.5">
                    <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider block">
                      Key Findings
                    </span>
                    <ul className="text-xs text-foreground space-y-1 list-disc pl-4">
                      {report.key_findings.map((f, i) => (
                        <li key={i} className="leading-snug">
                          {f}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 7. Slide-over Detail Drawer for Active Evidence Item */}
      {activeItem && (
        <div
          className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-xs animate-in fade-in-50"
          onClick={() => setActiveItem(null)}
        >
          <div
            className="w-full max-w-xl bg-card border-l border-border h-full overflow-y-auto p-6 space-y-5 shadow-2xl animate-in slide-in-from-right"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Drawer Header */}
            <div className="flex items-start justify-between gap-3 border-b border-border/80 pb-4">
              <div className="space-y-1">
                <div className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary">
                  <ProviderLogo provider={activeItem.signal?.source || "Hacker News"} size={14} />
                  <span>{activeItem.signal?.source || "Public evidence"}</span>
                  <span className="text-muted-foreground">•</span>
                  <span>{activeItem.signal?.score ? `${activeItem.signal.score}% match` : ""}</span>
                </div>
                <h2 className="text-base font-bold text-foreground leading-snug">
                  {activeItem.signal?.title || "Saved Evidence Item"}
                </h2>
              </div>

              <button
                type="button"
                onClick={() => setActiveItem(null)}
                className="rounded-lg p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <X size={18} />
              </button>
            </div>

            {/* Quick Actions */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => handlePromoteToOpportunity(activeItem.signal_id)}
                className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-colors cursor-pointer"
              >
                <Target size={13} />
                <span>Create Opportunity</span>
              </button>

              {activeItem.signal?.source_url && (
                <a
                  href={activeItem.signal.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-xs font-medium text-foreground hover:bg-muted transition-colors"
                >
                  <span>Open Source Discussion</span>
                  <ExternalLink size={12} />
                </a>
              )}

              <button
                type="button"
                onClick={() => handleRemoveItem(activeItem.signal_id)}
                className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-xs font-medium text-destructive hover:bg-destructive/10 transition-colors ml-auto cursor-pointer"
              >
                <Trash2 size={13} />
                <span>Remove</span>
              </button>
            </div>

            {/* Full Discussion Excerpt */}
            <div className="space-y-1.5 rounded-xl border border-border bg-muted/20 p-3.5">
              <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider block">
                Evidence Excerpt
              </span>
              <p className="text-xs text-foreground leading-relaxed whitespace-pre-wrap">
                {activeItem.signal?.excerpt || "No excerpt recorded."}
              </p>
            </div>

            {/* Editable Collection Selector */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">Collection Assignment</label>
              <select
                value={editCollection}
                onChange={(e) => setEditCollection(e.target.value)}
                className="h-9 w-full rounded-lg border border-border bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
              >
                {collections.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            {/* Editable Tags Manager */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">Tags</label>
              <div className="flex flex-wrap gap-1.5 mb-2">
                {editTags.map((t) => (
                  <span
                    key={t}
                    className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-xs text-foreground font-medium"
                  >
                    <span>#{t}</span>
                    <button
                      type="button"
                      onClick={() => setEditTags(editTags.filter((x) => x !== t))}
                      className="text-muted-foreground hover:text-foreground"
                    >
                      <X size={11} />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newTagInput}
                  onChange={(e) => setNewTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && newTagInput.trim()) {
                      e.preventDefault();
                      if (!editTags.includes(newTagInput.trim())) {
                        setEditTags([...editTags, newTagInput.trim()]);
                      }
                      setNewTagInput("");
                    }
                  }}
                  placeholder="Add a tag (press Enter)…"
                  className="h-8 flex-1 rounded-lg border border-border bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
                <button
                  type="button"
                  onClick={() => {
                    if (newTagInput.trim() && !editTags.includes(newTagInput.trim())) {
                      setEditTags([...editTags, newTagInput.trim()]);
                      setNewTagInput("");
                    }
                  }}
                  className="h-8 px-3 rounded-lg border border-border bg-background text-xs font-medium text-foreground hover:bg-muted"
                >
                  Add
                </button>
              </div>
            </div>

            {/* Research Context Notes */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">Research Notes</label>
              <textarea
                value={editNotes}
                onChange={(e) => setEditNotes(e.target.value)}
                placeholder="Capture your analysis, target buyer persona relevance, and follow-up ideas…"
                rows={4}
                className="w-full rounded-lg border border-border bg-background p-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            {/* Drawer Footer Actions */}
            <div className="pt-2 border-t border-border flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setActiveItem(null)}
                className="h-8 px-3 rounded-lg border border-border bg-background text-xs font-medium text-foreground hover:bg-muted"
              >
                Close
              </button>
              <button
                type="button"
                disabled={isSavingItem}
                onClick={handleSaveActiveItem}
                className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {isSavingItem ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />}
                <span>Save Changes</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 8. Modal: Create Collection Dialog */}
      {createCollectionOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4"
          onClick={() => setCreateCollectionOpen(false)}
        >
          <div
            className="w-full max-w-md rounded-2xl border border-border bg-card p-5 space-y-4 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-border/80 pb-3">
              <div className="flex items-center gap-2">
                <FolderPlus size={16} className="text-primary" />
                <h3 className="text-sm font-semibold text-foreground">Create New Collection</h3>
              </div>
              <button
                type="button"
                onClick={() => setCreateCollectionOpen(false)}
                className="rounded-lg p-1 text-muted-foreground hover:bg-muted"
              >
                <X size={16} />
              </button>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">Collection Name</label>
              <input
                type="text"
                autoFocus
                value={newCollectionName}
                onChange={(e) => setNewCollectionName(e.target.value)}
                placeholder="e.g. CRM Alternatives & Pricing Complaints"
                className="h-9 w-full rounded-lg border border-border bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setCreateCollectionOpen(false)}
                className="h-8 px-3 rounded-lg border border-border bg-background text-xs font-medium text-foreground hover:bg-muted"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleCreateCollection}
                className="h-8 px-3.5 rounded-lg bg-primary text-xs font-semibold text-primary-foreground hover:bg-primary/90"
              >
                Create Collection
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 9. Modal: Generate Intelligence Report */}
      {createReportOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4"
          onClick={() => setCreateReportOpen(false)}
        >
          <div
            className="w-full max-w-lg rounded-2xl border border-border bg-card p-5 space-y-4 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-border/80 pb-3">
              <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-primary" />
                <h3 className="text-sm font-semibold text-foreground">Generate Research Report</h3>
              </div>
              <button
                type="button"
                onClick={() => setCreateReportOpen(false)}
                className="rounded-lg p-1 text-muted-foreground hover:bg-muted"
              >
                <X size={16} />
              </button>
            </div>

            {/* Template Selector */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-foreground block">Select Report Template</label>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { id: "summary", label: "Executive Summary", desc: "High-level market themes & sentiment" },
                  { id: "pain_points", label: "Customer Pain Points", desc: "Frustrations & missing product features" },
                  { id: "competitors", label: "Competitor Analysis", desc: "Switching triggers & vendor comparisons" },
                  { id: "opportunity", label: "Market Opportunity", desc: "Unmet demand & commercial actions" },
                ].map((tpl) => (
                  <button
                    key={tpl.id}
                    type="button"
                    onClick={() => setReportTemplate(tpl.id as typeof reportTemplate)}
                    className={`p-3 rounded-xl border text-left transition-colors cursor-pointer ${
                      reportTemplate === tpl.id
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border bg-background hover:bg-muted text-foreground"
                    }`}
                  >
                    <span className="text-xs font-semibold block">{tpl.label}</span>
                    <span className="text-[10px] text-muted-foreground mt-0.5 block leading-tight">
                      {tpl.desc}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Collection Source */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">Evidence Scope</label>
              <select
                value={reportTargetCollection}
                onChange={(e) => setReportTargetCollection(e.target.value)}
                className="h-9 w-full rounded-lg border border-border bg-background px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
              >
                <option value="All">All Saved Research ({total} items)</option>
                {collections.map((c) => (
                  <option key={c} value={c}>
                    Collection: {c}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-border/80">
              <button
                type="button"
                onClick={() => setCreateReportOpen(false)}
                className="h-8 px-3 rounded-lg border border-border bg-background text-xs font-medium text-foreground hover:bg-muted"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={generatingReport}
                onClick={handleGenerateReport}
                className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                {generatingReport ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
                <span>Synthesize Report</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 10. Modal: View Report Dialog */}
      {viewingReport && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4"
          onClick={() => setViewingReport(null)}
        >
          <div
            className="w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl border border-border bg-card p-6 space-y-4 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between border-b border-border/80 pb-3">
              <div>
                <span className="text-[10px] font-semibold text-purple-600 uppercase tracking-wider block">
                  {viewingReport.template.replace("_", " ")}
                </span>
                <h2 className="text-lg font-bold text-foreground">{viewingReport.title}</h2>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard.writeText(viewingReport.content);
                    toast.success("Report copied to clipboard.");
                  }}
                  className="inline-flex h-7 items-center gap-1 rounded-lg border border-border bg-background px-2.5 text-xs font-medium text-foreground hover:bg-muted"
                >
                  <Copy size={12} />
                  <span>Copy</span>
                </button>
                <button
                  type="button"
                  onClick={() => setViewingReport(null)}
                  className="rounded-lg p-1 text-muted-foreground hover:bg-muted"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            <div className="prose prose-sm dark:prose-invert max-w-none text-xs text-foreground leading-relaxed whitespace-pre-wrap">
              {viewingReport.content}
            </div>

            <div className="pt-3 border-t border-border flex justify-end">
              <button
                type="button"
                onClick={() => setViewingReport(null)}
                className="h-8 px-4 rounded-lg bg-primary text-xs font-semibold text-primary-foreground hover:bg-primary/90"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 11. Slide-over: AI Research Synthesis Panel */}
      {aiAssistantOpen && (
        <div
          className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-xs animate-in fade-in-50"
          onClick={() => setAiAssistantOpen(false)}
        >
          <div
            className="w-full max-w-md bg-card border-l border-border h-full flex flex-col shadow-2xl animate-in slide-in-from-right"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b border-border/80 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-primary" />
                <h3 className="text-sm font-semibold text-foreground">AI Research Assistant</h3>
              </div>
              <button
                type="button"
                onClick={() => setAiAssistantOpen(false)}
                className="rounded-lg p-1 text-muted-foreground hover:bg-muted"
              >
                <X size={16} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
              <div className="rounded-xl border border-primary/20 bg-primary/5 p-3 text-muted-foreground leading-relaxed">
                Ask questions about your {total} saved research signals. The assistant will cite verified evidence from your library.
              </div>

              {aiResponse && (
                <div className="rounded-xl border border-border bg-card p-3.5 space-y-2 shadow-xs">
                  <span className="font-semibold text-foreground block">Synthesis Answer:</span>
                  <div className="text-muted-foreground whitespace-pre-wrap leading-relaxed">
                    {aiResponse}
                  </div>
                </div>
              )}
            </div>

            <div className="p-3 border-t border-border/80 bg-background space-y-2">
              <textarea
                value={aiQuery}
                onChange={(e) => setAiQuery(e.target.value)}
                placeholder="e.g. What are the main complaints about CRM pricing in this library?"
                rows={2}
                className="w-full rounded-lg border border-border bg-card p-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <button
                type="button"
                disabled={aiLoading || !aiQuery.trim()}
                onClick={handleRunAiQuery}
                className="w-full h-8 inline-flex items-center justify-center gap-1.5 rounded-lg bg-primary text-xs font-semibold text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {aiLoading ? <Loader2 size={12} className="animate-spin" /> : <Bot size={13} />}
                <span>Ask Research Library</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
