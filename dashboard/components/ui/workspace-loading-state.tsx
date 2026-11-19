"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Loader2, AlertCircle, RefreshCw, ArrowLeft, Building2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface WorkspaceLoadingStateProps {
  title?: string;
  description?: string;
  className?: string;
}

export function WorkspaceLoadingState({
  title = "Loading your workspace",
  description = "Preparing your workspace and account settings…",
  className = "",
}: WorkspaceLoadingStateProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex flex-col items-center justify-center min-h-[55vh] py-16 px-4 text-center select-none ${className}`}
    >
      <div className="relative mb-4 flex items-center justify-center">
        <div className="h-10 w-10 rounded-full border-2 border-primary/20 border-t-primary animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center">
          <Building2 size={16} className="text-primary/70" />
        </div>
      </div>
      <div className="space-y-1.5 max-w-sm">
        <h2 className="text-base font-semibold text-foreground tracking-tight">{title}</h2>
        <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
      </div>
    </div>
  );
}

export interface WorkspaceErrorStateProps {
  title?: string;
  description?: string;
  error?: string | null;
  onRetry?: () => void | Promise<void>;
  secondaryAction?: {
    label: string;
    href?: string;
    onClick?: () => void;
  };
  className?: string;
}

export function WorkspaceErrorState({
  title = "Unable to load your workspace",
  description = "We couldn't connect to your workspace. Please check your connection or sign in again.",
  error,
  onRetry,
  secondaryAction = { label: "Back to dashboard", href: "/intent-radar" },
  className = "",
}: WorkspaceErrorStateProps) {
  const [retrying, setRetrying] = useState(false);

  async function handleRetry() {
    if (!onRetry || retrying) return;
    setRetrying(true);
    try {
      await onRetry();
    } finally {
      setRetrying(false);
    }
  }

  return (
    <div
      role="alert"
      className={`flex items-center justify-center min-h-[55vh] py-12 px-4 ${className}`}
    >
      <div className="w-full max-w-[460px] rounded-2xl border border-border bg-card p-6 sm:p-8 text-center shadow-sm space-y-4">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-destructive/10 text-destructive">
          <AlertCircle size={22} />
        </div>

        <div className="space-y-1.5">
          <h2 className="text-base font-semibold text-foreground tracking-tight">{title}</h2>
          <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
          {error && (
            <p className="mt-2 rounded-lg bg-muted/60 p-2 font-mono text-[11px] text-muted-foreground break-all text-left">
              {error}
            </p>
          )}
        </div>

        <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-2.5">
          {onRetry && (
            <Button
              type="button"
              onClick={() => void handleRetry()}
              disabled={retrying}
              className="w-full sm:w-auto h-9 px-4 text-xs font-semibold gap-1.5 cursor-pointer"
            >
              <RefreshCw size={13} className={retrying ? "animate-spin" : ""} />
              <span>{retrying ? "Retrying…" : "Retry loading"}</span>
            </Button>
          )}

          {secondaryAction?.href ? (
            <Link
              href={secondaryAction.href}
              className="w-full sm:w-auto inline-flex h-9 items-center justify-center gap-1.5 rounded-lg border border-border bg-background px-4 text-xs font-medium text-foreground hover:bg-muted transition-colors"
            >
              <ArrowLeft size={13} />
              <span>{secondaryAction.label}</span>
            </Link>
          ) : secondaryAction?.onClick ? (
            <Button
              type="button"
              variant="outline"
              onClick={secondaryAction.onClick}
              className="w-full sm:w-auto h-9 px-4 text-xs font-medium cursor-pointer"
            >
              <span>{secondaryAction.label}</span>
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function WorkspaceRetryButton({
  onClick,
  loading = false,
  className = "",
}: {
  onClick: () => void | Promise<void>;
  loading?: boolean;
  className?: string;
}) {
  return (
    <Button
      type="button"
      size="sm"
      variant="outline"
      onClick={() => void onClick()}
      disabled={loading}
      className={`h-8 px-3 text-xs gap-1.5 cursor-pointer ${className}`}
    >
      <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
      <span>{loading ? "Retrying…" : "Retry"}</span>
    </Button>
  );
}

export function WorkspaceEmptyState({
  title = "No workspace found",
  description = "You do not have access to an active workspace. Create one or request an invitation from your team.",
  actionHref = "/settings/workspaces",
  actionLabel = "Create workspace",
}: {
  title?: string;
  description?: string;
  actionHref?: string;
  actionLabel?: string;
}) {
  return (
    <div
      role="status"
      className="flex items-center justify-center min-h-[50vh] py-12 px-4 text-center"
    >
      <div className="w-full max-w-md rounded-2xl border border-border bg-card p-6 sm:p-8 space-y-4 shadow-sm">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <Building2 size={22} />
        </div>
        <div className="space-y-1.5">
          <h2 className="text-base font-semibold text-foreground tracking-tight">{title}</h2>
          <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
        </div>
        <div className="pt-2">
          <Link
            href={actionHref}
            className="inline-flex h-9 items-center justify-center rounded-lg bg-primary px-4 text-xs font-semibold text-primary-foreground hover:opacity-95 transition-opacity"
          >
            {actionLabel}
          </Link>
        </div>
      </div>
    </div>
  );
}
