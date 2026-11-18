"use client";

import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { useQuery } from "@tanstack/react-query";
import { Loader2, Target, X } from "lucide-react";
import type { IntentOpportunity } from "@/lib/intent-radar";
import { request } from "@/lib/intelligence";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface TeamMember {
  id: string;
  email: string;
  display_name: string;
  role: string;
}

export function OpportunityModal({
  opportunity,
  open,
  onOpenChange,
  onSave,
  canWrite = true,
}: {
  opportunity: IntentOpportunity | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (patch: {
    revision: number;
    status: string;
    priority: string;
    notes: string;
    next_action: string;
    assigned_to: string | null;
  }) => Promise<void>;
  canWrite?: boolean;
}) {
  const membersQuery = useQuery({
    queryKey: ["workspace-members"],
    queryFn: ({ signal }) =>
      request<{ items: TeamMember[] }>("/organization/members", { signal }),
    retry: false,
    enabled: open,
  });

  const [status, setStatus] = useState("New");
  const [priority, setPriority] = useState("Medium");
  const [notes, setNotes] = useState("");
  const [nextAction, setNextAction] = useState("");
  const [assignedTo, setAssignedTo] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (opportunity) {
      setStatus(opportunity.status || "New");
      setPriority(opportunity.priority || "Medium");
      setNotes(opportunity.notes || "");
      setNextAction(opportunity.next_action || "Review context");
      setAssignedTo(opportunity.assigned_to || "");
      setError(null);
    }
  }, [opportunity]);

  if (!opportunity) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (submitting || !canWrite) return;
    setSubmitting(true);
    setError(null);
    try {
      await onSave({
        revision: opportunity!.revision,
        status,
        priority,
        notes,
        next_action: nextAction.trim() || "Review context",
        assigned_to: assignedTo.trim() || null,
      });
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update opportunity.");
    } finally {
      setSubmitting(false);
    }
  }

  const members = membersQuery.data?.items || [];

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[1px]" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 flex w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 flex-col rounded-2xl border border-border bg-card p-5 shadow-2xl space-y-4">
          <div className="flex items-start justify-between gap-3 border-b border-border/70 pb-3">
            <div className="min-w-0">
              <Dialog.Title className="text-base font-semibold text-foreground flex items-center gap-2">
                <Target size={16} className="text-primary" />
                Edit Opportunity
              </Dialog.Title>
              <Dialog.Description className="text-xs text-muted-foreground mt-0.5 truncate">
                {opportunity.signal?.title || "Update opportunity details & assignments"}
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                className="rounded-lg p-1 text-muted-foreground hover:bg-muted"
                aria-label="Close"
              >
                <X size={16} />
              </button>
            </Dialog.Close>
          </div>

          <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4 text-xs">
            {error && (
              <div
                role="alert"
                className="rounded-xl border border-destructive/25 bg-destructive/5 p-3 text-destructive"
              >
                {error}
              </div>
            )}

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label htmlFor="opp-edit-status" className="font-medium text-foreground">
                  Status
                </label>
                <select
                  id="opp-edit-status"
                  value={status}
                  disabled={submitting || !canWrite}
                  onChange={(e) => setStatus(e.target.value)}
                  className="h-8 w-full rounded-lg border border-border bg-background px-2.5 text-xs text-foreground"
                >
                  <option value="New">New</option>
                  <option value="Reviewing">Reviewing</option>
                  <option value="Qualified">Qualified</option>
                  <option value="Saved">Saved</option>
                  <option value="Dismissed">Dismissed</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label htmlFor="opp-edit-priority" className="font-medium text-foreground">
                  Priority
                </label>
                <select
                  id="opp-edit-priority"
                  value={priority}
                  disabled={submitting || !canWrite}
                  onChange={(e) => setPriority(e.target.value)}
                  className="h-8 w-full rounded-lg border border-border bg-background px-2.5 text-xs text-foreground"
                >
                  <option value="High">High</option>
                  <option value="Medium">Medium</option>
                  <option value="Low">Low</option>
                </select>
              </div>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="opp-edit-assignee" className="font-medium text-foreground">
                Assigned Reviewer
              </label>
              <select
                id="opp-edit-assignee"
                value={assignedTo}
                disabled={submitting || !canWrite}
                onChange={(e) => setAssignedTo(e.target.value)}
                className="h-8 w-full rounded-lg border border-border bg-background px-2.5 text-xs text-foreground"
              >
                <option value="">Unassigned</option>
                {members.map((m) => (
                  <option key={m.email} value={m.email}>
                    {m.display_name} ({m.email})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="opp-edit-action" className="font-medium text-foreground">
                Recommended Next Action
              </label>
              <Input
                id="opp-edit-action"
                value={nextAction}
                maxLength={300}
                disabled={submitting || !canWrite}
                onChange={(e) => setNextAction(e.target.value)}
                placeholder="e.g. Reach out via public discussion or explore team context"
                className="h-8 text-xs"
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="opp-edit-notes" className="font-medium text-foreground">
                Opportunity Notes
              </label>
              <textarea
                id="opp-edit-notes"
                rows={3}
                maxLength={4000}
                value={notes}
                disabled={submitting || !canWrite}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="What makes this conversation actionable? Add qualification notes or customer context…"
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-border/70 pt-3">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onOpenChange(false)}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={submitting || !canWrite}>
                {submitting ? (
                  <>
                    <Loader2 size={13} className="animate-spin mr-1.5" />
                    Saving…
                  </>
                ) : (
                  "Save Changes"
                )}
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
