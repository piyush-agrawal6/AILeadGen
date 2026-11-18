"use client";

import { useEffect, useState } from "react";
import { Check, X } from "lucide-react";
import type { IntentSearch, SourceId } from "@/lib/intent-radar";
import { Button } from "@/components/ui/button";
import { SourceOptionsEditor } from "../advanced-controls";
import { ProviderLogo } from "../provider-logo";
import { useRadarCapabilities } from "../provider";

export function SourceConfigDrawer({
  sourceId,
  value,
  onChange,
  onClose,
}: {
  sourceId: SourceId | null;
  value: IntentSearch;
  onChange: (value: IntentSearch) => void;
  onClose: () => void;
}) {
  const access = useRadarCapabilities();
  const [savedPing, setSavedPing] = useState(false);

  useEffect(() => {
    if (!sourceId) return;
    setSavedPing(false);
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [sourceId, onClose]);

  if (!sourceId) return null;

  const sourceMeta = access.data?.sources.find((s) => (s.id || "hacker_news") === sourceId);
  const label = sourceMeta?.name || sourceId.replace("_", " ");

  function handleOptionChange(next: IntentSearch) {
    onChange(next);
    setSavedPing(true);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/45 backdrop-blur-[1px]"
      role="dialog"
      aria-modal="true"
      aria-label={`Configure ${label}`}
      onClick={onClose}
    >
      <div
        className="relative flex h-full w-full max-w-md flex-col border-l border-border bg-card shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-border px-5 py-4">
          <div className="flex items-start gap-3 min-w-0">
            <span className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-background shrink-0">
              <ProviderLogo provider={label} size={18} />
            </span>
            <div className="min-w-0 space-y-0.5">
              <h3 className="text-sm font-semibold text-foreground truncate">
                Configure {label}
              </h3>
              {sourceMeta?.coverage && (
                <p className="text-xs text-muted-foreground leading-snug">
                  {sourceMeta.coverage}
                </p>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close source configuration"
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          <SourceOptionsEditor sourceId={sourceId} value={value} onChange={handleOptionChange} />
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-border bg-muted/20 px-5 py-3.5">
          <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
            {savedPing ? (
              <>
                <Check size={13} className="text-emerald-600 dark:text-emerald-400" />
                <span className="text-foreground font-medium">Updated in search draft</span>
              </>
            ) : (
              <span>Changes apply immediately to your draft.</span>
            )}
          </span>
          <Button size="sm" onClick={onClose}>
            Done
          </Button>
        </div>
      </div>
    </div>
  );
}
