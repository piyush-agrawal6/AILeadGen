"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Activity,
  ArrowUpRight,
  CheckCircle2,
  Pencil,
  ShieldCheck,
  Target,
  Trash2,
  UserCheck,
  UserX,
} from "lucide-react";
import type { IntentOpportunity } from "@/lib/intent-radar";
import {useRadarCapabilities} from '../provider';
import { ProviderLogo } from "../provider-logo";
import { Button } from "@/components/ui/button";
import { PrimaryTabs } from "@/components/ui/tabs";
import {
  RecordEditDrawer,
  UnifiedDetailHeader,
  CompactDecisionSummary,
  EvidencePanel,
  ActivityTimeline,
  UnifiedAIAnalysisPanel,
} from "../detail";

type DetailTab = "overview" | "evidence" | "intelligence" | "activity";

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
  const [editDrawerOpen, setEditDrawerOpen] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const actions=useRadarCapabilities().data?.actions_enabled;
  const signal = opp.signal;
  const rawExcerpt = signal?.excerpt || signal?.title || "";

  async function handleDrawerSave(values: {
    status: string;
    priority?: string;
    assigned_to?: string | null;
    next_action?: string;
    notes?: string;
  }) {
    await onUpdate({
      revision: opp.revision,
      status: values.status,
      priority: values.priority || opp.priority,
      assigned_to: values.assigned_to ?? null,
      next_action: values.next_action || opp.next_action,
      notes: values.notes ?? opp.notes,
    });
    setOpp((prev) => ({
      ...prev,
      status: values.status,
      priority: values.priority || prev.priority,
      assigned_to: values.assigned_to ?? null,
      next_action: values.next_action || prev.next_action,
      notes: values.notes ?? prev.notes,
      revision: prev.revision + 1,
    }));
    setNotice("Opportunity updated.");
  }

  // Buying intent tone
  const buyingTone =
    signal?.buying_intent === "Explicit commercial intent"
      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
      : signal?.buying_intent === "Possible commercial intent"
        ? "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300"
        : "border-border bg-muted text-muted-foreground";

  // Tab definitions
  const tabs = [
    { id: "overview", label: "Overview" },
    { id: "evidence", label: "Evidence" },
    { id: "intelligence", label: "AI Intelligence" },
    { id: "activity", label: "Activity & Notes" },
  ];

  return (
    <div className="space-y-5">
      {/* Unified Detail Header */}
      <UnifiedDetailHeader
        backHref="/intent-radar/opportunities"
        backLabel="Back to Opportunities"
        source={signal?.source || "Opportunity"}
        title={signal?.title || "Qualified Opportunity"}
        status={opp.status}
        priority={opp.priority}
        category={signal?.category}
        repo={signal?.evidence?.provenance?.repo}
        observedAt={opp.created_at}
        sourceUrl={signal?.source_url}
        recordType="opportunity"
        recordId={opp.id}
        onOpenEdit={canWrite ? () => setEditDrawerOpen(true) : undefined}
        primaryAction={
          actions&&canWrite&&signal?.available ? <Link className="control" href={'/intent-radar/actions?opportunity='+opp.id}>Take action</Link> : signal?.id ? (
            <Link
              href={`/intent-radar/signals/${signal.id}`}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-semibold text-foreground hover:border-primary/50 hover:text-primary transition-colors"
            >
              <Activity size={13} />
              View Signal
              <ArrowUpRight size={12} />
            </Link>
          ) : null
        }
        menuItems={[
          ...(canWrite
            ? [
                {
                  label: "Delete Opportunity",
                  icon: Trash2,
                  destructive: true,
                  onClick: () => setDeleteConfirm(true),
                },
              ]
            : []),
        ]}
      />

      {/* Notice Banner */}
      {notice && (
        <div
          role="status"
          className="flex items-center justify-between gap-2 rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-2.5 text-xs font-medium text-emerald-700 dark:text-emerald-300"
        >
          <div className="flex items-center gap-2">
            <CheckCircle2 size={14} className="shrink-0" />
            <span>{notice}</span>
          </div>
          <button
            type="button"
            onClick={() => setNotice(null)}
            className="text-muted-foreground hover:text-foreground cursor-pointer text-xs"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Compact Decision Summary Strip */}
      <CompactDecisionSummary
        score={signal?.score ?? 0}
        confidenceOrCategory={signal?.category}
        buyingIntentLabel={signal?.buying_intent || "Buyer Discussion"}
        buyingIntentTone={buyingTone}
        icpFitLabel={signal?.icp_fit || "Unassessed"}
        statusLabel={opp.status}
        priorityLabel={opp.priority}
        recommendedNextStep={
          opp.next_action
            ? `Next action: ${opp.next_action}`
            : "Review original conversation evidence and reach out to the prospect."
        }
        actions={
          canWrite ? (
            <Button
              size="sm"
              variant="outline"
              onClick={() => setEditDrawerOpen(true)}
              className="h-7 text-xs gap-1"
            >
              <Pencil size={11} /> Edit Action
            </Button>
          ) : undefined
        }
      />

      {/* Primary Underline Tabs */}
      <PrimaryTabs
        items={tabs}
        activeId={activeTab}
        onChange={(tabId) => setActiveTab(tabId as DetailTab)}
      />

      {/* Tab 1: Overview */}
      {activeTab === "overview" && (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px] items-start">
          {/* Main Column */}
          <div className="space-y-4 min-w-0">
            {/* Why This Opportunity Matters */}
            <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                  <ShieldCheck size={15} className="text-primary" />
                  Why this conversation matters
                </h3>
                <span className="text-[11px] text-muted-foreground">
                  Relevance: {signal?.score ?? 0}%
                </span>
              </div>

              <p className="text-xs leading-relaxed text-foreground">
                {signal?.evidence?.explanation ||
                  "This discussion matched your workspace discovery criteria and demonstrates commercial intent indicators."}
              </p>

              {/* Matched Keywords */}
              {signal?.evidence?.matched_keywords && signal.evidence.matched_keywords.length > 0 && (
                <div className="space-y-1.5 border-t border-border/70 pt-3">
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
            </section>

            {/* Extracted Discussion Problem / Commercial Context */}
            <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Target size={15} className="text-primary" />
                Buyer Problem &amp; Commercial Context
              </h3>

              {signal?.evidence?.intent_phrase && (
                <div className="rounded-xl border border-primary/20 bg-primary/5 p-3.5 text-xs space-y-1">
                  <span className="font-semibold text-primary">Matched Commercial Intent Phrase:</span>
                  <p className="italic text-foreground">“{signal.evidence.intent_phrase}”</p>
                </div>
              )}

              <div className="rounded-xl border border-border/80 bg-muted/15 p-4 text-xs leading-relaxed text-foreground whitespace-pre-wrap">
                {rawExcerpt.slice(0, 400)}
                {rawExcerpt.length > 400 && "…"}
              </div>

              <div className="flex items-center justify-end">
                <button
                  type="button"
                  onClick={() => setActiveTab("evidence")}
                  className="text-xs font-semibold text-primary hover:underline inline-flex items-center gap-1 cursor-pointer"
                >
                  View full excerpt &amp; provenance <ArrowUpRight size={12} />
                </button>
              </div>
            </section>
          </div>

          {/* Secondary Column: CRM Status, Next Action, Source Info */}
          <div className="space-y-4">
            {/* Status Card */}
            <section className="rounded-2xl border border-border bg-card p-5 space-y-3.5">
              <div className="flex items-center justify-between gap-2 border-b border-border/70 pb-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Opportunity Status
                </h4>
                {canWrite && (
                  <button
                    type="button"
                    onClick={() => setEditDrawerOpen(true)}
                    className="text-xs font-semibold text-primary hover:underline"
                  >
                    Edit
                  </button>
                )}
              </div>

              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-[11px] text-muted-foreground block">Workflow Stage</span>
                  <span className="font-semibold text-foreground mt-0.5 block">{opp.status}</span>
                </div>

                <div>
                  <span className="text-[11px] text-muted-foreground block">Priority Level</span>
                  <span className="font-semibold text-foreground mt-0.5 block">{opp.priority}</span>
                </div>

                <div>
                  <span className="text-[11px] text-muted-foreground block">Assigned Owner</span>
                  {opp.assigned_to ? (
                    <span className="inline-flex items-center gap-1.5 font-medium text-foreground mt-0.5">
                      <UserCheck size={12} className="text-primary" />
                      {opp.assigned_to}
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 text-muted-foreground mt-0.5">
                      <UserX size={12} /> Unassigned
                    </span>
                  )}
                </div>

                <div className="rounded-xl border border-primary/25 bg-primary/[0.04] p-3 space-y-1">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-primary">
                    Next Action
                  </span>
                  <p className="text-xs font-medium text-foreground">
                    {opp.next_action || "Review source discussion"}
                  </p>
                </div>
              </div>
            </section>

            {/* Linked Signal Card */}
            {signal && (
              <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
                <div className="flex items-center justify-between gap-2 border-b border-border/70 pb-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    Originating Signal
                  </h4>
                  <Link
                    href={`/intent-radar/signals/${signal.id}`}
                    className="text-xs font-semibold text-primary hover:underline inline-flex items-center gap-1"
                  >
                    View <ArrowUpRight size={11} />
                  </Link>
                </div>
                <div className="space-y-2 text-xs">
                  <p className="font-medium text-foreground line-clamp-2">{signal.title}</p>
                  <div className="flex items-center gap-1.5 text-muted-foreground">
                    <ProviderLogo provider={signal.source} size={14} />
                    <span>{signal.source}</span>
                    <span>·</span>
                    <span>{signal.score}% match</span>
                  </div>
                </div>
              </section>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Evidence */}
      {activeTab === "evidence" && (
        <EvidencePanel
          source={signal?.source || "Public Source"}
          sourceUrl={signal?.source_url}
          excerpt={rawExcerpt}
          title={signal?.title || opp.next_action}
          evidence={signal?.evidence}
          observedAt={opp.created_at}
        />
      )}

      {/* Tab 3: AI Analysis */}
      {activeTab === "intelligence" && signal?.id && (
        <UnifiedAIAnalysisPanel
          signalId={signal.id}
          available={signal.available}
        />
      )}

      {/* Tab 4: Activity & Notes */}
      {activeTab === "activity" && (
        <ActivityTimeline
          events={signal?.activity || []}
          notes={opp.notes}
          canWrite={canWrite}
          createdAt={opp.created_at}
          createdBy={opp.created_by}
          onSaveNotes={async (newNotes) => {
            await onUpdate({
              revision: opp.revision,
              status: opp.status,
              priority: opp.priority,
              notes: newNotes,
              next_action: opp.next_action,
              assigned_to: opp.assigned_to,
            });
            setOpp((prev) => ({ ...prev, notes: newNotes, revision: prev.revision + 1 }));
            setNotice("Notes updated.");
          }}
        />
      )}

      {/* Slide-over Edit Drawer */}
      <RecordEditDrawer
        open={editDrawerOpen}
        onOpenChange={setEditDrawerOpen}
        title="Edit Opportunity"
        initialValues={{
          status: opp.status,
          priority: opp.priority,
          assigned_to: opp.assigned_to,
          next_action: opp.next_action,
          notes: opp.notes,
        }}
        canWrite={canWrite}
        onSave={handleDrawerSave}
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
