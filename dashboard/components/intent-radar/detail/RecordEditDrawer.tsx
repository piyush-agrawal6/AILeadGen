"use client";

import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { useQuery } from "@tanstack/react-query";
import { Loader2, Pencil, X } from "lucide-react";
import { request } from "@/lib/intelligence";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface TeamMember {
  id: string;
  email: string;
  display_name: string;
  role: string;
}

export interface RecordEditValues {
  status: string;
  priority?: string;
  assigned_to?: string | null;
  next_action?: string;
  notes?: string;
}

export function RecordEditDrawer({
  open,
  onOpenChange,
  initialValues,
  title = "Edit Record",
  statusOptions = ["New", "Reviewing", "Qualified", "Saved", "Dismissed"],
  showPriority = true,
  showAssignee = true,
  showNextAction = true,
  canWrite = true,
  onSave,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialValues: RecordEditValues;
  title?: string;
  statusOptions?: string[];
  showPriority?: boolean;
  showAssignee?: boolean;
  showNextAction?: boolean;
  canWrite?: boolean;
  onSave: (values: RecordEditValues) => Promise<void>;
}) {
  const membersQuery = useQuery({
    queryKey: ["workspace-members"],
    queryFn: ({ signal }) =>
      request<{ items: TeamMember[] }>("/organization/members", { signal }),
    retry: false,
    enabled: open && showAssignee,
  });

  const [status, setStatus] = useState(initialValues.status || "New");
  const [priority, setPriority] = useState(initialValues.priority || "Medium");
  const [assignedTo, setAssignedTo] = useState(initialValues.assigned_to || "");
  const [nextAction, setNextAction] = useState(initialValues.next_action || "");
  const [notes, setNotes] = useState(initialValues.notes || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setStatus(initialValues.status || "New");
      setPriority(initialValues.priority || "Medium");
      setAssignedTo(initialValues.assigned_to || "");
      setNextAction(initialValues.next_action || "");
      setNotes(initialValues.notes || "");
      setError(null);
    }
  }, [open, initialValues]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (saving || !canWrite) return;
    setSaving(true);
    setError(null);
    try {
      await onSave({
        status,
        ...(showPriority ? { priority } : {}),
        ...(showAssignee ? { assigned_to: assignedTo.trim() || null } : {}),
        ...(showNextAction ? { next_action: nextAction.trim() } : {}),
        notes: notes.trim(),
      });
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update record.");
    } finally {
      setSaving(false);
    }
  }

  const members = membersQuery.data?.items || [];

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs transition-opacity animate-in fade-in" />
        <Dialog.Content className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-border bg-card p-6 shadow-2xl animate-in slide-in-from-right duration-200">
          <div className="flex items-center justify-between border-b border-border/80 pb-4">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
                <Pencil size={15} />
              </div>
              <div>
                <Dialog.Title className="text-base font-semibold text-foreground">
                  {title}
                </Dialog.Title>
                <Dialog.Description className="text-xs text-muted-foreground">
                  Update workflow status, priority, and next actions.
                </Dialog.Description>
              </div>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                aria-label="Close drawer"
              >
                <X size={16} />
              </button>
            </Dialog.Close>
          </div>

          <form onSubmit={handleSubmit} className="flex-1 flex flex-col justify-between overflow-y-auto py-5 space-y-4">
            <div className="space-y-4">
              {error && (
                <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
                  {error}
                </div>
              )}

              {/* Status */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">Status</label>
                <select
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none"
                >
                  {statusOptions.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>

              {/* Priority */}
              {showPriority && (
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Priority</label>
                  <div className="grid grid-cols-3 gap-2">
                    {["High", "Medium", "Low"].map((p) => (
                      <button
                        key={p}
                        type="button"
                        onClick={() => setPriority(p)}
                        className={`rounded-lg border px-3 py-2 text-xs font-semibold transition-colors ${
                          priority === p
                            ? p === "High"
                              ? "border-amber-500 bg-amber-500/15 text-amber-700 dark:text-amber-300"
                              : p === "Medium"
                                ? "border-blue-500 bg-blue-500/15 text-blue-700 dark:text-blue-300"
                                : "border-slate-500 bg-slate-500/15 text-foreground"
                            : "border-border bg-card text-muted-foreground hover:border-border/80"
                        }`}
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Assignee */}
              {showAssignee && (
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Assigned To</label>
                  <select
                    value={assignedTo}
                    onChange={(e) => setAssignedTo(e.target.value)}
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground focus:border-primary focus:outline-none"
                  >
                    <option value="">Unassigned</option>
                    {members.map((m) => (
                      <option key={m.email} value={m.email}>
                        {m.display_name} ({m.email})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Next Action */}
              {showNextAction && (
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Next Action</label>
                  <Input
                    value={nextAction}
                    onChange={(e) => setNextAction(e.target.value)}
                    placeholder="e.g. Follow up regarding vector DB migration"
                    className="h-9 text-xs"
                  />
                </div>
              )}

              {/* Notes */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">Internal Notes</label>
                <textarea
                  rows={4}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Add internal research notes, context, or qualification details..."
                  className="w-full rounded-lg border border-border bg-background p-3 text-xs text-foreground focus:border-primary focus:outline-none resize-none"
                />
              </div>
            </div>

            <div className="border-t border-border/80 pt-4 flex items-center justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onOpenChange(false)}
                disabled={saving}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={saving || !canWrite}
                className="gap-1.5"
              >
                {saving && <Loader2 size={13} className="animate-spin" />}
                Save Changes
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
