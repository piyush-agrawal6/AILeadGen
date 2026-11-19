"use client";

import { useState } from "react";
import {
  Activity,
  CheckCircle2,
  Loader2,
  MessageSquare,
  Send,
  Sparkles,
  User,
} from "lucide-react";
import type { SignalActivityEvent } from "@/lib/intent-radar";
import { Button } from "@/components/ui/button";

export interface ActivityTimelineProps {
  events?: SignalActivityEvent[];
  notes?: string;
  onSaveNotes?: (newNotes: string) => Promise<void>;
  canWrite?: boolean;
  createdAt?: string | null;
  createdBy?: string | null;
}

function formatEventTime(iso?: string | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function ActivityTimeline({
  events = [],
  notes = "",
  onSaveNotes,
  canWrite = true,
  createdAt,
  createdBy,
}: ActivityTimelineProps) {
  const [currentNotes, setCurrentNotes] = useState(notes);
  const [savingNotes, setSavingNotes] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  async function handleNotesSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (savingNotes || !onSaveNotes || !canWrite) return;
    setSavingNotes(true);
    setSavedSuccess(false);
    try {
      await onSaveNotes(currentNotes);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } finally {
      setSavingNotes(false);
    }
  }

  // Combine default creation event if present
  const allEvents = [...events];
  if (createdAt && !allEvents.some((e) => e.kind === "created" || e.kind === "collected")) {
    allEvents.unshift({
      kind: "collected",
      title: "Record Observed",
      detail: "Discovered and indexed by Intent Radar",
      actor: createdBy || "Intent Engine",
      at: createdAt,
    });
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* Activity Timeline Column */}
      <section className="rounded-2xl border border-border bg-card p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Activity size={15} className="text-primary" />
          <h3 className="text-sm font-semibold text-foreground">Activity Timeline</h3>
        </div>

        {allEvents.length === 0 ? (
          <div className="rounded-xl border border-border/80 bg-background p-6 text-center text-xs text-muted-foreground">
            No logged activity events recorded yet.
          </div>
        ) : (
          <div className="relative pl-6 space-y-5 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-border">
            {allEvents.map((evt, idx) => {
              const isAi = evt.kind === "analysis";
              return (
                <div key={idx} className="relative space-y-1 text-xs">
                  <div
                    className={`absolute -left-6 top-0.5 flex h-5 w-5 items-center justify-center rounded-full border ${
                      isAi
                        ? "border-primary/40 bg-primary/10 text-primary"
                        : "border-border bg-card text-muted-foreground"
                    }`}
                  >
                    {isAi ? <Sparkles size={11} /> : <CheckCircle2 size={11} />}
                  </div>

                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-foreground">{evt.title}</span>
                    <span className="text-[10px] text-muted-foreground tabular-nums">
                      {formatEventTime(evt.at)}
                    </span>
                  </div>

                  {evt.detail && (
                    <p className="text-muted-foreground leading-relaxed">{evt.detail}</p>
                  )}

                  {evt.actor && (
                    <span className="inline-flex items-center gap-1 text-[10px] text-muted-foreground">
                      <User size={10} /> {evt.actor}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Internal Notes Column */}
      <section className="rounded-2xl border border-border bg-card p-5 space-y-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <MessageSquare size={15} className="text-primary" />
            <h3 className="text-sm font-semibold text-foreground">Internal Notes &amp; Context</h3>
          </div>
          {savedSuccess && (
            <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400 animate-in fade-in">
              Notes saved
            </span>
          )}
        </div>

        {onSaveNotes ? (
          <form onSubmit={handleNotesSubmit} className="space-y-3">
            <textarea
              rows={6}
              value={currentNotes}
              onChange={(e) => setCurrentNotes(e.target.value)}
              placeholder="Record your qualification notes, team decisions, outreach strategy, or key objections..."
              disabled={!canWrite || savingNotes}
              className="w-full rounded-xl border border-border bg-background p-3.5 text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none resize-none leading-relaxed"
            />

            {canWrite && (
              <div className="flex items-center justify-end">
                <Button
                  type="submit"
                  size="sm"
                  disabled={savingNotes || currentNotes === notes}
                  className="gap-1.5"
                >
                  {savingNotes ? (
                    <Loader2 size={13} className="animate-spin" />
                  ) : (
                    <Send size={12} />
                  )}
                  Save Notes
                </Button>
              </div>
            )}
          </form>
        ) : (
          <div className="rounded-xl border border-border/80 bg-background p-4 text-xs text-foreground whitespace-pre-wrap leading-relaxed">
            {notes || "No notes added yet."}
          </div>
        )}
      </section>
    </div>
  );
}
