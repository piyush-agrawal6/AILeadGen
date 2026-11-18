'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Check, ChevronDown, ChevronUp, ArrowUpRight } from 'lucide-react';
import type { FixedTermData } from './fixed-term-payments';
import { type PlanCode } from '@/lib/plan-intent';

export type CommercialCatalog = {
  version: string;
  name: string;
  list_currency: string;
  interval: string;
  allowances_approved: boolean;
  catalog_sha256: string;
  plans: {
    code: PlanCode;
    name: string;
    monthly_minor: number | null;
    audience: string;
    limits: Record<string, number> | null;
  }[];
  limit_definitions: { key: string; label: string; description: string }[];
  capabilities: { id: string; name: string; description: string }[];
  disclosures: string[];
};

export type CommercialBilling = {
  catalog: CommercialCatalog;
  provider: 'creem';
  checkout_enabled: boolean;
  fixed_term?: FixedTermData;
  blockers: string[];
  historical_payments: {
    provider: string;
    provider_id: string;
    mode: string;
    amount: number;
    currency: string;
    status: string;
    recorded_at: string;
  }[];
};

const formatMoney = (minor: number, currency: string) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(minor / 100);

const formatCount = (n: number) => new Intl.NumberFormat('en-US').format(n);

function planHighlights(plan: CommercialCatalog['plans'][number]): string[] {
  if (!plan.limits) {
    return [
      'Custom monthly search and monitoring volume',
      'Dedicated AI analysis & token capacity',
      'Multi-seat workspace access & custom API limits',
      'Dedicated onboarding and tailored data retention',
    ];
  }
  const l = plan.limits;
  return [
    `${formatCount(l.searches)} monthly searches`,
    `${formatCount(l.ai_calls)} shared AI operations (${formatCount(l.ai_tokens)} reserved tokens)`,
    `${formatCount(l.monitors)} active monitors · ${formatCount(l.monitor_executions)} scheduled checks`,
    `${formatCount(l.reports)} monthly reports · ${formatCount(l.api_requests)} API requests`,
    `${formatCount(l.team_members)} workspace ${l.team_members === 1 ? 'seat' : 'seats'}`,
  ];
}

export function CommercialPlans({
  data,
  selectedPlan,
  currentPlanCode = null,
  currentIsTrial = false,
}: {
  data: CommercialBilling;
  selectedPlan: PlanCode | null;
  currentPlanCode?: string | null;
  currentIsTrial?: boolean;
}) {
  const [showComparison, setShowComparison] = useState(false);

  return (
    <div className="space-y-6">
      <section className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-primary">
              Monthly plans · Tax-inclusive USD
            </p>
            <h2 className="text-xl font-semibold tracking-tight text-foreground mt-0.5">
              Intent intelligence for your next stage
            </h2>
            <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
              Compare monthly plans, published allowances, and team capacity. Eligible accounts can start with a 3-day card trial before converting.
            </p>
          </div>
          <span className="rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-medium text-primary">
            Billed via Creem
          </span>
        </div>

        {selectedPlan && (
          <p
            role="status"
            className="rounded-xl border border-primary/25 bg-primary/5 px-4 py-2.5 text-xs text-foreground"
          >
            Selected plan:{' '}
            <strong>{data.catalog.plans.find((p) => p.code === selectedPlan)?.name}</strong>. Your
            selection is saved; it does not create a subscription or authorize payment.
          </p>
        )}

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {data.catalog.plans.map((plan) => {
            const isSelected = selectedPlan === plan.code;
            const isCurrent = currentPlanCode?.toLowerCase() === plan.code.toLowerCase();
            const isEnterprise = plan.code === 'enterprise';
            const highlights = planHighlights(plan);

            return (
              <article
                key={plan.code}
                className={
                  'flex flex-col justify-between rounded-2xl border bg-card p-5 transition-colors ' +
                  (isCurrent
                    ? 'border-primary ring-1 ring-primary/25'
                    : isSelected
                      ? 'commercial-selected border-primary/70'
                      : 'border-border hover:border-primary/40')
                }
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="text-base font-semibold text-foreground">{plan.name}</h3>
                    {isCurrent && (
                      <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-[11px] font-semibold text-primary">
                        {currentIsTrial ? 'Current Trial' : 'Current Plan'}
                      </span>
                    )}
                  </div>

                  <div className="flex items-baseline gap-1">
                    <p className="commercial-price text-3xl font-bold tracking-tight text-foreground">
                      {plan.monthly_minor === null
                        ? 'Custom'
                        : formatMoney(plan.monthly_minor, data.catalog.list_currency)}
                    </p>
                    {plan.monthly_minor !== null && (
                      <span className="text-xs text-muted-foreground">/month</span>
                    )}
                  </div>

                  <p className="text-xs text-muted-foreground leading-relaxed min-h-[2.5rem]">
                    {plan.audience}
                  </p>

                  <ul className="space-y-2 border-t border-border/70 pt-3.5 text-xs text-foreground/90">
                    {highlights.map((item) => (
                      <li key={item} className="flex items-start gap-2">
                        <Check size={14} className="text-primary shrink-0 mt-0.5" aria-hidden="true" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="pt-5">
                  <a
                    className={
                      'inline-flex w-full items-center justify-center gap-1.5 rounded-xl px-4 py-2.5 text-xs font-semibold transition-colors ' +
                      (isCurrent && !currentIsTrial
                        ? 'border border-border bg-muted/40 text-foreground hover:bg-muted'
                        : isEnterprise
                          ? 'border border-border bg-card text-foreground hover:border-primary/50'
                          : 'bg-primary text-primary-foreground hover:opacity-95')
                    }
                    href={
                      isEnterprise
                        ? 'mailto:contact@planebyte.com?subject=Enterprise%20subscription'
                        : '/billing/subscription'
                    }
                  >
                    <span>
                      {isEnterprise
                        ? 'Contact sales'
                        : isCurrent && !currentIsTrial
                          ? `Manage ${plan.name}`
                          : `Choose ${plan.name}`}
                    </span>
                    <ArrowUpRight size={14} aria-hidden="true" />
                  </a>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      {/* Collapsible Feature Comparison */}
      <section className="rounded-2xl border border-border bg-card overflow-hidden">
        <button
          type="button"
          aria-expanded={showComparison}
          onClick={() => setShowComparison((prev) => !prev)}
          className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left hover:bg-muted/30 transition-colors cursor-pointer"
        >
          <div>
            <span className="text-sm font-semibold text-foreground">Compare All Features</span>
            <p className="text-xs text-muted-foreground mt-0.5">
              View complete monthly search, AI, monitoring, reporting, and API allowances across every plan.
            </p>
          </div>
          <span className="inline-flex items-center gap-1 text-xs font-medium text-primary shrink-0">
            {showComparison ? (
              <>
                Hide table <ChevronUp size={15} />
              </>
            ) : (
              <>
                Expand table <ChevronDown size={15} />
              </>
            )}
          </span>
        </button>

        {showComparison && (
          <div className="border-t border-border overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <caption className="sr-only">
                Catalog {data.catalog.version} approved plan allowances
              </caption>
              <thead className="bg-muted/40 text-muted-foreground">
                <tr>
                  <th
                    scope="col"
                    className="sticky left-0 z-10 bg-muted/90 backdrop-blur px-5 py-3 font-semibold text-foreground min-w-[200px]"
                  >
                    Feature / Allowance
                  </th>
                  {data.catalog.plans.map((p) => {
                    const isCurrent = currentPlanCode?.toLowerCase() === p.code.toLowerCase();
                    return (
                      <th
                        scope="col"
                        key={p.code}
                        className={
                          'px-4 py-3 font-semibold whitespace-nowrap ' +
                          (isCurrent ? 'text-primary bg-primary/5' : 'text-foreground')
                        }
                      >
                        {p.name}
                        {isCurrent && (
                          <span className="ml-1.5 rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px]">
                            {currentIsTrial ? 'Trial' : 'Current'}
                          </span>
                        )}
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody className="divide-y divide-border/70">
                <tr>
                  <th
                    scope="row"
                    className="sticky left-0 bg-card px-5 py-3 font-medium text-foreground"
                  >
                    Monthly price (USD, tax-inclusive)
                  </th>
                  {data.catalog.plans.map((p) => (
                    <td key={p.code} className="px-4 py-3 font-semibold text-foreground">
                      {p.monthly_minor === null ? 'Custom' : formatMoney(p.monthly_minor, 'USD')}
                    </td>
                  ))}
                </tr>

                {data.catalog.limit_definitions.map((item) => (
                  <tr key={item.key}>
                    <th
                      scope="row"
                      className="sticky left-0 bg-card px-5 py-3 font-medium text-foreground align-top"
                    >
                      <div>{item.label}</div>
                      <div className="font-normal text-[11px] text-muted-foreground mt-0.5 max-w-xs">
                        {item.description}
                      </div>
                    </th>
                    {data.catalog.plans.map((p) => (
                      <td key={p.code} className="px-4 py-3 tabular-nums text-foreground">
                        {p.limits ? formatCount(p.limits[item.key]) : 'By agreement'}
                      </td>
                    ))}
                  </tr>
                ))}

                <tr>
                  <th
                    scope="row"
                    className="sticky left-0 bg-card px-5 py-3 font-medium text-foreground"
                  >
                    Scheduled monitoring frequency
                  </th>
                  {data.catalog.plans.map((p) => (
                    <td key={p.code} className="px-4 py-3 text-muted-foreground">
                      {p.limits ? 'Daily (minimum interval)' : 'By agreement'}
                    </td>
                  ))}
                </tr>

                {data.catalog.capabilities.map((cap) => (
                  <tr key={cap.id}>
                    <th
                      scope="row"
                      className="sticky left-0 bg-card px-5 py-3 font-medium text-foreground align-top"
                    >
                      <div>{cap.name}</div>
                      <div className="font-normal text-[11px] text-muted-foreground mt-0.5 max-w-xs">
                        {cap.description}
                      </div>
                    </th>
                    {data.catalog.plans.map((p) => (
                      <td key={p.code} className="px-4 py-3 text-muted-foreground">
                        {p.code === 'enterprise' ? 'By agreement' : 'Included'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Concise legal & policy footer (replaces old dense Before purchasing block) */}
      <footer className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/70 bg-muted/20 px-4 py-3 text-xs text-muted-foreground">
        <span>
          Prices are tax-inclusive USD. Automatic renewal terms are shown before checkout authorization.
        </span>
        <nav className="flex flex-wrap items-center gap-3.5" aria-label="Billing policies">
          <Link href="/terms" className="text-primary hover:underline">
            Terms
          </Link>
          <Link href="/privacy" className="text-primary hover:underline">
            Privacy
          </Link>
          <Link href="/refund" className="text-primary hover:underline">
            Refund Policy
          </Link>
          <Link href="/cancellation" className="text-primary hover:underline">
            Cancellation Terms
          </Link>
        </nav>
      </footer>
    </div>
  );
}
