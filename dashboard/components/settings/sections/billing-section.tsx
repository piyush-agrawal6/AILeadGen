"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CreditCard,
  ExternalLink,
  FileText,
  Info,
  Radio,
  Receipt,
  RefreshCw,
  Search,
  Sparkles,
} from "lucide-react";
import { request } from "@/lib/intelligence";
import { Button } from "@/components/ui/button";
import { useUsage, type UsageData } from "@/components/workspaces/usage";
import { CommercialPlans } from "@/components/workspaces/commercial-plans";
import { FixedTermPayments } from "@/components/workspaces/fixed-term-payments";
import {
  SubscriptionPayment,
  type SubscriptionState,
} from "@/components/workspaces/subscription-payment";

type Allowance = UsageData["usage"][number];

const formatDate = (unix?: number | null) =>
  unix
    ? new Date(unix * 1000).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "—";

const formatDateTime = (unix?: number | null) =>
  unix
    ? new Date(unix * 1000).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
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
  planSubtitle: string;
  explanation: string;
  isTrial: boolean;
  isCanceled: boolean;
  isActive: boolean;
};

function resolvePlanStatus(
  subState?: SubscriptionState | null,
  usage?: UsageData | null
): ResolvedStatus {
  const contract = subState?.contract;
  const sub = usage?.subscription;
  const isActive = Boolean(subState?.active || (usage?.access.intent_radar && sub));
  const isTrial = Boolean(
    contract?.is_trial ??
      sub?.is_trial ??
      usage?.access.is_trial ??
      (contract?.trial_start != null && contract.period_start === contract.trial_start)
  );
  const rawStatus = (contract?.status || sub?.provider_status || sub?.status || "").toLowerCase();
  const isCanceled = Boolean(
    contract?.cancel_confirmed_at ||
      sub?.cancel_confirmed_at ||
      rawStatus === "canceled" ||
      rawStatus === "scheduled_cancel"
  );
  const endTs =
    (isTrial ? contract?.trial_end ?? sub?.trial_end : null) ??
    contract?.period_end ??
    sub?.period_end ??
    usage?.native_access?.expires_at ??
    null;

  const planCode = (contract?.plan_code || sub?.plan_code || "").trim().toLowerCase();
  const tierName = planCode
    ? planCode.charAt(0).toUpperCase() + planCode.slice(1)
    : "";
  const planTitle =
    contract?.entitlement_label ||
    sub?.entitlement_label ||
    (tierName ? (isTrial ? `${tierName} Trial` : `Paid ${tierName}`) : usage?.access.kind || "No active plan");

  if (!contract && !sub) {
    if (usage?.access.intent_radar) {
      return {
        label: "Active",
        tone: "blue",
        planTitle: usage.access.kind || "Approved Access",
        planSubtitle: "Workspace access is enabled",
        explanation: "Your workspace currently has authorized access without a recurring Creem subscription.",
        isTrial: false,
        isCanceled: false,
        isActive: true,
      };
    }
    return {
      label: "No Subscription",
      tone: "muted",
      planTitle: "No active subscription",
      planSubtitle: "Choose a plan or start a 3-day card trial",
      explanation: "Activate a verified subscription via Creem to unlock Intent Radar searches, monitoring, and reports.",
      isTrial: false,
      isCanceled: false,
      isActive: false,
    };
  }

  if (rawStatus === "past_due" || rawStatus === "unpaid") {
    return {
      label: "Past Due",
      tone: "red",
      planTitle,
      planSubtitle: "Payment attention required",
      explanation: "Your last subscription payment failed or is past due. Update your payment method in the Creem billing portal to restore access.",
      isTrial,
      isCanceled,
      isActive: false,
    };
  }

  if (rawStatus === "pending" || rawStatus === "creating") {
    return {
      label: "Payment Pending",
      tone: "amber",
      planTitle,
      planSubtitle: "Awaiting provider confirmation",
      explanation: "Creem is confirming your checkout. Refresh status shortly — no duplicate charge will be created.",
      isTrial,
      isCanceled: false,
      isActive: false,
    };
  }

  if (!isActive || rawStatus === "expired") {
    return {
      label: "Expired",
      tone: "muted",
      planTitle,
      planSubtitle: endTs ? `Ended ${formatDate(endTs)}` : "Subscription period ended",
      explanation: "Your previous access period has ended. Saved research remains available; choose a plan to resume discovery.",
      isTrial,
      isCanceled: true,
      isActive: false,
    };
  }

  if (isTrial && isCanceled) {
    return {
      label: "Canceled — Access Remaining",
      tone: "amber",
      planTitle,
      planSubtitle: "3-day card trial · renewal canceled",
      explanation: `Your trial has been canceled. You can continue using your current access until ${formatDateTime(endTs)}. No automatic renewal is scheduled.`,
      isTrial: true,
      isCanceled: true,
      isActive: true,
    };
  }

  if (isTrial) {
    return {
      label: "Trial Active",
      tone: "blue",
      planTitle,
      planSubtitle: "3-day card trial",
      explanation: `Your 3-day trial is active until ${formatDateTime(endTs)}. Unless canceled before expiration, your plan will convert automatically to Paid ${tierName || "Starter"}.`,
      isTrial: true,
      isCanceled: false,
      isActive: true,
    };
  }

  if (isCanceled) {
    return {
      label: endTs ? `Cancels on ${formatDate(endTs)}` : "Canceled — Access Remaining",
      tone: "amber",
      planTitle,
      planSubtitle: "Paid monthly subscription · renewal canceled",
      explanation: `Automatic renewal is canceled. Your paid access remains active until ${formatDateTime(endTs)} with no future charge.`,
      isTrial: false,
      isCanceled: true,
      isActive: true,
    };
  }

  return {
    label: "Active",
    tone: "emerald",
    planTitle,
    planSubtitle: "Paid monthly subscription",
    explanation: `Your subscription is active and renews automatically on ${formatDate(contract?.next_charge_at ?? endTs)}.`,
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

function barColor(used: number, limit: number, neutral = false): string {
  if (neutral) return "bg-primary/70";
  if (limit > 0 && used >= limit) return "bg-destructive";
  if (limit > 0 && used / limit >= 0.8) return "bg-amber-500";
  return "bg-primary";
}

function PrimaryMetricCard({
  title,
  icon: Icon,
  item,
  secondaryNote,
  exhaustedBanner,
}: {
  title: string;
  icon: typeof Search;
  item?: Allowance;
  secondaryNote?: string;
  exhaustedBanner?: string;
}) {
  if (!item) return null;
  const notIncluded = item.limit === 0;
  const exhausted = !notIncluded && item.remaining === 0;
  const approaching = !notIncluded && !exhausted && item.used / item.limit >= 0.8;
  const percent = notIncluded ? 0 : Math.min(100, Math.round((item.used / item.limit) * 100));

  return (
    <article className="flex flex-col justify-between rounded-2xl border border-border bg-card p-5 space-y-3">
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <Icon size={16} className="text-primary shrink-0" aria-hidden="true" />
            <span>{title}</span>
          </div>
          {notIncluded ? (
            <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
              Not included
            </span>
          ) : exhausted ? (
            <span className="rounded-full bg-destructive/10 px-2 py-0.5 text-[11px] font-semibold text-destructive">
              Exhausted
            </span>
          ) : approaching ? (
            <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[11px] font-semibold text-amber-700 dark:text-amber-300">
              Near limit
            </span>
          ) : (
            <span className="text-xs font-medium text-muted-foreground tabular-nums">
              {item.remaining.toLocaleString()} left
            </span>
          )}
        </div>

        {notIncluded ? (
          <div className="space-y-1 pt-1">
            <p className="text-sm font-medium text-muted-foreground">
              Not included in your current plan
            </p>
            <p className="text-xs text-muted-foreground">
              Upgrade to a paid plan to unlock {title.toLowerCase()}.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="flex items-baseline justify-between gap-2">
              <p className="text-2xl font-bold tracking-tight text-foreground tabular-nums">
                {item.used.toLocaleString()}
                <span className="text-sm font-normal text-muted-foreground">
                  {" "}
                  of {item.limit.toLocaleString()} used
                </span>
              </p>
            </div>
            <div
              className="h-2 w-full overflow-hidden rounded-full bg-muted"
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
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
              <span>
                {exhausted
                  ? "No allowance remaining"
                  : `${item.remaining.toLocaleString()} remaining`}
              </span>
              {item.resets_at && (
                <span>Resets {new Date(item.resets_at).toLocaleDateString()}</span>
              )}
            </div>
          </div>
        )}

        {exhaustedBanner && (
          <div className="rounded-xl border border-destructive/25 bg-destructive/5 px-3 py-2 text-xs text-destructive leading-relaxed">
            {exhaustedBanner}
          </div>
        )}
      </div>

      {secondaryNote && (
        <p className="border-t border-border/60 pt-2.5 text-[11px] text-muted-foreground">
          {secondaryNote}
        </p>
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
  const usageQuery = useUsage();
  const subQuery = useQuery({
    queryKey: ["workspace-subscription"],
    queryFn: ({ signal }) => request<SubscriptionState>("/billing/subscription", { signal }),
    retry: false,
    refetchOnWindowFocus: false,
  });

  const [busyAction, setBusyAction] = useState<"portal" | "cancel" | "refresh" | null>(null);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [actionNotice, setActionNotice] = useState("");
  const [actionError, setActionError] = useState("");
  const [showDetailedUsage, setShowDetailedUsage] = useState(false);
  const [showAiDetails, setShowAiDetails] = useState(false);
  const [showInvoices, setShowInvoices] = useState(false);

  async function runSubscriptionAction(kind: "portal" | "cancel" | "refresh") {
    setBusyAction(kind);
    setActionError("");
    setActionNotice("");
    try {
      if (kind === "refresh") {
        const next = await request<SubscriptionState>("/billing/subscription/refresh", {
          method: "POST",
        });
        client.setQueryData(["workspace-subscription"], next);
        await usageQuery.refetch();
        setActionNotice("Subscription status synchronized with Creem.");
      } else if (kind === "portal") {
        const res = await request<{ url?: string }>("/billing/subscription/portal", {
          method: "POST",
        });
        if (res.url) {
          window.location.assign(res.url);
        } else {
          setActionError("Billing portal link was not returned by Creem.");
        }
      } else if (kind === "cancel") {
        const res = await request<{ status?: string }>("/billing/subscription/cancel", {
          method: "POST",
          body: JSON.stringify({ request_id: crypto.randomUUID() }),
        });
        setConfirmCancel(false);
        setActionNotice(
          res.status === "CONFIRMED"
            ? "Automatic renewal has been canceled with Creem. Your access remains active until the end of the current period."
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

  if (usageQuery.isPending) {
    return (
      <div className="space-y-5" role="status" aria-label="Loading billing and usage">
        <div className="h-44 rounded-2xl border border-border bg-muted/30 animate-pulse" />
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="h-36 rounded-2xl border border-border bg-muted/30 animate-pulse" />
          <div className="h-36 rounded-2xl border border-border bg-muted/30 animate-pulse" />
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
      </div>
    );
  }

  const data = usageQuery.data;
  const subState = subQuery.data;
  const resolved = resolvePlanStatus(subState, data);
  const contract = subState?.contract;
  const currentPlanCode = contract?.plan_code || data.subscription?.plan_code || null;
  const catalogPlan = data.commercial.catalog.plans.find(
    (p) => p.code.toLowerCase() === (currentPlanCode || "").toLowerCase()
  );

  if (activeTab === "plans") {
    return (
      <CommercialPlans
        data={data.commercial}
        selectedPlan={null}
        currentPlanCode={currentPlanCode}
        currentIsTrial={resolved.isTrial}
      />
    );
  }

  // Categorize allowances cleanly
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

  const periodStart = contract?.trial_start ?? contract?.period_start ?? data.subscription?.period_start ?? data.native_access?.starts_at ?? null;
  const periodEnd =
    (resolved.isTrial ? contract?.trial_end ?? data.subscription?.trial_end : null) ??
    contract?.period_end ??
    data.subscription?.period_end ??
    data.native_access?.expires_at ??
    null;

  const creemInvoices = subState?.history || [];
  const legacyPayments = data.commercial.historical_payments || [];
  const totalInvoices = creemInvoices.length + legacyPayments.length;

  return (
    <div className="space-y-6">
      {/* 1. Authoritative Current Subscription Summary */}
      <section
        aria-label="Your Current Plan"
        className="rounded-2xl border border-border bg-card p-5 sm:p-6 space-y-5"
      >
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div className="space-y-1.5">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Your Current Plan
            </p>
            <div className="flex flex-wrap items-center gap-2.5">
              <h3 className="text-xl font-bold tracking-tight text-foreground">
                {resolved.planTitle}
              </h3>
              <span
                className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${BADGE_TONES[resolved.tone]}`}
              >
                {resolved.tone === "emerald" ? (
                  <CheckCircle2 size={13} aria-hidden="true" />
                ) : resolved.tone === "red" || resolved.tone === "amber" ? (
                  <AlertTriangle size={13} aria-hidden="true" />
                ) : (
                  <Info size={13} aria-hidden="true" />
                )}
                {resolved.label}
              </span>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed max-w-2xl">
              {resolved.explanation}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            {contract && subState?.can_manage && (
              <Button
                size="sm"
                disabled={busyAction !== null}
                onClick={() => void runSubscriptionAction("portal")}
                className="gap-1.5"
              >
                <CreditCard size={14} />
                {busyAction === "portal" ? "Opening portal…" : "Manage Subscription"}
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => onSwitchTab?.("plans")}
            >
              View Plans
            </Button>
          </div>
        </div>

        {/* Clean 4-item billing facts strip */}
        {(contract || data.subscription) && (
          <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 border-t border-border/70 pt-4 text-xs">
            <div className="rounded-xl bg-muted/30 px-3.5 py-2.5">
              <dt className="text-muted-foreground">Subscription type</dt>
              <dd className="font-semibold text-foreground mt-0.5">{resolved.planSubtitle}</dd>
            </div>
            <div className="rounded-xl bg-muted/30 px-3.5 py-2.5">
              <dt className="text-muted-foreground">
                {resolved.isTrial ? "Trial window" : "Current billing period"}
              </dt>
              <dd className="font-semibold text-foreground mt-0.5">
                {periodStart ? `${formatDate(periodStart)} – ${formatDate(periodEnd)}` : formatDate(periodEnd)}
              </dd>
            </div>
            <div className="rounded-xl bg-muted/30 px-3.5 py-2.5">
              <dt className="text-muted-foreground">Next charge</dt>
              <dd className="font-semibold text-foreground mt-0.5">
                {resolved.isCanceled
                  ? "No automatic renewal scheduled"
                  : contract?.next_charge_at && catalogPlan?.monthly_minor
                    ? `${formatMoney(catalogPlan.monthly_minor)} on ${formatDate(contract.next_charge_at)}`
                    : "—"}
              </dd>
            </div>
            <div className="rounded-xl bg-muted/30 px-3.5 py-2.5">
              <dt className="text-muted-foreground">Billing provider</dt>
              <dd className="font-semibold text-foreground mt-0.5 capitalize">
                {contract?.provider || "Creem"} · {contract?.environment || data.subscription?.mode || "live"}
              </dd>
            </div>
          </dl>
        )}

        {/* Trial vs Paid Allowance Difference Callout */}
        {resolved.isTrial && catalogPlan?.limits && (
          <div className="flex items-start gap-2.5 rounded-xl border border-blue-500/20 bg-blue-500/5 px-4 py-3 text-xs text-foreground">
            <Info size={15} className="text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" aria-hidden="true" />
            <p className="leading-relaxed">
              <strong>Starter Trial allowances apply</strong> (5 searches, 3 shared AI operations, 150,000 reserved AI tokens, 1 manual monitor). Paid {catalogPlan.name} unlocks{" "}
              {catalogPlan.limits.searches.toLocaleString()} monthly searches,{" "}
              {catalogPlan.limits.ai_calls.toLocaleString()} AI operations,{" "}
              {catalogPlan.limits.monitors} active monitors, scheduled checks, reports, and Developer API access.
            </p>
          </div>
        )}

        {/* Owner-Only Temporary Internal Testing Allowance Notice (omitted for all regular customers) */}
        {data.internal_testing?.active && (
          <div
            role="status"
            className="flex items-start gap-2.5 rounded-xl border border-amber-500/35 bg-amber-500/10 px-4 py-3 text-xs text-foreground"
          >
            <Sparkles size={15} className="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" aria-hidden="true" />
            <div className="space-y-0.5">
              <p className="font-semibold">
                Temporary internal testing allowance active (owner testing workspace only)
              </p>
              <p className="text-muted-foreground leading-relaxed">
                Underlying plan remains <strong>{data.internal_testing.base_entitlement || resolved.planTitle}</strong> and your original trial usage history is preserved untouched. Bounded testing capacity auto-expires on{" "}
                <strong>{formatDateTime(data.internal_testing.expires_at)}</strong>.
              </p>
            </div>
          </div>
        )}

        {/* Secondary Subscription Actions */}
        {contract && subState?.can_manage && (
          <div className="flex flex-wrap items-center gap-2 border-t border-border/70 pt-3.5">
            {!resolved.isCanceled && resolved.isActive && !confirmCancel && (
              <Button
                variant="outline"
                size="sm"
                disabled={busyAction !== null}
                onClick={() => setConfirmCancel(true)}
              >
                Cancel Renewal
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              disabled={busyAction !== null}
              onClick={() => void runSubscriptionAction("refresh")}
              className="gap-1.5 text-muted-foreground"
            >
              <RefreshCw size={13} className={busyAction === "refresh" ? "animate-spin" : ""} />
              {busyAction === "refresh" ? "Syncing…" : "Refresh Status"}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowInvoices((v) => !v)}
              className="gap-1.5 text-muted-foreground ml-auto"
            >
              <Receipt size={13} />
              Payment History &amp; Invoices ({totalInvoices})
            </Button>
          </div>
        )}

        {/* Inline Cancel Confirmation */}
        {confirmCancel && (
          <div
            role="alertdialog"
            aria-label="Confirm automatic renewal cancellation"
            className="rounded-xl border border-destructive/30 bg-destructive/5 p-4 space-y-3"
          >
            <p className="text-xs text-foreground leading-relaxed">
              <strong>Cancel automatic renewal?</strong> Your current access will continue until{" "}
              <strong>{formatDateTime(periodEnd)}</strong>. No further renewal charge will be billed, and your saved research remains preserved.
            </p>
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="destructive"
                disabled={busyAction !== null}
                onClick={() => void runSubscriptionAction("cancel")}
              >
                {busyAction === "cancel" ? "Canceling…" : "Confirm cancellation"}
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={busyAction !== null}
                onClick={() => setConfirmCancel(false)}
              >
                Keep renewal active
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

      {/* Only render full checkout flow when workspace does NOT have an active verified subscription */}
      {!resolved.isActive && subState?.enabled && <SubscriptionPayment />}

      {/* Legacy fixed-term history if present */}
      {!!data.commercial.fixed_term?.items.length && (
        <FixedTermPayments
          data={data.commercial.fixed_term}
          plans={data.commercial.catalog.plans}
        />
      )}

      {/* 2. Primary Customer Usage Dashboard */}
      <section aria-label="Usage overview" className="space-y-3.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-base font-semibold tracking-tight text-foreground">
              {data.internal_testing?.active
                ? "Active Testing Usage"
                : resolved.isTrial
                  ? `${resolved.planTitle} Usage`
                  : "Plan Usage"}
            </h3>
            <p className="text-xs text-muted-foreground">
              Enforced server-side in UTC across your current allowance window.
            </p>
          </div>
          {periodEnd && (
            <span className="text-xs text-muted-foreground">
              Window ends {formatDate(periodEnd)}
            </span>
          )}
        </div>

        {monthlySearchBlockedButDailyAvailable && (
          <div
            role="status"
            className="flex items-start gap-2.5 rounded-xl border border-destructive/25 bg-destructive/5 px-4 py-3 text-xs text-foreground"
          >
            <AlertTriangle size={15} className="text-destructive shrink-0 mt-0.5" aria-hidden="true" />
            <div>
              <p className="font-semibold text-destructive">Search allowance exhausted</p>
              <p className="text-muted-foreground mt-0.5">
                Your monthly search allowance has been reached, even though your daily safety limit has remaining capacity ({dailySearches?.remaining.toLocaleString()} left today).
              </p>
            </div>
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          <PrimaryMetricCard
            title="Monthly Searches"
            icon={Search}
            item={planSearches || dailySearches}
            secondaryNote={
              data.search_usage
                ? `${data.search_usage.manual_searches} manual searches · ${data.search_usage.scheduled_checks} scheduled checks`
                : undefined
            }
          />
          <PrimaryMetricCard
            title="AI Operations"
            icon={Sparkles}
            item={planAiCalls || findAllowance(data.usage, "ai_calls")}
            secondaryNote={
              planAiTokens
                ? `Shared token capacity: ${planAiTokens.used.toLocaleString()} / ${planAiTokens.limit.toLocaleString()} reserved`
                : undefined
            }
          />
          <PrimaryMetricCard
            title="Active Monitors"
            icon={Radio}
            item={planMonitors || findAllowance(data.usage, "monitors")}
            secondaryNote={
              planMonitorChecks
                ? planMonitorChecks.limit === 0
                  ? "Scheduled monitoring checks: Not included in your current plan"
                  : `Scheduled checks: ${planMonitorChecks.used.toLocaleString()} / ${planMonitorChecks.limit.toLocaleString()}`
                : undefined
            }
          />
          <PrimaryMetricCard
            title="Monthly Reports"
            icon={FileText}
            item={planReports}
            secondaryNote="Reports use both monthly report allowance and shared AI operations."
          />
        </div>
      </section>

      {/* 3. Expandable Detailed Usage (Tokens, API, Seats, Daily Safety Limits) */}
      <section className="rounded-2xl border border-border bg-card overflow-hidden">
        <button
          type="button"
          aria-expanded={showDetailedUsage}
          onClick={() => setShowDetailedUsage((v) => !v)}
          className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left hover:bg-muted/30 transition-colors cursor-pointer"
        >
          <div>
            <span className="text-sm font-semibold text-foreground">Detailed Usage</span>
            <p className="text-xs text-muted-foreground mt-0.5">
              Reserved AI tokens, Developer API requests, workspace seats, and daily safety limits.
            </p>
          </div>
          {showDetailedUsage ? (
            <ChevronUp size={16} className="text-muted-foreground shrink-0" />
          ) : (
            <ChevronDown size={16} className="text-muted-foreground shrink-0" />
          )}
        </button>

        {showDetailedUsage && (
          <div className="border-t border-border p-5 space-y-5">
            <div className="grid gap-3.5 sm:grid-cols-3 text-xs">
              {planAiTokens && (
                <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5 space-y-1.5">
                  <span className="font-semibold text-foreground">Reserved AI Token Allowance</span>
                  <p className="text-sm font-bold tabular-nums text-foreground">
                    {planAiTokens.used.toLocaleString()}{" "}
                    <span className="font-normal text-muted-foreground">
                      / {planAiTokens.limit.toLocaleString()}
                    </span>
                  </p>
                  <p className="text-[11px] text-muted-foreground">
                    Upper-bound capacity reserved before AI requests run.
                  </p>
                </div>
              )}

              {planApiRequests && (
                <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5 space-y-1.5">
                  <span className="font-semibold text-foreground">Developer API Requests</span>
                  {planApiRequests.limit === 0 ? (
                    <p className="text-xs text-muted-foreground">Not included in your current plan</p>
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

              <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5 space-y-1.5">
                <span className="font-semibold text-foreground">Team Seats</span>
                <p className="text-sm font-bold tabular-nums text-foreground">
                  {data.team_seats}{" "}
                  <span className="font-normal text-muted-foreground">
                    of {planSeats ? planSeats.limit : data.team_seats} assigned
                  </span>
                </p>
                <p className="text-[11px] text-muted-foreground">
                  Active workspace members on your current plan.
                </p>
              </div>
            </div>

            {dailyItems.length > 0 && (
              <div className="space-y-2.5 border-t border-border/70 pt-4">
                <div>
                  <h4 className="text-xs font-semibold text-foreground">Daily Safety Limits (UTC)</h4>
                  <p className="text-[11px] text-muted-foreground">
                    Per-day operational safeguards apply independently of your monthly plan allowances.
                  </p>
                </div>
                <div className="grid gap-2.5 sm:grid-cols-2">
                  {dailyItems.map((item) => (
                    <div
                      key={item.dimension}
                      className="flex items-center justify-between rounded-xl border border-border/70 bg-muted/15 px-3.5 py-2.5 text-xs"
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

      {/* 4. Expandable AI Usage Details (Telemetry) */}
      <section className="rounded-2xl border border-border bg-card overflow-hidden">
        <button
          type="button"
          aria-expanded={showAiDetails}
          onClick={() => setShowAiDetails((v) => !v)}
          className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left hover:bg-muted/30 transition-colors cursor-pointer"
        >
          <div>
            <span className="text-sm font-semibold text-foreground">AI Usage Details</span>
            <p className="text-xs text-muted-foreground mt-0.5">
              Provider-reported model requests and token consumption (separate from reserved allowance).
            </p>
          </div>
          {showAiDetails ? (
            <ChevronUp size={16} className="text-muted-foreground shrink-0" />
          ) : (
            <ChevronDown size={16} className="text-muted-foreground shrink-0" />
          )}
        </button>

        {showAiDetails && (
          <div className="border-t border-border p-5 space-y-4">
            <div className="grid gap-3.5 sm:grid-cols-3">
              <div className="rounded-xl bg-muted/30 p-3.5 space-y-1">
                <span className="text-xs text-muted-foreground">Provider Requests (Month)</span>
                <p className="text-xl font-bold tabular-nums text-foreground">
                  {data.provider_usage.requests.toLocaleString()}
                </p>
              </div>
              <div className="rounded-xl bg-muted/30 p-3.5 space-y-1">
                <span className="text-xs text-muted-foreground">Reported Input Tokens</span>
                <p className="text-xl font-bold tabular-nums text-foreground">
                  {data.provider_usage.input_tokens_reported.toLocaleString()}
                </p>
              </div>
              <div className="rounded-xl bg-muted/30 p-3.5 space-y-1">
                <span className="text-xs text-muted-foreground">Reported Output Tokens</span>
                <p className="text-xl font-bold tabular-nums text-foreground">
                  {data.provider_usage.output_tokens_reported.toLocaleString()}
                </p>
              </div>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Token counts are reported directly by Vertex AI / Gemini and are shown for transparency — PlaneByte bills by monthly subscription plan, not per-token overages. Reserved token capacity is an upper-bound safeguard and may differ from actual reported consumption.
            </p>
          </div>
        )}
      </section>

      {/* 5. Expandable Payment History & Invoices */}
      {showInvoices && (
        <section className="rounded-2xl border border-border bg-card p-5 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-foreground">Payment History &amp; Invoices</h3>
            {contract && subState?.can_manage && (
              <Button
                variant="outline"
                size="sm"
                disabled={busyAction !== null}
                onClick={() => void runSubscriptionAction("portal")}
                className="gap-1.5"
              >
                Open Creem Invoices <ExternalLink size={13} />
              </Button>
            )}
          </div>

          {totalInvoices === 0 ? (
            <p className="text-xs text-muted-foreground py-2">
              {resolved.isTrial
                ? "No payments or invoices recorded yet ($0 charged during your 3-day trial)."
                : "No verified payments or invoices have been recorded for this workspace."}
            </p>
          ) : (
            <div className="divide-y divide-border rounded-xl border border-border overflow-hidden">
              {creemInvoices.map((p) => (
                <div
                  key={`${p.provider}:${p.environment}:${p.payment_id}`}
                  className="flex items-center justify-between p-3.5 text-xs"
                >
                  <div>
                    <span className="font-medium text-foreground">
                      {new Date(p.recorded_at).toLocaleDateString()}
                    </span>
                    <p className="text-muted-foreground capitalize mt-0.5">
                      {p.provider} · {p.environment}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="font-semibold text-foreground">
                      {formatMoney(p.amount_minor, p.currency)}
                    </span>
                    <p className="capitalize text-muted-foreground mt-0.5">{p.status}</p>
                  </div>
                </div>
              ))}
              {legacyPayments.map((p) => (
                <div
                  key={`${p.provider}:${p.provider_id}`}
                  className="flex items-center justify-between p-3.5 text-xs"
                >
                  <div>
                    <span className="font-medium text-foreground">
                      {new Date(p.recorded_at).toLocaleDateString()}
                    </span>
                    <p className="text-muted-foreground capitalize mt-0.5">
                      {p.provider} · {p.mode}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="font-semibold text-foreground">
                      {formatMoney(p.amount, p.currency)}
                    </span>
                    <p className="capitalize text-muted-foreground mt-0.5">
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
