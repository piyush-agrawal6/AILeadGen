"use client";

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CreditCard,
  ExternalLink,
  FileText,
  Radio,
  Receipt,
  RefreshCw,
  Search,
  Sparkles,
} from "lucide-react";
import { request } from "@/lib/intelligence";
import { Button } from "@/components/ui/button";
import { useUsage, type UsageData } from "@/components/workspaces/usage";
import { useWorkspace } from "@/components/workspaces/use-workspace";
import { CommercialPlans } from "@/components/workspaces/commercial-plans";
import Link from "next/link";
import { FixedTermPayments } from "@/components/workspaces/fixed-term-payments";
import {
  SubscriptionPayment,
  useSubscription,subKey,
  type SubscriptionState,
} from "@/components/workspaces/subscription-payment";

type Allowance = UsageData["usage"][number];

const formatDate = (unix?: number | null) =>
  unix
    ? new Date(unix * 1000).toLocaleDateString(undefined, {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : "—";

const formatMoney = (minor: number, currency = "USD") =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: minor % 100 === 0 ? 0 : 2,
  }).format(minor / 100);

type ResolvedStatus = {
  label: string;
  tone: "emerald" | "amber" | "blue" | "red" | "muted";
  planTitle: string;
  isTrial: boolean;
  isCanceled: boolean;
  isActive: boolean;
  alertMessage?: string;
};

function resolvePlanStatus(
  subState?: SubscriptionState | null,
  usage?: UsageData | null
): ResolvedStatus {
  const contract = subState?.contract;
  const sub = usage?.subscription;
  const isActive = subState?.enabled ? subState.active : Boolean(usage?.access.intent_radar && sub);
  const isTrial = Boolean(
    contract?.is_trial ??
      sub?.is_trial ??
      usage?.access.is_trial ??
      (contract?.trial_start != null && contract.period_start === contract.trial_start)
  );
  const rawStatus = (contract?.status || sub?.provider_status || sub?.status || "").toLowerCase();
  if(sub?.status==='COMPLIMENTARY')return {label:'Active',tone:'blue',planTitle:'Starter — Development Access',isActive:true,isTrial:false,isCanceled:false};
  const isCanceled = Boolean(
    contract?.cancel_confirmed_at ||
      sub?.cancel_confirmed_at ||
      rawStatus === "canceled" ||
      rawStatus === "scheduled_cancel"
  );

  const planCode = (contract?.plan_code || sub?.plan_code || "").trim().toLowerCase();
  const tierName = planCode
    ? planCode.charAt(0).toUpperCase() + planCode.slice(1)
    : "";
  const planTitle =
    contract?.entitlement_label ||
    sub?.entitlement_label ||
    (tierName ? (isTrial ? `${tierName} Trial` : tierName) : usage?.access.kind || "No active plan");

  if(subState?.lifecycle?.pending_checkout&&!isActive)return {label:'Payment pending',tone:'amber',planTitle:'Awaiting verification',isActive:false,isTrial:false,isCanceled:false};
  if(subState?.lifecycle?.phase==='trial_ended')return {label:'Trial ended',tone:'muted',planTitle:'Trial Ended',isActive:false,isTrial:true,isCanceled:true};
  if (!contract && !sub) {
    if (usage?.access.intent_radar) {
      return {
        label: "Active",
        tone: "blue",
        planTitle: usage.access.kind || "Workspace Access",
        isTrial: false,
        isCanceled: false,
        isActive: true,
      };
    }
    return {
      label: "No subscription",
      tone: "muted",
      planTitle: "No active plan",
      isTrial: false,
      isCanceled: false,
      isActive: false,
    };
  }

  if (rawStatus === "past_due" || rawStatus === "unpaid") {
    return {
      label: "Past due",
      tone: "red",
      planTitle,
      isTrial,
      isCanceled,
      isActive: false,
      alertMessage: "Payment failed or past due. Update your payment method in the billing portal to restore access.",
    };
  }

  if (rawStatus === "pending" || rawStatus === "creating") {
    return {
      label: "Payment pending",
      tone: "amber",
      planTitle,
      isTrial,
      isCanceled: false,
      isActive: false,
      alertMessage: "Awaiting Creem checkout confirmation. Refresh status shortly — no duplicate charge will be created.",
    };
  }

  if (!isActive || rawStatus === "expired") {
    return {
      label: "Expired",
      tone: "muted",
      planTitle,
      isTrial,
      isCanceled: true,
      isActive: false,
    };
  }

  if (isCanceled) {
    return {
      label: "Canceled · Access remaining",
      tone: "amber",
      planTitle,
      isTrial,
      isCanceled: true,
      isActive: true,
    };
  }

  if (isTrial) {
    return {
      label: "Trial active",
      tone: "blue",
      planTitle,
      isTrial: true,
      isCanceled: false,
      isActive: true,
    };
  }

  return {
    label: "Active",
    tone: "emerald",
    planTitle,
    isTrial: false,
    isCanceled: false,
    isActive: true,
  };
}

const BADGE_TONES: Record<ResolvedStatus["tone"], string> = {
  emerald: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/25",
  amber: "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30",
  blue: "bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/25",
  red: "bg-destructive/10 text-destructive border-destructive/25",
  muted: "bg-muted text-muted-foreground border-border",
};

function findAllowance(items: Allowance[], dimension: string): Allowance | undefined {
  return items.find((i) => i.dimension === dimension);
}

function barColor(used: number, limit: number): string {
  if (limit > 0 && used >= limit) return "bg-destructive";
  if (limit > 0 && used / limit >= 0.8) return "bg-amber-500";
  return "bg-primary";
}

function CompactUsageCard({
  title,
  icon: Icon,
  item,
}: {
  title: string;
  icon: typeof Search;
  item?: Allowance;
}) {
  if (!item) return null;
  const notIncluded = item.limit === 0;
  const exhausted = !notIncluded && item.remaining === 0;
  const approaching = !notIncluded && !exhausted && item.used / item.limit >= 0.8;
  const percent = notIncluded ? 0 : Math.min(100, Math.round((item.used / item.limit) * 100));

  return (
    <article className="rounded-xl border border-border bg-card px-4 py-3.5 space-y-2.5">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs font-semibold text-foreground min-w-0">
          <Icon size={14} className="text-primary shrink-0" aria-hidden="true" />
          <span className="leading-tight">{title}</span>
        </div>
        {!notIncluded && exhausted ? (
          <span className="rounded-full bg-destructive/10 px-2 py-0.5 text-[10px] font-semibold text-destructive shrink-0">
            Exhausted
          </span>
        ) : !notIncluded && approaching ? (
          <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold text-amber-700 dark:text-amber-300 shrink-0">
            Near limit
          </span>
        ) : null}
      </div>

      {notIncluded ? (
        <p className="text-xs text-muted-foreground pt-1">Not included in current plan</p>
      ) : (
        <div className="space-y-1.5">
          <p className="text-base font-bold tracking-tight text-foreground tabular-nums">
            {item.used.toLocaleString()}
            <span className="text-xs font-normal text-muted-foreground">
              {" "}
              / {item.limit.toLocaleString()}
            </span>
          </p>
          <div
            className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
            role="progressbar"
            aria-label={title}
            aria-valuenow={item.used}
            aria-valuemin={0}
            aria-valuemax={item.limit}
          >
            <div
              className={`h-full rounded-full transition-all ${barColor(item.used, item.limit)}`}
              style={{ width: `${percent}%` }}
            />
          </div>
          <p className="text-[11px] text-muted-foreground tabular-nums">
            {exhausted
              ? "0 remaining"
              : `${item.remaining.toLocaleString()} remaining`}
          </p>
        </div>
      )}
    </article>
  );
}

export function BillingSection({
  activeTab,
  onSwitchTab,
}: {
  activeTab: string;
  onSwitchTab?: (tab: string) => void;
}) {
  const client = useQueryClient();
  const workspace = useWorkspace();
  const orgId = workspace.data?.active_organization_id || "";
  const usageQuery = useUsage();
  const subQuery=useSubscription(orgId,!!orgId);

  const [busyAction, setBusyAction] = useState<"portal" | "cancel" | "refresh" | null>(null);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [actionNotice, setActionNotice] = useState("");
  const [actionError, setActionError] = useState("");
  const [showDetailedUsage, setShowDetailedUsage] = useState(false);
  const [showInvoices, setShowInvoices] = useState(false);
  const returnedHandled = useRef(false);

  const selectedPlanParam =
    typeof window !== "undefined"
      ? (new URLSearchParams(window.location.search).get("plan") as
          | "starter"
          | "growth"
          | "scale"
          | null)
      : null;

  useEffect(() => {
    if (typeof window === "undefined" || returnedHandled.current || !orgId) return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("payment") === "returned") {
      returnedHandled.current = true;
      params.delete("payment");
      const nextUrl = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ""}`;
      window.history.replaceState({}, "", nextUrl);
      void runSubscriptionAction("refresh");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId]);

  async function runSubscriptionAction(kind: "portal" | "cancel" | "refresh") {
    setBusyAction(kind);
    setActionError("");
    setActionNotice("");
    try {
      if (kind === "refresh") {
        const next = await request<SubscriptionState>("/billing/subscription/refresh", {
          expectedWorkspace:orgId,
          method: "POST",
        });
        client.setQueryData(subKey(orgId), next);
        await usageQuery.refetch();
        setActionNotice("Billing status synchronized with Creem.");
        const dest=sessionStorage.getItem('billing-return:'+orgId);if(next.active&&dest&&/^\/intent-radar(?:\/[a-z0-9-]+)*$/i.test(dest)){sessionStorage.removeItem('billing-return:'+orgId);window.location.assign(dest);}
      } else if (kind === "portal") {
        const res = await request<{ url?: string }>("/billing/subscription/portal", {
          expectedWorkspace:orgId,
          method: "POST",
        });
        if (res.url) {
          window.location.assign(res.url);
        } else {
          setActionError("Billing portal link was not returned by Creem.");
        }
      } else if (kind === "cancel") {
        const res = await request<{ status?: string }>("/billing/subscription/cancel", {
          expectedWorkspace:orgId,
          method: "POST",
          body: JSON.stringify({ request_id: crypto.randomUUID() }),
        });
        setConfirmCancel(false);
        setActionNotice(
          res.status === "CONFIRMED"
            ? "Automatic renewal canceled. Access remains active until the end of your current period."
            : "Cancellation requested and awaiting Creem confirmation."
        );
        await Promise.all([subQuery.refetch(), usageQuery.refetch()]);
      }
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Subscription action failed.");
    } finally {
      setBusyAction(null);
    }
  }

  if(workspace.isError||(!workspace.isPending&&!orgId))return <p role="alert">Select a workspace to view billing. <Button onClick={()=>void workspace.refetch()}>Retry workspaces</Button></p>;
  if(subQuery.isError)return <p role="alert">Subscription status unavailable. <Button onClick={()=>void subQuery.refetch()}>Retry billing</Button></p>;
  if (usageQuery.isPending || subQuery.isPending) {
    return (
      <div className="space-y-4" role="status" aria-label="Loading billing and usage">
        <div className="h-32 rounded-2xl border border-border bg-muted/30 animate-pulse" />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="h-28 rounded-xl border border-border bg-muted/30 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (usageQuery.isError || !usageQuery.data) {
    return (
      <div
        role="alert"
        className="rounded-2xl border border-destructive/25 bg-destructive/5 p-5 space-y-3"
      >
        <h3 className="text-sm font-semibold text-destructive">
          Unable to load billing and usage data
        </h3>
        <p className="text-xs text-muted-foreground">
          {usageQuery.error?.message || "Please try again in a moment."}
        </p>
        <Button variant="outline" size="sm" onClick={() => void usageQuery.refetch()}>
          Retry
        </Button>
        {subQuery.data?.enabled&&<SubscriptionPayment key={orgId} orgId={orgId}/>}
      </div>
    );
  }

  const data = usageQuery.data;
  const subState = subQuery.data;
  const resolved = resolvePlanStatus(subState, data);
  const contract = subState?.contract;
  const development = data.subscription?.status==='COMPLIMENTARY';
  const currentPlanCode = resolved.isActive&&!development?(subState?.lifecycle?.effective_plan||contract?.plan_code||data.subscription?.plan_code||null):null;
  const catalogPlan = data.commercial.catalog.plans.find(
    (p) => p.code.toLowerCase() === (currentPlanCode || "").toLowerCase()
  );

  if (activeTab === "plans") {
    return (
      <CommercialPlans
        key={orgId}
        workspaceId={orgId}
        data={data.commercial}
        selectedPlan={selectedPlanParam}
        currentPlanCode={currentPlanCode}
        currentIsTrial={resolved.isTrial}
        subscriptionState={subState ?? null}
      />
    );
  }

  const planSearches = findAllowance(data.usage, "plan_searches");
  const dailySearches = findAllowance(data.usage, "searches");
  const planAiCalls = findAllowance(data.usage, "plan_ai_calls");
  const planAiTokens = findAllowance(data.usage, "plan_ai_tokens");
  const planMonitors = findAllowance(data.usage, "plan_monitors");
  const planMonitorChecks = findAllowance(data.usage, "plan_monitor_executions");
  const planReports = findAllowance(data.usage, "plan_reports");
  const planApiRequests = findAllowance(data.usage, "plan_api_requests");
  const planSeats = findAllowance(data.usage, "plan_team_members");
  const dailyItems = data.usage.filter((item) => !item.dimension.startsWith("plan_"));

  const monthlySearchBlockedButDailyAvailable = Boolean(
    planSearches &&
      planSearches.limit > 0 &&
      planSearches.remaining === 0 &&
      dailySearches &&
      dailySearches.remaining > 0
  );

  const periodEnd = development ? data.subscription?.period_end :
    (resolved.isTrial ? contract?.trial_end ?? data.subscription?.trial_end : null) ??
    contract?.period_end ??
    data.subscription?.period_end ??
    data.native_access?.expires_at ??
    null;

  const nextPaymentText = development ? 'No automatic renewal or charge' : resolved.isCanceled
    ? "None scheduled"
    : contract?.next_charge_at && catalogPlan?.monthly_minor
      ? `${formatMoney(catalogPlan.monthly_minor)} on ${formatDate(contract.next_charge_at)}`
      : resolved.isTrial && periodEnd && catalogPlan?.monthly_minor
        ? `${formatMoney(catalogPlan.monthly_minor)} on ${formatDate(periodEnd)}`
        : "None scheduled";

  const creemInvoices = subState?.history || [];
  const legacyPayments = data.commercial.historical_payments || [];
  const totalInvoices = creemInvoices.length + legacyPayments.length;

  return (
    <div className="space-y-5">
      {/* 1. Compact Current Subscription Summary */}
      <section
        aria-label="Current subscription"
        className="rounded-2xl border border-border bg-card p-5 space-y-4"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2.5">
            <h3 className="text-lg font-bold tracking-tight text-foreground">
              {resolved.planTitle}
            </h3>
            <span
              className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${BADGE_TONES[resolved.tone]}`}
            >
              {resolved.tone === "emerald" ? (
                <CheckCircle2 size={12} aria-hidden="true" />
              ) : resolved.tone === "red" || resolved.tone === "amber" ? (
                <AlertTriangle size={12} aria-hidden="true" />
              ) : null}
              {resolved.label}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            {contract && !development && subState?.can_manage ? (
              <Button
                size="sm"
                disabled={busyAction !== null}
                onClick={() => void runSubscriptionAction("portal")}
                className="h-8 text-xs gap-1.5"
              >
                <CreditCard size={13} />
                {busyAction === "portal" ? "Opening…" : "Manage Subscription"}
              </Button>
            ) : null}
            <Button
              variant={contract && subState?.can_manage ? "outline" : "default"}
              size="sm"
              onClick={() => onSwitchTab?.("plans")}
              className="h-8 text-xs"
            >
              {contract && !development ? "Change Plan" : "Choose Plan"}
            </Button>
          </div>
        </div>

        {resolved.alertMessage && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-xl border border-destructive/25 bg-destructive/5 px-3.5 py-2.5 text-xs text-destructive"
          >
            <AlertTriangle size={14} className="shrink-0 mt-0.5" aria-hidden="true" />
            <span>{resolved.alertMessage}</span>
          </div>
        )}

        {/* Concise 4-item key-value summary */}
        <dl className="grid gap-3 grid-cols-2 lg:grid-cols-4 border-t border-border/70 pt-3.5 text-xs">
          <div>
            <dt className="text-[11px] text-muted-foreground">Current plan</dt>
            <dd className="font-semibold text-foreground mt-0.5">{resolved.planTitle}</dd>
          </div>
          <div>
            <dt className="text-[11px] text-muted-foreground">Status</dt>
            <dd className="font-semibold text-foreground mt-0.5">{resolved.label}</dd>
          </div>
          <div>
            <dt className="text-[11px] text-muted-foreground">
              {development || resolved.isCanceled || resolved.isTrial ? "Access until" : "Current period ends"}
            </dt>
            <dd className="font-semibold text-foreground mt-0.5">{formatDate(periodEnd)}</dd>
          </div>
          <div>
            <dt className="text-[11px] text-muted-foreground">Next payment</dt>
            <dd className="font-semibold text-foreground mt-0.5">{nextPaymentText}</dd>
          </div>
        </dl>

        {/* Compact Secondary Controls Row */}
        {contract && !development && subState?.can_manage && (
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border/60 pt-3 text-xs">
            <div className="flex flex-wrap items-center gap-1.5">
              {!resolved.isCanceled && resolved.isActive && !confirmCancel && (
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={busyAction !== null}
                  onClick={() => setConfirmCancel(true)}
                  className="h-7 px-2.5 text-xs text-muted-foreground hover:text-destructive"
                >
                  Cancel Renewal
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                disabled={busyAction !== null}
                onClick={() => void runSubscriptionAction("refresh")}
                className="h-7 px-2.5 text-xs gap-1.5 text-muted-foreground"
              >
                <RefreshCw size={12} className={busyAction === "refresh" ? "animate-spin" : ""} />
                {busyAction === "refresh" ? "Syncing…" : "Refresh Status"}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowInvoices((v) => !v)}
                className="h-7 px-2.5 text-xs gap-1.5 text-muted-foreground"
              >
                <Receipt size={12} />
                Invoices ({totalInvoices})
              </Button>
            </div>
            <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
              <Link
                href="/help?article=billing-subscriptions"
                className="text-primary hover:underline"
              >
                Billing guide
              </Link>
              <span>·</span>
              <span>
                Billed via <span className="capitalize">{contract.provider || "Creem"}</span>
              </span>
            </div>
          </div>
        )}

        {/* Inline Cancel Confirmation (preserves required cancellation disclosure) */}
        {confirmCancel && (
          <div
            role="alertdialog"
            aria-label="Confirm automatic renewal cancellation"
            className="rounded-xl border border-destructive/30 bg-destructive/5 p-3.5 space-y-2.5"
          >
            <p className="text-xs text-foreground leading-relaxed">
              <strong>Cancel automatic renewal?</strong> Your access will continue until{" "}
              <strong>{formatDate(periodEnd)}</strong> with no further renewal charge.
            </p>
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="destructive"
                disabled={busyAction !== null}
                onClick={() => void runSubscriptionAction("cancel")}
                className="h-7 text-xs"
              >
                {busyAction === "cancel" ? "Canceling…" : "Confirm cancellation"}
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={busyAction !== null}
                onClick={() => setConfirmCancel(false)}
                className="h-7 text-xs"
              >
                Keep active
              </Button>
            </div>
          </div>
        )}

        {actionNotice && (
          <p role="status" className="text-xs font-medium text-emerald-700 dark:text-emerald-400">
            {actionNotice}
          </p>
        )}
        {actionError && (
          <p role="alert" className="text-xs font-medium text-destructive">
            {actionError}
          </p>
        )}
      </section>

      {/* Only show checkout onboarding panel when no active subscription exists */}
      {!resolved.isActive && subState?.enabled && <SubscriptionPayment key={orgId} orgId={orgId} />}

      {/* Legacy fixed-term records if present */}
      {!!data.commercial.fixed_term?.items.length && (
        <FixedTermPayments
          data={data.commercial.fixed_term}
          plans={data.commercial.catalog.plans}
        />
      )}

      {/* 2. Compact 4-Card Usage Overview */}
      <section aria-label="Usage overview" className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-semibold tracking-tight text-foreground">Usage Overview</h3>
          {periodEnd && (
            <span className="text-[11px] text-muted-foreground">
              Resets {formatDate(periodEnd)}
            </span>
          )}
        </div>

        {monthlySearchBlockedButDailyAvailable && (
          <div
            role="status"
            className="flex items-center gap-2 rounded-xl border border-destructive/25 bg-destructive/5 px-3.5 py-2 text-xs text-destructive"
          >
            <AlertTriangle size={14} className="shrink-0" aria-hidden="true" />
            <span>
              <strong>Monthly search allowance exhausted</strong> (daily safety limit still has{" "}
              {dailySearches?.remaining.toLocaleString()} left today).
            </span>
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <CompactUsageCard
            title="Monthly Searches"
            icon={Search}
            item={planSearches || dailySearches}
          />
          <CompactUsageCard
            title="AI Operations"
            icon={Sparkles}
            item={planAiCalls || findAllowance(data.usage, "ai_calls")}
          />
          <CompactUsageCard
            title="Active Monitors"
            icon={Radio}
            item={planMonitors || findAllowance(data.usage, "monitors")}
          />
          <CompactUsageCard
            title="Monthly Reports"
            icon={FileText}
            item={planReports}
          />
        </div>
      </section>

      {/* 3. Single Collapsed Detailed Usage Drawer (Tokens, Provider Telemetry, API, Seats, Daily Limits) */}
      <section className="rounded-2xl border border-border bg-card overflow-hidden">
        <button
          type="button"
          aria-expanded={showDetailedUsage}
          onClick={() => setShowDetailedUsage((v) => !v)}
          className="flex w-full items-center justify-between gap-4 px-4 py-3 text-left hover:bg-muted/30 transition-colors cursor-pointer"
        >
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-xs font-semibold text-foreground">Detailed Usage</span>
            <span className="hidden sm:inline text-[11px] text-muted-foreground truncate">
              · AI tokens, provider consumption, API requests, seats, scheduled checks &amp; daily limits
            </span>
          </div>
          {showDetailedUsage ? (
            <ChevronUp size={15} className="text-muted-foreground shrink-0" />
          ) : (
            <ChevronDown size={15} className="text-muted-foreground shrink-0" />
          )}
        </button>

        {showDetailedUsage && (
          <div className="border-t border-border p-4 space-y-4 text-xs">
            {/* Monthly Plan Sub-Allowances */}
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {planAiTokens && (
                <div className="rounded-xl border border-border/80 bg-muted/20 p-3 space-y-1">
                  <span className="text-[11px] font-medium text-muted-foreground">
                    Reserved AI Tokens
                  </span>
                  <p className="text-sm font-bold tabular-nums text-foreground">
                    {planAiTokens.used.toLocaleString()}{" "}
                    <span className="font-normal text-muted-foreground">
                      / {planAiTokens.limit.toLocaleString()}
                    </span>
                  </p>
                  <p className="text-[10px] text-muted-foreground">
                    Upper-bound capacity reserved before AI calls
                  </p>
                </div>
              )}

              {planApiRequests && (
                <div className="rounded-xl border border-border/80 bg-muted/20 p-3 space-y-1">
                  <span className="text-[11px] font-medium text-muted-foreground">
                    Developer API Requests
                  </span>
                  {planApiRequests.limit === 0 ? (
                    <p className="text-xs text-muted-foreground">Not included in current plan</p>
                  ) : (
                    <p className="text-sm font-bold tabular-nums text-foreground">
                      {planApiRequests.used.toLocaleString()}{" "}
                      <span className="font-normal text-muted-foreground">
                        / {planApiRequests.limit.toLocaleString()}
                      </span>
                    </p>
                  )}
                </div>
              )}

              <div className="rounded-xl border border-border/80 bg-muted/20 p-3 space-y-1">
                <span className="text-[11px] font-medium text-muted-foreground">Team Seats</span>
                <p className="text-sm font-bold tabular-nums text-foreground">
                  {data.team_seats}{" "}
                  <span className="font-normal text-muted-foreground">
                    / {planSeats ? planSeats.limit : data.team_seats}
                  </span>
                </p>
                <p className="text-[10px] text-muted-foreground">Active workspace members</p>
              </div>

              {planMonitorChecks && (
                <div className="rounded-xl border border-border/80 bg-muted/20 p-3 space-y-1">
                  <span className="text-[11px] font-medium text-muted-foreground">
                    Scheduled Checks
                  </span>
                  {planMonitorChecks.limit === 0 ? (
                    <p className="text-xs text-muted-foreground">Not included in current plan</p>
                  ) : (
                    <p className="text-sm font-bold tabular-nums text-foreground">
                      {planMonitorChecks.used.toLocaleString()}{" "}
                      <span className="font-normal text-muted-foreground">
                        / {planMonitorChecks.limit.toLocaleString()}
                      </span>
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Provider-Reported AI Token Consumption */}
            <div className="space-y-2 border-t border-border/70 pt-3.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h4 className="text-xs font-semibold text-foreground">
                  Provider-Reported AI Consumption (Month)
                </h4>
                <span className="text-[11px] text-muted-foreground">
                  Actual Vertex AI / Gemini usage · separate from reserved capacity
                </span>
              </div>
              <div className="grid gap-2.5 sm:grid-cols-3">
                <div className="flex items-center justify-between rounded-lg border border-border/70 bg-muted/15 px-3 py-2">
                  <span className="text-muted-foreground">Model requests</span>
                  <span className="font-semibold tabular-nums text-foreground">
                    {data.provider_usage.requests.toLocaleString()}
                  </span>
                </div>
                <div className="flex items-center justify-between rounded-lg border border-border/70 bg-muted/15 px-3 py-2">
                  <span className="text-muted-foreground">Input tokens</span>
                  <span className="font-semibold tabular-nums text-foreground">
                    {data.provider_usage.input_tokens_reported.toLocaleString()}
                  </span>
                </div>
                <div className="flex items-center justify-between rounded-lg border border-border/70 bg-muted/15 px-3 py-2">
                  <span className="text-muted-foreground">Output tokens</span>
                  <span className="font-semibold tabular-nums text-foreground">
                    {data.provider_usage.output_tokens_reported.toLocaleString()}
                  </span>
                </div>
              </div>
            </div>

            {/* Daily Safety Limits */}
            {dailyItems.length > 0 && (
              <div className="space-y-2 border-t border-border/70 pt-3.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h4 className="text-xs font-semibold text-foreground">Daily Safety Limits (UTC)</h4>
                  <span className="text-[11px] text-muted-foreground">
                    Resets daily at 00:00 UTC · independent of monthly allowances
                  </span>
                </div>
                <div className="grid gap-2 sm:grid-cols-2">
                  {dailyItems.map((item) => (
                    <div
                      key={item.dimension}
                      className="flex items-center justify-between rounded-lg border border-border/70 bg-muted/15 px-3 py-2"
                    >
                      <span className="text-muted-foreground">{item.label}</span>
                      <span className="font-semibold tabular-nums text-foreground">
                        {item.used.toLocaleString()} / {item.limit.toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      {/* 4. Collapsible Payment History & Invoices */}
      {showInvoices && (
        <section className="rounded-2xl border border-border bg-card p-4 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-xs font-semibold text-foreground">Payment History &amp; Invoices</h3>
            {contract && subState?.can_manage && (
              <Button
                variant="outline"
                size="sm"
                disabled={busyAction !== null}
                onClick={() => void runSubscriptionAction("portal")}
                className="h-7 text-xs gap-1.5"
              >
                Open Creem Invoices <ExternalLink size={12} />
              </Button>
            )}
          </div>

          {totalInvoices === 0 ? (
            <p className="text-xs text-muted-foreground py-1">
              {resolved.isTrial
                ? "No invoices recorded yet ($0 charged during trial)."
                : "No verified payments or invoices recorded yet."}
            </p>
          ) : (
            <div className="divide-y divide-border rounded-xl border border-border overflow-hidden">
              {creemInvoices.map((p) => (
                <div
                  key={`${p.provider}:${p.environment}:${p.payment_id}`}
                  className="flex items-center justify-between px-3.5 py-2.5 text-xs"
                >
                  <div>
                    <span className="font-medium text-foreground">
                      {new Date(p.recorded_at).toLocaleDateString()}
                    </span>
                    <p className="text-[11px] text-muted-foreground capitalize">
                      {p.provider} · {p.environment}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="font-semibold text-foreground">
                      {formatMoney(p.amount_minor, p.currency)}
                    </span>
                    <p className="text-[11px] capitalize text-muted-foreground">{p.status}</p>
                  </div>
                </div>
              ))}
              {legacyPayments.map((p) => (
                <div
                  key={`${p.provider}:${p.provider_id}`}
                  className="flex items-center justify-between px-3.5 py-2.5 text-xs"
                >
                  <div>
                    <span className="font-medium text-foreground">
                      {new Date(p.recorded_at).toLocaleDateString()}
                    </span>
                    <p className="text-[11px] text-muted-foreground capitalize">
                      {p.provider} · {p.mode}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="font-semibold text-foreground">
                      {formatMoney(p.amount, p.currency)}
                    </span>
                    <p className="text-[11px] capitalize text-muted-foreground">
                      {p.status.toLowerCase()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
