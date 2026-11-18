"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Activity,
  ArrowLeft,
  ArrowUpRight,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  ExternalLink,
  Pencil,
  ShieldCheck,
  Sparkles,
  Target,
  Trash2,
  UserCheck,
  UserX,
} from "lucide-react";
import type { IntentOpportunity } from "@/lib/intent-radar";
import { ProviderLogo } from "../provider-logo";
import { SignalScore } from "../signals";
import { SafeMarkdown } from "@/components/ui/safe-markdown";
import { Button } from "@/components/ui/button";
import { OpportunityModal } from "./OpportunityModal";

type DetailTab = "overview" | "evidence" | "intelligence" | "activity";

const PRIORITY_STYLES: Record<string, string> = {
  High: "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/25",
  Medium: "bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/25",
  Low: "bg-muted text-muted-foreground border-border",
};

const STATUS_STYLES: Record<string, string> = {
  New: "bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/20",
  Reviewing: "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/20",
  Qualified: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/20",
  Saved: "bg-primary/10 text-primary border-primary/20",
  Dismissed: "bg-muted text-muted-foreground border-border",
};

function formatDate(iso?: string | null) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return "—";
  }
}

function formatDateTime(iso?: string | null) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}

export function OpportunityDetail({
  opportunity: initialOpp,
  onUpdate,
  onDelete,
  canWrite = true,
}: {
  opportunity: IntentOpportunity;
  onUpdate: (patch: {
    revision: number;
    status: string;
    priority: string;
    notes: string;
    next_action: string;
    assigned_to: string | null;
  }) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  canWrite?: boolean;
}) {
  const router = useRouter();
  const [opp, setOpp] = useState<IntentOpportunity>(initialOpp);
  const [activeTab, setActiveTab] = useState<DetailTab>("overview");
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [expandedExcerpt, setExpandedExcerpt] = useState(false);
  const [submittingAction, setSubmittingAction] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const signal = opp.signal;
  const rawExcerpt = signal?.excerpt || signal?.title || "";
  const isLongExcerpt = rawExcerpt.length > 500;

  async function handleQuickStatus(status: string) {
    if (!canWrite || submittingAction) return;
    setSubmittingAction(true);
    setNotice(null);
    try {
      await onUpdate({
        revision: opp.revision,
        status,
        priority: opp.priority,
        notes: opp.notes,
        next_action: opp.next_action,
        assigned_to: opp.assigned_to,
      });
      setOpp((prev) => ({ ...prev, status, revision: prev.revision + 1 }));
      setNotice(`Status updated to ${status}.`);
    } finally {
      setSubmittingAction(false);
    }
  }

  async function handleQuickPriority(priority: string) {
    if (!canWrite || submittingAction) return;
    setSubmittingAction(true);
    setNotice(null);
    try {
      await onUpdate({
        revision: opp.revision,
        status: opp.status,
        priority,
        notes: opp.notes,
        next_action: opp.next_action,
        assigned_to: opp.assigned_to,
      });
      setOpp((prev) => ({ ...prev, priority, revision: prev.revision + 1 }));
      setNotice(`Priority updated to ${priority}.`);
    } finally {
      setSubmittingAction(false);
    }
  }

  return (
    <div className="space-y-5">
      {/* Top Navigation & Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/70 pb-3">
        <Link
          href="/intent-radar/opportunities"
          className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-semibold text-foreground hover:border-primary/50 hover:text-primary transition-colors"
        >
          <ArrowLeft size={14} />
          Back to Opportunities
        </Link>

        {/* Action Bar */}
        <div className="flex flex-wrap items-center gap-1.5">
          {canWrite && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => setEditModalOpen(true)}
              className="h-8 text-xs gap-1.5"
            >
              <Pencil size={13} />
              Edit Details
            </Button>
          )}

          {canWrite && (
            <>
              <select
                aria-label="Change priority"
                disabled={submittingAction}
                value={opp.priority}
                onChange={(e) => void handleQuickPriority(e.target.value)}
                className="h-8 rounded-lg border border-border bg-card px-2.5 text-xs font-medium text-foreground cursor-pointer"
              >
                <option value="High">Priority: High</option>
                <option value="Medium">Priority: Medium</option>
                <option value="Low">Priority: Low</option>
              </select>

              <select
                aria-label="Change workflow status"
                disabled={submittingAction}
                value={opp.status}
                onChange={(e) => void handleQuickStatus(e.target.value)}
                className="h-8 rounded-lg border border-border bg-card px-2.5 text-xs font-medium text-foreground cursor-pointer"
              >
                <option value="New">Status: New</option>
                <option value="Reviewing">Status: Reviewing</option>
                <option value="Qualified">Status: Qualified</option>
                <option value="Saved">Status: Saved</option>
                <option value="Dismissed">Status: Dismissed</option>
              </select>
            </>
          )}

          {signal?.id && (
            <Link
              href={`/intent-radar/signals/${signal.id}`}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-medium text-foreground hover:border-primary/50 hover:text-primary transition-colors"
            >
              <Activity size={13} />
              View Signal
              <ArrowUpRight size={12} />
            </Link>
          )}

          <Link
            href={`/intelligence/assistant?context=opportunity&entityId=${encodeURIComponent(opp.id)}&prompt=${encodeURIComponent(`Analyze this opportunity ("${signal?.title?.slice(0, 80) || "Opportunity"}") and suggest next sales actions.`)}`}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 px-2.5 text-xs font-semibold text-primary hover:bg-primary/15 transition-colors"
          >
            <Sparkles size={13} />
            Ask AI
          </Link>

          {canWrite && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setDeleteConfirm(true)}
              className="h-8 px-2 text-xs text-muted-foreground hover:text-destructive gap-1"
            >
              <Trash2 size={13} />
            </Button>
          )}
        </div>
      </div>

      {/* Notice Banner */}
      {notice && (
        <div
          role="status"
          className="flex items-center gap-2 rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-2.5 text-xs font-medium text-emerald-700 dark:text-emerald-300"
        >
          <CheckCircle2 size={14} className="shrink-0" />
          <span>{notice}</span>
        </div>
      )}

      {/* Header Overview Card */}
      <section className="rounded-2xl border border-border bg-card p-5 space-y-4">
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          {signal?.source && (
            <span className="inline-flex items-center gap-1.5 font-semibold text-foreground">
              <ProviderLogo provider={signal.source} size={18} />
              <span>{signal.source}</span>
            </span>
          )}
          <span
            className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${
              PRIORITY_STYLES[opp.priority] || PRIORITY_STYLES.Medium
            }`}
          >
            {opp.priority} Priority
          </span>
          <span
            className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${
              STATUS_STYLES[opp.status] || STATUS_STYLES.New
            }`}
          >
            {opp.status}
          </span>
          {opp.assigned_to ? (
            <span className="inline-flex items-center gap-1 rounded-full border border-border bg-muted/30 px-2.5 py-0.5 text-[11px] font-medium text-foreground">
              <UserCheck size={11} className="text-primary" />
              {opp.assigned_to}
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full border border-dashed border-border px-2.5 py-0.5 text-[11px] text-muted-foreground">
              <UserX size={11} />
              Unassigned
            </span>
          )}
          <span>Created {formatDate(opp.created_at)}</span>
        </div>

        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground leading-snug">
          {signal?.title || "Qualified Opportunity"}
        </h1>

        {/* 4-Field Fast Summary Bar */}
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 border-t border-border/70 pt-3.5 text-xs">
          <div className="rounded-xl border border-border/80 bg-muted/15 p-3 space-y-1">
            <span className="text-[11px] text-muted-foreground font-medium">Relevance Score</span>
            <div className="flex items-center gap-2">
              <SignalScore score={signal?.score ?? 0} />
              <span className="text-[11px] font-medium text-foreground">
                {signal?.category || "Qualified"}
              </span>
            </div>
          </div>

          <div className="rounded-xl border border-border/80 bg-muted/15 p-3 space-y-1">
            <span className="text-[11px] text-muted-foreground font-medium">Buying Intent</span>
            <p className="font-semibold text-foreground truncate">
              {signal?.buying_intent || "Buyer Discussion"}
            </p>
          </div>

          <div className="rounded-xl border border-border/80 bg-muted/15 p-3 space-y-1">
            <span className="text-[11px] text-muted-foreground font-medium">Next Recommended Action</span>
            <p className="font-medium text-foreground truncate" title={opp.next_action}>
              {opp.next_action || "Review context"}
            </p>
          </div>

          <div className="rounded-xl border border-border/80 bg-muted/15 p-3 space-y-1">
            <span className="text-[11px] text-muted-foreground font-medium">Opportunity ID</span>
            <p className="font-mono text-[11px] text-muted-foreground truncate" title={opp.id}>
              {opp.id.slice(0, 16)}…
            </p>
          </div>
        </div>
      </section>

      {/* CRM Navigation Tabs */}
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

      {/* Tab 1: Overview */}
      {activeTab === "overview" && (
        <div className="grid gap-5 lg:grid-cols-2">
          {/* Action & Notes Card */}
          <section className="rounded-2xl border border-border bg-card p-5 space-y-4">
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <Target size={15} className="text-primary" />
              Opportunity Follow-up
            </h3>

            <div className="space-y-3 text-xs">
              <div className="rounded-xl border border-primary/25 bg-primary/[0.04] p-3.5 space-y-1">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-primary">
                  Next Action
                </span>
                <p className="text-sm font-medium text-foreground">
                  {opp.next_action || "Review source discussion"}
                </p>
              </div>

              <div className="space-y-1.5">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Reviewer Notes
                </span>
                {opp.notes ? (
                  <div className="rounded-xl border border-border bg-muted/15 p-3.5 text-foreground leading-relaxed">
                    <SafeMarkdown content={opp.notes} compact />
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground italic">
                    No notes recorded yet. Click Edit Details to add context.
                  </p>
                )}
              </div>
            </div>
          </section>

          {/* Why It Matters & Signal Link Card */}
          <section className="rounded-2xl border border-border bg-card p-5 space-y-4">
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <ShieldCheck size={15} className="text-primary" />
              Why this conversation matters
            </h3>

            <div className="space-y-3 text-xs">
              <p className="text-muted-foreground leading-relaxed">
                {signal?.evidence?.explanation ||
                  "This discussion matched your workspace keywords and exhibits commercial intent indicators worth following up on."}
              </p>

              {signal?.evidence?.matched_keywords && signal.evidence.matched_keywords.length > 0 && (
                <div className="space-y-1.5">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Matched criteria
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {signal.evidence.matched_keywords.map((kw) => (
                      <span
                        key={kw}
                        className="rounded-md border border-border bg-muted/40 px-2 py-0.5 text-[11px] font-medium text-foreground"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {signal && (
                <div className="rounded-xl border border-border bg-muted/15 p-3.5 space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[11px] font-semibold text-foreground">
                      Linked Intent Signal
                    </span>
                    <Link
                      href={`/intent-radar/signals/${signal.id}`}
                      className="text-[11px] font-medium text-primary hover:underline inline-flex items-center gap-1"
                    >
                      Open full signal <ArrowUpRight size={11} />
                    </Link>
                  </div>
                  <p className="line-clamp-2 text-xs text-muted-foreground">
                    {signal.title}
                  </p>
                </div>
              )}
            </div>
          </section>
        </div>
      )}

      {/* Tab 2: Evidence */}
      {activeTab === "evidence" && (
        <section className="rounded-2xl border border-border bg-card p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-foreground">
              Original Conversation Evidence
            </h3>
            {signal?.source_url?.startsWith("http") && (
              <a
                href={signal.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-background px-3 py-1.5 text-xs font-semibold text-foreground hover:border-primary/50 hover:text-primary transition-colors"
              >
                Open original discussion <ExternalLink size={12} />
              </a>
            )}
          </div>

          <blockquote className="rounded-xl border-l-4 border-primary/50 bg-muted/20 p-4 text-xs leading-relaxed text-foreground whitespace-pre-line break-words">
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
                  Collapse excerpt <ChevronUp size={13} />
                </>
              ) : (
                <>
                  Show full excerpt ({rawExcerpt.length.toLocaleString()} characters) <ChevronDown size={13} />
                </>
              )}
            </button>
          )}

          <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 border-t border-border/70 pt-3.5 text-xs">
            <div>
              <dt className="text-[11px] text-muted-foreground">Source Provider</dt>
              <dd className="font-medium text-foreground mt-0.5">{signal?.source || "—"}</dd>
            </div>
            <div>
              <dt className="text-[11px] text-muted-foreground">Observed Date</dt>
              <dd className="font-medium text-foreground mt-0.5">
                {formatDateTime(signal?.observed_at)}
              </dd>
            </div>
            <div>
              <dt className="text-[11px] text-muted-foreground">Retrieved Date</dt>
              <dd className="font-medium text-foreground mt-0.5">
                {formatDateTime(signal?.retrieved_at)}
              </dd>
            </div>
            <div>
              <dt className="text-[11px] text-muted-foreground">Public Discussion URL</dt>
              <dd className="font-medium text-foreground mt-0.5 truncate">
                {signal?.source_url ? (
                  <a
                    href={signal.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                  >
                    {signal.source_url.replace(/^https?:\/\//, "")}
                  </a>
                ) : (
                  "—"
                )}
              </dd>
            </div>
          </dl>
        </section>
      )}

      {/* Tab 3: AI Intelligence */}
      {activeTab === "intelligence" && (
        <section className="rounded-2xl border border-border bg-card p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Sparkles size={15} className="text-primary" />
                AI Commercial Intelligence
              </h3>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                Evidence-grounded evaluation of buying intent and targeting fit.
              </p>
            </div>
            {signal?.id && (
              <Link
                href={`/intent-radar/signals/${signal.id}#ai-intelligence`}
                className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 px-3 text-xs font-semibold text-primary hover:bg-primary/15 transition-colors"
              >
                Open Full Signal Intelligence
                <ArrowUpRight size={12} />
              </Link>
            )}
          </div>

          <div className="grid gap-3.5 sm:grid-cols-2 text-xs">
            <div className="rounded-xl border border-border/80 bg-muted/15 p-4 space-y-2">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Buying Intent Evaluation
              </span>
              <p className="text-sm font-semibold text-foreground">
                {signal?.buying_intent || "Buyer Discussion"}
              </p>
              <p className="text-[11px] text-muted-foreground">
                {signal?.buying_intent_basis === "ai_assessed"
                  ? "Assessed from verified public conversation quotes via AI Gateway."
                  : "Derived from source criteria and intent keywords."}
              </p>
            </div>

            <div className="rounded-xl border border-border/80 bg-muted/15 p-4 space-y-2">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Ideal Customer Fit
              </span>
              <p className="text-sm font-semibold text-foreground">
                {signal?.icp_fit || "Unassessed"}
              </p>
              <p className="text-[11px] text-muted-foreground">
                {signal?.icp_fit_detail || "Select an ICP in Signal Details to assess alignment."}
              </p>
            </div>
          </div>

          {signal?.latest_analysis_summary && (
            <div className="rounded-xl border border-border bg-card p-4 space-y-1.5 text-xs">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                AI Synthesis Summary
              </span>
              <p className="text-foreground leading-relaxed">
                {signal.latest_analysis_summary}
              </p>
            </div>
          )}

          <div className="rounded-xl border border-border/70 bg-muted/20 p-3.5 text-xs text-muted-foreground space-y-1">
            <p className="font-semibold text-foreground">Grounded SaaS Safeguard</p>
            <p>
              Evaluations are limited to public text provided. Contact information, individual authority, and purchasing budgets are never assumed or fabricated.
            </p>
          </div>
        </section>
      )}

      {/* Tab 4: Activity & Notes */}
      {activeTab === "activity" && (
        <section className="rounded-2xl border border-border bg-card p-5 space-y-4">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <Clock size={15} className="text-primary" />
              Opportunity Activity &amp; Audit
            </h3>
            {canWrite && (
              <Button size="sm" variant="outline" onClick={() => setEditModalOpen(true)} className="h-7 text-xs">
                Edit Notes
              </Button>
            )}
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex items-start gap-3 rounded-xl border border-border/80 bg-muted/15 p-3.5">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Target size={14} />
              </div>
              <div className="min-w-0 flex-1 space-y-0.5">
                <p className="font-semibold text-foreground">Opportunity Created</p>
                <p className="text-muted-foreground">
                  Promoted from signal with {opp.priority} priority. Next action set to &ldquo;{opp.next_action}&rdquo;.
                </p>
                <span className="text-[11px] text-muted-foreground tabular-nums">
                  {formatDateTime(opp.created_at)}
                </span>
              </div>
            </div>

            {opp.updated_at && opp.updated_at !== opp.created_at && (
              <div className="flex items-start gap-3 rounded-xl border border-border/80 bg-muted/15 p-3.5">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                  <Clock size={14} />
                </div>
                <div className="min-w-0 flex-1 space-y-0.5">
                  <p className="font-semibold text-foreground">Opportunity Updated</p>
                  <p className="text-muted-foreground">
                    Current status: {opp.status} · Priority: {opp.priority}
                    {opp.assigned_to ? ` · Assigned to ${opp.assigned_to}` : ""}
                  </p>
                  <span className="text-[11px] text-muted-foreground tabular-nums">
                    {formatDateTime(opp.updated_at)}
                  </span>
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Edit Details Modal */}
      <OpportunityModal
        opportunity={opp}
        open={editModalOpen}
        onOpenChange={setEditModalOpen}
        canWrite={canWrite}
        onSave={async (patch) => {
          await onUpdate(patch);
          setOpp((prev) => ({ ...prev, ...patch, revision: prev.revision + 1 }));
          setNotice("Opportunity updated.");
        }}
      />

      {/* Delete / Dismiss Confirmation Dialog */}
      {deleteConfirm && (
        <div
          role="alertdialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-[1px] p-4"
        >
          <div className="w-full max-w-md rounded-2xl border border-border bg-card p-5 shadow-2xl space-y-4">
            <h3 className="text-base font-semibold text-foreground">
              Delete Opportunity?
            </h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              This will remove this opportunity record from your workspace. The original signal and its review history will remain preserved.
            </p>
            <div className="flex items-center justify-end gap-2 pt-1">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setDeleteConfirm(false)}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={async () => {
                  setDeleteConfirm(false);
                  await onDelete(opp.id);
                  router.push("/intent-radar/opportunities");
                }}
              >
                Delete Opportunity
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
