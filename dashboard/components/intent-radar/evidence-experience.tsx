"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Activity,
  ArrowLeft,
  ArrowUpRight,
  Bookmark,
  CheckCheck,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Clock,
  ExternalLink,
  HelpCircle,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  StickyNote,
  Target,
  ThumbsDown,
  ThumbsUp,
  X,
  XCircle,
} from "lucide-react";
import type { IntentSignal } from "@/lib/intent-radar";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "./provider";
import { ErrorState, LoadingSkeleton } from "./ui";
import { SignalScore } from "./signals";
import { ProviderLogo } from "./provider-logo";
import { SignalIntelligencePanel } from "./signals/SignalIntelligencePanel";
import { CreateOpportunityModal } from "./signals/CreateOpportunityModal";
import { Button } from "@/components/ui/button";
import {
  buyingIntentDisplay,
  formatObservedDate,
  provenanceSummary,
  readSignalsReturnContext,
  statusPillClasses,
} from "./signals/signals-context";

type DetailTab = "overview" | "evidence" | "intelligence" | "activity";

export function EvidenceDetail({ id }: { id: string }) {
  const query = useRadarRead<IntentSignal>("/signals/" + id);
  const access = useRadarCapabilities();
  if (query.error) {
    return (
      <div className="ir-page space-y-4">
        <Link
          href="/intent-radar/signals"
          className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-semibold text-foreground hover:border-primary/50"
        >
          <ArrowLeft size={14} /> Back to Signals
        </Link>
        <ErrorState message={query.error.message} retry={() => void query.refetch()} />
      </div>
    );
  }
  if (!query.data) return <LoadingSkeleton />;
  return <EvidenceContent key={id} signal={query.data} canWrite={Boolean(access.data?.can_write)} />;
}

function EvidenceContent({ signal: s, canWrite }: { signal: IntentSignal; canWrite: boolean }) {
  const router = useRouter();
  const mutation = useRadarMutation();
  const feedbackHistory = useRadarRead<{
    feedback?: {
      items: { actor: string; label: string; note?: string; active: number; updated_at?: string }[];
      ranking_adjustment: number;
    };
  }>(`/signals/${s.id}/analysis`);

  const [activeTab, setActiveTab] = useState<DetailTab>("overview");
  const [notes, setNotes] = useState(s.notes || "");
  const [expandedExcerpt, setExpandedExcerpt] = useState(false);
  const [oppModalOpen, setOppModalOpen] = useState(false);
  const [dismissConfirm, setDismissConfirm] = useState(false);
  const [fbLabel, setFbLabel] = useState<string>(s.feedback_label || "");
  const [fbNote, setFbNote] = useState("");
  const [fbSavedMsg, setFbSavedMsg] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState<{
    message: string;
    undo?: { revision: number; previousStatus: string };
  } | null>(null);

  const [returnCtx, setReturnCtx] = useState<{
    returnUrl: string;
    prevId: string | null;
    nextId: string | null;
  }>({ returnUrl: "/intent-radar/signals", prevId: null, nextId: null });

  useEffect(() => {
    setNotes(s.notes || "");
    setFbLabel(s.feedback_label || "");
  }, [s.id, s.notes, s.feedback_label]);

  useEffect(() => {
    const activeFb = feedbackHistory.data?.feedback?.items?.find((f) => f.active);
    if (activeFb?.note) {
      setFbNote((prev) => (prev ? prev : activeFb.note || ""));
    }
  }, [feedbackHistory.data?.feedback?.items]);

  useEffect(() => {
    const ctx = readSignalsReturnContext();
    if (!ctx) {
      setReturnCtx({ returnUrl: "/intent-radar/signals", prevId: null, nextId: null });
      return;
    }
    const idx = ctx.orderedIds.indexOf(s.id);
    setReturnCtx({
      returnUrl: ctx.returnUrl || "/intent-radar/signals",
      prevId: idx > 0 ? ctx.orderedIds[idx - 1] : null,
      nextId: idx >= 0 && idx < ctx.orderedIds.length - 1 ? ctx.orderedIds[idx + 1] : null,
    });
  }, [s.id]);

  const disabled = !canWrite || mutation.isPending;
  const observed = formatObservedDate(s.observed_at);
  const retrieved = formatObservedDate(s.retrieved_at);
  const buying = buyingIntentDisplay(s);
  const prov = provenanceSummary(s);
  const eligibility = s.opportunity_eligibility;
  const rawExcerpt = s.excerpt || s.title;
  const isLongExcerpt = rawExcerpt.length > 500;
  const rankingAdj = feedbackHistory.data?.feedback?.ranking_adjustment ?? 0;

  async function updateReview(nextStatus: string, saveNotes = false) {
    setError("");
    const prevStatus = s.status;
    try {
      const updated = (await mutation.mutateAsync({
        path: `/signals/${s.id}`,
        method: "PATCH",
        body: { revision: s.revision, status: nextStatus, ...(saveNotes ? { notes } : {}) },
      })) as IntentSignal | undefined;
      const nextRev = typeof updated?.revision === "number" ? updated.revision : s.revision + 1;
      setDismissConfirm(false);
      if (!saveNotes && nextStatus !== prevStatus) {
        setNotice({
          message: `Signal status updated to ${nextStatus}.`,
          undo: { revision: nextRev, previousStatus: prevStatus },
        });
      } else if (saveNotes) {
        setNotice({ message: "Review notes saved." });
      }
    } catch (e) {
      setError((e as Error).message || "Could not update signal.");
    }
  }

  async function toggleBookmark() {
    if (disabled) return;
    setError("");
    try {
      await mutation.mutateAsync({
        path: `/saved/${s.id}`,
        method: s.saved ? "DELETE" : "POST",
      });
      setNotice({
        message: s.saved
          ? "Removed from Saved bookmarks."
          : "Saved to bookmarks (review status preserved).",
      });
    } catch (e) {
      setError((e as Error).message || "Could not update bookmark.");
    }
  }

  async function submitFeedback(label: string, active = true) {
    if (disabled) return;
    setError("");
    setFbSavedMsg("");
    try {
      await mutation.mutateAsync({
        path: `/signals/${s.id}/feedback`,
        method: "PUT",
        body: { label, note: fbNote.trim(), active },
      });
      setFbLabel(active ? label : "");
      setFbSavedMsg(active ? `Saved feedback: ${label}` : "Cleared your feedback.");
    } catch (e) {
      setError((e as Error).message || "Could not save feedback.");
    }
  }

  async function handleUndo() {
    if (!notice?.undo || mutation.isPending) return;
    const { revision, previousStatus } = notice.undo;
    setNotice(null);
    try {
      await mutation.mutateAsync({
        path: `/signals/${s.id}`,
        method: "PATCH",
        body: { revision, status: previousStatus },
      });
    } catch {
      // ignore stale revision
    }
  }

  const recommendedNextStep = s.opportunity_id
    ? "Follow up in the linked Opportunity record."
    : eligibility?.eligible
      ? "Review unknowns and promote to an Opportunity if this matches your offering."
      : s.has_analysis
        ? "Review AI evaluation and original discussion before qualifying or dismissing."
        : "Inspect the source excerpt or run Analyze Signal to evaluate commercial intent.";

  return (
    <div className="ir-page space-y-5">
      {/* Top Navigation */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/80 pb-3">
        <Link
          href={returnCtx.returnUrl}
          className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-semibold text-foreground hover:border-primary/50 hover:text-primary transition-colors"
        >
          <ArrowLeft size={14} />
          Back to Signals
        </Link>

        <div className="flex items-center gap-1.5">
          <Link
            href={`/intelligence/assistant?context=signal&entityId=${encodeURIComponent(s.id)}&prompt=${encodeURIComponent(`Analyze this signal ("${s.title.slice(0, 80)}") against my primary ICP and recommend next steps.`)}`}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 px-2.5 text-xs font-semibold text-primary hover:bg-primary/15 transition-colors"
          >
            <Sparkles size={13} />
            Ask AI
          </Link>
          <button
            type="button"
            disabled={!returnCtx.prevId}
            onClick={() => returnCtx.prevId && router.push(`/intent-radar/signals/${returnCtx.prevId}`)}
            className="inline-flex h-8 items-center gap-1 rounded-lg border border-border bg-card px-2.5 text-xs font-medium text-foreground hover:bg-muted disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
          >
            <ChevronLeft size={14} /> Previous Signal
          </button>
          <button
            type="button"
            disabled={!returnCtx.nextId}
            onClick={() => returnCtx.nextId && router.push(`/intent-radar/signals/${returnCtx.nextId}`)}
            className="inline-flex h-8 items-center gap-1 rounded-lg border border-border bg-card px-2.5 text-xs font-medium text-foreground hover:bg-muted disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
          >
            Next Signal <ChevronRight size={14} />
          </button>
        </div>
      </div>

      {/* Header */}
      <header className="space-y-3">
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5 font-semibold text-foreground">
            <ProviderLogo provider={s.source} size={20} />
            <span>{s.source}</span>
          </span>
          {prov.repo && (
            <span className="rounded-md border border-border bg-muted/40 px-2 py-0.5 text-[11px] font-medium text-foreground">
              {prov.repo}
            </span>
          )}
          <span className="rounded-full border border-border bg-muted/40 px-2.5 py-0.5 text-[11px] font-medium text-foreground">
            {s.category}
          </span>
          <span
            className={
              "rounded-full border px-2.5 py-0.5 text-[11px] font-semibold " + statusPillClasses(s.status)
            }
          >
            {s.status}
          </span>
          {s.saved && (
            <span className="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
              <Bookmark size={11} fill="currentColor" /> Saved
            </span>
          )}
          <span className="whitespace-nowrap" title={observed.full}>
            Observed {observed.short}
          </span>
        </div>

        <div className="flex flex-wrap items-start justify-between gap-4">
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground leading-snug break-words max-w-4xl">
            {s.title}
          </h1>

          {s.source_url?.startsWith("http") && (
            <a
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-card px-3.5 text-xs font-semibold text-foreground hover:border-primary/50 hover:text-primary shrink-0"
              href={s.source_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Open original public discussion <ArrowUpRight size={14} />
            </a>
          )}
        </div>
      </header>

      {/* Notice Banner */}
      {notice && (
        <div
          role="status"
          className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border bg-card px-4 py-2.5 text-xs text-foreground shadow-sm"
        >
          <span>{notice.message}</span>
          <div className="flex items-center gap-2">
            {notice.undo && (
              <button
                type="button"
                onClick={() => void handleUndo()}
                className="inline-flex items-center gap-1 rounded-md border border-primary/40 bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary cursor-pointer"
              >
                <RotateCcw size={12} /> Undo
              </button>
            )}
            <button
              type="button"
              aria-label="Dismiss notice"
              onClick={() => setNotice(null)}
              className="text-muted-foreground hover:text-foreground cursor-pointer"
            >
              <X size={14} />
            </button>
          </div>
        </div>
      )}

      {error && <ErrorState message={error} />}

      {/* Decision Summary Card */}
      <section className="rounded-2xl border border-border bg-card p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-foreground">Decision Summary</h2>
          <span className="text-[11px] text-muted-foreground">
            Scores reflect observed public text only, never verified budget or buying authority.
          </span>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-border/80 bg-background p-3 space-y-1">
            <span className="text-[11px] font-medium text-muted-foreground">Topic Relevance</span>
            <div className="flex items-center gap-2">
              <SignalScore score={s.score} />
              <span className="text-xs font-medium text-foreground truncate">
                {s.evidence?.confidence || s.category}
              </span>
            </div>
          </div>

          <div className="rounded-xl border border-border/80 bg-background p-3 space-y-1">
            <span className="text-[11px] font-medium text-muted-foreground">Buying Intent</span>
            <div>
              <span
                className={
                  "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold " +
                  buying.tone
                }
              >
                {buying.label}
              </span>
            </div>
          </div>

          <div className="rounded-xl border border-border/80 bg-background p-3 space-y-1">
            <span className="text-[11px] font-medium text-muted-foreground">ICP Fit</span>
            <p className="text-xs font-medium text-foreground">
              {s.icp_fit && s.icp_fit !== "Unassessed" ? s.icp_fit : "Unassessed"}
            </p>
          </div>

          <div className="rounded-xl border border-border/80 bg-background p-3 space-y-1">
            <span className="text-[11px] font-medium text-muted-foreground">Opportunity Status</span>
            <p className="text-xs font-medium text-foreground">
              {s.opportunity_id
                ? `Linked (${s.opportunity_status || "Active"})`
                : eligibility?.eligible
                  ? "Eligible candidate"
                  : "Needs review"}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/70 bg-muted/20 px-4 py-3">
          <div className="space-y-0.5 text-xs">
            <span className="font-semibold text-foreground">Recommended next step: </span>
            <span className="text-muted-foreground">{recommendedNextStep}</span>
          </div>

          {/* Primary Review Actions */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={disabled || s.status === "Qualified"}
              onClick={() => void updateReview("Qualified")}
              style={{ background: "#059669", borderColor: "#059669", color: "#ffffff" }}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg px-3 text-xs font-semibold hover:opacity-90 disabled:opacity-50 cursor-pointer"
            >
              <CheckCircle2 size={13} /> {s.status === "Qualified" ? "Qualified" : "Qualify"}
            </button>

            <button
              type="button"
              disabled={disabled || s.status === "Reviewed"}
              onClick={() => void updateReview("Reviewed")}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-medium text-foreground hover:bg-muted disabled:opacity-50 cursor-pointer"
            >
              <CheckCheck size={13} /> Mark Reviewed
            </button>

            <button
              type="button"
              disabled={disabled}
              onClick={() => void toggleBookmark()}
              className={
                "inline-flex h-8 items-center gap-1.5 rounded-lg border px-3 text-xs font-medium cursor-pointer disabled:opacity-50 " +
                (s.saved
                  ? "border-primary/40 bg-primary/10 text-primary"
                  : "border-border bg-card text-foreground hover:bg-muted")
              }
            >
              <Bookmark size={13} fill={s.saved ? "currentColor" : "none"} />
              {s.saved ? "Saved" : "Save"}
            </button>

            <button
              type="button"
              disabled={disabled}
              onClick={() => setOppModalOpen(true)}
              className="ir-primary inline-flex h-8 items-center gap-1.5 rounded-lg px-3 text-xs font-semibold hover:opacity-90 disabled:opacity-50 cursor-pointer"
            >
              <Target size={13} />
              {s.opportunity_id ? "View Opportunity" : "Create Opportunity"}
            </button>

            {dismissConfirm ? (
              <div className="inline-flex items-center gap-1.5">
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => void updateReview("Dismissed")}
                  style={{ background: "#dc2626", borderColor: "#dc2626", color: "#ffffff", minHeight: "32px" }}
                  className="inline-flex h-8 items-center rounded-lg px-3 text-xs font-semibold cursor-pointer"
                >
                  Confirm Dismiss
                </button>
                <button
                  type="button"
                  onClick={() => setDismissConfirm(false)}
                  style={{ minHeight: "32px" }}
                  className="inline-flex h-8 items-center rounded-lg border border-border bg-card px-2.5 text-xs text-foreground cursor-pointer"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                type="button"
                disabled={disabled || s.status === "Dismissed"}
                onClick={() => setDismissConfirm(true)}
                className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-medium text-muted-foreground hover:border-destructive/40 hover:text-destructive disabled:opacity-50 cursor-pointer"
              >
                <XCircle size={13} /> Dismiss
              </button>
            )}
          </div>
        </div>
      </section>

      {/* Tab Bar for Supporting Details */}
      <div className="flex items-center gap-1 overflow-x-auto border-b border-border/80 pb-px">
        {[
          { id: "overview", label: "Overview" },
          { id: "evidence", label: "Evidence" },
          { id: "intelligence", label: "AI Intelligence" },
          { id: "activity", label: "Activity & Notes" },
        ].map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setActiveTab(t.id as DetailTab)}
            className={`shrink-0 border-b-2 px-3.5 py-2 text-xs font-semibold transition-colors cursor-pointer ${
              activeTab === t.id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Main Two-Column Layout */}
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px] items-start">
        {/* Left Main Tab Content */}
        <div className="space-y-5 min-w-0">
          {/* Tab 1: Overview */}
          {activeTab === "overview" && (
            <div className="space-y-4">
              <section className="rounded-2xl border border-border bg-card p-5 space-y-4">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                    <ShieldCheck size={15} className="text-primary" />
                    Why this signal matched
                  </h3>
                  <span className="text-[11px] text-muted-foreground">
                    Confidence: {s.evidence?.confidence || "Medium"}
                  </span>
                </div>

                <p className="text-xs leading-relaxed text-foreground">
                  {s.evidence?.explanation || "Matched workspace discovery keywords and intent criteria."}
                </p>

                <div className="grid gap-3.5 sm:grid-cols-2 text-xs border-t border-border/70 pt-3.5">
                  <div className="space-y-1.5">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Matched keywords
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {s.evidence?.matched_keywords?.length ? (
                        s.evidence.matched_keywords.map((kw) => (
                          <span
                            key={kw}
                            className="rounded-md border border-border bg-muted/50 px-2 py-0.5 text-[11px] font-medium text-foreground"
                          >
                            {kw}
                          </span>
                        ))
                      ) : (
                        <span className="text-muted-foreground">None recorded</span>
                      )}
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Detected intent phrase
                    </span>
                    <p className="text-foreground font-medium">
                      {s.evidence?.intent_phrase ? `“${s.evidence.intent_phrase}”` : "No explicit commercial phrase detected."}
                    </p>
                  </div>
                </div>

                <div className="rounded-xl border border-border/70 bg-muted/15 p-3.5 space-y-1.5 text-xs">
                  <span className="font-semibold text-foreground">Uncertain or unverified information</span>
                  <ul className="list-disc pl-4 space-y-1 text-muted-foreground">
                    {(s.evidence?.unknown || ["Budget, buying authority, and timeline are unverified."]).map(
                      (u, idx) => (
                        <li key={idx}>{u}</li>
                      ),
                    )}
                  </ul>
                </div>
              </section>

              {/* Excerpt Snippet in Overview */}
              <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="text-sm font-semibold text-foreground">Conversation Excerpt</h3>
                  <button
                    type="button"
                    onClick={() => setActiveTab("evidence")}
                    className="text-[11px] font-medium text-primary hover:underline cursor-pointer"
                  >
                    View full discussion details →
                  </button>
                </div>
                <blockquote className="rounded-xl border-l-4 border-primary/45 bg-muted/20 p-3.5 text-xs leading-relaxed text-foreground whitespace-pre-line line-clamp-4">
                  {rawExcerpt}
                </blockquote>
              </section>

              {/* AI Intelligence Panel also directly accessible in Overview */}
              <SignalIntelligencePanel id={s.id} available={s.available} />
            </div>
          )}

          {/* Tab 2: Evidence */}
          {activeTab === "evidence" && (
            <section className="rounded-2xl border border-border bg-card p-5 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-foreground">
                  Original Conversation Evidence
                </h3>
                {s.source_url?.startsWith("http") && (
                  <a
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1 text-xs font-semibold text-foreground hover:border-primary/50 hover:text-primary transition-colors"
                    href={s.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Open original public discussion <ExternalLink size={12} />
                  </a>
                )}
              </div>

              <blockquote className="rounded-xl border-l-4 border-primary/45 bg-muted/20 p-4 text-xs leading-relaxed text-foreground whitespace-pre-line break-words">
                {!expandedExcerpt && isLongExcerpt ? rawExcerpt.slice(0, 500) + "…" : rawExcerpt}
              </blockquote>

              {isLongExcerpt && (
                <button
                  type="button"
                  onClick={() => setExpandedExcerpt((v) => !v)}
                  className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline cursor-pointer"
                >
                  {expandedExcerpt ? (
                    <>
                      Collapse full excerpt <ChevronUp size={14} />
                    </>
                  ) : (
                    <>
                      Show full conversation excerpt ({rawExcerpt.length.toLocaleString()} chars) <ChevronDown size={14} />
                    </>
                  )}
                </button>
              )}

              <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 border-t border-border/70 pt-3.5 text-xs">
                <div>
                  <dt className="text-[11px] text-muted-foreground">Source Provider</dt>
                  <dd className="font-medium text-foreground mt-0.5">{s.source}</dd>
                </div>
                <div>
                  <dt className="text-[11px] text-muted-foreground">Observed Timestamp</dt>
                  <dd className="font-medium text-foreground mt-0.5">{observed.full}</dd>
                </div>
                <div>
                  <dt className="text-[11px] text-muted-foreground">Retrieved Timestamp</dt>
                  <dd className="font-medium text-foreground mt-0.5">{retrieved.full}</dd>
                </div>
                <div>
                  <dt className="text-[11px] text-muted-foreground">Attribution</dt>
                  <dd className="font-medium text-foreground mt-0.5 truncate">
                    {prov.author ? (
                      prov.authorUrl?.startsWith("http") ? (
                        <a
                          href={prov.authorUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary hover:underline"
                        >
                          {prov.author}
                        </a>
                      ) : (
                        prov.author
                      )
                    ) : (
                      "Public user"
                    )}
                  </dd>
                </div>
              </dl>
            </section>
          )}

          {/* Tab 3: AI Intelligence */}
          {activeTab === "intelligence" && (
            <div className="space-y-4">
              <SignalIntelligencePanel id={s.id} available={s.available} />
            </div>
          )}

          {/* Tab 4: Activity & Notes */}
          {activeTab === "activity" && (
            <div className="space-y-4">
              {/* Review Notes Section */}
              <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                  <StickyNote size={15} className="text-primary" />
                  Review Notes
                </h3>
                <textarea
                  rows={3}
                  maxLength={4000}
                  aria-label="Your review notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Capture context, qualification rationale, or follow-up questions…"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-primary"
                />
                <div className="flex items-center justify-between gap-2 text-xs">
                  <span className="text-[11px] text-muted-foreground">
                    {notes !== (s.notes || "") ? "Unsaved changes" : "Notes saved"}
                  </span>
                  <Button
                    size="sm"
                    disabled={disabled || notes === (s.notes || "")}
                    onClick={() => void updateReview(s.status, true)}
                    className="h-7 text-xs"
                  >
                    Save Note
                  </Button>
                </div>
              </section>

              {/* Activity Timeline */}
              <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                  <Clock size={15} className="text-primary" />
                  Signal Activity &amp; Audit Trail
                </h3>

                <div className="space-y-2.5 text-xs">
                  {(s.activity || []).map((ev, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-2.5 rounded-xl border border-border/70 bg-muted/15 p-3"
                    >
                      <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary mt-0.5">
                        <Activity size={12} />
                      </div>
                      <div className="min-w-0 flex-1 space-y-0.5">
                        <p className="font-semibold text-foreground">{ev.title}</p>
                        {ev.detail && <p className="text-muted-foreground">{ev.detail}</p>}
                        <span className="text-[11px] text-muted-foreground tabular-nums">
                          {ev.actor ? `${ev.actor} · ` : ""}
                          {ev.at ? new Date(ev.at).toLocaleString() : ""}
                        </span>
                      </div>
                    </div>
                  ))}

                  {(!s.activity || s.activity.length === 0) && (
                    <p className="text-xs text-muted-foreground italic">
                      No explicit activity recorded beyond collection.
                    </p>
                  )}
                </div>
              </section>
            </div>
          )}
        </div>

        {/* Right Sidebar: Provenance + Feedback + Opportunity */}
        <aside className="space-y-4 min-w-0">
          {/* Related Opportunity Card */}
          <section className="rounded-2xl border border-border bg-card p-4 space-y-2.5 text-xs">
            <h3 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <Target size={14} className="text-primary" />
              Opportunity Status
            </h3>
            {s.opportunity_id ? (
              <div className="space-y-2">
                <p className="text-muted-foreground">
                  Linked to an active workspace opportunity.
                </p>
                <div className="flex items-center justify-between">
                  <span className="rounded-full border border-primary/20 bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
                    {s.opportunity_status || "Active"}
                  </span>
                  <Link
                    href={`/intent-radar/opportunities/${s.opportunity_id}`}
                    className="font-medium text-primary hover:underline inline-flex items-center gap-1"
                  >
                    Open Opportunity <ArrowUpRight size={11} />
                  </Link>
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-muted-foreground">
                  {eligibility?.eligible
                    ? "Qualified as an evidence-backed buyer opportunity candidate."
                    : "Not yet promoted to an Opportunity."}
                </p>
                {canWrite && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setOppModalOpen(true)}
                    className="w-full h-7 text-xs gap-1.5"
                  >
                    <Target size={12} />
                    Promote to Opportunity
                  </Button>
                )}
              </div>
            )}
          </section>

          {/* Reviewer Relevance Feedback */}
          <section className="rounded-2xl border border-border bg-card p-4 space-y-3 text-xs">
            <div className="space-y-0.5">
              <h3 className="text-xs font-semibold text-foreground">Relevance Feedback</h3>
              <p className="text-[11px] text-muted-foreground">
                Reversibly adjusts workspace ranking (adjustment: {rankingAdj >= 0 ? `+${rankingAdj}` : rankingAdj}).
              </p>
            </div>

            <div className="grid grid-cols-3 gap-1.5">
              {(
                [
                  { label: "Relevant", icon: ThumbsUp },
                  { label: "Not relevant", icon: ThumbsDown },
                  { label: "Unsure", icon: HelpCircle },
                ] as const
              ).map(({ label, icon: Icon }) => {
                const active = fbLabel === label;
                return (
                  <button
                    key={label}
                    type="button"
                    disabled={disabled}
                    aria-pressed={active}
                    onClick={() => void submitFeedback(label, true)}
                    className={`inline-flex flex-col items-center justify-center gap-1 rounded-xl border px-1.5 py-2 text-[10px] font-medium transition-colors cursor-pointer disabled:opacity-50 ${
                      active
                        ? "border-primary bg-primary/10 text-primary font-semibold"
                        : "border-border bg-background text-foreground hover:bg-muted/50"
                    }`}
                  >
                    <Icon size={13} />
                    <span>{label}</span>
                  </button>
                );
              })}
            </div>

            {fbSavedMsg && (
              <span className="text-[11px] text-emerald-700 dark:text-emerald-300 block">
                {fbSavedMsg}
              </span>
            )}
          </section>

          {/* Source & Provenance */}
          <section className="rounded-2xl border border-border bg-card p-4 space-y-2.5 text-xs">
            <h3 className="text-xs font-semibold text-foreground">Source &amp; Provenance</h3>
            <dl className="space-y-1.5 text-[11px]">
              <div className="flex items-start justify-between gap-2">
                <dt className="text-muted-foreground">Provider</dt>
                <dd className="font-medium text-foreground text-right">{s.source}</dd>
              </div>
              <div className="flex items-start justify-between gap-2">
                <dt className="text-muted-foreground">Collection</dt>
                <dd className="font-medium text-foreground text-right">{prov.fetchLabel}</dd>
              </div>
              {prov.repo && (
                <div className="flex items-start justify-between gap-2">
                  <dt className="text-muted-foreground">Repo</dt>
                  <dd className="font-medium text-foreground text-right break-all">{prov.repo}</dd>
                </div>
              )}
              {prov.contentKind && (
                <div className="flex items-start justify-between gap-2">
                  <dt className="text-muted-foreground">Kind</dt>
                  <dd className="font-medium text-foreground capitalize text-right">{prov.contentKind}</dd>
                </div>
              )}
              <div className="flex items-start justify-between gap-2">
                <dt className="text-muted-foreground">Observed</dt>
                <dd className="text-foreground text-right" title={observed.full}>
                  {observed.short}
                </dd>
              </div>
            </dl>
          </section>
        </aside>
      </div>

      {/* Create Opportunity Modal */}
      <CreateOpportunityModal
        signal={s}
        open={oppModalOpen}
        onClose={() => setOppModalOpen(false)}
        onCreated={() => {
          setNotice({ message: "Opportunity created successfully." });
        }}
      />
    </div>
  );
}
