"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowUpRight,
  Bookmark,
  CheckCheck,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  ExternalLink,
  Loader2,
  Sparkles,
  Target,
  X,
  XCircle,
} from "lucide-react";
import type { IntentSignal } from "@/lib/intent-radar";
import { ProviderLogo } from "../provider-logo";
import { SignalScore } from "../signals";
import { useRadarCapabilities, useRadarMutation } from "../provider";
import {
  buyingIntentDisplay,
  formatObservedDate,
  provenanceSummary,
  statusPillClasses,
} from "./signals-context";

interface SignalQuickDrawerProps {
  signal: IntentSignal | null;
  open: boolean;
  onClose: () => void;
  onPrev?: () => void;
  onNext?: () => void;
  hasPrev?: boolean;
  hasNext?: boolean;
  onBeforeOpenFull?: () => void;
  onOpenOpportunityModal: (signal: IntentSignal) => void;
  onStatusChanged?: (signal: IntentSignal, previousStatus: string, nextStatus: string) => void;
}

export function SignalQuickDrawer({
  signal,
  open,
  onClose,
  onPrev,
  onNext,
  hasPrev = false,
  hasNext = false,
  onBeforeOpenFull,
  onOpenOpportunityModal,
  onStatusChanged,
}: SignalQuickDrawerProps) {
  const access = useRadarCapabilities();
  const mutation = useRadarMutation();
  const [expandedExcerpt, setExpandedExcerpt] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setExpandedExcerpt(false);
    setError("");
  }, [signal?.id]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [open, onClose]);

  if (!open || !signal) return null;

  const canWrite = !!access.data?.can_write;
  const disabled = !canWrite || mutation.isPending || !!busyAction;
  const observed = formatObservedDate(signal.observed_at);
  const buying = buyingIntentDisplay(signal);
  const prov = provenanceSummary(signal);
  const excerptText = signal.excerpt || "";
  const isLongExcerpt = excerptText.length > 260;

  async function updateStatus(nextStatus: string) {
    if (!signal || disabled) return;
    setError("");
    setBusyAction(nextStatus);
    const prevStatus = signal.status;
    try {
      await mutation.mutateAsync({
        path: `/signals/${signal.id}`,
        method: "PATCH",
        body: { revision: signal.revision, status: nextStatus },
      });
      onStatusChanged?.(signal, prevStatus, nextStatus);
    } catch (e) {
      setError((e as Error).message || "Could not update signal status.");
    } finally {
      setBusyAction(null);
    }
  }

  async function toggleSave() {
    if (!signal || disabled) return;
    setError("");
    setBusyAction("save");
    try {
      await mutation.mutateAsync({
        path: `/saved/${signal.id}`,
        method: signal.saved ? "DELETE" : "POST",
      });
    } catch (e) {
      setError((e as Error).message || "Could not update bookmark.");
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/45 backdrop-blur-[1px]"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Quick signal review"
    >
      <aside
        className="flex h-full w-full max-w-xl flex-col border-l border-border bg-card shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top bar */}
        <div className="flex items-center justify-between gap-2 border-b border-border px-5 py-3.5 shrink-0">
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={onPrev}
              disabled={!hasPrev}
              aria-label="Previous signal"
              style={{ minHeight: "32px", padding: "4px 10px" }}
              className="inline-flex h-8 items-center gap-1 rounded-lg border border-border bg-background text-xs font-medium text-foreground hover:bg-muted disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
            >
              <ChevronLeft size={14} /> Prev
            </button>
            <button
              type="button"
              onClick={onNext}
              disabled={!hasNext}
              aria-label="Next signal"
              style={{ minHeight: "32px", padding: "4px 10px" }}
              className="inline-flex h-8 items-center gap-1 rounded-lg border border-border bg-background text-xs font-medium text-foreground hover:bg-muted disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
            >
              Next <ChevronRight size={14} />
            </button>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href={`/intent-radar/signals/${signal.id}`}
              onClick={() => onBeforeOpenFull?.()}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground hover:opacity-90"
            >
              Open Full Details <ArrowUpRight size={13} />
            </Link>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close quick review drawer"
              style={{ minHeight: "32px", width: "32px", padding: 0 }}
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-transparent text-muted-foreground hover:bg-muted hover:text-foreground cursor-pointer"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Single-column scrollable body */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
          {/* Header summary */}
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                <ProviderLogo provider={signal.source} size={18} />
                <span>{signal.source}</span>
              </span>
              {prov.repo && (
                <span className="rounded-md bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                  {prov.repo}
                </span>
              )}
              <span className="text-[11px] text-muted-foreground whitespace-nowrap" title={observed.full}>
                Observed {observed.short}
              </span>
            </div>

            <h2 className="text-lg font-semibold leading-snug text-foreground break-words">
              {signal.title}
            </h2>

            <div className="flex flex-wrap items-center gap-2">
              <SignalScore score={signal.score} />
              <span className="inline-flex items-center rounded-full border border-border bg-muted/40 px-2.5 py-0.5 text-[11px] font-medium text-foreground">
                {signal.category}
              </span>
              <span
                className={
                  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold " +
                  statusPillClasses(signal.status)
                }
              >
                {signal.status}
              </span>
              <span
                className={
                  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium " +
                  buying.tone
                }
                title={buying.label}
              >
                {buying.shortLabel}
              </span>
              {signal.saved && (
                <span className="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
                  <Bookmark size={11} fill="currentColor" /> Saved
                </span>
              )}
            </div>
          </div>

          {/* Concise Evidence Excerpt */}
          <section className="rounded-xl border border-border bg-muted/20 p-4 space-y-2.5">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Evidence excerpt
              </h3>
              {signal.source_url?.startsWith("http") && (
                <a
                  href={signal.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                >
                  Original source <ExternalLink size={12} />
                </a>
              )}
            </div>

            <p
              className={
                "text-sm leading-relaxed text-foreground/90 whitespace-pre-line break-words " +
                (!expandedExcerpt && isLongExcerpt ? "line-clamp-4" : "")
              }
            >
              {excerptText || "No body excerpt was supplied by the source. Open the original link to inspect full context."}
            </p>

            {isLongExcerpt && (
              <button
                type="button"
                onClick={() => setExpandedExcerpt((v) => !v)}
                className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline cursor-pointer"
              >
                {expandedExcerpt ? (
                  <>
                    Show less <ChevronUp size={13} />
                  </>
                ) : (
                  <>
                    Expand full excerpt <ChevronDown size={13} />
                  </>
                )}
              </button>
            )}

            <p className="text-[11px] text-muted-foreground">
              {prov.fetchLabel}
              {prov.contentKind ? ` · ${prov.contentKind}` : ""}
              {prov.author ? ` · Author: ${prov.author}` : ""}
            </p>
          </section>

          {/* Match Rationale */}
          <section className="rounded-xl border border-border bg-background p-4 space-y-2.5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Why this matched
            </h3>
            <p className="text-xs leading-relaxed text-foreground">
              {signal.evidence?.explanation || "Matched workspace discovery keywords."}
            </p>
            {signal.evidence?.matched_keywords && signal.evidence.matched_keywords.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {signal.evidence.matched_keywords.map((kw) => (
                  <span
                    key={kw}
                    className="rounded-md border border-border bg-muted/50 px-2 py-0.5 text-[11px] font-medium text-foreground"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            )}
            {signal.evidence?.intent_phrase && (
              <p className="text-xs text-muted-foreground">
                Matched phrase:{" "}
                <span className="font-medium text-foreground">“{signal.evidence.intent_phrase}”</span>
              </p>
            )}
          </section>

          {/* AI Summary snapshot (if analyzed) */}
          <section className="rounded-xl border border-border bg-background p-4 space-y-2">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Sparkles size={13} className="text-primary" />
                AI Intelligence
              </h3>
              <span className="text-[11px] text-muted-foreground">
                {signal.has_analysis ? signal.latest_analysis_mode || "Analyzed" : "Not yet analyzed"}
              </span>
            </div>
            {signal.has_analysis && signal.latest_analysis_summary ? (
              <div className="space-y-1.5">
                <p className="text-xs leading-relaxed text-foreground">{signal.latest_analysis_summary}</p>
                <p className="text-[11px] text-muted-foreground">
                  Buying intent: <strong className="text-foreground">{buying.label}</strong> · ICP fit:{" "}
                  <strong className="text-foreground">{signal.icp_fit || "Unassessed"}</strong>
                </p>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                Open Full Details to run evidence-grounded AI analysis, evaluate ICP fit, and inspect cited source quotes.
              </p>
            )}
          </section>

          {/* Opportunity readiness hint */}
          {signal.opportunity_id ? (
            <div className="flex items-center justify-between gap-3 rounded-xl border border-emerald-500/25 bg-emerald-500/[0.06] px-4 py-3">
              <div className="flex items-center gap-2 text-xs font-medium text-emerald-700 dark:text-emerald-300">
                <CheckCircle2 size={15} />
                Linked to Opportunity ({signal.opportunity_status || "Saved"})
              </div>
              <Link
                href={`/intent-radar/opportunities/${signal.opportunity_id}`}
                className="text-xs font-semibold text-primary hover:underline"
              >
                View Opportunity →
              </Link>
            </div>
          ) : signal.opportunity_eligibility ? (
            <div className="rounded-xl border border-border/80 bg-muted/15 px-4 py-3 space-y-1">
              <p className="text-xs font-medium text-foreground">
                {signal.opportunity_eligibility.eligible
                  ? "Ready for opportunity promotion"
                  : "Needs review before opportunity promotion"}
              </p>
              <p className="text-[11px] text-muted-foreground">
                {signal.opportunity_eligibility.next_step}
              </p>
            </div>
          ) : null}

          {error && (
            <p role="alert" className="text-xs text-destructive">
              {error}
            </p>
          )}
        </div>

        {/* Sticky action footer */}
        <div className="border-t border-border bg-card px-4 py-3 shrink-0 space-y-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              disabled={disabled || signal.status === "Qualified"}
              onClick={() => void updateStatus("Qualified")}
              style={{
                background: "#059669",
                borderColor: "#059669",
                color: "#ffffff",
                padding: "6px 10px",
              }}
              className="inline-flex items-center gap-1 rounded-lg text-xs font-semibold hover:opacity-90 disabled:opacity-50 cursor-pointer"
            >
              {busyAction === "Qualified" ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle2 size={13} />}
              {signal.status === "Qualified" ? "Qualified" : "Qualify"}
            </button>

            <button
              type="button"
              disabled={disabled || signal.status === "Reviewed"}
              onClick={() => void updateStatus("Reviewed")}
              style={{ padding: "6px 10px" }}
              className="inline-flex items-center gap-1 rounded-lg border border-border bg-background text-xs font-medium text-foreground hover:bg-muted disabled:opacity-50 cursor-pointer"
            >
              {busyAction === "Reviewed" ? <Loader2 size={13} className="animate-spin" /> : <CheckCheck size={13} />}
              Reviewed
            </button>

            <button
              type="button"
              disabled={disabled}
              onClick={() => void toggleSave()}
              style={{ padding: "6px 10px" }}
              className={
                "inline-flex items-center gap-1 rounded-lg border text-xs font-medium cursor-pointer disabled:opacity-50 " +
                (signal.saved
                  ? "border-primary/40 bg-primary/10 text-primary"
                  : "border-border bg-background text-foreground hover:bg-muted")
              }
            >
              {busyAction === "save" ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <Bookmark size={13} fill={signal.saved ? "currentColor" : "none"} />
              )}
              {signal.saved ? "Saved" : "Save"}
            </button>

            {signal.opportunity_id ? (
              <Link
                href={`/intent-radar/opportunities/${signal.opportunity_id}`}
                style={{ padding: "6px 10px" }}
                className="ir-primary inline-flex items-center gap-1 rounded-lg text-xs font-semibold hover:opacity-90"
              >
                <Target size={13} />
                View Opportunity
              </Link>
            ) : (
              <button
                type="button"
                disabled={disabled}
                onClick={() => onOpenOpportunityModal(signal)}
                style={{ padding: "6px 10px" }}
                title={!canWrite ? "Read-only workspace access" : "Create Opportunity"}
                className="ir-primary inline-flex items-center gap-1 rounded-lg text-xs font-semibold hover:opacity-90 disabled:opacity-50 cursor-pointer"
              >
                <Target size={13} />
                Create Opportunity
              </button>
            )}

            <button
              type="button"
              disabled={disabled || signal.status === "Dismissed"}
              onClick={() => void updateStatus("Dismissed")}
              style={{ padding: "6px 10px" }}
              className="inline-flex items-center gap-1 rounded-lg border border-border bg-background text-xs font-medium text-muted-foreground hover:border-destructive/40 hover:text-destructive disabled:opacity-50 cursor-pointer ml-auto"
            >
              {busyAction === "Dismissed" ? <Loader2 size={13} className="animate-spin" /> : <XCircle size={13} />}
              Dismiss
            </button>
          </div>
          {!canWrite && (
            <p className="text-[11px] text-muted-foreground">
              Your workspace role allows viewing evidence only.
            </p>
          )}
        </div>
      </aside>
    </div>
  );
}
