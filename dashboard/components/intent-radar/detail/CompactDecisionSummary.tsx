"use client";

import { SignalScore } from "../signals";

export interface CompactDecisionSummaryProps {
  score: number;
  confidenceOrCategory?: string;
  buyingIntentLabel: string;
  buyingIntentTone: string;
  icpFitLabel: string;
  statusLabel: string;
  priorityLabel?: string;
  recommendedNextStep: string;
  actions?: React.ReactNode;
}

export function CompactDecisionSummary({
  score,
  confidenceOrCategory,
  buyingIntentLabel,
  buyingIntentTone,
  icpFitLabel,
  statusLabel,
  priorityLabel,
  recommendedNextStep,
  actions,
}: CompactDecisionSummaryProps) {
  return (
    <section className="rounded-2xl border border-border bg-card p-4 sm:p-5 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-foreground">Decision Summary</h2>
        <span className="text-[11px] text-muted-foreground">
          Scores reflect observed public text only, never verified budget or buying authority.
        </span>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {/* Metric 1: Topic Relevance */}
        <div className="rounded-xl border border-border/80 bg-background p-3 space-y-1">
          <span className="text-[11px] font-medium text-muted-foreground">Topic Relevance</span>
          <div className="flex items-center gap-2">
            <SignalScore score={score} />
            <span className="text-xs font-semibold text-foreground truncate">
              {confidenceOrCategory || `${score}% Match`}
            </span>
          </div>
        </div>

        {/* Metric 2: Buying Intent */}
        <div className="rounded-xl border border-border/80 bg-background p-3 space-y-1">
          <span className="text-[11px] font-medium text-muted-foreground">Buying Intent</span>
          <div>
            <span
              className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold ${buyingIntentTone}`}
            >
              {buyingIntentLabel}
            </span>
          </div>
        </div>

        {/* Metric 3: ICP Fit */}
        <div className="rounded-xl border border-border/80 bg-background p-3 space-y-1">
          <span className="text-[11px] font-medium text-muted-foreground">ICP Fit</span>
          <p className="text-xs font-semibold text-foreground">
            {icpFitLabel && icpFitLabel !== "Unassessed" ? icpFitLabel : "Unassessed"}
          </p>
        </div>

        {/* Metric 4: Status & Priority */}
        <div className="rounded-xl border border-border/80 bg-background p-3 space-y-1">
          <span className="text-[11px] font-medium text-muted-foreground">Workflow Status</span>
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xs font-semibold text-foreground">
              {statusLabel}
            </span>
            {priorityLabel && (
              <span className="text-[10px] text-muted-foreground">
                ({priorityLabel} Priority)
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Recommended Next Step Strip */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/70 bg-muted/20 px-4 py-3">
        <div className="space-y-0.5 text-xs max-w-2xl">
          <span className="font-semibold text-foreground">Recommended next step: </span>
          <span className="text-muted-foreground">{recommendedNextStep}</span>
        </div>

        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </section>
  );
}
