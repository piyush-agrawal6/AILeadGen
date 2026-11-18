"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
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
  HelpCircle,
  Loader2,
  RotateCcw,
  ShieldCheck,
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
import {
  buyingIntentDisplay,
  formatObservedDate,
  provenanceSummary,
  readSignalsReturnContext,
  statusPillClasses,
} from "./signals/signals-context";

export function EvidenceDetail({ id }: { id: string }) {
  const query = useRadarRead<IntentSignal>("/signals/" + id);
  const access = useRadarCapabilities();
  if (query.error) {
    return <ErrorState message={query.error.message} retry={() => void query.refetch()} />;
  }
  if (!query.data) return <LoadingSkeleton />;
  return <EvidenceContent key={id} signal={query.data} canWrite={!!access.data?.can_write} />;
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
  const isLongExcerpt = rawExcerpt.length > 600;
  const rankingAdj = feedbackHistory.data?.feedback?.ranking_adjustment ?? 0;

  async function updateReview(nextStatus: string, saveNotes = false) {
    setError("");
    const prevStatus = s.status;
    try {
      await mutation.mutateAsync({
        path: `/signals/${s.id}`,
        method: "PATCH",
        body: { revision: s.revision, status: nextStatus, ...(saveNotes ? { notes } : {}) },
      });
      setDismissConfirm(false);
      if (!saveNotes && nextStatus !== prevStatus) {
        setNotice({
          message: `Signal status updated to ${nextStatus}.`,
          undo: { revision: s.revision + 1, previousStatus: prevStatus },
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
      ? "Review unknowns and create an Opportunity if this matches your offering."
      : s.has_analysis
        ? "Review AI summary and original discussion before qualifying or dismissing."
        : "Inspect the source excerpt or run Analyze Signal to verify commercial intent.";

  return (
    <div className="ir-page space-y-5">
      {/* Top Navigation: Prominent Back to Signals + Prev / Next within active list context */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/80 pb-3">
        <Link
          href={returnCtx.returnUrl}
          className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-semibold text-foreground hover:border-primary/50 hover:text-primary transition-colors"
        >
          <ArrowLeft size={14} />
          Back to Signals
        </Link>

        <div className="flex items-center gap-1.5">
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

      {/* Notice / Undo Banner */}
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

      {/* 1. Decision Summary Card (Above the Fold — Fast Triage!) */}
      <section className="rounded-2xl border border-border bg-card p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-foreground">Decision Summary</h2>
          <span className="text-[11px] text-muted-foreground">
            Scores and labels reflect observed public text only, never verified buying authority.
          </span>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-border/80 bg-background p-3 space-y-1">
            <span className="text-[11px] font-medium text-muted-foreground">Topic Relevance</span>
            <div className="flex items-center gap-2">
              <SignalScore score={s.score} />
              <span className="text-xs font-medium text-foreground truncate">{s.evidence?.confidence || s.category}</span>
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
            <span className="text-[11px] font-medium text-muted-foreground">Opportunity Readiness</span>
            <p className="text-xs font-medium text-foreground">
              {s.opportunity_id
                ? `Linked (${s.opportunity_status || "Saved"})`
                : eligibility?.eligible
                  ? "Evidence-backed candidate"
                  : "Needs review first"}
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
                  className="inline-flex h-8 items-center rounded-lg bg-destructive px-3 text-xs font-semibold text-white cursor-pointer"
                >
                  Confirm Dismiss
                </button>
                <button
                  type="button"
                  onClick={() => setDismissConfirm(false)}
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

      {/* Main Two-Column Content Grid */}
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px] items-start">
        {/* Left Main Column */}
        <div className="space-y-5 min-w-0">
          {/* 2. Evidence & Source Provenance */}
          <section className="rounded-2xl border border-border bg-card p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-base font-semibold text-foreground">Original Conversation Evidence</h2>
              <span className="rounded-full border border-border bg-muted/40 px-2.5 py-0.5 text-[11px] font-medium text-muted-foreground">
                {prov.visibility || "Public source"}
              </span>
            </div>

            <blockquote className="rounded-xl border-l-4 border-primary/45 bg-muted/25 p-4 text-sm leading-relaxed text-foreground whitespace-pre-line break-words">
              {!expandedExcerpt && isLongExcerpt ? rawExcerpt.slice(0, 600) + "…" : rawExcerpt}
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

            {/* Match Breakdown */}
            <div className="rounded-xl border border-border/80 bg-background p-4 space-y-3">
              <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                <ShieldCheck size={15} className="text-primary" />
                Why this signal matched
              </div>
              <p className="text-xs leading-relaxed text-muted-foreground">
                {s.evidence?.explanation || "Matched workspace discovery criteria."}
              </p>

              <div className="grid gap-3 sm:grid-cols-2 text-xs">
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
                  <p className="text-foreground">
                    {s.evidence?.intent_phrase ? `“${s.evidence.intent_phrase}”` : "No explicit commercial phrase detected."}
                  </p>
                </div>
              </div>

              <details className="border-t border-border/60 pt-2.5 text-xs">
                <summary className="cursor-pointer font-medium text-muted-foreground hover:text-foreground">
                  Uncertain or unverified attributes
                </summary>
                <ul className="mt-2 list-disc pl-4 space-y-1 text-muted-foreground">
                  {(s.evidence?.unknown || ["Budget, buying authority, and purchasing readiness are not verified."]).map(
                    (u, idx) => (
                      <li key={idx}>{u}</li>
                    )
                  )}
                </ul>
              </details>
            </div>
          </section>

          {/* 3. AI Intelligence Panel */}
          <SignalIntelligencePanel id={s.id} />
        </div>

        {/* Right Column: Provenance + Unified Notes, Feedback & Activity */}
        <aside className="space-y-5 min-w-0">
          {/* Source & Search Provenance */}
          <section className="rounded-2xl border border-border bg-card p-5 space-y-3 text-xs">
            <h2 className="text-sm font-semibold text-foreground">Source & Provenance</h2>
            <dl className="space-y-2">
              <div className="flex items-start justify-between gap-2">
                <dt className="text-muted-foreground">Provider</dt>
                <dd className="font-medium text-foreground text-right">{s.source}</dd>
              </div>
              <div className="flex items-start justify-between gap-2">
                <dt className="text-muted-foreground">Collection method</dt>
                <dd className="font-medium text-foreground text-right">{prov.fetchLabel}</dd>
              </div>
              {prov.repo && (
                <div className="flex items-start justify-between gap-2">
                  <dt className="text-muted-foreground">Repository</dt>
                  <dd className="font-medium text-foreground text-right break-all">{prov.repo}</dd>
                </div>
              )}
              {prov.contentKind && (
                <div className="flex items-start justify-between gap-2">
                  <dt className="text-muted-foreground">Content type</dt>
                  <dd className="font-medium text-foreground capitalize text-right">{prov.contentKind}</dd>
                </div>
              )}
              {prov.author && (
                <div className="flex items-start justify-between gap-2">
                  <dt className="text-muted-foreground">Public author</dt>
                  <dd className="font-medium text-foreground text-right">{prov.author}</dd>
                </div>
              )}
              <div className="flex items-start justify-between gap-2">
                <dt className="text-muted-foreground">Observed</dt>
                <dd className="text-foreground text-right whitespace-nowrap" title={observed.full}>
                  {observed.short}
                </dd>
              </div>
              <div className="flex items-start justify-between gap-2">
                <dt className="text-muted-foreground">Retrieved</dt>
                <dd className="text-foreground text-right whitespace-nowrap" title={retrieved.full}>
                  {retrieved.short}
                </dd>
              </div>
              {s.discovery_id && (
                <div className="flex items-start justify-between gap-2">
                  <dt className="text-muted-foreground">Discovery run</dt>
                  <dd className="text-right">
                    <Link
                      href={`/intent-radar/discover/runs/${s.discovery_id}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {s.discovery_title || "View run"}
                    </Link>
                  </dd>
                </div>
              )}
              {s.monitors && s.monitors.length > 0 && (
                <div className="space-y-1 pt-1 border-t border-border/60">
                  <dt className="text-muted-foreground">Matched monitors</dt>
                  <dd className="flex flex-wrap gap-1.5">
                    {s.monitors.map((m) => (
                      <Link
                        key={m.id}
                        href={`/intent-radar/monitors/${m.id}`}
                        className="rounded-md border border-border bg-muted/40 px-2 py-0.5 font-medium text-primary hover:underline"
                      >
                        {m.name}
                      </Link>
                    ))}
                  </dd>
                </div>
              )}
            </dl>
            <p className="border-t border-border/60 pt-2 text-[11px] text-muted-foreground">
              Language and geography are not independently verified from public excerpts.
            </p>
          </section>

          {/* Reviewer Relevance Feedback (Simple, Bounded, Reversible) */}
          <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
            <div className="space-y-0.5">
              <h2 className="text-sm font-semibold text-foreground">Was this signal relevant?</h2>
              <p className="text-[11px] text-muted-foreground">
                Your feedback reversibly adjusts workspace ranking (current adjustment: {rankingAdj >= 0 ? `+${rankingAdj}` : rankingAdj}).
              </p>
            </div>

            <div className="grid grid-cols-3 gap-2">
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
                    className={
                      "inline-flex flex-col items-center justify-center gap-1 rounded-xl border px-2 py-2.5 text-[11px] font-medium transition-colors cursor-pointer disabled:opacity-50 " +
                      (active
                        ? "border-primary bg-primary/10 text-primary font-semibold"
                        : "border-border bg-background text-foreground hover:bg-muted/50")
                    }
                  >
                    <Icon size={14} />
                    <span>{label}</span>
                  </button>
                );
              })}
            </div>

            <textarea
              rows={2}
              maxLength={1000}
              aria-label="Optional feedback explanation"
              value={fbNote}
              onChange={(e) => setFbNote(e.target.value)}
              placeholder="Optional note explaining why…"
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground"
            />

            <div className="flex items-center justify-between gap-2 text-[11px]">
              <span className="text-emerald-700 dark:text-emerald-300">{fbSavedMsg}</span>
              {fbLabel && (
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => void submitFeedback(fbLabel, false)}
                  className="text-muted-foreground hover:text-foreground underline cursor-pointer"
                >
                  Clear my feedback
                </button>
              )}
            </div>
          </section>

          {/* Review Notes */}
          <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
            <h2 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
              <StickyNote size={15} className="text-primary" />
              Review Notes
            </h2>
            <textarea
              rows={3}
              maxLength={4000}
              aria-label="Your review notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Capture context, qualification rationale, or follow-up questions…"
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground"
            />
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] text-muted-foreground">
                {notes !== (s.notes || "") ? "Unsaved changes" : "Notes saved"}
              </span>
              <button
                type="button"
                disabled={disabled || notes === (s.notes || "")}
                onClick={() => void updateReview(s.status, true)}
                className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-50 cursor-pointer"
              >
                {mutation.isPending ? <Loader2 size={13} className="animate-spin" /> : null}
                Save Note
              </button>
            </div>
          </section>

          {/* Activity Timeline */}
          {s.activity && s.activity.length > 0 && (
            <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
              <h2 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                <Clock size={15} className="text-muted-foreground" />
                Activity History
              </h2>
              <ol className="space-y-2.5 border-l border-border pl-3.5 text-xs">
                {s.activity.slice(0, 10).map((ev, idx) => (
                  <li key={`${ev.kind}-${ev.at}-${idx}`} className="space-y-0.5">
                    <p className="font-medium text-foreground">{ev.title}</p>
                    {ev.detail && <p className="text-[11px] text-muted-foreground break-words">{ev.detail}</p>}
                    <p className="text-[10px] text-muted-foreground">
                      {ev.at ? formatObservedDate(ev.at).short : ""}
                      {ev.actor ? ` · ${ev.actor}` : ""}
                    </p>
                  </li>
                ))}
              </ol>
            </section>
          )}
        </aside>
      </div>

      {/* Controlled Editable Create Opportunity Modal */}
      <CreateOpportunityModal
        signal={s}
        open={oppModalOpen}
        onClose={() => setOppModalOpen(false)}
        onCreated={() => setNotice({ message: "Opportunity created and linked to this signal." })}
      />
    </div>
  );
}
