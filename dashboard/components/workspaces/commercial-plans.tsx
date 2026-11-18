'use client';

import { useRef, useState } from 'react';
import Link from 'next/link';
import {
  AlertCircle,
  ArrowUpRight,
  Check,
  ChevronDown,
  ChevronUp,
  CreditCard,
  Loader2,
  Lock,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-react';
import { request } from '@/lib/intelligence';
import { Button } from '@/components/ui/button';
import type { FixedTermData } from './fixed-term-payments';
import type { SubscriptionState } from './subscription-payment';
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

const formatMoney = (minor: number, currency = 'USD') =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: minor % 100 === 0 ? 0 : 2,
  }).format(minor / 100);

const formatCount = (n: number) => new Intl.NumberFormat('en-US').format(n);

function planHighlights(plan: CommercialCatalog['plans'][number]): string[] {
  if (!plan.limits) {
    return [
      'Custom search & monitor limits',
      'Dedicated AI capacity',
      'Multi-seat & custom API',
      'Dedicated onboarding & SLA',
    ];
  }
  const l = plan.limits;
  return [
    `${formatCount(l.searches)} monthly searches`,
    `${formatCount(l.ai_calls)} AI operations`,
    `${formatCount(l.monitors)} active monitors`,
    `${formatCount(l.reports)} monthly reports`,
    `${formatCount(l.team_members)} workspace ${l.team_members === 1 ? 'seat' : 'seats'}`,
  ];
}

export function CommercialPlans({
  data,
  selectedPlan,
  currentPlanCode = null,
  currentIsTrial = false,
  subscriptionState = null,
}: {
  data: CommercialBilling;
  selectedPlan: PlanCode | null;
  currentPlanCode?: string | null;
  currentIsTrial?: boolean;
  subscriptionState?: SubscriptionState | null;
}) {
  const [showComparison, setShowComparison] = useState(false);
  const [activeCheckoutPlan, setActiveCheckoutPlan] = useState<PlanCode | null>(
    selectedPlan && selectedPlan !== 'enterprise' ? selectedPlan : null
  );
  const [useTrial, setUseTrial] = useState(false);
  const [consent, setConsent] = useState(false);
  const [busyPlan, setBusyPlan] = useState<string | null>(null);
  const [checkoutError, setCheckoutError] = useState('');
  const [checkoutNotice, setCheckoutNotice] = useState('');
  const [loadedSub, setLoadedSub] = useState<SubscriptionState | null>(subscriptionState);
  const requestIdRef = useRef<string>(crypto.randomUUID());

  const sub = subscriptionState ?? loadedSub;
  const hasManageableContract = Boolean(
    sub?.contract && !['expired'].includes((sub.contract.status || '').toLowerCase())
  );

  async function ensureSubscriptionState(): Promise<SubscriptionState | null> {
    if (sub) return sub;
    try {
      const fresh = await request<SubscriptionState>('/billing/subscription');
      setLoadedSub(fresh);
      return fresh;
    } catch (e) {
      setCheckoutError(
        e instanceof Error ? e.message : 'Unable to verify current subscription state.'
      );
      return null;
    }
  }

  async function handleChoosePlan(planCode: PlanCode) {
    if (planCode === 'enterprise' || busyPlan) return;
    setCheckoutError('');
    setCheckoutNotice('');
    setBusyPlan(planCode);

    try {
      const currentSub = await ensureSubscriptionState();
      if (!currentSub) return;

      if (!currentSub.can_manage) {
        setCheckoutError('Only the workspace owner can start checkout or change plans.');
        return;
      }

      const existingStatus = (currentSub.contract?.status || '').toLowerCase();
      const hasExistingContract = Boolean(
        currentSub.contract && existingStatus !== 'expired'
      );

      // Existing active or canceled-with-remaining-access subscription: route directly to Creem Billing Portal
      if (hasExistingContract) {
        const portal = await request<{ url?: string }>('/billing/subscription/portal', {
          method: 'POST',
        });
        if (portal.url) {
          window.location.assign(portal.url);
          return;
        }
        setCheckoutError(
          'Your existing Creem subscription is active. Open the Creem Billing Portal from Billing Overview to switch plans without creating a duplicate subscription.'
        );
        return;
      }

      // Fresh or expired workspace: open compact direct Creem Checkout confirmation for this exact plan
      requestIdRef.current = crypto.randomUUID();
      setActiveCheckoutPlan(planCode);
      setUseTrial(Boolean(currentSub.trial_eligible && planCode === 'starter'));
      setConsent(false);
    } catch (e) {
      setCheckoutError(
        e instanceof Error ? e.message : 'Could not initiate Creem checkout right now.'
      );
    } finally {
      setBusyPlan(null);
    }
  }

  async function launchCreemCheckout() {
    if (!activeCheckoutPlan || activeCheckoutPlan === 'enterprise' || busyPlan || !consent) return;
    setCheckoutError('');
    setCheckoutNotice('');
    setBusyPlan(activeCheckoutPlan);

    try {
      const currentSub = await ensureSubscriptionState();
      if (!currentSub) return;
      const variant = useTrial && currentSub.trial_eligible ? 'trial' : 'paid';
      const blockers =
        (variant === 'trial' ? currentSub.trial_blockers : currentSub.paid_blockers) ||
        currentSub.blockers ||
        [];
      if (blockers.length > 0) {
        setCheckoutError(blockers[0]);
        return;
      }

      const res = await request<{ checkout_url: string | null; status: string }>(
        '/billing/subscription/checkout',
        {
          method: 'POST',
          body: JSON.stringify({
            plan_code: activeCheckoutPlan,
            variant,
            request_id: requestIdRef.current,
            terms_version: currentSub.terms_version,
            accepted_terms: true,
            accepted_recurring: true,
            ...(currentSub.customer_name ? { customer_name: currentSub.customer_name } : {}),
          }),
        }
      );

      if (res.checkout_url) {
        setCheckoutNotice('Redirecting to Creem secure checkout…');
        window.location.assign(res.checkout_url);
      } else {
        setCheckoutNotice(
          'Checkout session is awaiting provider reconciliation. No duplicate charge will be created.'
        );
      }
    } catch (e) {
      setCheckoutError(
        e instanceof Error
          ? e.message
          : 'Could not start Creem checkout. Refresh billing status before retrying.'
      );
    } finally {
      setBusyPlan(null);
    }
  }

  const checkoutPlanObj = activeCheckoutPlan
    ? data.catalog.plans.find((p) => p.code === activeCheckoutPlan) || null
    : null;

  return (
    <div className="space-y-5">
      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold tracking-tight text-foreground">
              Compare Plans
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Monthly plans in tax-inclusive USD · Billed via Creem
            </p>
          </div>
        </div>

        {selectedPlan && (
          <p
            role="status"
            className="rounded-xl border border-primary/25 bg-primary/5 px-4 py-2.5 text-xs text-foreground"
          >
            Selected plan:{' '}
            <strong>{data.catalog.plans.find((p) => p.code === selectedPlan)?.name}</strong>. Your
            selection is saved; it does not create a subscription or authorize payment until you confirm checkout.
          </p>
        )}

        {checkoutNotice && (
          <div
            role="status"
            className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-2.5 text-xs font-medium text-emerald-700 dark:text-emerald-300"
          >
            {checkoutNotice}
          </div>
        )}

        {checkoutError && (
          <div
            role="alert"
            className="rounded-xl border border-destructive/25 bg-destructive/5 px-4 py-3 text-xs text-destructive flex items-start gap-2"
          >
            <AlertCircle size={15} className="shrink-0 mt-0.5" aria-hidden="true" />
            <span>{checkoutError}</span>
          </div>
        )}

        <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
          {data.catalog.plans.map((plan) => {
            const isSelected = selectedPlan === plan.code || activeCheckoutPlan === plan.code;
            const isCurrent = currentPlanCode?.toLowerCase() === plan.code.toLowerCase();
            const isEnterprise = plan.code === 'enterprise';
            const isBusy = busyPlan === plan.code;
            const highlights = planHighlights(plan);

            return (
              <article
                key={plan.code}
                className={
                  'flex flex-col justify-between rounded-xl border bg-card p-4 transition-colors ' +
                  (isCurrent
                    ? 'border-primary ring-1 ring-primary/20'
                    : isSelected
                      ? 'commercial-selected border-primary/70'
                      : 'border-border hover:border-primary/40')
                }
              >
                <div className="space-y-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="text-sm font-semibold text-foreground">{plan.name}</h3>
                    {isCurrent && (
                      <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
                        {currentIsTrial ? 'Current Trial' : 'Current Plan'}
                      </span>
                    )}
                  </div>

                  <div className="flex items-baseline gap-1">
                    <p className="commercial-price text-2xl font-bold tracking-tight text-foreground">
                      {plan.monthly_minor === null
                        ? 'Custom'
                        : formatMoney(plan.monthly_minor, data.catalog.list_currency)}
                    </p>
                    {plan.monthly_minor !== null && (
                      <span className="text-xs text-muted-foreground">/mo</span>
                    )}
                  </div>

                  <p className="text-[11px] text-muted-foreground leading-snug line-clamp-2 min-h-[2rem]">
                    {plan.audience}
                  </p>

                  <ul className="space-y-1.5 border-t border-border/70 pt-3 text-xs text-foreground/90">
                    {highlights.map((item) => (
                      <li key={item} className="flex items-start gap-2">
                        <Check size={13} className="text-primary shrink-0 mt-0.5" aria-hidden="true" />
                        <span className="leading-snug">{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="pt-4">
                  {isEnterprise ? (
                    <a
                      className="inline-flex h-8 w-full items-center justify-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-semibold text-foreground hover:border-primary/50 transition-colors"
                      href="mailto:contact@planebyte.com?subject=Enterprise%20subscription"
                    >
                      <span>Contact sales</span>
                      <ArrowUpRight size={13} aria-hidden="true" />
                    </a>
                  ) : (
                    <button
                      type="button"
                      disabled={busyPlan !== null}
                      aria-busy={isBusy}
                      onClick={() => void handleChoosePlan(plan.code)}
                      className={
                        'inline-flex h-8 w-full items-center justify-center gap-1.5 rounded-lg px-3 text-xs font-semibold transition-colors cursor-pointer disabled:opacity-60 ' +
                        (isCurrent && !currentIsTrial
                          ? 'border border-border bg-muted/40 text-foreground hover:bg-muted'
                          : 'bg-primary text-primary-foreground hover:opacity-95')
                      }
                    >
                      {isBusy ? (
                        <>
                          <Loader2 size={13} className="animate-spin" aria-hidden="true" />
                          <span>
                            {hasManageableContract ? 'Opening Portal…' : 'Preparing…'}
                          </span>
                        </>
                      ) : (
                        <>
                          <span>
                            {isCurrent && !currentIsTrial
                              ? `Manage ${plan.name}`
                              : hasManageableContract
                                ? `Switch to ${plan.name}`
                                : `Choose ${plan.name}`}
                          </span>
                          <ArrowUpRight size={13} aria-hidden="true" />
                        </>
                      )}
                    </button>
                  )}
                </div>
              </article>
            );
          })}
        </div>

        {/* Direct In-Place Creem Checkout Confirmation Panel (No /billing/subscription detour!) */}
        {checkoutPlanObj && !hasManageableContract && (
          <section
            aria-label={`Direct checkout for ${checkoutPlanObj.name}`}
            className="rounded-2xl border border-primary/35 bg-card p-5 shadow-sm space-y-4"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="space-y-1">
                <p className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-primary">
                  <ShieldCheck size={13} aria-hidden="true" /> Direct Creem Checkout
                </p>
                <h3 className="text-base font-semibold text-foreground">
                  Complete {checkoutPlanObj.name} checkout (
                  {formatMoney(checkoutPlanObj.monthly_minor || 0, data.catalog.list_currency)}/mo)
                </h3>
                <p className="text-xs text-muted-foreground">
                  Tax-inclusive USD total. You will be redirected directly to Creem&apos;s hosted checkout without intermediate pages.
                </p>
              </div>
              <button
                type="button"
                aria-label="Close checkout confirmation"
                onClick={() => setActiveCheckoutPlan(null)}
                className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            {sub?.trial_eligible && (
              <label className="flex items-center gap-2.5 rounded-xl border border-border bg-muted/20 px-3.5 py-2.5 text-xs cursor-pointer">
                <input
                  type="checkbox"
                  checked={useTrial}
                  onChange={(e) => {
                    setUseTrial(e.target.checked);
                    requestIdRef.current = crypto.randomUUID();
                  }}
                  className="accent-primary"
                />
                <span className="inline-flex items-center gap-1.5 text-foreground font-medium">
                  <Sparkles size={13} className="text-primary" aria-hidden="true" />
                  Start with a 3-day free trial ($0 today, card required, converts to{' '}
                  {checkoutPlanObj.name} after 72h unless canceled)
                </span>
              </label>
            )}

            <label className="flex items-start gap-2.5 rounded-xl border border-border/80 bg-muted/15 px-3.5 py-3 text-xs leading-relaxed cursor-pointer">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                className="accent-primary mt-0.5 shrink-0"
              />
              <span className="text-foreground">
                I choose <strong>{checkoutPlanObj.name}</strong> at{' '}
                <strong>
                  {formatMoney(checkoutPlanObj.monthly_minor || 0, data.catalog.list_currency)}{' '}
                  USD/month (tax-inclusive)
                </strong>{' '}
                with automatic monthly renewal until canceled, and accept the{' '}
                <Link href="/terms" className="text-primary underline">
                  Terms
                </Link>
                ,{' '}
                <Link href="/refund" className="text-primary underline">
                  Refund Policy
                </Link>
                , and{' '}
                <Link href="/cancellation" className="text-primary underline">
                  Cancellation Terms
                </Link>
                .
              </span>
            </label>

            <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  disabled={!consent || busyPlan !== null}
                  onClick={() => void launchCreemCheckout()}
                  className="gap-1.5"
                >
                  {busyPlan === checkoutPlanObj.code ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      Redirecting to Creem…
                    </>
                  ) : (
                    <>
                      <CreditCard size={14} />
                      Proceed to Creem Checkout
                    </>
                  )}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={busyPlan !== null}
                  onClick={() => setActiveCheckoutPlan(null)}
                >
                  Cancel
                </Button>
              </div>
              <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                <Lock size={11} aria-hidden="true" /> Secured by Creem · Merchant of Record
              </span>
            </div>
          </section>
        )}
      </section>

      {/* Collapsible Feature Comparison */}
      <section className="rounded-xl border border-border bg-card overflow-hidden">
        <button
          type="button"
          aria-expanded={showComparison}
          onClick={() => setShowComparison((prev) => !prev)}
          className="flex w-full items-center justify-between gap-4 px-4 py-3.5 text-left hover:bg-muted/30 transition-colors cursor-pointer"
        >
          <div>
            <span className="text-sm font-semibold text-foreground">Compare All Features</span>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Full monthly limits, monitoring, reporting, and API allowances across plans.
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
                    className="sticky left-0 z-10 bg-muted/90 backdrop-blur px-4 py-2.5 font-semibold text-foreground min-w-[190px]"
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
                          'px-3.5 py-2.5 font-semibold whitespace-nowrap ' +
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
                    className="sticky left-0 bg-card px-4 py-2.5 font-medium text-foreground"
                  >
                    Monthly price (USD, tax-inclusive)
                  </th>
                  {data.catalog.plans.map((p) => (
                    <td key={p.code} className="px-3.5 py-2.5 font-semibold text-foreground">
                      {p.monthly_minor === null ? 'Custom' : formatMoney(p.monthly_minor, 'USD')}
                    </td>
                  ))}
                </tr>

                {data.catalog.limit_definitions.map((item) => (
                  <tr key={item.key}>
                    <th
                      scope="row"
                      className="sticky left-0 bg-card px-4 py-2.5 font-medium text-foreground align-top"
                    >
                      <div>{item.label}</div>
                      <div className="font-normal text-[11px] text-muted-foreground mt-0.5 max-w-xs">
                        {item.description}
                      </div>
                    </th>
                    {data.catalog.plans.map((p) => (
                      <td key={p.code} className="px-3.5 py-2.5 tabular-nums text-foreground">
                        {p.limits ? formatCount(p.limits[item.key]) : 'By agreement'}
                      </td>
                    ))}
                  </tr>
                ))}

                <tr>
                  <th
                    scope="row"
                    className="sticky left-0 bg-card px-4 py-2.5 font-medium text-foreground"
                  >
                    Scheduled monitoring frequency
                  </th>
                  {data.catalog.plans.map((p) => (
                    <td key={p.code} className="px-3.5 py-2.5 text-muted-foreground">
                      {p.limits ? 'Daily (minimum interval)' : 'By agreement'}
                    </td>
                  ))}
                </tr>

                {data.catalog.capabilities.map((cap) => (
                  <tr key={cap.id}>
                    <th
                      scope="row"
                      className="sticky left-0 bg-card px-4 py-2.5 font-medium text-foreground align-top"
                    >
                      <div>{cap.name}</div>
                      <div className="font-normal text-[11px] text-muted-foreground mt-0.5 max-w-xs">
                        {cap.description}
                      </div>
                    </th>
                    {data.catalog.plans.map((p) => (
                      <td key={p.code} className="px-3.5 py-2.5 text-muted-foreground">
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

      <footer className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/70 bg-muted/20 px-4 py-3 text-xs text-muted-foreground">
        <span>
          Prices are tax-inclusive USD. Automatic renewal terms are confirmed before Creem authorization.
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
