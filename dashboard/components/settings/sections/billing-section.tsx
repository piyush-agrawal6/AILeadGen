"use client";

import { useUsage } from "@/components/workspaces/usage";
import { CommercialPlans } from "@/components/workspaces/commercial-plans";
import { CreditCard, ShieldCheck, Sparkles, Check, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export function BillingSection({ activeTab, onSwitchTab }: { activeTab: string; onSwitchTab?: (tab: string) => void }) {
  const usageQuery = useUsage();

  if (usageQuery.isPending) {
    return <p role="status" className="text-sm text-muted-foreground">Loading workspace billing & usage telemetry…</p>;
  }

  if (usageQuery.isError || !usageQuery.data) {
    return (
      <div role="alert" className="rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
        <p>Billing telemetry could not be loaded: {usageQuery.error?.message || "Unknown error"}</p>
        <Button variant="outline" size="sm" className="mt-3" onClick={() => void usageQuery.refetch()}>
          Retry
        </Button>
      </div>
    );
  }

  const data = usageQuery.data;

  if (activeTab === "plans") {
    return (
      <div className="space-y-6">
        <div className="border-b pb-4">
          <h2 className="text-xl font-semibold tracking-tight">Subscription Plans Catalog</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Compare plans, monthly search allowances, and Growth Intelligence capabilities. Synchronized with planebyte.com/pricing.
          </p>
        </div>
        <CommercialPlans data={data.commercial} selectedPlan={null} />
      </div>
    );
  }

  return (
    <div className="space-y-7">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Current Plan & Usage</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Understand active product access, search allowances, and AI token consumption.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          onClick={() => onSwitchTab?.("plans")}
        >
          <CreditCard size={14} /> Compare all plans
        </Button>
      </div>

      {/* Plan Status Card */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 rounded-xl border bg-card p-5">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary border border-primary/20">
              {data.access.kind}
            </span>
            <span className="text-xs text-muted-foreground">
              {data.subscription?.mode === "test" ? "Sandbox Mode" : "Pilot Access"}
            </span>
          </div>
          <h3 className="text-base font-semibold">Intent Radar + Growth Intelligence</h3>
          <p className="text-xs text-muted-foreground">
            {data.team_seats} active workspace seat{data.team_seats === 1 ? "" : "s"} · Enforced server-side
          </p>
        </div>

        <div className="text-left sm:text-right space-y-1">
          <p className="text-xs text-muted-foreground">
            {data.search_usage?.reset_at ? (
              <>Allowance resets {new Date(data.search_usage.reset_at).toLocaleDateString()}</>
            ) : (
              <>Resets monthly</>
            )}
          </p>
          <a
            href={data.support_url}
            className="inline-flex text-xs font-medium text-primary hover:underline"
          >
            Contact support about limits →
          </a>
        </div>
      </div>

      {/* Usage Allowances */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold">Monthly Search & Monitoring Allowances</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          {data.usage.map((item) => {
            const percent = Math.min(100, Math.round((item.used / Math.max(1, item.limit)) * 100));
            return (
              <div key={item.dimension} className="rounded-xl border bg-card p-4 space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold">{item.label}</span>
                  <span className="text-muted-foreground tabular-nums">
                    {item.used.toLocaleString()} / {item.limit.toLocaleString()}
                  </span>
                </div>

                <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className={`h-full transition-all ${
                      percent > 90 ? "bg-destructive" : percent > 75 ? "bg-amber-500" : "bg-primary"
                    }`}
                    style={{ width: `${percent}%` }}
                  />
                </div>

                <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                  <span>{item.remaining.toLocaleString()} remaining</span>
                  <span>{percent}% used</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* AI Token Accounting */}
      <div className="rounded-xl border bg-card p-5 space-y-4">
        <div>
          <h3 className="text-sm font-semibold">Model Requests & Reported AI Tokens</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Token telemetry is reported directly by provider infrastructure (Vertex AI / Gemini).
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-3 pt-1">
          <div className="rounded-lg bg-muted/30 p-3 space-y-1">
            <span className="text-xs text-muted-foreground">Provider Requests</span>
            <p className="text-xl font-semibold tabular-nums">{data.provider_usage.requests}</p>
          </div>
          <div className="rounded-lg bg-muted/30 p-3 space-y-1">
            <span className="text-xs text-muted-foreground">Input Tokens Reported</span>
            <p className="text-xl font-semibold tabular-nums">{data.provider_usage.input_tokens_reported.toLocaleString()}</p>
          </div>
          <div className="rounded-lg bg-muted/30 p-3 space-y-1">
            <span className="text-xs text-muted-foreground">Output Tokens Reported</span>
            <p className="text-xl font-semibold tabular-nums">{data.provider_usage.output_tokens_reported.toLocaleString()}</p>
          </div>
        </div>

        {data.provider_usage.estimated_cost_usd && (
          <p className="text-xs text-muted-foreground">
            Estimated provider inference cost this period: <strong>${data.provider_usage.estimated_cost_usd}</strong>
          </p>
        )}
      </div>

      {/* Payment History */}
      {data.commercial.historical_payments.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold">Transaction & Payment Records</h3>
          <div className="divide-y rounded-xl border bg-card overflow-hidden">
            {data.commercial.historical_payments.map((p) => (
              <div key={p.provider_id} className="flex items-center justify-between p-4 text-xs">
                <div>
                  <span className="font-medium">{new Date(p.recorded_at).toLocaleDateString()}</span>
                  <p className="text-muted-foreground mt-0.5">{p.provider} · {p.mode}</p>
                </div>
                <div className="text-right">
                  <span className="font-semibold">
                    {new Intl.NumberFormat("en-US", { style: "currency", currency: p.currency }).format(p.amount / 100)}
                  </span>
                  <p className="capitalize text-muted-foreground mt-0.5">{p.status.toLowerCase()}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
