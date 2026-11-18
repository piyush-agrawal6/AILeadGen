"use client";

import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronUp,
  Info,
  Loader2,
  MoreHorizontal,
  RefreshCw,
  RotateCcw,
  Send,
  Sparkles,
  X,
} from "lucide-react";
import type {
  CopilotProposal,
  CopilotResponse,
  DiscoveryContextSummary,
  IntentSearch,
  SearchStrategy,
  SourceId,
} from "@/lib/intent-radar";
import { Button } from "@/components/ui/button";
import { Menu, MenuContent } from "@/components/ui/menu";
import { useRadarMutation, useRadarRead } from "../provider";

export const DISCOVERY_PRELOAD_KEY = "planebyte:discovery-preload";

export type CopilotQuickAction =
  | "improve_keywords"
  | "suggest_sources"
  | "exclude_noise"
  | "align_icp"
  | "broaden_search"
  | "narrow_search"
  | "explain_strategy"
  | "suggest_search"
  | "refine_after_results";

type ThreadEntry = {
  id: string;
  role: "user" | "assistant";
  content: string;
  mode?: string;
  warnings?: string[];
  proposals?: CopilotProposal[];
  draftFingerprint?: string;
  dismissed?: boolean;
  appliedIds?: string[];
  appliedAll?: boolean;
};

export function computeDraftKey(draft: IntentSearch): string {
  return JSON.stringify({
    keywords: [...(draft.keywords || [])].map((k) => k.toLowerCase()).sort(),
    excluded: [...(draft.excluded || [])].map((k) => k.toLowerCase()).sort(),
    sources: [...(draft.sources || ["hacker_news"])].sort(),
    categories: [...(draft.categories || [])].sort(),
    icp_id: draft.icp_id || null,
    min_relevance: draft.min_relevance || 0,
    result_limit: draft.result_limit || 20,
  });
}

export function applyProposalsToDraft(
  draft: IntentSearch,
  proposals: CopilotProposal[]
): IntentSearch {
  let next: IntentSearch = {
    ...draft,
    keywords: [...(draft.keywords || [])],
    excluded: [...(draft.excluded || [])],
    phrases: [...(draft.phrases || [])],
    topics: [...(draft.topics || [])],
    categories: [...(draft.categories || [])],
    sources: [...(draft.sources ?? ["hacker_news"])],
  };

  for (const prop of proposals) {
    if (prop.action === "add_keywords" && prop.keywords?.length) {
      const seen = new Set(next.keywords.map((k) => k.toLowerCase()));
      const merged = [...next.keywords];
      for (const kw of prop.keywords) {
        if (!seen.has(kw.toLowerCase()) && merged.length < 12) {
          seen.add(kw.toLowerCase());
          merged.push(kw);
        }
      }
      next = { ...next, keywords: merged };
    } else if (prop.action === "remove_keywords" && prop.keywords?.length) {
      const drop = new Set(prop.keywords.map((k) => k.toLowerCase()));
      next = { ...next, keywords: next.keywords.filter((k) => !drop.has(k.toLowerCase())) };
    } else if (prop.action === "replace_keywords" && prop.keywords?.length) {
      next = { ...next, keywords: prop.keywords.slice(0, 12) };
    } else if (prop.action === "add_exclusions" && prop.excluded?.length) {
      const seen = new Set(next.excluded.map((k) => k.toLowerCase()));
      const merged = [...next.excluded];
      for (const ex of prop.excluded) {
        if (!seen.has(ex.toLowerCase()) && merged.length < 12) {
          seen.add(ex.toLowerCase());
          merged.push(ex);
        }
      }
      next = { ...next, excluded: merged };
    } else if (prop.action === "set_intent_categories" && prop.categories) {
      next = { ...next, categories: prop.categories };
    } else if (prop.action === "select_sources" && prop.sources?.length) {
      next = { ...next, sources: [...new Set(prop.sources)] as SourceId[] };
    } else if (prop.action === "choose_icp") {
      next = { ...next, icp_id: prop.icp_id || null };
    } else if (prop.action === "update_filters") {
      next = {
        ...next,
        ...(prop.min_relevance !== null && prop.min_relevance !== undefined
          ? { min_relevance: prop.min_relevance }
          : {}),
        ...(prop.result_limit !== null && prop.result_limit !== undefined
          ? { result_limit: prop.result_limit }
          : {}),
        ...(prop.from_date !== undefined ? { from_date: prop.from_date } : {}),
        ...(prop.to_date !== undefined ? { to_date: prop.to_date } : {}),
      };
    } else if (prop.action === "suggest_search_configuration" && prop.configuration) {
      next = {
        ...next,
        ...prop.configuration,
        semantic: next.semantic,
      };
    }
  }
  return next;
}

function proposalItems(prop: CopilotProposal): string[] {
  if (prop.action === "add_keywords" || prop.action === "replace_keywords" || prop.action === "remove_keywords") {
    return prop.keywords || [];
  }
  if (prop.action === "add_exclusions") return prop.excluded || [];
  if (prop.action === "select_sources") return (prop.sources || []).map((s) => s.replace("_", " "));
  if (prop.action === "set_intent_categories") return prop.categories || [];
  if (prop.action === "suggest_search_configuration" && prop.configuration) {
    return (prop.configuration.keywords || []).slice(0, 5);
  }
  return [];
}

function proposalDiffLine(draft: IntentSearch, prop: CopilotProposal): string {
  if (prop.action === "add_keywords") return `Add keywords: ${(prop.keywords || []).join(", ")}`;
  if (prop.action === "remove_keywords") return `Remove keywords: ${(prop.keywords || []).join(", ")}`;
  if (prop.action === "replace_keywords") {
    return `Replace [${draft.keywords.join(", ") || "empty"}] → [${(prop.keywords || []).join(", ")}]`;
  }
  if (prop.action === "add_exclusions") return `Exclude: ${(prop.excluded || []).join(", ")}`;
  if (prop.action === "select_sources") {
    return `Sources: ${(draft.sources ?? ["hacker_news"]).join(", ")} → ${(prop.sources || []).join(", ")}`;
  }
  if (prop.action === "set_intent_categories") return `Categories → ${(prop.categories || []).join(", ") || "All"}`;
  if (prop.action === "choose_icp") return prop.icp_id ? "Align search with selected workspace ICP" : "Clear ICP filter";
  if (prop.action === "update_filters") {
    const parts: string[] = [];
    if (prop.min_relevance !== null && prop.min_relevance !== undefined) parts.push(`min relevance ${prop.min_relevance}`);
    if (prop.result_limit !== null && prop.result_limit !== undefined) parts.push(`limit ${prop.result_limit}`);
    return parts.join(" · ") || "Update filters";
  }
  if (prop.action === "suggest_search_configuration" && prop.configuration) {
    return `Set ${(prop.configuration.keywords || []).length} keywords across ${(prop.configuration.sources || []).join(", ")}`;
  }
  return prop.label;
}

/** Safe inline markdown formatter (bold, code, safe https links — no raw HTML). */
function renderInline(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|https:\/\/[^\s)]+)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={i} className="font-semibold text-foreground">{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      return (
        <code key={i} className="rounded bg-muted px-1 py-0.5 font-mono text-[12px] text-foreground">
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith("https://")) {
      return (
        <a
          key={i}
          href={part}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary underline break-all hover:opacity-80"
        >
          {part}
        </a>
      );
    }
    return <Fragment key={i}>{part}</Fragment>;
  });
}

function SafeMarkdown({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/).filter((b) => b.trim());
  return (
    <div className="space-y-2 text-[13px] leading-relaxed text-foreground break-words">
      {blocks.map((block, idx) => {
        const lines = block.split("\n").map((l) => l.trim()).filter(Boolean);
        const isList = lines.length > 0 && lines.every((l) => /^[-*•]\s+/.test(l));
        if (isList) {
          return (
            <ul key={idx} className="list-disc pl-4 space-y-1">
              {lines.map((l, li) => (
                <li key={li}>{renderInline(l.replace(/^[-*•]\s+/, ""))}</li>
              ))}
            </ul>
          );
        }
        return (
          <p key={idx} className="whitespace-pre-wrap">
            {renderInline(block)}
          </p>
        );
      })}
    </div>
  );
}

export function DiscoveryCopilotPanel({
  open,
  onClose,
  draft,
  originalPrompt,
  activeRunId,
  resultCount,
  aiExhausted,
  canWrite,
  externalTrigger,
  onClearExternalTrigger,
  onApplyDraft,
  onUpdateStrategy,
}: {
  open: boolean;
  onClose: () => void;
  draft: IntentSearch;
  originalPrompt: string;
  activeRunId: string | null;
  resultCount?: number | null;
  aiExhausted: boolean;
  canWrite: boolean;
  externalTrigger: { action: CopilotQuickAction; message: string; nonce: number } | null;
  onClearExternalTrigger: () => void;
  onApplyDraft: (next: IntentSearch) => void;
  onUpdateStrategy: (strategy: SearchStrategy) => void;
}) {
  const ctxQuery = useRadarRead<DiscoveryContextSummary>(
    `/discover/context${draft.icp_id ? `?icp_id=${draft.icp_id}` : ""}`
  );
  const mutation = useRadarMutation();

  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ThreadEntry[]>([]);
  const [selectedIds, setSelectedIds] = useState<Record<string, boolean>>({});
  const [expandedDiffs, setExpandedDiffs] = useState<Record<string, boolean>>({});
  const [showContextDetails, setShowContextDetails] = useState(false);
  const [undoSnapshot, setUndoSnapshot] = useState<IntentSearch | null>(null);
  const [quotaReached, setQuotaReached] = useState(false);
  const [errorState, setErrorState] = useState<{ message: string; retryText: string; retryAction?: CopilotQuickAction } | null>(null);
  const [lastContext, setLastContext] = useState<DiscoveryContextSummary | null>(null);

  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  const userScrolledUpRef = useRef(false);
  const inFlightRef = useRef(false);
  const reqSeqRef = useRef(0);

  const currentDraftKey = useMemo(() => computeDraftKey(draft), [draft]);
  const summary = lastContext || ctxQuery.data || null;
  const isQuotaBlocked = aiExhausted || quotaReached;

  const [isDesktop, setIsDesktop] = useState(true);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const update = () => setIsDesktop(window.innerWidth >= 1024);
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  // Escape closes mobile drawer cleanly
  useEffect(() => {
    if (!open || isDesktop) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, isDesktop, onClose]);

  async function askCopilot(message: string, quickAction?: CopilotQuickAction) {
    const trimmed = message.trim();
    if (!trimmed || inFlightRef.current || mutation.isPending || !canWrite || isQuotaBlocked) return;

    inFlightRef.current = true;
    const mySeq = ++reqSeqRef.current;
    setErrorState(null);

    const userEntry: ThreadEntry = {
      id: `u-${Date.now()}-${mySeq}`,
      role: "user",
      content: trimmed,
    };
    const historyForApi = messages.slice(-6).map((m) => ({
      role: m.role,
      content: m.content,
    }));
    const prevInput = input;
    setMessages((prev) => [...prev, userEntry]);
    setInput("");
    userScrolledUpRef.current = false;

    try {
      const draftKeyBefore = computeDraftKey(draft);
      const res = (await mutation.mutateAsync({
        path: "/discover/copilot",
        body: {
          message: trimmed,
          quick_action: quickAction || null,
          draft: draft.keywords.length ? draft : null,
          original_prompt: originalPrompt,
          icp_id: draft.icp_id || null,
          active_run_id: activeRunId || null,
          history: historyForApi,
        },
      })) as CopilotResponse;

      if (mySeq !== reqSeqRef.current) return;

      if (!res || typeof res.reply !== "string") {
        throw new Error("Received an unexpected response format from Discovery Copilot.");
      }

      if (res.context_summary) setLastContext(res.context_summary);
      if (res.quota_exhausted) setQuotaReached(true);
      if (res.strategy) onUpdateStrategy(res.strategy);

      const entryId = `a-${Date.now()}-${mySeq}`;
      const defaults: Record<string, boolean> = {};
      for (const p of res.proposals || []) {
        defaults[`${entryId}:${p.id}`] = true;
      }
      setSelectedIds((prev) => ({ ...prev, ...defaults }));
      setMessages((prev) => [
        ...prev,
        {
          id: entryId,
          role: "assistant",
          content: res.reply,
          mode: res.mode,
          warnings: res.warnings,
          proposals: res.proposals,
          draftFingerprint: draftKeyBefore,
          appliedIds: [],
        },
      ]);
    } catch (e) {
      if (mySeq !== reqSeqRef.current) return;
      const errMsg = e instanceof Error ? e.message : "Discovery Copilot could not respond.";
      if (/quota|allowance|exhausted|429/i.test(errMsg)) {
        setQuotaReached(true);
      }
      // Preserve user's typed message on failure so they can retry cleanly
      if (prevInput.trim()) setInput(prevInput);
      setErrorState({ message: errMsg, retryText: trimmed, retryAction: quickAction });
    } finally {
      inFlightRef.current = false;
    }
  }

  useEffect(() => {
    if (!externalTrigger) return;
    const { action, message } = externalTrigger;
    onClearExternalTrigger();
    void askCopilot(message, action);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [externalTrigger?.nonce]);

  useEffect(() => {
    if (!userScrolledUpRef.current && typeof endRef.current?.scrollIntoView === "function") {
      endRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [messages.length, mutation.isPending]);

  function handleScroll() {
    const el = scrollContainerRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 64;
    userScrolledUpRef.current = !nearBottom;
  }

  function applyProposals(entry: ThreadEntry, onlySelected: boolean) {
    const props = (entry.proposals || []).filter((p) => {
      if (entry.appliedIds?.includes(p.id)) return false;
      return onlySelected ? selectedIds[`${entry.id}:${p.id}`] !== false : true;
    });
    if (!props.length) return;
    setUndoSnapshot(draft);
    const next = applyProposalsToDraft(draft, props);
    onApplyDraft(next);
    const nextApplied = [...(entry.appliedIds || []), ...props.map((p) => p.id)];
    const allDone = (entry.proposals || []).every((p) => nextApplied.includes(p.id));
    setMessages((prev) =>
      prev.map((m) =>
        m.id === entry.id
          ? { ...m, appliedIds: nextApplied, appliedAll: allDone }
          : m
      )
    );
  }

  function dismissProposals(entryId: string) {
    setMessages((prev) =>
      prev.map((m) => (m.id === entryId ? { ...m, dismissed: true } : m))
    );
  }

  function handleUndo() {
    if (!undoSnapshot) return;
    onApplyDraft(undoSnapshot);
    setUndoSnapshot(null);
  }

  // Context-aware primary quick actions (only 3 visible + More dropdown)
  const primaryQuickActions: { id: CopilotQuickAction; label: string; prompt: string }[] = [
    draft.keywords.length === 0
      ? {
          id: "improve_keywords",
          label: "Generate keywords",
          prompt: "Generate specific, high-intent B2B discovery keywords based on my company profile and workspace context.",
        }
      : {
          id: "improve_keywords",
          label: "Improve keywords",
          prompt: "Improve my search keywords with sharper B2B phrases and remove generic terms.",
        },
    {
      id: "suggest_sources",
      label: "Suggest sources",
      prompt: "Review my selected sources and suggest the best available sources in this workspace.",
    },
    activeRunId && resultCount === 0
      ? {
          id: "broaden_search",
          label: "Broaden search",
          prompt: "My last search returned no results. Suggest broader keywords or additional sources.",
        }
      : {
          id: "exclude_noise",
          label: "Exclude noise",
          prompt: "Suggest negative exclusions to remove recruiting posts, tutorials, and irrelevant chatter.",
        },
  ];

  const contextOneLiner = summary
    ? [
        summary.has_company_profile ? summary.company_name || "Company profile" : "Workspace",
        `${summary.available_source_count} sources available`,
        summary.selected_icp_name ? `ICP: ${summary.selected_icp_name}` : "No ICP selected",
      ].join(" · ")
    : "Loading workspace context…";

  // Keep component mounted when closed so conversation history, input, and Undo state survive close/reopen!
  if (!open) {
    return <div id="discovery-copilot-panel" hidden aria-hidden="true" />;
  }

  const panelBody = (
    <div
      id="discovery-copilot-panel"
      className="flex h-full lg:h-[calc(100vh-7.5rem)] lg:max-h-[820px] flex-col rounded-2xl border border-border bg-card shadow-sm overflow-hidden"
    >
      {/* 1. Compact Header */}
      <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-3 shrink-0">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 text-primary shrink-0">
            <Sparkles size={15} aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-foreground leading-tight truncate">
              Discovery Copilot
            </h2>
            <p className="text-[11px] text-muted-foreground leading-tight truncate">
              AI research assistant
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {undoSnapshot && (
            <button
              type="button"
              onClick={handleUndo}
              className="inline-flex items-center gap-1 rounded-lg border border-border bg-background px-2 py-1 text-xs font-medium text-foreground hover:border-primary/50 hover:text-primary transition-colors cursor-pointer"
              title="Undo last Copilot change"
            >
              <RotateCcw size={12} aria-hidden="true" />
              Undo
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            aria-label="Close Discovery Copilot"
            title="Close Discovery Copilot"
            className="inline-flex h-7 w-7 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <X size={15} aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* 2. Compact Single-Line Context Indicator */}
      <div className="border-b border-border/70 bg-muted/20 px-4 py-2 shrink-0">
        <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
          <span className="truncate">{contextOneLiner}</span>
          <button
            type="button"
            aria-expanded={showContextDetails}
            onClick={() => setShowContextDetails((v) => !v)}
            className="inline-flex items-center gap-0.5 text-[11px] font-medium text-primary hover:underline shrink-0 cursor-pointer"
          >
            Details
            {showContextDetails ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
        </div>
        {showContextDetails && (
          <div className="mt-2 space-y-1 border-t border-border/60 pt-2 text-[11px] text-muted-foreground">
            <p>
              <strong className="text-foreground">Company:</strong>{" "}
              {summary?.has_company_profile ? summary.company_name : "Not configured"}
            </p>
            <p>
              <strong className="text-foreground">ICP:</strong>{" "}
              {summary?.selected_icp_name || "No ICP selected — Copilot still uses your company profile and source catalog."}
            </p>
            <p>
              <strong className="text-foreground">Workspace history:</strong>{" "}
              {summary?.recent_run_count ?? 0} recent runs indexed
            </p>
          </div>
        )}
      </div>

      {/* Context-Aware Quick Actions (3 primary + More menu) */}
      <div className="flex flex-wrap items-center gap-1.5 border-b border-border/70 px-4 py-2 shrink-0">
        {primaryQuickActions.map((qa) => (
          <button
            key={qa.id}
            type="button"
            disabled={mutation.isPending || !canWrite || isQuotaBlocked}
            onClick={() => void askCopilot(qa.prompt, qa.id)}
            className="rounded-lg border border-border bg-background px-2.5 py-1 text-xs font-medium text-foreground hover:border-primary/50 hover:text-primary transition-colors disabled:opacity-45 disabled:cursor-not-allowed cursor-pointer"
          >
            {qa.label}
          </button>
        ))}

        <Menu.Root>
          <Menu.Trigger asChild>
            <button
              type="button"
              disabled={mutation.isPending || !canWrite || isQuotaBlocked}
              aria-label="More Copilot actions"
              className="inline-flex items-center gap-1 rounded-lg border border-border bg-background px-2 py-1 text-xs font-medium text-muted-foreground hover:border-primary/50 hover:text-foreground transition-colors disabled:opacity-45 cursor-pointer"
            >
              <MoreHorizontal size={13} aria-hidden="true" />
              <span>More</span>
            </button>
          </Menu.Trigger>
          <MenuContent align="end" className="w-56 p-1 text-xs">
            <Menu.Item
              onSelect={() =>
                void askCopilot(
                  "Broaden my discovery search to capture adjacent buyer pain points and alternatives.",
                  "broaden_search"
                )
              }
              className="rounded-md px-2.5 py-1.5 cursor-pointer hover:bg-muted outline-none"
            >
              Broaden search
            </Menu.Item>
            <Menu.Item
              onSelect={() =>
                void askCopilot(
                  "Narrow my search to higher commercial intent and product evaluation signals.",
                  "narrow_search"
                )
              }
              className="rounded-md px-2.5 py-1.5 cursor-pointer hover:bg-muted outline-none"
            >
              Narrow search
            </Menu.Item>
            <Menu.Item
              onSelect={() =>
                void askCopilot(
                  "Explain the strengths, weaknesses, and coverage tradeoffs of my current search draft.",
                  "explain_strategy"
                )
              }
              className="rounded-md px-2.5 py-1.5 cursor-pointer hover:bg-muted outline-none"
            >
              Explain strategy
            </Menu.Item>
            {activeRunId && (
              <Menu.Item
                onSelect={() =>
                  void askCopilot(
                    "Refine my search criteria based on the latest discovery run results.",
                    "refine_after_results"
                  )
                }
                className="rounded-md px-2.5 py-1.5 cursor-pointer hover:bg-muted outline-none font-medium text-primary"
              >
                Refine after results
              </Menu.Item>
            )}
            <Menu.Separator className="my-1 h-px bg-border" />
            {summary && summary.icp_count > 0 ? (
              <Menu.Item
                onSelect={() =>
                  void askCopilot(
                    "Align this search with my workspace company profile and ideal customer profile.",
                    "align_icp"
                  )
                }
                className="rounded-md px-2.5 py-1.5 cursor-pointer hover:bg-muted outline-none"
              >
                Align with ICP
              </Menu.Item>
            ) : (
              <div className="px-2.5 py-1.5 text-[11px] text-muted-foreground space-y-1">
                <p>Set up an ICP to personalize research further.</p>
                <Link href="/settings/icp" className="text-primary font-medium hover:underline">
                  Configure ICP →
                </Link>
              </div>
            )}
          </MenuContent>
        </Menu.Root>
      </div>

      {/* Quota Exhausted Banner */}
      {isQuotaBlocked && (
        <div
          role="status"
          className="mx-4 mt-3 rounded-xl border border-amber-500/40 bg-amber-500/10 p-3 text-xs space-y-1 shrink-0"
        >
          <div className="flex items-start gap-2">
            <AlertTriangle size={14} className="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
            <p className="text-foreground font-medium">
              Shared AI allowance exhausted. Manual keyword editing and search execution remain available.
            </p>
          </div>
          <Link
            href="/settings?category=billing&tab=overview"
            className="inline-block font-semibold text-primary hover:underline pl-5"
          >
            View Billing &amp; Usage →
          </Link>
        </div>
      )}

      {/* 3. Spacious Scrollable Conversation Area */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-4 py-4 space-y-4 min-h-[260px]"
      >
        {messages.length === 0 && (
          <div className="rounded-xl border border-dashed border-border bg-muted/15 p-4 text-[13px] text-muted-foreground space-y-1.5 leading-relaxed">
            <p className="font-semibold text-foreground">
              Refine your discovery search with Copilot
            </p>
            <p>
              Ask for sharper B2B phrases, noise exclusions, or source recommendations. Every suggestion stays reviewable until you click Apply.
            </p>
          </div>
        )}

        {messages.map((entry) => {
          const isStale =
            entry.role === "assistant" &&
            Boolean(entry.proposals?.length) &&
            !entry.dismissed &&
            !entry.appliedAll &&
            entry.draftFingerprint !== currentDraftKey;
          const pendingProps = (entry.proposals || []).filter(
            (p) => !entry.appliedIds?.includes(p.id)
          );
          const hasAppliedAny = Boolean(entry.appliedIds?.length);
          const showDiff = Boolean(expandedDiffs[entry.id]);

          if (entry.role === "user") {
            return (
              <div key={entry.id} className="flex justify-end">
                <div className="max-w-[88%] rounded-2xl rounded-br-sm bg-primary px-3.5 py-2.5 text-[13px] leading-relaxed text-primary-foreground whitespace-pre-wrap break-words">
                  {entry.content}
                </div>
              </div>
            );
          }

          return (
            <div key={entry.id} className="space-y-2.5">
              {/* Concise conversational explanation */}
              <div className="rounded-2xl rounded-bl-sm border border-border/80 bg-muted/20 px-3.5 py-3 space-y-2">
                <SafeMarkdown text={entry.content} />

                {entry.warnings && entry.warnings.length > 0 && (
                  <div className="flex items-start gap-2 rounded-lg border border-amber-500/35 bg-amber-500/10 p-2.5 text-xs text-amber-900 dark:text-amber-200">
                    <Info size={13} className="shrink-0 mt-0.5" />
                    <div className="space-y-0.5">
                      {entry.warnings.map((w, i) => (
                        <p key={i}>{w}</p>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Clean, Compact Suggested Changes Card */}
              {entry.proposals && entry.proposals.length > 0 && !entry.dismissed && (
                pendingProps.length === 0 && hasAppliedAny ? (
                  <div className="flex items-center justify-between gap-2 rounded-xl border border-border bg-muted/25 px-3 py-2 text-xs">
                    <span className="inline-flex items-center gap-1.5 font-medium text-foreground">
                      <Check size={13} className="text-emerald-600 dark:text-emerald-400" />
                      Changes applied to search.
                    </span>
                    {undoSnapshot && (
                      <button
                        type="button"
                        onClick={handleUndo}
                        className="font-semibold text-primary hover:underline cursor-pointer"
                      >
                        Undo
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="rounded-xl border border-border bg-card p-3 space-y-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold text-foreground">
                        Suggested changes ({pendingProps.length})
                      </span>
                      <button
                        type="button"
                        onClick={() =>
                          setExpandedDiffs((prev) => ({ ...prev, [entry.id]: !prev[entry.id] }))
                        }
                        className="text-[11px] font-medium text-primary hover:underline cursor-pointer"
                      >
                        {showDiff ? "Hide changes" : "View changes"}
                      </button>
                    </div>

                    {isStale && (
                      <p className="text-[11px] text-amber-700 dark:text-amber-300">
                        Your search draft changed since this suggestion was generated. Review before applying.
                      </p>
                    )}

                    {/* Selectable clean proposal list with readable chips */}
                    <div className="space-y-2">
                      {pendingProps.map((prop) => {
                        const checked = selectedIds[`${entry.id}:${prop.id}`] !== false;
                        const items = proposalItems(prop);
                        return (
                          <label
                            key={prop.id}
                            className="flex items-start gap-2.5 rounded-lg border border-border/70 bg-muted/15 p-2.5 text-xs hover:border-primary/40 transition-colors cursor-pointer"
                          >
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={(e) =>
                                setSelectedIds((prev) => ({
                                  ...prev,
                                  [`${entry.id}:${prop.id}`]: e.target.checked,
                                }))
                              }
                              className="mt-0.5 accent-primary shrink-0"
                            />
                            <div className="min-w-0 flex-1 space-y-1.5">
                              <div className="font-semibold text-foreground leading-snug">
                                {prop.label}
                              </div>
                              {items.length > 0 && (
                                <div className="flex flex-wrap gap-1">
                                  {items.map((chip) => (
                                    <span
                                      key={chip}
                                      className="rounded-md border border-border bg-card px-2 py-0.5 text-[11px] font-medium text-foreground"
                                    >
                                      {chip}
                                    </span>
                                  ))}
                                </div>
                              )}
                              {showDiff && (
                                <p className="text-[11px] text-muted-foreground font-mono break-words">
                                  {proposalDiffLine(draft, prop)}
                                </p>
                              )}
                            </div>
                          </label>
                        );
                      })}
                    </div>

                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      <Button
                        size="sm"
                        onClick={() => applyProposals(entry, true)}
                        className="h-7 px-3 text-xs"
                      >
                        Apply Selected
                      </Button>
                      {pendingProps.length > 1 && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => applyProposals(entry, false)}
                          className="h-7 px-2.5 text-xs"
                        >
                          Apply All
                        </Button>
                      )}
                      <button
                        type="button"
                        onClick={() => dismissProposals(entry.id)}
                        className="ml-auto text-xs text-muted-foreground hover:text-foreground cursor-pointer"
                      >
                        Dismiss
                      </button>
                    </div>
                  </div>
                )
              )}

              {entry.dismissed && (
                <p className="text-[11px] text-muted-foreground pl-1">Suggestions dismissed.</p>
              )}
            </div>
          );
        })}

        {/* Honest loading state tied to active mutation */}
        {mutation.isPending && (
          <div
            role="status"
            aria-live="polite"
            className="flex items-center gap-2 rounded-xl border border-border/80 bg-muted/20 px-3.5 py-2.5 text-xs text-muted-foreground"
          >
            <Loader2 size={14} className="animate-spin text-primary shrink-0" />
            <span>Drafting recommendations…</span>
          </div>
        )}

        {/* Recoverable error banner with Retry */}
        {errorState && (
          <div
            role="alert"
            className="rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive space-y-2"
          >
            <p>{errorState.message}</p>
            {!isQuotaBlocked && (
              <button
                type="button"
                onClick={() => void askCopilot(errorState.retryText, errorState.retryAction)}
                className="inline-flex items-center gap-1 font-semibold underline cursor-pointer"
              >
                <RefreshCw size={12} /> Retry
              </button>
            )}
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* 4. Fixed Bottom Composer */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void askCopilot(input);
        }}
        className="border-t border-border bg-card p-3 space-y-1.5 shrink-0"
      >
        <div className="flex items-end gap-2">
          <textarea
            rows={2}
            value={input}
            maxLength={1500}
            disabled={!canWrite || mutation.isPending || isQuotaBlocked}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void askCopilot(input);
              }
            }}
            placeholder={
              isQuotaBlocked
                ? "AI allowance exhausted — edit criteria manually"
                : "Ask Copilot to refine keywords, sources, or exclusions…"
            }
            className="flex-1 resize-none rounded-xl border border-border bg-background px-3 py-2 text-[13px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-60"
          />
          <Button
            type="submit"
            size="sm"
            disabled={!input.trim() || mutation.isPending || !canWrite || isQuotaBlocked}
            aria-label="Send message to Discovery Copilot"
            className="h-9 px-3 shrink-0"
          >
            {mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
          </Button>
        </div>
        <p className="text-[11px] text-muted-foreground">
          Enter to send · Shift+Enter for new line · 1 shared AI op/request
        </p>
      </form>
    </div>
  );

  if (isDesktop) {
    return (
      <aside aria-label="Discovery Copilot" className="sticky top-6 self-start">
        {panelBody}
      </aside>
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/45 backdrop-blur-[1px]"
      role="dialog"
      aria-modal="true"
      aria-label="Discovery Copilot"
      onClick={onClose}
    >
      <div
        className="h-full w-full max-w-md p-3 bg-background"
        onClick={(e) => e.stopPropagation()}
      >
        {panelBody}
      </div>
    </div>
  );
}
