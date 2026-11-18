"use client";

import { useEffect } from "react";
import { X } from "lucide-react";
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

  useEffect(() => {
    if (!sourceId) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [sourceId, onClose]);

  if (!sourceId) return null;

  const sourceMeta = access.data?.sources.find((s) => (s.id || "hacker_news") === sourceId);
  const label = sourceMeta?.name || sourceId.replace("_", " ");

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
        <div className="flex items-center justify-between gap-3 border-b border-border px-5 py-4">
          <div className="flex items-center gap-2.5 min-w-0">
            <ProviderLogo provider={label} size={20} />
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-foreground truncate">
                Configure {label}
              </h3>
              {sourceMeta?.coverage && (
                <p className="text-[11px] text-muted-foreground truncate">
                  {sourceMeta.coverage}
                </p>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close source configuration"
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground cursor-pointer"
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          <SourceOptionsEditor sourceId={sourceId} value={value} onChange={onChange} />
        </div>

        <div className="flex items-center justify-between gap-3 border-t border-border bg-muted/20 px-5 py-3.5">
          <span className="text-[11px] text-muted-foreground">
            Changes apply immediately to your search draft.
          </span>
          <Button size="sm" onClick={onClose}>
            Done
          </Button>
        </div>
      </div>
    </div>
  );
}
