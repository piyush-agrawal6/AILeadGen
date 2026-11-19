"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import * as Menu from "@radix-ui/react-dropdown-menu";
import {
  ArrowLeft,
  ArrowUpRight,
  Bookmark,
  ChevronLeft,
  ChevronRight,
  Copy,
  ExternalLink,
  MoreHorizontal,
  Pencil,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { ProviderLogo } from "../provider-logo";
import { Button } from "@/components/ui/button";

interface HeaderMenuItem {
  label: string;
  icon?: React.ComponentType<{ size?: number; className?: string }>;
  onClick: () => void;
  destructive?: boolean;
}

export function UnifiedDetailHeader({
  backHref,
  backLabel,
  prevHref,
  nextHref,
  source,
  title,
  status,
  priority,
  category,
  repo,
  observedAt,
  sourceUrl,
  recordType = "signal",
  recordId,
  isSaved,
  onToggleSave,
  onOpenEdit,
  primaryAction,
  menuItems = [],
}: {
  backHref: string;
  backLabel: string;
  prevHref?: string | null;
  nextHref?: string | null;
  source: string;
  title: string;
  status: string;
  priority?: string;
  category?: string;
  repo?: string | null;
  observedAt?: string | null;
  sourceUrl?: string | null;
  recordType?: "signal" | "opportunity";
  recordId: string;
  isSaved?: boolean;
  onToggleSave?: () => void;
  onOpenEdit?: () => void;
  primaryAction?: React.ReactNode;
  menuItems?: HeaderMenuItem[];
}) {
  const router = useRouter();

  const formattedDate = observedAt
    ? (() => {
        try {
          const d = new Date(observedAt);
          return d.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
          });
        } catch {
          return observedAt;
        }
      })()
    : null;

  function handleCopyLink() {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
      toast.success("Copied record link to clipboard");
    }
  }

  // Priority color
  const priorityClasses =
    priority === "High"
      ? "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300"
      : priority === "Medium"
        ? "border-blue-500/30 bg-blue-500/10 text-blue-700 dark:text-blue-300"
        : "border-border bg-muted text-muted-foreground";

  // Status color
  const statusClasses =
    status === "Qualified"
      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
      : status === "Reviewing" || status === "Needs Review"
        ? "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300"
        : status === "Saved"
          ? "border-primary/30 bg-primary/10 text-primary"
          : status === "Dismissed"
            ? "border-border bg-muted text-muted-foreground"
            : "border-blue-500/20 bg-blue-500/10 text-blue-700 dark:text-blue-300";

  return (
    <div className="space-y-4">
      {/* Navigation Top Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/70 pb-3">
        <Link
          href={backHref}
          className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-semibold text-foreground hover:border-primary/50 hover:text-primary transition-colors"
        >
          <ArrowLeft size={14} />
          {backLabel}
        </Link>

        <div className="flex items-center gap-1.5">
          <Link
            href={`/intelligence/assistant?context=${recordType}&entityId=${encodeURIComponent(recordId)}&prompt=${encodeURIComponent(`Analyze this ${recordType} ("${title.slice(0, 80)}") against my ICP and suggest next actions.`)}`}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 px-2.5 text-xs font-semibold text-primary hover:bg-primary/15 transition-colors"
          >
            <Sparkles size={13} />
            Ask AI
          </Link>

          <Button
            variant="outline"
            size="sm"
            aria-label={recordType === "opportunity" ? "Previous Opportunity" : "Previous Signal"}
            disabled={!prevHref}
            onClick={() => prevHref && router.push(prevHref)}
            className="h-8 gap-1 px-2.5 text-xs"
          >
            <ChevronLeft size={14} /> Prev
          </Button>

          <Button
            variant="outline"
            size="sm"
            aria-label={recordType === "opportunity" ? "Next Opportunity" : "Next Signal"}
            disabled={!nextHref}
            onClick={() => nextHref && router.push(nextHref)}
            className="h-8 gap-1 px-2.5 text-xs"
          >
            Next <ChevronRight size={14} />
          </Button>
        </div>
      </div>

      {/* Record Title & Badges */}
      <header className="space-y-3">
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5 font-semibold text-foreground">
            <ProviderLogo provider={source} size={18} />
            <span>{source}</span>
          </span>

          {repo && (
            <span className="rounded-md border border-border bg-muted/40 px-2 py-0.5 text-[11px] font-medium text-foreground">
              {repo}
            </span>
          )}

          {category && (
            <span className="rounded-full border border-border bg-muted/40 px-2.5 py-0.5 text-[11px] font-medium text-foreground">
              {category}
            </span>
          )}

          <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${statusClasses}`}>
            {status}
          </span>

          {priority && (
            <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${priorityClasses}`}>
              {priority} Priority
            </span>
          )}

          {isSaved && (
            <span className="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
              <Bookmark size={11} fill="currentColor" /> Saved
            </span>
          )}

          {formattedDate && (
            <span className="whitespace-nowrap text-muted-foreground">
              {recordType === "opportunity" ? "Created" : "Observed"} {formattedDate}
            </span>
          )}
        </div>

        <div className="flex flex-wrap items-start justify-between gap-4">
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground leading-snug break-words max-w-4xl">
            {title}
          </h1>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            {sourceUrl?.startsWith("http") && (
              <a
                className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-semibold text-foreground hover:border-primary/50 hover:text-primary transition-colors"
                href={sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Open original public discussion"
              >
                Original Discussion <ArrowUpRight size={13} />
              </a>
            )}

            {onToggleSave && (
              <Button
                variant="outline"
                size="sm"
                onClick={onToggleSave}
                className="h-8 gap-1.5 px-3 text-xs"
              >
                <Bookmark size={13} fill={isSaved ? "currentColor" : "none"} />
                {isSaved ? "Saved" : "Save"}
              </Button>
            )}

            {onOpenEdit && (
              <Button
                variant="outline"
                size="sm"
                onClick={onOpenEdit}
                className="h-8 gap-1.5 px-3 text-xs font-semibold"
              >
                <Pencil size={13} />
                Edit Details
              </Button>
            )}

            {primaryAction}

            {/* More Menu */}
            <Menu.Root>
              <Menu.Trigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  className="h-8 w-8"
                  aria-label="More actions"
                >
                  <MoreHorizontal size={14} />
                </Button>
              </Menu.Trigger>
              <Menu.Portal>
                <Menu.Content
                  className="z-50 min-w-[170px] rounded-xl border border-border bg-popover p-1 text-xs shadow-md animate-in fade-in-50"
                  sideOffset={4}
                  align="end"
                >
                  <Menu.Item
                    className="flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-1.5 text-foreground hover:bg-muted outline-none"
                    onSelect={handleCopyLink}
                  >
                    <Copy size={13} />
                    Copy Link
                  </Menu.Item>

                  {sourceUrl?.startsWith("http") && (
                    <Menu.Item
                      className="flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-1.5 text-foreground hover:bg-muted outline-none"
                      onSelect={() => window.open(sourceUrl, "_blank")}
                    >
                      <ExternalLink size={13} />
                      Open in Browser
                    </Menu.Item>
                  )}

                  {menuItems.length > 0 && <Menu.Separator className="my-1 h-px bg-border" />}

                  {menuItems.map((item, idx) => {
                    const Icon = item.icon;
                    return (
                      <Menu.Item
                        key={idx}
                        className={`flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-1.5 outline-none ${
                          item.destructive
                            ? "text-destructive hover:bg-destructive/10"
                            : "text-foreground hover:bg-muted"
                        }`}
                        onSelect={item.onClick}
                      >
                        {Icon && <Icon size={13} />}
                        {item.label}
                      </Menu.Item>
                    );
                  })}
                </Menu.Content>
              </Menu.Portal>
            </Menu.Root>
          </div>
        </div>
      </header>
    </div>
  );
}
