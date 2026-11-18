"use client";

import { useState } from "react";
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Globe,
  Loader2,
  RefreshCw,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import type { SignalAnalysisStructured } from "@/lib/intent-radar";
import { useRadarCapabilities, useRadarMutation, useRadarRead } from "../provider";

interface Claim {
  kind: string;
  quote: string;
  interpretation: string;
  target?: string;
  translation?: string;
}

interface CriterionAssessment {
  criterion: string;
  status: string;
  quote: string;
  explanation: string;
  basis: string;
}

export interface SignalAnalysisRecord {
  mode: string;
  model: string | null;
  provider?: string | null;
  version?: string;
  analysis_at?: string;
  fallback_reason: string | null;
  source_url?: string;
  summary_language?: string | null;
  icp: { id?: string; name: string; revision: number } | null;
  interpretation: {
    categories: string[];
    claims: Claim[];
    uncertainty: string;
    review_needed: boolean;
    summary?: Claim | null;
    buyer_problem?: Claim | null;
    business_relevance?: Claim | null;
    detected_language?: string;
    language_evidence?: string;
    icp_assessments?: CriterionAssessment[];
  } | null;
  scoring: {
    version?: string;
    overall: number;
    tier: string;
    intent_strength: string;
    icp_fit: string;
    dimensions: Record<string, number>;
    unknown: string[];
  };
  structured?: SignalAnalysisStructured;
  recommendation: string;
  cached: boolean;
}

const LANGUAGES = [
  { code: "en", label: "English (en)" },
  { code: "es", label: "Spanish (es)" },
  { code: "fr", label: "French (fr)" },
  { code: "de", label: "German (de)" },
  { code: "pt", label: "Portuguese (pt)" },
  { code: "hi", label: "Hindi (hi)" },
  { code: "ja", label: "Japanese (ja)" },
];

function buyingIntentBadge(value: string): string {
  if (value === "Explicit commercial intent") {
    return "border-emerald-500/30 bg-emerald-500/12 text-emerald-700 dark:text-emerald-300";
  }
  if (value === "Possible commercial intent") {
    return "border-amber-500/30 bg-amber-500/12 text-amber-700 dark:text-amber-300";
  }
  return "border-border bg-muted/60 text-muted-foreground";
}

export function SignalIntelligencePanel({
  id,
  monitorId,
}: {
  id: string;
  monitorId?: string;
}) {
  const history = useRadarRead<{
    items: SignalAnalysisRecord[];
    feedback: { items: { actor: string; label: string; note?: string; active: number; updated_at?: string }[]; ranking_adjustment: number };
  }>(`/signals/${id}/analysis`);
  const icps = useRadarRead<{ items: { id: string; name: string }[] }>("/icps");
  const access = useRadarCapabilities();
  const mutation = useRadarMutation();

  const [selectedIcp, setSelectedIcp] = useState("");
  const [showTranslate, setShowTranslate] = useState(false);
  const [translateLang, setTranslateLang] = useState("en");
  const [localResult, setLocalResult] = useState<SignalAnalysisRecord | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [showEvidenceDetail, setShowEvidenceDetail] = useState(false);

  const refreshed = localResult?.analysis_at
    ? history.data?.items?.find((i) => i.analysis_at === localResult.analysis_at)
    : undefined;
  const current = refreshed || localResult || history.data?.items?.find((i) => !!i.scoring) || null;
  const canManage = !!access.data?.can_manage;

  async function runAnalysis(summaryLanguage: string | null = null) {
    if (!canManage || submitting || mutation.isPending) return;
    setError("");
    setSubmitting(true);
    try {
      const res = (await mutation.mutateAsync({
        path: `/signals/${id}/analysis`,
        body: {
          icp_id: selectedIcp || null,
          monitor_id: monitorId || null,
          ...(summaryLanguage ? { summary_language: summaryLanguage } : {}),
        },
      })) as SignalAnalysisRecord;
      setLocalResult(res);
    } catch (e) {
      setError((e as Error).message || "AI analysis failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  const structured: SignalAnalysisStructured | null = current
    ? current.structured || {
        summary: current.interpretation?.summary?.interpretation || null,
        problem: current.interpretation?.buyer_problem?.interpretation || null,
        topic_relevance: current.interpretation?.business_relevance?.interpretation || null,
        buying_intent:
          current.scoring.intent_strength === "Explicit evidence"
            ? "Explicit commercial intent"
            : current.scoring.intent_strength === "Contradictory / non-buying"
              ? "No demonstrated commercial intent"
              : "Insufficient evidence",
        icp_fit: current.icp
          ? `${current.icp.name}: ${current.scoring.icp_fit}`
          : "Unassessed — no ICP selected",
        recommended_next_step: current.recommendation || "Read original discussion",
        source_statements: (current.interpretation?.claims || []).map((c) => c.quote).filter(Boolean),
        model_inferences: (current.interpretation?.claims || []).map((c) => c.interpretation).filter(Boolean),
        unknowns: current.scoring.unknown || [],
      }
    : null;

  const isPolicyGated = current?.mode === "Policy gated";
  const isQuotaExhausted =
    Boolean(current?.fallback_reason?.toLowerCase().includes("budget")) ||
    Boolean(error.toLowerCase().includes("budget") || error.toLowerCase().includes("quota") || error.toLowerCase().includes("limit"));

  return (
    <section className="rounded-2xl border border-border bg-card p-5 space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
            <Sparkles size={16} className="text-primary" />
            AI Intelligence & ICP Fit
          </h2>
          <p className="text-xs text-muted-foreground">
            Evidence-grounded evaluation through the shared AI gateway. Every claim cites verbatim source text.
          </p>
        </div>
        {current?.cached && (
          <span className="rounded-full border border-border bg-muted/50 px-2.5 py-0.5 text-[11px] font-medium text-muted-foreground">
            Cached analysis
          </span>
        )}
      </div>

      {/* Primary Control Bar: ONE clear primary CTA + optional ICP selector */}
      <div className="flex flex-wrap items-end gap-2.5 rounded-xl border border-border/80 bg-muted/20 p-3.5">
        <label className="flex-1 min-w-[200px] space-y-1">
          <span className="text-[11px] font-medium text-muted-foreground">Evaluate against ICP (optional)</span>
          <select
            value={selectedIcp}
            onChange={(e) => setSelectedIcp(e.target.value)}
            aria-label="ICP for analysis"
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground"
          >
            <option value="">No ICP selected (evaluate signal only)</option>
            {(icps.data?.items || []).map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>

        <button
          type="button"
          disabled={!canManage || submitting || mutation.isPending}
          onClick={() => void runAnalysis(null)}
          className="ir-primary inline-flex h-9 items-center gap-1.5 rounded-lg px-4 text-xs font-semibold hover:opacity-90 disabled:opacity-50 cursor-pointer"
        >
          {submitting ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
          {submitting ? "Analyzing signal…" : current ? "Re-analyze Signal" : "Analyze Signal"}
        </button>

        <button
          type="button"
          onClick={() => setShowTranslate((v) => !v)}
          className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-xs font-medium text-muted-foreground hover:text-foreground cursor-pointer"
        >
          <Globe size={13} />
          Translate
          {showTranslate ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </button>
      </div>

      {/* Secondary Collapsible Translation Control */}
      {showTranslate && (
        <div className="flex flex-wrap items-center gap-2.5 rounded-xl border border-border/70 bg-background px-3.5 py-2.5">
          <span className="text-xs text-muted-foreground">Optional translated summary (preserves original quotes):</span>
          <select
            value={translateLang}
            onChange={(e) => setTranslateLang(e.target.value)}
            aria-label="Translation language"
            style={{ width: "auto" }}
            className="rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs text-foreground"
          >
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={!canManage || submitting || mutation.isPending}
            onClick={() => void runAnalysis(translateLang)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground hover:border-primary/50 hover:text-primary disabled:opacity-50 cursor-pointer"
          >
            Run with translation
          </button>
        </div>
      )}

      {/* Policy Gated Banner (YouTube / Discourse) */}
      {isPolicyGated && (
        <div className="flex items-start gap-2.5 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5 text-xs text-amber-800 dark:text-amber-200">
          <ShieldAlert size={16} className="shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold">AI analytics policy gate active</p>
            <p>{current.fallback_reason}</p>
          </div>
        </div>
      )}

      {/* Quota Exhausted / Error Recovery Banner */}
      {(error || (current?.fallback_reason && !isPolicyGated)) && (
        <div
          role="alert"
          className="flex items-start justify-between gap-3 rounded-xl border border-destructive/30 bg-destructive/10 p-3.5 text-xs text-destructive"
        >
          <div className="flex items-start gap-2">
            <AlertTriangle size={15} className="shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <p className="font-semibold">
                {isQuotaExhausted ? "AI analysis quota reached" : "Analysis notice"}
              </p>
              <p>{error || current?.fallback_reason}</p>
            </div>
          </div>
          {error && !isQuotaExhausted && (
            <button
              type="button"
              onClick={() => void runAnalysis(null)}
              className="inline-flex items-center gap-1 rounded-lg border border-destructive/40 bg-background px-2.5 py-1 text-xs font-medium text-foreground hover:bg-muted cursor-pointer shrink-0"
            >
              <RefreshCw size={12} /> Retry
            </button>
          )}
        </div>
      )}

      {/* Structured AI Output */}
      {current && structured && !isPolicyGated ? (
        <div className="space-y-4">
          {/* Key Assessment Strip */}
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-border bg-background p-3 space-y-1">
              <span className="text-[11px] font-medium text-muted-foreground">Buying Intent</span>
              <div>
                <span
                  className={
                    "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold " +
                    buyingIntentBadge(structured.buying_intent)
                  }
                >
                  {structured.buying_intent}
                </span>
              </div>
            </div>

            <div className="rounded-xl border border-border bg-background p-3 space-y-1">
              <span className="text-[11px] font-medium text-muted-foreground">ICP Fit</span>
              <p className="text-xs font-medium text-foreground leading-snug">{structured.icp_fit}</p>
            </div>

            <div className="rounded-xl border border-border bg-background p-3 space-y-1">
              <span className="text-[11px] font-medium text-muted-foreground">Recommended Next Step</span>
              <p className="text-xs font-medium text-foreground leading-snug">
                {structured.recommended_next_step}
              </p>
            </div>
          </div>

          {/* Concise Summary / Problem / Business Relevance */}
          <div className="space-y-2.5 rounded-xl border border-border/80 bg-muted/15 p-4">
            {structured.summary && (
              <div>
                <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Summary
                </h3>
                <p className="mt-1 text-xs leading-relaxed text-foreground">{structured.summary}</p>
              </div>
            )}
            {structured.problem && (
              <div>
                <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Stated Problem
                </h3>
                <p className="mt-1 text-xs leading-relaxed text-foreground">{structured.problem}</p>
              </div>
            )}
            {structured.topic_relevance && (
              <div>
                <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Topic & Business Relevance
                </h3>
                <p className="mt-1 text-xs leading-relaxed text-foreground">{structured.topic_relevance}</p>
              </div>
            )}
            {!structured.summary && !structured.problem && !structured.topic_relevance && (
              <p className="text-xs text-muted-foreground">
                Deterministic review completed ({current.scoring.overall}/100 relevance). No AI narrative summary was returned for this signal.
              </p>
            )}
          </div>

          {/* Explicit separation: Source statements vs Model inferences vs Unknowns */}
          <div className="border-t border-border/70 pt-2">
            <button
              type="button"
              onClick={() => setShowEvidenceDetail((v) => !v)}
              style={{ justifyContent: "space-between" }}
              className="flex w-full items-center justify-between py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground cursor-pointer"
            >
              <span>Cited source evidence, inferences, unknowns & diagnostics</span>
              {showEvidenceDetail ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>

            {showEvidenceDetail && (
              <div className="mt-2 space-y-3 rounded-xl border border-border/80 bg-background p-4 text-xs">
                {structured.source_statements.length > 0 && (
                  <div className="space-y-1.5">
                    <h4 className="font-semibold text-foreground">Direct source statements (verbatim quotes)</h4>
                    <ul className="space-y-1.5">
                      {structured.source_statements.map((quote, idx) => (
                        <li
                          key={idx}
                          className="border-l-2 border-primary/40 pl-2.5 italic text-foreground/90"
                        >
                          “{quote}”
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {structured.model_inferences.length > 0 && (
                  <div className="space-y-1">
                    <h4 className="font-semibold text-foreground">Model inferences (require human verification)</h4>
                    <ul className="list-disc pl-4 space-y-1 text-muted-foreground">
                      {structured.model_inferences.map((inf, idx) => (
                        <li key={idx}>{inf}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {current.interpretation?.icp_assessments && current.interpretation.icp_assessments.length > 0 && (
                  <div className="space-y-1.5">
                    <h4 className="font-semibold text-foreground">Selected ICP criterion checks</h4>
                    <div className="space-y-1.5">
                      {current.interpretation.icp_assessments.map((item) => (
                        <div key={item.criterion} className="rounded-lg border border-border/70 p-2.5">
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-medium text-foreground">{item.criterion}</span>
                            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-semibold">
                              {item.status}
                            </span>
                          </div>
                          <p className="mt-1 text-muted-foreground">{item.explanation}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {structured.unknowns.length > 0 && (
                  <div className="space-y-1">
                    <h4 className="font-semibold text-foreground">Unverified / unknown attributes</h4>
                    <p className="text-muted-foreground">{structured.unknowns.join(" · ")}</p>
                  </div>
                )}

                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-border/60 pt-2 text-[11px] text-muted-foreground">
                  <span>Mode: {current.mode}</span>
                  <span>Score: {current.scoring.overall}/100 ({current.scoring.tier})</span>
                  {current.model && <span>Model: {current.model}</span>}
                  {current.analysis_at && (
                    <span>Analyzed: {new Date(current.analysis_at).toLocaleString()}</span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      ) : !current ? (
        <p className="text-xs text-muted-foreground">
          No AI analysis has been run for this signal yet. Click <strong>Analyze Signal</strong> to evaluate commercial intent, problem context, and optional ICP fit.
        </p>
      ) : null}

      {!canManage && (
        <p className="text-[11px] text-muted-foreground">
          Workspace Admin or Owner role is required to run new AI analyses.
        </p>
      )}
    </section>
  );
}
