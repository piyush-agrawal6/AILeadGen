"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Building2,
  Check,
  History,
  Loader2,
  RotateCcw,
  Send,
  Sparkles,
  Target,
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
};

const QUICK_ACTIONS: { id: CopilotQuickAction; label: string; prompt: string }[] = [
  { id: "improve_keywords", label: "Improve keywords", prompt: "Improve my search keywords with specific high-intent B2B phrases and remove generic terms." },
  { id: "suggest_sources", label: "Suggest sources", prompt: "Suggest the best available sources in my workspace for this discovery topic." },
  { id: "exclude_noise", label: "Exclude noise", prompt: "Suggest negative exclusions to remove hiring posts, tutorials, and irrelevant noise." },
  { id: "align_icp", label: "Align with ICP", prompt: "Align this search with my workspace company profile and ideal customer profile." },
  { id: "broaden_search", label: "Broaden", prompt: "Broaden my discovery search to capture adjacent buyer pain points and alternatives." },
  { id: "narrow_search", label: "Narrow", prompt: "Narrow my search to focus on higher commercial intent and product evaluation signals." },
  { id: "explain_strategy", label: "Explain strategy", prompt: "Explain the strengths, weaknesses, and coverage tradeoffs of my current search draft." },
];

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

function proposalDiffPreview(draft: IntentSearch, prop: CopilotProposal): string {
  if (prop.action === "add_keywords") {
    return `+ Add ${(prop.keywords || []).join(", ")}`;
  }
  if (prop.action === "remove_keywords") {
    return `- Remove ${(prop.keywords || []).join(", ")}`;
  }
  if (prop.action === "replace_keywords") {
    return `Keywords: [${draft.keywords.join(", ") || "none"}] → [${(prop.keywords || []).join(", ")}]`;
  }
  if (prop.action === "add_exclusions") {
    return `+ Exclude ${(prop.excluded || []).join(", ")}`;
  }
  if (prop.action === "select_sources") {
    const before = (draft.sources ?? ["hacker_news"]).join(", ");
    return `Sources: ${before} → ${(prop.sources || []).join(", ")}`;
  }
  if (prop.action === "set_intent_categories") {
    return `Categories → ${(prop.categories || []).join(", ") || "All"}`;
  }
  if (prop.action === "choose_icp") {
    return prop.icp_id ? "Align search with selected workspace ICP" : "Clear ICP filter";
  }
  if (prop.action === "update_filters") {
    const parts: string[] = [];
    if (prop.min_relevance !== null && prop.min_relevance !== undefined) parts.push(`min relevance ${prop.min_relevance}`);
    if (prop.result_limit !== null && prop.result_limit !== undefined) parts.push(`limit ${prop.result_limit}`);
    return parts.join(" · ") || "Update search filters";
  }
  if (prop.action === "suggest_search_configuration" && prop.configuration) {
    return `Draft: ${(prop.configuration.keywords || []).slice(0, 4).join(", ")} across ${(prop.configuration.sources || []).join(", ")}`;
  }
  return prop.label;
}

export function DiscoveryCopilotPanel({
  draft,
  originalPrompt,
  activeRunId,
  aiExhausted,
  canWrite,
  externalTrigger,
  onClearExternalTrigger,
  onApplyDraft,
  onUpdateStrategy,
  mobileOpen,
  onCloseMobile,
}: {
  draft: IntentSearch;
  originalPrompt: string;
  activeRunId: string | null;
  aiExhausted: boolean;
  canWrite: boolean;
  externalTrigger: { action: CopilotQuickAction; message: string; nonce: number } | null;
  onClearExternalTrigger: () => void;
  onApplyDraft: (next: IntentSearch) => void;
  onUpdateStrategy: (strategy: SearchStrategy) => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}) {
  const ctxQuery = useRadarRead<DiscoveryContextSummary>(
    `/discover/context${draft.icp_id ? `?icp_id=${draft.icp_id}` : ""}`
  );
  const mutation = useRadarMutation();

  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ThreadEntry[]>([]);
  const [selectedIds, setSelectedIds] = useState<Record<string, boolean>>({});
  const [undoSnapshot, setUndoSnapshot] = useState<IntentSearch | null>(null);
  const [quotaReached, setQuotaReached] = useState(false);
  const [error, setError] = useState("");
  const [lastContext, setLastContext] = useState<DiscoveryContextSummary | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  const currentDraftKey = useMemo(() => computeDraftKey(draft), [draft]);
  const summary = lastContext || ctxQuery.data || null;

  async function askCopilot(message: string, quickAction?: CopilotQuickAction) {
    const trimmed = message.trim();
    if (!trimmed || mutation.isPending || !canWrite) return;
    setError("");
    const userEntry: ThreadEntry = {
      id: `u-${Date.now()}`,
      role: "user",
      content: trimmed,
    };
    const historyForApi = messages.slice(-6).map((m) => ({
      role: m.role,
      content: m.content,
    }));
    setMessages((prev) => [...prev, userEntry]);
    setInput("");

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

      if (res.context_summary) setLastContext(res.context_summary);
      if (res.quota_exhausted) setQuotaReached(true);
      if (res.strategy) onUpdateStrategy(res.strategy);

      const entryId = `a-${Date.now()}`;
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
      setError(e instanceof Error ? e.message : "Discovery Copilot could not respond.");
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
    if (typeof endRef.current?.scrollIntoView === "function") {
      endRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [messages.length]);

  function applyProposals(entry: ThreadEntry, onlySelected: boolean) {
    const props = (entry.proposals || []).filter((p) => {
      if (entry.appliedIds?.includes(p.id)) return false;
      return onlySelected ? selectedIds[`${entry.id}:${p.id}`] !== false : true;
    });
    if (!props.length) return;
    setUndoSnapshot(draft);
    const next = applyProposalsToDraft(draft, props);
    onApplyDraft(next);
    setMessages((prev) =>
      prev.map((m) =>
        m.id === entry.id
          ? { ...m, appliedIds: [...(m.appliedIds || []), ...props.map((p) => p.id)] }
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

  const panelBody = (
    <div className="flex h-full flex-col rounded-2xl border border-border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-3.5 bg-gradient-to-r from-primary/[0.06] to-transparent">
        <div className="flex items-center gap-2 min-w-0">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/15 text-primary shrink-0">
            <Sparkles size={15} aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-foreground truncate">
              Discovery Copilot
            </h2>
            <p className="text-[11px] text-muted-foreground truncate">
              Context-aware search strategist
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {undoSnapshot && (
            <button
              type="button"
              onClick={handleUndo}
              className="inline-flex items-center gap-1 rounded-lg border border-border bg-background px-2 py-1 text-[11px] font-medium text-foreground hover:border-primary/50 hover:text-primary cursor-pointer"
              title="Undo last Copilot draft change"
            >
              <RotateCcw size={11} /> Undo
            </button>
          )}
          <button
            type="button"
            onClick={onCloseMobile}
            aria-label="Close Discovery Copilot"
            className="lg:hidden rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground cursor-pointer"
          >
            <X size={15} />
          </button>
        </div>
      </div>

      {/* Workspace Context Badges */}
      <div className="flex flex-wrap items-center gap-1.5 border-b border-border/80 bg-muted/20 px-4 py-2.5 text-[10px]">
        <span className="inline-flex items-center gap-1 rounded-full border border-border bg-card px-2 py-0.5 text-muted-foreground">
          <Building2 size={10} className="text-primary" aria-hidden="true" />
          {summary?.has_company_profile ? summary.company_name || "Company profile" : "No company profile"}
        </span>
        <span className="inline-flex items-center gap-1 rounded-full border border-border bg-card px-2 py-0.5 text-muted-foreground">
          <Target size={10} className="text-primary" aria-hidden="true" />
          {summary?.selected_icp_name ? `ICP: ${summary.selected_icp_name}` : "No ICP active"}
        </span>
        <span className="inline-flex items-center gap-1 rounded-full border border-border bg-card px-2 py-0.5 text-muted-foreground">
          {summary ? `${summary.available_source_count} sources ready` : "Workspace sources"}
        </span>
        {summary && summary.recent_run_count > 0 && (
          <span className="inline-flex items-center gap-1 rounded-full border border-border bg-card px-2 py-0.5 text-muted-foreground">
            <History size={10} aria-hidden="true" />
            {summary.recent_run_count} recent
          </span>
        )}
      </div>

      {/* Quota Exhausted Banner */}
      {(aiExhausted || quotaReached) && (
        <div
          role="status"
          className="mx-3 mt-3 rounded-xl border border-amber-500/40 bg-amber-500/10 p-3 text-[11px] space-y-1.5"
        >
          <div className="flex items-start gap-2">
            <AlertTriangle size={13} className="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
            <p className="text-foreground font-medium">
              Shared AI allowance exhausted. Manual keyword editing and search execution remain available.
            </p>
          </div>
          <Link
            href="/settings?category=billing&tab=overview"
            className="inline-block font-semibold text-primary hover:underline"
          >
            View Billing &amp; Usage →
          </Link>
        </div>
      )}

      {/* Quick Action Chips */}
      <div className="border-b border-border/70 px-3.5 py-2.5">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
          Quick Actions
        </p>
        <div className="flex flex-wrap gap-1.5">
          {QUICK_ACTIONS.map((qa) => (
            <button
              key={qa.id}
              type="button"
              disabled={mutation.isPending || !canWrite}
              onClick={() => void askCopilot(qa.prompt, qa.id)}
              className="rounded-full border border-border bg-muted/30 px-2.5 py-1 text-[11px] font-medium text-foreground hover:border-primary/50 hover:bg-primary/10 hover:text-primary transition-colors disabled:opacity-50 cursor-pointer"
            >
              {qa.label}
            </button>
          ))}
          {activeRunId && (
            <button
              type="button"
              disabled={mutation.isPending || !canWrite}
              onClick={() =>
                void askCopilot(
                  "Refine my search criteria based on the latest discovery run results.",
                  "refine_after_results"
                )
              }
              className="rounded-full border border-primary/40 bg-primary/10 px-2.5 py-1 text-[11px] font-semibold text-primary hover:bg-primary/15 transition-colors disabled:opacity-50 cursor-pointer"
            >
              Refine after results
            </button>
          )}
        </div>
      </div>

      {/* Conversation Thread */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-[240px] max-h-[520px]">
        {messages.length === 0 && (
          <div className="rounded-xl border border-dashed border-border bg-muted/20 p-4 text-xs text-muted-foreground space-y-2">
            <p className="font-semibold text-foreground">
              Ask Copilot to sharpen your discovery search
            </p>
            <p className="leading-relaxed">
              Copilot reads your workspace company profile, saved ICPs, and active sources to propose high-signal phrases, exclusions, and source mixes. Nothing changes until you click Apply.
            </p>
          </div>
        )}

        {messages.map((entry) => {
          const isStale =
            entry.role === "assistant" &&
            Boolean(entry.proposals?.length) &&
            !entry.dismissed &&
            entry.draftFingerprint !== currentDraftKey;
          const pendingProps = (entry.proposals || []).filter(
            (p) => !entry.appliedIds?.includes(p.id)
          );

          return (
            <div
              key={entry.id}
              className={
                entry.role === "user"
                  ? "ml-6 rounded-xl bg-primary px-3.5 py-2.5 text-xs text-primary-foreground"
                  : "mr-2 rounded-xl border border-border bg-muted/25 px-3.5 py-3 text-xs space-y-2.5"
              }
            >
              <div className="whitespace-pre-wrap leading-relaxed">{entry.content}</div>

              {entry.warnings && entry.warnings.length > 0 && (
                <div className="rounded-lg border border-amber-500/35 bg-amber-500/10 p-2 text-[11px] text-amber-800 dark:text-amber-200 space-y-0.5">
                  {entry.warnings.map((w, i) => (
                    <p key={i}>{w}</p>
                  ))}
                </div>
              )}

              {/* Selectable Actionable Proposals */}
              {entry.role === "assistant" &&
                entry.proposals &&
                entry.proposals.length > 0 &&
                !entry.dismissed && (
                  <div className="space-y-2 pt-1 border-t border-border/70">
                    {isStale && pendingProps.length > 0 && (
                      <p className="text-[10px] font-medium text-amber-700 dark:text-amber-300">
                        Draft edited since this proposal was generated — review before applying.
                      </p>
                    )}

                    <div className="space-y-1.5">
                      {entry.proposals.map((prop) => {
                        const alreadyApplied = Boolean(entry.appliedIds?.includes(prop.id));
                        const checked = selectedIds[`${entry.id}:${prop.id}`] !== false;
                        return (
                          <label
                            key={prop.id}
                            className={
                              "flex items-start gap-2 rounded-lg border p-2.5 text-[11px] transition-colors " +
                              (alreadyApplied
                                ? "border-emerald-500/30 bg-emerald-500/10"
                                : "border-border bg-card hover:border-primary/40 cursor-pointer")
                            }
                          >
                            {alreadyApplied ? (
                              <Check size={13} className="text-emerald-600 shrink-0 mt-0.5" />
                            ) : (
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
                            )}
                            <div className="min-w-0 flex-1 space-y-0.5">
                              <div className="font-semibold text-foreground">{prop.label}</div>
                              <div className="text-primary font-medium break-words">
                                {proposalDiffPreview(draft, prop)}
                              </div>
                              {prop.rationale && (
                                <p className="text-muted-foreground leading-snug">{prop.rationale}</p>
                              )}
                            </div>
                          </label>
                        );
                      })}
                    </div>

                    {pendingProps.length > 0 ? (
                      <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
                        <Button
                          size="sm"
                          onClick={() => applyProposals(entry, true)}
                          className="h-7 px-2.5 text-[11px]"
                        >
                          Apply Selected
                        </Button>
                        {pendingProps.length > 1 && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => applyProposals(entry, false)}
                            className="h-7 px-2.5 text-[11px]"
                          >
                            Apply All
                          </Button>
                        )}
                        <button
                          type="button"
                          onClick={() => dismissProposals(entry.id)}
                          className="ml-auto text-[11px] text-muted-foreground hover:text-foreground cursor-pointer"
                        >
                          Dismiss
                        </button>
                      </div>
                    ) : (
                      <p className="text-[11px] font-medium text-emerald-700 dark:text-emerald-300">
                        Applied to search draft.
                      </p>
                    )}
                  </div>
                )}
            </div>
          );
        })}

        {mutation.isPending && (
          <div className="flex items-center gap-2 rounded-xl border border-border bg-muted/20 px-3.5 py-2.5 text-xs text-muted-foreground">
            <Loader2 size={13} className="animate-spin text-primary" />
            Thinking through your search strategy…
          </div>
        )}

        {error && (
          <div role="alert" className="rounded-xl border border-destructive/40 bg-destructive/10 p-2.5 text-[11px] text-destructive">
            {error}
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Composer */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void askCopilot(input);
        }}
        className="border-t border-border bg-muted/15 p-3 space-y-2"
      >
        <div className="flex items-end gap-2">
          <textarea
            rows={2}
            value={input}
            maxLength={1500}
            disabled={!canWrite || mutation.isPending}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void askCopilot(input);
              }
            }}
            placeholder="Ask Copilot to refine keywords, exclude noise, or target an ICP…"
            className="flex-1 resize-none rounded-xl border border-border bg-card px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
          <Button
            type="submit"
            size="sm"
            disabled={!input.trim() || mutation.isPending || !canWrite}
            aria-label="Send message to Discovery Copilot"
            className="h-9 px-3 shrink-0"
          >
            <Send size={13} />
          </Button>
        </div>
        <p className="text-[10px] text-muted-foreground">
          Each Copilot request uses 1 shared AI operation. Never auto-runs searches.
        </p>
      </form>
    </div>
  );

  return (
    <>
      {/* Desktop Sticky Right Rail (~30%) */}
      <aside aria-label="Discovery Copilot" className="hidden lg:block lg:sticky lg:top-6 self-start">
        {panelBody}
      </aside>

      {/* Mobile / Tablet Slide-Over Drawer */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-50 flex justify-end bg-black/45 backdrop-blur-[1px] lg:hidden"
          role="dialog"
          aria-modal="true"
          aria-label="Discovery Copilot"
          onClick={onCloseMobile}
        >
          <div
            className="h-full w-full max-w-md p-3 bg-background"
            onClick={(e) => e.stopPropagation()}
          >
            {panelBody}
          </div>
        </div>
      )}
    </>
  );
}
