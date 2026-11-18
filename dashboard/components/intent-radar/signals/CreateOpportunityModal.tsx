"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, CheckCircle2, ExternalLink, Loader2, Target, X } from "lucide-react";
import type { IntentSignal } from "@/lib/intent-radar";
import { useRadarMutation } from "../provider";

interface CreateOpportunityModalProps {
  signal: IntentSignal | null;
  open: boolean;
  onClose: () => void;
  onCreated?: (opportunityId: string) => void;
}

export function CreateOpportunityModal({
  signal,
  open,
  onClose,
  onCreated,
}: CreateOpportunityModalProps) {
  const mutation = useRadarMutation();
  const [priority, setPriority] = useState<"High" | "Medium" | "Low">("Medium");
  const [nextAction, setNextAction] = useState("Review context and verify fit");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open || !signal) return;
    setPriority(signal.score >= 85 ? "High" : signal.score >= 60 ? "Medium" : "Low");
    setNextAction("Review original discussion and verify company context");
    setNotes(
      signal.notes ||
        signal.latest_analysis_summary ||
        signal.opportunity_eligibility?.intent_quote ||
        ""
    );
    setError("");
  }, [open, signal]);

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

  const eligibility = signal.opportunity_eligibility;
  const eligible = eligibility ? eligibility.eligible : true;
  const alreadyLinked = Boolean(signal.opportunity_id);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!signal || !eligible || alreadyLinked) return;
    setError("");
    try {
      const res = (await mutation.mutateAsync({
        path: `/opportunities/${signal.id}`,
        method: "POST",
        body: {
          priority,
          notes: notes.trim(),
          next_action: nextAction.trim() || "Review context",
        },
      })) as { id?: string };
      onCreated?.(res?.id || "");
      onClose();
    } catch (err) {
      setError((err as Error).message || "Could not create opportunity.");
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-[1px]"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-opp-title"
    >
      <div
        className="w-full max-w-lg rounded-2xl border border-border bg-card shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
          <div className="min-w-0">
            <h2 id="create-opp-title" className="text-base font-semibold text-foreground flex items-center gap-2">
              <Target size={16} className="text-primary shrink-0" />
              {alreadyLinked ? "Linked Opportunity" : "Create Opportunity"}
            </h2>
            <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{signal.title}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close modal"
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-transparent text-muted-foreground hover:bg-muted hover:text-foreground cursor-pointer"
          >
            <X size={16} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Anti-duplication check */}
          {alreadyLinked ? (
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 space-y-2.5">
              <div className="flex items-center gap-2 text-sm font-semibold text-emerald-700 dark:text-emerald-300">
                <CheckCircle2 size={16} />
                An opportunity already exists for this signal
              </div>
              <p className="text-xs text-muted-foreground">
                Duplicate opportunities are prevented automatically. Current status:{" "}
                <strong className="text-foreground">{signal.opportunity_status || "Saved"}</strong>.
              </p>
              <div className="flex items-center gap-2 pt-1">
                <Link
                  href={`/intent-radar/opportunities/${signal.opportunity_id}`}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:opacity-90"
                >
                  Open Opportunity <ExternalLink size={13} />
                </Link>
                <button
                  type="button"
                  onClick={onClose}
                  className="inline-flex items-center rounded-lg border border-border bg-background px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted cursor-pointer"
                >
                  Close
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Readiness Evaluation */}
              <div
                className={
                  "rounded-xl border p-3.5 space-y-1.5 " +
                  (eligible
                    ? "border-emerald-500/25 bg-emerald-500/[0.06]"
                    : "border-amber-500/30 bg-amber-500/[0.08]")
                }
              >
                <div className="flex items-center gap-2 text-xs font-semibold">
                  {eligible ? (
                    <>
                      <CheckCircle2 size={14} className="text-emerald-600 dark:text-emerald-400 shrink-0" />
                      <span className="text-emerald-700 dark:text-emerald-300">
                        Opportunity readiness check passed
                      </span>
                    </>
                  ) : (
                    <>
                      <AlertTriangle size={14} className="text-amber-600 dark:text-amber-400 shrink-0" />
                      <span className="text-amber-700 dark:text-amber-300">
                        Additional commercial evidence required before creating an opportunity
                      </span>
                    </>
                  )}
                </div>
                {eligibility?.intent_quote && (
                  <p className="text-xs italic text-foreground/90 border-l-2 border-primary/40 pl-2.5">
                    “{eligibility.intent_quote}”
                  </p>
                )}
                {eligibility?.reasons && eligibility.reasons.length > 0 && (
                  <ul className="list-disc pl-4 space-y-0.5 text-xs text-muted-foreground">
                    {eligibility.reasons.map((r) => (
                      <li key={r}>{r}</li>
                    ))}
                  </ul>
                )}
                <p className="text-[11px] text-muted-foreground">
                  {eligibility?.basis ||
                    "Derived from observed public discussion only. No private contacts, budget, or buyer identity are fabricated."}
                </p>
              </div>

              {eligible && (
                <form onSubmit={(e) => void handleSubmit(e)} className="space-y-3.5">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <label className="block space-y-1">
                      <span className="text-xs font-medium text-foreground">Priority</span>
                      <select
                        value={priority}
                        onChange={(e) => setPriority(e.target.value as "High" | "Medium" | "Low")}
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground"
                      >
                        <option value="High">High</option>
                        <option value="Medium">Medium</option>
                        <option value="Low">Low</option>
                      </select>
                    </label>
                    <label className="block space-y-1">
                      <span className="text-xs font-medium text-foreground">Recommended next action</span>
                      <input
                        type="text"
                        maxLength={300}
                        value={nextAction}
                        onChange={(e) => setNextAction(e.target.value)}
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground"
                      />
                    </label>
                  </div>

                  <label className="block space-y-1">
                    <span className="text-xs font-medium text-foreground">
                      Opportunity notes (editable)
                    </span>
                    <textarea
                      rows={3}
                      maxLength={4000}
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="Summarize the stated need, rationale, and unknowns to verify..."
                      className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground"
                    />
                  </label>

                  {error && (
                    <p role="alert" className="text-xs text-destructive">
                      {error}
                    </p>
                  )}

                  <div className="flex items-center justify-end gap-2 pt-1">
                    <button
                      type="button"
                      onClick={onClose}
                      className="inline-flex items-center rounded-lg border border-border bg-background px-3.5 py-2 text-xs font-medium text-foreground hover:bg-muted cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={mutation.isPending}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-50 cursor-pointer"
                    >
                      {mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Target size={14} />}
                      Confirm & Create Opportunity
                    </button>
                  </div>
                </form>
              )}

              {!eligible && (
                <div className="flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={onClose}
                    className="inline-flex items-center rounded-lg border border-border bg-background px-3.5 py-2 text-xs font-medium text-foreground hover:bg-muted cursor-pointer"
                  >
                    Close
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
