"use client";

import Link from "next/link";
import {useState} from 'react';
import { Sparkles, ArrowRight, ShieldAlert, CreditCard } from "lucide-react";
import * as Tooltip from "@radix-ui/react-tooltip";
import { useQueryClient } from "@tanstack/react-query";
import { useUsage } from "@/components/workspaces/usage";
import { useWorkspace } from "@/components/workspaces/use-workspace";

interface TrialUsageCardProps {
  collapsed?: boolean;
  mobile?: boolean;
}

export function TrialUsageCard({ collapsed = false, mobile = false }: TrialUsageCardProps) {
  let hasQueryClient = false;
  try {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    hasQueryClient = Boolean(useQueryClient());
  } catch {
    hasQueryClient = false;
  }

  if (!hasQueryClient) {
    return null;
  }

  return <TrialUsageCardContent collapsed={collapsed} mobile={mobile} />;
}

function TrialUsageCardContent({ collapsed = false, mobile = false }: TrialUsageCardProps) {
  const usageQuery = useUsage();
  const workspace = useWorkspace();
  const [renderedAt]=useState(()=>Math.floor(Date.now()/1000));

  if(usageQuery.isError||workspace.isError||(!workspace.isPending&&workspace.data&&!workspace.data.active_organization_id))return <div className="mx-3 rounded-lg border p-3 text-xs" role="status">Billing status unavailable. <button onClick={()=>{void workspace.refetch();void usageQuery.refetch();}}>Retry</button> · <Link href="/billing">Billing</Link></div>;
  if (usageQuery.isPending) {
    if (collapsed && !mobile) {
      return (
        <div className="mx-auto my-3 flex h-9 w-9 items-center justify-center rounded-xl border border-border/70 bg-muted/40 animate-pulse" />
      );
    }
    return (
      <div className="mx-3 my-2 rounded-xl border border-border/70 bg-card p-3 space-y-2 animate-pulse">
        <div className="h-3.5 w-24 bg-muted/60 rounded" />
        <div className="h-1.5 w-full bg-muted/40 rounded-full" />
        <div className="h-2.5 w-32 bg-muted/50 rounded" />
        <div className="h-7 w-full bg-muted/60 rounded-lg mt-2" />
      </div>
    );
  }

  const usageData = usageQuery.data;
  const sub = usageData?.subscription;
  const isTrial = Boolean(sub?.is_trial || usageData?.access?.is_trial);
  const entitlementLabel = sub?.entitlement_label || usageData?.access?.kind || 'No active subscription';

  // Calculate trial / subscription period
  const endTimestamp = (isTrial?sub?.trial_end:sub?.period_end) || 0;
  const nowSec = Math.floor((usageQuery.dataUpdatedAt||renderedAt*1000)/1000);
  const secondsRemaining = Math.max(0, endTimestamp - nowSec);
  const daysRemaining = Math.ceil(secondsRemaining / 86400);

  // Standard trial duration is typically 7 or 14 days
  const startTimestamp = sub?.trial_start || sub?.period_start || endTimestamp;
  const totalDurationSec = Math.max(86400, endTimestamp - startTimestamp);
  const totalDays = Math.max(1, Math.round(totalDurationSec / 86400));
  const elapsedSec = Math.max(0, nowSec - startTimestamp);
  const daysUsed = Math.max(1, Math.min(totalDays, totalDays - daysRemaining));
  const trialProgressPercent = Math.min(100, Math.max(0, Math.round((elapsedSec / totalDurationSec) * 100)));

  // Real Usage Metrics
  const items = usageData?.usage || [];
  const searchAllowance =
    items.find((i) => i.dimension === "plan_searches") ||
    (!sub && usageData?.access?.intent_radar ? items.find((i) => i.dimension === "searches") : undefined);

  const aiAllowance =
    items.find((i) => i.dimension === "plan_ai_calls") ||
    (!sub && usageData?.access?.intent_radar ? items.find((i) => i.dimension === "ai_calls") : undefined);

  const isExpired = isTrial && daysRemaining <= 0 && endTimestamp > 0;
  const isExpiringSoon = isTrial && daysRemaining > 0 && daysRemaining <= 3;
  const isPaid = !isTrial && Boolean(sub && sub.status.toLowerCase()==='active');
  const isCanceled = Boolean(
    sub && (sub.cancel_confirmed_at || sub.provider_status==='canceled'||sub.provider_status==='scheduled_cancel')
  );
  const isLimitReached = (searchAllowance&&searchAllowance.used>=searchAllowance.limit)||(aiAllowance&&aiAllowance.used>=aiAllowance.limit);
  const searchText=searchAllowance?`${searchAllowance.used} / ${searchAllowance.limit}`:'—',aiText=aiAllowance?`${aiAllowance.used} / ${aiAllowance.limit}`:'—';

  // Tooltip content for collapsed mode
  const tooltipContent = (
    <div className="p-2 space-y-1.5 text-xs max-w-[200px]">
      <div className="font-semibold text-foreground flex items-center justify-between">
        <span>{entitlementLabel}</span>
        {isTrial && isExpired && (
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-destructive/10 text-destructive">
            Expired
          </span>
        )}
      </div>
      <div className="text-[11px] text-muted-foreground space-y-0.5">
        <div>Searches: {searchText}</div>
        <div>AI requests: {aiText}</div>
      </div>
      <Link
        href="/billing"
        className="block text-center mt-2 w-full py-1 rounded bg-primary text-primary-foreground text-[11px] font-medium hover:bg-primary/90"
      >
        {isPaid ? "Manage Plan" : "Upgrade Plan →"}
      </Link>
    </div>
  );

  if (collapsed && !mobile) {
    return (
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <Link
            href="/billing"
            aria-label={`Subscription: ${entitlementLabel}`}
            className="mx-auto my-2.5 flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-card text-foreground shadow-xs hover:border-primary/40 hover:bg-muted/50 transition-colors"
          >
            {isExpired ? (
              <ShieldAlert size={16} className="text-destructive" />
            ) : isExpiringSoon ? (
              <Sparkles size={16} className="text-amber-500" />
            ) : isPaid ? (
              <CreditCard size={16} className="text-primary" />
            ) : (
              <Sparkles size={16} className="text-primary" />
            )}
          </Link>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            className="z-50 rounded-xl border border-border bg-card p-2 text-foreground shadow-xl animate-in fade-in-50"
            side="right"
            sideOffset={12}
          >
            {tooltipContent}
            <Tooltip.Arrow className="fill-border" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    );
  }

  return (
    <div className="mx-3 my-2 rounded-xl border border-border bg-card p-3 shadow-xs space-y-2.5 text-xs">
      {/* Header with Title (Remaining days badge removed as requested) */}
      <div className="flex items-center justify-between gap-1">
        <div className="flex items-center gap-1.5 font-semibold text-foreground">
          {isPaid ? (
            <CreditCard size={13} className="text-primary shrink-0" />
          ) : (
            <Sparkles size={13} className="text-primary shrink-0" />
          )}
          <span className="truncate">{entitlementLabel}</span>
        </div>

        {isTrial && isExpired && (
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full shrink-0 bg-destructive/10 text-destructive font-semibold">
            Expired
          </span>
        )}

        {isPaid && isCanceled && (
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-muted text-muted-foreground">
            Canceled
          </span>
        )}

        {isPaid && !isCanceled && (
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-300">
            Active
          </span>
        )}
      </div>

      {/* Progress Bar (Only for active trial) */}
      {isTrial && !isExpired && (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground">
            <span>Trial period</span>
            <span className="font-medium text-foreground tabular-nums">
              {daysUsed} / {totalDays} days used
            </span>
          </div>
          <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
            <div
              className="h-full transition-all duration-300 rounded-full bg-primary"
              style={{ width: `${Math.max(5, Math.min(100, trialProgressPercent))}%` }}
              role="progressbar"
              aria-label="Trial period progress"
              aria-valuenow={trialProgressPercent}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
        </div>
      )}

      {/* Usage summary counts */}
      <div className="space-y-1 text-[11px] text-muted-foreground pt-0.5">
        <div className="flex items-center justify-between">
          <span>Discovery searches</span>
          <span className="font-medium text-foreground tabular-nums">
            {searchText}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span>AI requests</span>
          <span className="font-medium text-foreground tabular-nums">
            {aiText}
          </span>
        </div>
      </div>

      {/* Limit reached warning or Expired message */}
      {isExpired ? (
        <p className="text-[11px] text-destructive leading-tight">
          Trial expired. Upgrade to resume searching &amp; monitoring.
        </p>
      ) : isLimitReached ? (
        <p className="text-[11px] text-muted-foreground leading-tight">
          Usage limit reached. Upgrade to increase limits.
        </p>
      ) : null}

      {/* CTA Button — matching main application CTA */}
      <Link
        href="/billing"
        className={`inline-flex h-7 w-full items-center justify-center gap-1.5 rounded-lg px-2.5 text-[11px] font-semibold transition-colors shadow-xs ${
          isPaid
            ? "border border-border bg-background text-foreground hover:bg-muted"
            : "bg-primary text-primary-foreground hover:bg-primary/90"
        }`}
      >
        <span>{isPaid ? "Manage Plan" : "Upgrade Plan"}</span>
        <ArrowRight size={11} />
      </Link>
    </div>
  );
}
