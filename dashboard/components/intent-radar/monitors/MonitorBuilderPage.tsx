"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  ChevronDown,
  ChevronRight,
  HelpCircle,
  Info,
  Loader2,
  SlidersHorizontal,
  Sparkles,
  Undo2,
  X,
} from "lucide-react";
import { toast } from "sonner";
import {
  INTENT_CATEGORIES,
  emptyIntentSearch,
  type IntentCategory,
  type IntentMonitor,
  type IntentSearch,
  type SourceId,
} from "@/lib/intent-radar";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "../provider";
import { ProviderLogo } from "../provider-logo";
import { SourceConfigDrawer } from "../discover/SourceConfigDrawer";
import { Button } from "@/components/ui/button";

const EXAMPLE_MONITOR_PROMPTS = [
  "Find SaaS founders looking for affordable CRM alternatives and discussing problems with their current tools",
  "Engineers evaluating vector databases or comparing Pinecone, Qdrant, and pgvector",
  "Product teams complaining about complex customer onboarding tools and looking for self-serve solutions",
  "Security leads asking for recommendation on SOC 2 automated compliance platforms",
];

const COMMON_TIMEZONES = [
  "UTC",
  "America/New_York",
  "America/Chicago",
  "America/Los_Angeles",
  "Europe/London",
  "Europe/Berlin",
  "Asia/Dubai",
  "Asia/Kolkata",
  "Asia/Singapore",
  "Asia/Tokyo",
  "Australia/Sydney",
];

interface DiscoveryStrategy {
  objective: string;
  search_rationale: string;
  target_customer: string;
  keywords: string[];
  excluded: string[];
  sources: SourceId[];
  categories: IntentCategory[];
  date_range: string;
  min_relevance: number;
  result_limit: number;
  suggested_frequency?: string;
}

export function MonitorBuilderPage({
  existing,
  onClose,
}: {
  existing?: IntentMonitor | null;
  onClose?: () => void;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const mutation = useRadarMutation();
  const access = useRadarCapabilities();
  const canWrite = Boolean(access.data?.can_write);

  // Pre-load from saved search if saved_search_id is provided in URL
  const savedSearchId = searchParams.get("saved_search_id");
  const savedSearchQuery = useRadarRead<{
    id: string;
    name: string;
    configuration: IntentSearch;
    prompt?: string;
  }>(`/saved-searches/${savedSearchId}`, Boolean(savedSearchId));

  // AI draft state
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiRefining, setAiRefining] = useState(false);
  const [aiRefineInput, setAiRefineInput] = useState("");
  const [aiDiffSummary, setAiDiffSummary] = useState<string | null>(null);
  const [historyStack, setHistoryStack] = useState<DiscoveryStrategy[]>([]);

  // Form Fields
  const [name, setName] = useState(existing?.name || "");
  const [description, setDescription] = useState(existing?.description || existing?.goal || "");
  const [selectedIcpId, setSelectedIcpId] = useState<string>(
    existing?.configuration?.icp_id ? String(existing.configuration.icp_id) : ""
  );

  // Criteria
  const [config, setConfig] = useState<IntentSearch>(() => existing?.configuration || emptyIntentSearch());
  const [keywordInput, setKeywordInput] = useState("");
  const [excludedInput, setExcludedInput] = useState("");
  const [showAdvancedExclusions, setShowAdvancedExclusions] = useState(false);

  // Source configuration drawer
  const [drawerSource, setDrawerSource] = useState<SourceId | null>(null);

  // Scheduling
  const [frequency, setFrequency] = useState<string>(existing?.schedule?.frequency || "Manual");
  const [timezone, setTimezone] = useState<string>(
    existing?.schedule?.timezone ||
      Intl.DateTimeFormat().resolvedOptions().timeZone ||
      "UTC"
  );
  const [notifyOnMatches, setNotifyOnMatches] = useState(true);
  const [highRelevanceOnly, setHighRelevanceOnly] = useState(false);

  // Error & submission
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Sync from existing or saved search
  useEffect(() => {
    if (existing) {
      setName(existing.name);
      setDescription(existing.description || existing.goal || "");
      setConfig(existing.configuration);
      if (existing.configuration.icp_id) {
        setSelectedIcpId(String(existing.configuration.icp_id));
      }
      if (existing.schedule?.frequency) {
        setFrequency(existing.schedule.frequency);
      }
      if (existing.schedule?.timezone) {
        setTimezone(existing.schedule.timezone);
      }
    } else if (savedSearchQuery.data) {
      const ss = savedSearchQuery.data;
      setName(`Monitor: ${ss.name}`);
      setDescription(ss.prompt || "");
      setConfig(ss.configuration);
      if (ss.configuration.icp_id) {
        setSelectedIcpId(String(ss.configuration.icp_id));
      }
      toast.info(`Pre-populated from Saved Search: "${ss.name}"`);
    }
  }, [existing, savedSearchQuery.data]);

  // Available sources catalog
  const catalogSources = useMemo(() => {
    return (access.data?.sources || []).map((s) => ({
      id: (s.id || s.name.toLowerCase().replace(/\s+/g, "_")) as SourceId,
      name: s.name,
      connected: s.state === "Connected" || Boolean(s.oauth_configured),
      available: s.state !== "Disabled" && s.state !== "Error",
      state: s.state,
    }));
  }, [access.data?.sources]);

  // Quality Validation checks (non-blocking informative warnings)
  const qualityWarnings = useMemo(() => {
    const warnings: string[] = [];
    const trimmedName = name.trim();
    if (trimmedName && /^(x|xx|xxx|test|asdf|foo)$/i.test(trimmedName)) {
      warnings.push("The monitor name is very generic. Use a descriptive name matching your goal.");
    }
    const lowInfo = config.keywords.find((kw) => /^(x|xx|xxx|test|asdf|foo)$/i.test(kw.trim()) || kw.trim().length <= 2);
    if (lowInfo) {
      warnings.push(`Low-information keyword detected ("${lowInfo}"). Very short non-specific keywords will produce noisy matches.`);
    }
    // Check conflicts between keywords and exclusions
    const keywordSet = new Set(config.keywords.map((k) => k.toLowerCase()));
    const conflicting = (config.excluded || []).filter((ex) => keywordSet.has(ex.toLowerCase()));
    if (conflicting.length > 0) {
      warnings.push(`Conflicting terms: "${conflicting.join(", ")}" appears in both Keywords and Excluded Terms.`);
    }
    return warnings;
  }, [name, config.keywords, config.excluded]);

  // Next check preview calculation
  const nextCheckPreview = useMemo(() => {
    if (frequency === "Manual") return "On demand (checks will only run when manually requested)";
    try {
      const now = new Date();
      let hoursToAdd = 24;
      if (frequency === "Daily") hoursToAdd = 24;
      else if (frequency === "12 hours") hoursToAdd = 12;
      else if (frequency === "6 hours") hoursToAdd = 6;
      else if (frequency === "Weekly") hoursToAdd = 168;

      const nextDate = new Date(now.getTime() + hoursToAdd * 3600 * 1000);
      return nextDate.toLocaleString(undefined, {
        weekday: "short",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        timeZoneName: "short",
      });
    } catch {
      return "Calculated upon activation";
    }
  }, [frequency]);

  // Available ICPs
  const icpsQuery = useRadarRead<{ items: { id: string; name: string }[] }>("/icps");
  const icps = icpsQuery.data?.items || [];

  // Keywords handlers
  function addKeyword(kw: string) {
    const val = kw.trim();
    if (!val) return;
    if (config.keywords.includes(val)) return;
    if (config.keywords.length >= 12) {
      toast.error("Maximum 12 keywords allowed.");
      return;
    }
    setConfig((c) => ({ ...c, keywords: [...c.keywords, val] }));
    setKeywordInput("");
  }

  function removeKeyword(idx: number) {
    setConfig((c) => ({
      ...c,
      keywords: c.keywords.filter((_, i) => i !== idx),
    }));
  }

  function addExcluded(ex: string) {
    const val = ex.trim();
    if (!val) return;
    if ((config.excluded || []).includes(val)) return;
    if ((config.excluded || []).length >= 12) {
      toast.error("Maximum 12 exclusions allowed.");
      return;
    }
    setConfig((c) => ({ ...c, excluded: [...(c.excluded || []), val] }));
    setExcludedInput("");
  }

  function removeExcluded(idx: number) {
    setConfig((c) => ({
      ...c,
      excluded: (c.excluded || []).filter((_, i) => i !== idx),
    }));
  }

  function toggleIntentCategory(cat: IntentCategory) {
    setConfig((c) => {
      const exists = c.categories.includes(cat);
      return {
        ...c,
        categories: exists ? c.categories.filter((x) => x !== cat) : [...c.categories, cat],
      };
    });
  }

  function toggleSource(sid: SourceId) {
    setConfig((c) => {
      const currentSources = c.sources || ["hacker_news"];
      const exists = currentSources.includes(sid);
      if (exists) {
        if (currentSources.length <= 1) {
          toast.error("At least one research source must remain selected.");
          return c;
        }
        return { ...c, sources: currentSources.filter((x) => x !== sid) };
      }
      return { ...c, sources: [...currentSources, sid] };
    });
  }

  // AI Generator
  async function handleAIGenerate() {
    if (!aiPrompt.trim()) {
      toast.error("Please enter what you want to monitor.");
      return;
    }
    setAiGenerating(true);
    setError("");
    try {
      const res = (await mutation.mutateAsync({
        path: "/draft",
        body: {
          prompt: aiPrompt,
          icp_id: selectedIcpId || null,
        },
      })) as DiscoveryStrategy;

      // Apply proposed strategy to form
      if (res.keywords && res.keywords.length > 0) {
        setName((prev) => prev.trim() || res.objective.slice(0, 80));
        setDescription(res.search_rationale || res.objective);
        setConfig((prev) => ({
          ...prev,
          keywords: res.keywords.slice(0, 12),
          excluded: (res.excluded || []).slice(0, 12),
          sources: (res.sources || ["hacker_news"]).filter((s) =>
            catalogSources.some((cs) => cs.id === s)
          ) as SourceId[],
          categories: res.categories || [],
          min_relevance: res.min_relevance ?? prev.min_relevance,
        }));

        if (res.suggested_frequency && ["Daily", "Weekly", "Manual"].includes(res.suggested_frequency)) {
          setFrequency(res.suggested_frequency);
        }

        setHistoryStack([res]);
        toast.success("Monitor setup generated by AI.");
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "AI generation failed. You can configure manually below.";
      setError(msg);
      toast.error(msg);
    } finally {
      setAiGenerating(false);
    }
  }

  // AI Refine
  async function handleAIRefine(refinementPrompt: string) {
    if (!refinementPrompt.trim()) return;
    setAiRefining(true);
    setError("");

    const currentStrategy: DiscoveryStrategy = {
      objective: name || description || "Monitor conversations",
      search_rationale: description,
      target_customer: selectedIcpId ? "Selected ICP" : "General audience",
      keywords: config.keywords,
      excluded: config.excluded || [],
      sources: config.sources || ["hacker_news"],
      categories: config.categories,
      date_range: "Any time",
      min_relevance: config.min_relevance,
      result_limit: config.result_limit,
    };

    try {
      const res = (await mutation.mutateAsync({
        path: "/draft",
        body: {
          prompt: refinementPrompt,
          icp_id: selectedIcpId || null,
          previous: currentStrategy,
        },
      })) as DiscoveryStrategy;

      if (res.keywords && res.keywords.length > 0) {
        setHistoryStack((prev) => [...prev, currentStrategy]);
        setConfig((prev) => ({
          ...prev,
          keywords: res.keywords.slice(0, 12),
          excluded: (res.excluded || []).slice(0, 12),
          sources: (res.sources || ["hacker_news"]).filter((s) =>
            catalogSources.some((cs) => cs.id === s)
          ) as SourceId[],
          categories: res.categories || prev.categories,
        }));
        setAiDiffSummary(`Refined: ${refinementPrompt}`);
        setAiRefineInput("");
        toast.success("Applied AI refinement.");
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not apply refinement.");
    } finally {
      setAiRefining(false);
    }
  }

  function handleUndoRefine() {
    if (historyStack.length === 0) return;
    const prev = historyStack[historyStack.length - 1];
    setHistoryStack((s) => s.slice(0, s.length - 1));
    setConfig((c) => ({
      ...c,
      keywords: prev.keywords,
      excluded: prev.excluded,
      sources: prev.sources,
      categories: prev.categories,
    }));
    setAiDiffSummary(null);
    toast.info("Reverted last refinement.");
  }

  // Save / Submit Monitor
  async function handleSubmit(saveAsDraft = false) {
    if (!name.trim()) {
      setError("Please provide a name for this monitor.");
      toast.error("Please provide a name for this monitor.");
      return;
    }
    if (config.keywords.length === 0) {
      setError("Please add at least one search keyword.");
      toast.error("Please add at least one search keyword.");
      return;
    }
    if ((config.sources || []).length === 0) {
      setError("Please select at least one research source.");
      toast.error("Please select at least one research source.");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const monitorStatus = saveAsDraft ? "Draft" : existing?.status === "Paused" ? "Paused" : "Active";
      const payloadConfig: IntentSearch = {
        ...config,
        icp_id: selectedIcpId || null,
      };

      const saved = (await mutation.mutateAsync({
        path: "/monitors" + (existing ? "/" + existing.id : ""),
        method: existing ? "PUT" : "POST",
        body: {
          name: name.trim(),
          description: description.trim(),
          goal: description.trim() || name.trim(),
          configuration: payloadConfig,
          status: monitorStatus,
          request_id: crypto.randomUUID(),
          revision: existing?.revision,
        },
      })) as IntentMonitor;

      // If scheduled and not draft, update schedule configuration
      if (!saveAsDraft && frequency !== "Manual" && saved?.id) {
        await mutation.mutateAsync({
          path: `/monitors/${saved.id}/schedule`,
          method: "PUT",
          body: {
            frequency,
            timezone,
            revision: saved.revision,
          },
        });
      }

      toast.success(
        saveAsDraft
          ? `Saved "${name}" as draft.`
          : existing
            ? `Updated monitor "${name}".`
            : `Created monitor "${name}".`
      );

      if (onClose) {
        onClose();
      } else {
        router.push("/intent-radar/monitors");
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to save monitor.";
      setError(msg);
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="ir-page p-4 sm:p-6 max-w-4xl mx-auto space-y-6 pb-24">
      {/* 1. Breadcrumb & Navigation */}
      <div className="flex items-center justify-between gap-3 border-b border-border pb-3">
        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Link
            href="/intent-radar/monitors"
            className="hover:text-foreground transition-colors inline-flex items-center gap-1"
          >
            <ArrowLeft size={13} />
            <span>Monitoring</span>
          </Link>
          <span>/</span>
          <span className="font-semibold text-foreground">
            {existing ? "Edit Monitor" : "Create Monitor"}
          </span>
        </nav>

        <Link
          href="/help?article=monitors-alerts"
          className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
        >
          <HelpCircle size={13} />
          <span>Monitoring Guide</span>
        </Link>
      </div>

      {/* 2. Page Title */}
      <div className="space-y-1">
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
          {existing ? `Edit: ${existing.name}` : "Create Monitor"}
        </h1>
        <p className="text-xs text-muted-foreground">
          Configure keywords, sources, and schedules to automatically detect conversations that matter to your business.
        </p>
      </div>

      {/* 3. AI-Assisted Setup Hero (Phase 3) */}
      {!existing && (
        <section
          aria-label="AI Monitor Setup"
          className="rounded-2xl border border-primary/20 bg-linear-to-b from-primary/5 to-card p-4 sm:p-5 shadow-xs space-y-3.5"
        >
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-primary font-semibold text-xs">
              <Sparkles size={15} />
              <span>Describe what you want to monitor</span>
            </div>
            {historyStack.length > 0 && (
              <button
                type="button"
                onClick={handleUndoRefine}
                className="inline-flex items-center gap-1 text-[11px] font-medium text-muted-foreground hover:text-foreground cursor-pointer"
              >
                <Undo2 size={12} />
                <span>Undo AI change</span>
              </button>
            )}
          </div>

          <div className="space-y-2">
            <textarea
              value={aiPrompt}
              onChange={(e) => setAiPrompt(e.target.value)}
              placeholder="Example: Find SaaS founders looking for affordable CRM alternatives and discussing problems with their current tools."
              rows={2}
              className="w-full rounded-xl border border-border bg-card p-3 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary shadow-xs resize-y"
            />

            {/* Quick example prompt chips */}
            <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
              <span className="text-[11px] text-muted-foreground">Suggestions:</span>
              {EXAMPLE_MONITOR_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => setAiPrompt(prompt)}
                  className="rounded-md border border-border/80 bg-card px-2 py-0.5 text-[11px] text-muted-foreground hover:border-primary/40 hover:text-foreground transition-colors truncate max-w-xs cursor-pointer"
                  title={prompt}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-border/60">
            <div className="flex items-center gap-2 text-xs">
              {icps.length > 0 && (
                <div className="flex items-center gap-1.5">
                  <span className="text-muted-foreground text-[11px]">Target ICP:</span>
                  <select
                    value={selectedIcpId}
                    onChange={(e) => setSelectedIcpId(e.target.value)}
                    className="rounded-md border border-border bg-card px-2 py-0.5 text-xs text-foreground"
                  >
                    <option value="">All / Workspace Default</option>
                    {icps.map((icp) => (
                      <option key={icp.id} value={icp.id}>
                        {icp.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  const target = document.getElementById("manual-section-focus");
                  target?.scrollIntoView({ behavior: "smooth" });
                }}
                className="text-xs text-muted-foreground hover:text-foreground font-medium px-2 py-1 cursor-pointer"
              >
                Configure Manually
              </button>
              <Button
                type="button"
                size="sm"
                onClick={() => void handleAIGenerate()}
                disabled={aiGenerating || !aiPrompt.trim()}
                className="h-8 text-xs font-semibold"
              >
                {aiGenerating ? (
                  <>
                    <Loader2 size={13} className="animate-spin" />
                    <span>Generating…</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={13} />
                    <span>Generate Monitor Setup</span>
                  </>
                )}
              </Button>
            </div>
          </div>

          {/* AI Refinement inline bar if strategy was generated */}
          {historyStack.length > 0 && (
            <div className="rounded-xl border border-primary/20 bg-card p-3 space-y-2 mt-2">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[11px] font-semibold text-primary">
                  Refine with AI
                </span>
                {aiDiffSummary && (
                  <span className="text-[11px] text-muted-foreground italic truncate max-w-sm">
                    {aiDiffSummary}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-1.5">
                <input
                  type="text"
                  value={aiRefineInput}
                  onChange={(e) => setAiRefineInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      void handleAIRefine(aiRefineInput);
                    }
                  }}
                  placeholder="e.g. Focus on B2B SaaS, exclude coding tutorials, use daily schedule…"
                  className="flex-1 rounded-lg border border-border bg-muted/20 px-2.5 py-1 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={aiRefining || !aiRefineInput.trim()}
                  onClick={() => void handleAIRefine(aiRefineInput)}
                  className="h-7 text-xs font-medium"
                >
                  {aiRefining ? <Loader2 size={11} className="animate-spin" /> : "Apply"}
                </Button>
              </div>

              <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
                {["Focus on small businesses", "Exclude hiring posts", "Track recommendation requests", "Focus on pain points"].map((pill) => (
                  <button
                    key={pill}
                    type="button"
                    onClick={() => void handleAIRefine(pill)}
                    className="rounded-full border border-border/80 bg-muted/30 px-2 py-0.5 text-[10px] text-muted-foreground hover:text-foreground cursor-pointer"
                  >
                    + {pill}
                  </button>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* Quality Warnings (non-blocking) */}
      {qualityWarnings.length > 0 && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 space-y-1 text-xs text-amber-800 dark:text-amber-200">
          <div className="flex items-center gap-1.5 font-semibold">
            <AlertTriangle size={14} className="text-amber-600 dark:text-amber-400" />
            <span>Setup Quality Notice</span>
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-[11px] text-amber-700 dark:text-amber-300">
            {qualityWarnings.map((w, idx) => (
              <li key={idx}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 4. Section 1: What to Monitor */}
      <section
        id="manual-section-focus"
        className="rounded-2xl border border-border bg-card p-5 space-y-4 shadow-xs"
      >
        <div className="border-b border-border/80 pb-3">
          <h2 className="text-sm font-semibold text-foreground">
            1. What to monitor
          </h2>
          <p className="text-xs text-muted-foreground">
            Give your monitor a clear title and research purpose.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5 sm:col-span-2">
            <label className="text-xs font-medium text-foreground">
              Monitor Name <span className="text-destructive">*</span>
            </label>
            <input
              type="text"
              value={name}
              maxLength={120}
              placeholder="e.g. CRM Alternatives & Dissatisfaction Discussions"
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-xl border border-border bg-card px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary shadow-xs"
            />
          </div>

          <div className="space-y-1.5 sm:col-span-2">
            <label className="text-xs font-medium text-foreground">
              Objective &amp; Business Context
            </label>
            <textarea
              value={description}
              maxLength={1000}
              placeholder="What specific buyer conversations, problems, or opportunities should this monitor uncover?"
              rows={2}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full rounded-xl border border-border bg-card p-3 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary shadow-xs resize-y"
            />
          </div>

          {icps.length > 0 && (
            <div className="space-y-1.5 sm:col-span-1">
              <label className="text-xs font-medium text-foreground">
                Target Ideal Customer Profile
              </label>
              <select
                value={selectedIcpId}
                onChange={(e) => setSelectedIcpId(e.target.value)}
                className="w-full rounded-xl border border-border bg-card px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary shadow-xs"
              >
                <option value="">None / All ICPs</option>
                {icps.map((icp) => (
                  <option key={icp.id} value={icp.id}>
                    {icp.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </section>

      {/* 5. Section 2: Search criteria & keywords */}
      <section className="rounded-2xl border border-border bg-card p-5 space-y-4 shadow-xs">
        <div className="border-b border-border/80 pb-3">
          <h2 className="text-sm font-semibold text-foreground">
            2. Search criteria &amp; keywords
          </h2>
          <p className="text-xs text-muted-foreground">
            Keywords, negative terms, and conversation categories to track.
          </p>
        </div>

        {/* Keywords */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-foreground flex items-center justify-between">
            <span>Search Keywords <span className="text-destructive">*</span></span>
            <span className="text-[11px] text-muted-foreground font-normal">
              {config.keywords.length}/12 keywords
            </span>
          </label>

          <div className="flex flex-wrap items-center gap-1.5 p-2 rounded-xl border border-border bg-card min-h-[42px]">
            {config.keywords.map((kw, idx) => (
              <span
                key={kw}
                className="inline-flex items-center gap-1 rounded-md border border-border bg-muted/40 px-2 py-0.5 text-xs text-foreground font-medium"
              >
                <span>{kw}</span>
                <button
                  type="button"
                  onClick={() => removeKeyword(idx)}
                  className="text-muted-foreground hover:text-foreground cursor-pointer"
                  aria-label={`Remove keyword ${kw}`}
                >
                  <X size={12} />
                </button>
              </span>
            ))}

            <input
              type="text"
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === ",") {
                  e.preventDefault();
                  addKeyword(keywordInput);
                }
              }}
              placeholder={config.keywords.length === 0 ? "Add keyword and press Enter…" : "Add more…"}
              className="flex-1 min-w-[140px] text-xs bg-transparent focus:outline-none placeholder:text-muted-foreground px-1 py-0.5"
            />
          </div>
        </div>

        {/* Excluded Terms (collapsible toggle) */}
        <div className="space-y-2">
          <button
            type="button"
            onClick={() => setShowAdvancedExclusions((prev) => !prev)}
            className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground cursor-pointer"
          >
            {showAdvancedExclusions ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            <span>Negative Exclusions ({(config.excluded || []).length})</span>
          </button>

          {showAdvancedExclusions && (
            <div className="space-y-1.5 pl-4 border-l-2 border-border/80">
              <p className="text-[11px] text-muted-foreground">
                Exclude conversations mentioning specific words (e.g. jobs, hiring, course, tutorial).
              </p>
              <div className="flex flex-wrap items-center gap-1.5 p-2 rounded-xl border border-border bg-card min-h-[38px]">
                {(config.excluded || []).map((ex, idx) => (
                  <span
                    key={ex}
                    className="inline-flex items-center gap-1 rounded-md border border-destructive/20 bg-destructive/5 px-2 py-0.5 text-xs text-destructive font-medium"
                  >
                    <span>−{ex}</span>
                    <button
                      type="button"
                      onClick={() => removeExcluded(idx)}
                      className="text-destructive/70 hover:text-destructive cursor-pointer"
                      aria-label={`Remove exclusion ${ex}`}
                    >
                      <X size={12} />
                    </button>
                  </span>
                ))}
                <input
                  type="text"
                  value={excludedInput}
                  onChange={(e) => setExcludedInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === ",") {
                      e.preventDefault();
                      addExcluded(excludedInput);
                    }
                  }}
                  placeholder="Type term to exclude and press Enter…"
                  className="flex-1 min-w-[140px] text-xs bg-transparent focus:outline-none placeholder:text-muted-foreground px-1 py-0.5"
                />
              </div>
            </div>
          )}
        </div>

        {/* Intent Categories */}
        <div className="space-y-2 pt-2 border-t border-border/60">
          <label className="text-xs font-medium text-foreground block">
            Intent Categories
          </label>
          <p className="text-[11px] text-muted-foreground">
            Select specific conversation intents to filter matches, or leave unselected to track all conversations.
          </p>

          <div className="flex flex-wrap gap-1.5 pt-1">
            {INTENT_CATEGORIES.map((cat) => {
              const active = config.categories.includes(cat);
              return (
                <button
                  key={cat}
                  type="button"
                  onClick={() => toggleIntentCategory(cat)}
                  className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium border transition-colors cursor-pointer ${
                    active
                      ? "border-primary/40 bg-primary/10 text-primary font-semibold dark:bg-primary/20"
                      : "border-border/70 bg-card text-muted-foreground hover:border-border hover:text-foreground"
                  }`}
                >
                  {active && <Check size={12} />}
                  <span>{cat}</span>
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {/* 6. Section 3: Approved sources */}
      <section className="rounded-2xl border border-border bg-card p-5 space-y-4 shadow-xs">
        <div className="border-b border-border/80 pb-3">
          <h2 className="text-sm font-semibold text-foreground">
            3. Approved sources
          </h2>
          <p className="text-xs text-muted-foreground">
            Select public research channels and community forums to monitor.
          </p>
        </div>

        {/* Research Sources */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-foreground flex items-center justify-between">
            <span>Research Sources <span className="text-destructive">*</span></span>
            <span className="text-[11px] text-muted-foreground font-normal">
              {(config.sources || []).length} selected
            </span>
          </label>

          <div className="grid gap-2 sm:grid-cols-2">
            {catalogSources.map((source) => {
              const isSelected = (config.sources || []).includes(source.id);
              const isAvailable = source.available;

              return (
                <div
                  key={source.id}
                  className={`flex items-center justify-between p-2.5 rounded-xl border transition-colors ${
                    isSelected
                      ? "border-primary/40 bg-primary/5"
                      : "border-border bg-card hover:border-border/80"
                  }`}
                >
                  <label className="flex items-center gap-2.5 cursor-pointer min-w-0 flex-1">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      disabled={!isAvailable}
                      onChange={() => toggleSource(source.id)}
                      className="rounded border-border text-primary focus:ring-primary"
                    />
                    <ProviderLogo provider={source.name} size={16} />
                    <div className="min-w-0">
                      <span className="text-xs font-semibold text-foreground block truncate">
                        {source.name}
                      </span>
                      <span className="text-[10px] text-muted-foreground block truncate">
                        {isAvailable ? (source.connected ? "Connected" : "Available") : "Setup Required"}
                      </span>
                    </div>
                  </label>

                  {/* Config drawer action for sources that have advanced options */}
                  {["stack_exchange", "github", "youtube", "hacker_news"].includes(source.id) && isSelected && (
                    <button
                      type="button"
                      onClick={() => setDrawerSource(source.id)}
                      className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline font-medium px-1.5 py-0.5 cursor-pointer"
                    >
                      <SlidersHorizontal size={11} />
                      <span>Configure</span>
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 7. Section 4: Schedule & check frequency */}
      <section className="rounded-2xl border border-border bg-card p-5 space-y-4 shadow-xs">
        <div className="border-b border-border/80 pb-3">
          <h2 className="text-sm font-semibold text-foreground">
            4. Schedule &amp; check frequency
          </h2>
          <p className="text-xs text-muted-foreground">
            Configure how often this monitor runs and when to notify you.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {/* Frequency selector */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-foreground">
              Monitoring Frequency
            </label>
            <select
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
              className="w-full rounded-xl border border-border bg-card px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary shadow-xs"
            >
              <option value="Manual">Manual / On demand</option>
              {access.data?.usage?.automatic_schedules_enabled && (
                <>
                  <option value="Daily">Daily</option>
                  {(access.data?.usage?.minimum_schedule_hours || 12) <= 12 && (
                    <option value="12 hours">Every 12 hours</option>
                  )}
                  {(access.data?.usage?.minimum_schedule_hours || 12) <= 6 && (
                    <option value="6 hours">Every 6 hours</option>
                  )}
                  <option value="Weekly">Weekly</option>
                </>
              )}
            </select>
            <p className="text-[11px] text-muted-foreground">
              {frequency === "Manual"
                ? "Checks will run only when triggered manually by you."
                : `Checks will automatically execute on a recurring ${frequency.toLowerCase()} schedule.`}
            </p>
          </div>

          {/* Timezone */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-foreground">
              Schedule Timezone
            </label>
            <select
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className="w-full rounded-xl border border-border bg-card px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary shadow-xs"
            >
              {COMMON_TIMEZONES.map((tz) => (
                <option key={tz} value={tz}>
                  {tz}
                </option>
              ))}
            </select>
            <p className="text-[11px] text-muted-foreground">
              Next scheduled check preview: <span className="font-semibold text-foreground">{nextCheckPreview}</span>
            </p>
          </div>
        </div>

        {/* Notifications Checkboxes */}
        <div className="pt-3 border-t border-border/60 space-y-2">
          <label className="text-xs font-medium text-foreground block">
            Notification Preferences
          </label>

          <div className="space-y-2">
            <label className="flex items-center gap-2 cursor-pointer text-xs text-foreground">
              <input
                type="checkbox"
                checked={notifyOnMatches}
                onChange={(e) => setNotifyOnMatches(e.target.checked)}
                className="rounded border-border text-primary focus:ring-primary"
              />
              <span>Send in-app notifications when new matching conversations are observed</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer text-xs text-foreground">
              <input
                type="checkbox"
                checked={highRelevanceOnly}
                onChange={(e) => setHighRelevanceOnly(e.target.checked)}
                className="rounded border-border text-primary focus:ring-primary"
              />
              <span>Only notify for high-relevance matches (relevance score &ge; 70)</span>
            </label>
          </div>
        </div>

        {/* Quota Transparency Notice */}
        <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5 space-y-1 text-xs">
          <div className="flex items-center gap-1.5 font-semibold text-foreground text-xs">
            <Info size={13} className="text-primary" />
            <span>Quota &amp; Resource Transparency</span>
          </div>
          <p className="text-[11px] text-muted-foreground leading-relaxed">
            This monitor is configured to query {(config.sources || []).length} sources with {config.keywords.length} keywords.
            {frequency !== "Manual"
              ? ` Running ${frequency.toLowerCase()} consumes ~${(config.sources || []).length} search requests per scheduled execution.`
              : " Running on-demand uses query quota only when an immediate check is explicitly run."}
          </p>
        </div>
      </section>

      {/* Error state if submission fails */}
      {error && <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">{error}</div>}

      {/* 7. Sticky Bottom Action Bar */}
      <div className="fixed bottom-0 left-0 right-0 z-40 border-t border-border bg-card/95 backdrop-blur-xs p-3.5 shadow-lg">
        <div className="max-w-4xl mx-auto flex items-center justify-between gap-3">
          <Link
            href="/intent-radar/monitors"
            className="inline-flex h-8 items-center rounded-lg border border-border bg-card px-3 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Cancel
          </Link>

          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={submitting}
              onClick={() => void handleSubmit(true)}
              className="h-8 text-xs font-medium"
            >
              Save Draft
            </Button>

            <Button
              type="button"
              variant="default"
              size="sm"
              disabled={submitting || !canWrite}
              onClick={() => void handleSubmit(false)}
              className="h-8 text-xs font-semibold"
            >
              {submitting ? (
                <>
                  <Loader2 size={13} className="animate-spin" />
                  <span>Saving…</span>
                </>
              ) : existing ? (
                <span>Save Monitor</span>
              ) : frequency === "Manual" ? (
                <span>Create Monitor</span>
              ) : (
                <span>Create &amp; Enable Schedule</span>
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Advanced Source Config Drawer */}
      {drawerSource && (
        <SourceConfigDrawer
          sourceId={drawerSource}
          value={config}
          onChange={(nextConfig: IntentSearch) => {
            setConfig(nextConfig);
            toast.success("Updated source configuration");
          }}
          onClose={() => setDrawerSource(null)}
        />
      )}
    </div>
  );
}
