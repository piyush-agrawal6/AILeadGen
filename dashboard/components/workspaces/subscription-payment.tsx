'use client';
import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { CreditCard, ShieldCheck, ArrowRight, RefreshCw, Check, Sparkles, Lock, User } from 'lucide-react';
import { request } from '@/lib/intelligence';
import { Button } from '@/components/ui/button';

type Plan = { code: string; name: string; monthly_minor: number | null; audience: string; limits: Record<string, number> | null };
type Contract = {
  id: string;
  plan_code: string;
  status: string;
  provider: string;
  environment: string;
  period_start: number;
  period_end: number;
  trial_start: number | null;
  trial_end: number | null;
  next_charge_at: number | null;
  cancel_at: number | null;
  cancel_confirmed_at: string | null;
  recurring_authorized: number;
  is_trial?: boolean;
  entitlement_label?: string | null;
};

function isTrialContract(contract?: Contract | null): boolean {
  if (!contract) return false;
  if (typeof contract.is_trial === 'boolean') return contract.is_trial;
  if (contract.trial_start != null && contract.period_start === contract.trial_start) return true;
  return contract.status === 'trialing';
}

function formatEntitlementLabel(contract?: Contract | null): string {
  if (!contract) return 'Subscription';
  if (contract.entitlement_label) return contract.entitlement_label;
  const code = (contract.plan_code || '').trim().toLowerCase();
  const tier = code ? code.charAt(0).toUpperCase() + code.slice(1) : 'Subscription';
  return isTrialContract(contract) ? `${tier} Trial` : `Paid ${tier}`;
}

export type SubscriptionState = {
  enabled: boolean;
  required: boolean;
  active: boolean;
  provider?: string | null;
  country?: string | null;
  country_verified?: boolean;
  account_email?: string | null;
  customer_name?: string | null;
  terms_version?: string;
  trial_eligible?: boolean;
  trial_seconds?: number;
  plans: Plan[];
  can_manage?: boolean;
  contract?: Contract | null;
  paid_blockers?: string[];
  trial_blockers?: string[];
  blockers?: string[];
  checkouts?: { id: string; plan_code: string; variant: string; status: string; environment: string }[];
  history?: { provider: string; environment: string; payment_id: string; amount_minor: number; currency: string; status: string; recorded_at: string; receipt_url: string | null }[];
  renewal_disclosure?: string;
  tax_disclosure?: string;
};

const money = (amount: number, currency = 'USD') =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: amount % 100 === 0 ? 0 : 2 }).format(amount / 100);

const formatDate = (value: number | null | undefined) =>
  value ? new Date(value * 1000).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : 'Confirmed at activation';

export function SubscriptionPayment({ onActivated, embedded = false }: { onActivated?: () => void; embedded?: boolean }) {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ['workspace-subscription'],
    queryFn: ({ signal }) => request<SubscriptionState>('/billing/subscription', { signal }),
    retry: false,
    refetchOnWindowFocus: false
  });

  const [choice, setChoice] = useState('trial');
  const [conversion, setConversion] = useState('starter');
  const [consent, setConsent] = useState(false);
  const [customerName, setCustomerName] = useState('');
  const [nameTouched, setNameTouched] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const returned = useRef(false);
  const [reviewTime] = useState(() => Math.floor(Date.now() / 1000));

  const data = query.data;
  const planCode = choice === 'trial' ? conversion : choice;
  const plan = data?.plans.find(p => p.code === planCode);
  const trial = choice === 'trial';
  const blockers = (trial ? data?.trial_blockers : data?.paid_blockers) || data?.blockers || [];

  useEffect(() => {
    if (data?.customer_name && !nameTouched && !customerName) {
      setCustomerName(data.customer_name);
    }
  }, [data?.customer_name, nameTouched, customerName]);

  async function refresh() {
    setPending(true);
    setError('');
    try {
      const next = await request<SubscriptionState>('/billing/subscription/refresh', { method: 'POST' });
      client.setQueryData(['workspace-subscription'], next);
      if (next.active) {
        await client.invalidateQueries({ queryKey: ['account-workspaces'] });
        onActivated?.();
      } else {
        setNotice('Provider verification is still pending. Your saved onboarding is retained.');
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPending(false);
    }
  }

  useEffect(() => {
    const selected = new URLSearchParams(window.location.search).get('plan');
    if (selected && ['starter', 'growth', 'scale'].includes(selected)) {
      setChoice(selected);
      setConsent(false);
    }
  }, []);

  useEffect(() => {
    if (query.data?.enabled && !returned.current && new URLSearchParams(window.location.search).get('payment') === 'returned') {
      returned.current = true;
      window.history.replaceState({}, '', window.location.pathname);
      void refresh();
    }
  }, [query.data?.enabled]);

  async function checkout() {
    if (!data || !plan || !consent) return;
    setPending(true);
    setError('');
    try {
      const trimmedName = customerName.trim();
      const payload: Record<string, unknown> = {
        plan_code: planCode,
        variant: trial ? 'trial' : 'paid',
        request_id: crypto.randomUUID(),
        terms_version: data.terms_version,
        accepted_terms: true,
        accepted_recurring: true
      };
      if (trimmedName.length >= 2) {
        payload.customer_name = trimmedName;
      }
      const value = await request<{ checkout_url: string | null; status: string }>('/billing/subscription/checkout', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      if (value.checkout_url) {
        window.location.assign(value.checkout_url);
      } else {
        setNotice('This checkout requires provider reconciliation. No access has been granted.');
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPending(false);
    }
  }

  async function action(kind: 'cancel' | 'portal') {
    setPending(true);
    setError('');
    try {
      const value = await request<{ url?: string; status?: string }>('/billing/subscription/' + kind, {
        method: 'POST',
        body: kind === 'cancel' ? JSON.stringify({ request_id: crypto.randomUUID() }) : undefined
      });
      if (value.url) {
        window.location.assign(value.url);
      } else {
        setNotice(
          value.status === 'CONFIRMED'
            ? 'Automatic renewal is canceled with the provider. Your confirmed period remains available until its scheduled end.'
            : 'The request is awaiting provider confirmation.'
        );
        await query.refetch();
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPending(false);
    }
  }

  if (query.isPending) {
    return (
      <div className="py-10 text-center text-sm text-muted-foreground" role="status">
        Loading your billing options…
      </div>
    );
  }
  if (query.isError || !data) {
    return (
      <section className="rounded-2xl border border-border bg-card p-6 text-center space-y-3" role="alert">
        <h2 className="text-lg font-semibold">Billing could not be loaded</h2>
        <p className="text-sm text-muted-foreground">Your saved onboarding is retained.</p>
        <Button onClick={() => void query.refetch()}>Retry billing</Button>
      </section>
    );
  }

  const paidPlans = data.plans.filter(p => p.code !== 'enterprise');

  return (
    <section className="subscription-payment space-y-6" aria-label="Choose Your Plan & Payment">
      <header className="space-y-1.5">
        <div className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-primary">
          <ShieldCheck size={14} />
          <span>{embedded ? 'Step 5 · Plan & Activation' : 'Billing & Subscription'}</span>
        </div>
        <h2 className="text-2xl font-semibold tracking-tight text-foreground">Choose Your Plan & Payment</h2>
        <p className="text-sm text-muted-foreground max-w-2xl">
          Start with a 3-day free trial ($0 today, card required) or subscribe directly. All USD prices are tax-inclusive.
        </p>
      </header>

      {data.active && (() => {
        const contractIsTrial = isTrialContract(data.contract);
        const label = formatEntitlementLabel(data.contract);
        const statusSummary = data.contract?.cancel_confirmed_at
          ? contractIsTrial
            ? 'Renewal canceled — trial access continues until expiration'
            : 'Renewal canceled — paid access continues until period end'
          : contractIsTrial
            ? '3-day card trial active'
            : 'Paid subscription active';
        return (
        <div className="rounded-2xl border border-primary/30 bg-primary/5 p-5 flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 font-semibold text-foreground">
                <Check size={18} className="text-primary" />
                {label}
              </span>
              <span
                className={
                  'rounded-full px-2.5 py-0.5 text-[11px] font-semibold border ' +
                  (contractIsTrial
                    ? 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30'
                    : 'bg-primary/10 text-primary border-primary/25')
                }
              >
                {contractIsTrial ? '3-Day Trial' : 'Paid Plan'}
              </span>
              {data.contract?.cancel_confirmed_at && (
                <span className="rounded-full bg-muted px-2.5 py-0.5 text-[11px] font-medium text-muted-foreground border border-border">
                  Renewal canceled
                </span>
              )}
            </div>
            <p className="text-sm text-muted-foreground">
              {statusSummary} · via <span className="capitalize">{data.contract?.provider}</span>
            </p>
            {data.contract && (
              <p className="text-xs text-muted-foreground">
                {contractIsTrial ? 'Trial started ' : 'Period started '}
                {formatDate(data.contract.trial_start ?? data.contract.period_start)} ·{' '}
                {contractIsTrial ? 'Trial expires ' : 'Period ends '}
                {formatDate(data.contract.trial_end ?? data.contract.period_end)}.{' '}
                {data.contract.cancel_confirmed_at
                  ? 'Automatic renewal canceled — no future charge will be made.'
                  : 'Next charge: ' + formatDate(data.contract.next_charge_at)}
              </p>
            )}
            {contractIsTrial && (
              <p className="text-xs text-muted-foreground">
                Starter Trial includes 5 searches, 3 AI operations, 150,000 AI tokens, and 1 manual monitor. Paid Starter unlocks 100 monthly searches, 20 AI operations, 2 monitors, scheduled checks, reports, and API access.
              </p>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2.5">
            {embedded && onActivated ? (
              <Button size="lg" className="ai-btn-primary" onClick={() => onActivated()}>
                Complete setup <ArrowRight size={15} className="ml-1.5" />
              </Button>
            ) : null}
            <Link
              className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium text-foreground hover:border-primary/50"
              href="/intent-radar"
            >
              Open dashboard <ArrowRight size={15} />
            </Link>
          </div>
        </div>
        );
      })()}

      {!data.active && (
        <>
          {/* 4 Compact Plan Cards */}
          <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-4" role="group" aria-label="Plan options">
            {[
              {
                code: 'trial',
                name: '3-Day Free Trial',
                monthly_minor: 0,
                audience: 'Card required · $0 today. Converts after 72 hours.',
                limits: null
              },
              ...paidPlans
            ].map(item => {
              const isSelected = choice === item.code;
              const isPopular = item.code === 'growth';
              const isTrialCard = item.code === 'trial';
              return (
                <button
                  key={item.code}
                  type="button"
                  aria-pressed={isSelected}
                  onClick={() => {
                    setChoice(item.code);
                    setConsent(false);
                  }}
                  className={
                    'relative flex flex-col justify-between rounded-2xl border p-4.5 text-left transition-all cursor-pointer ' +
                    (isSelected
                      ? 'border-primary bg-primary/[0.04] ring-2 ring-primary/25 shadow-sm'
                      : 'border-border bg-card hover:border-primary/45')
                  }
                >
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-sm text-foreground">{item.name}</span>
                      {isPopular && (
                        <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
                          Popular
                        </span>
                      )}
                      {isTrialCard && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-violet-500/10 px-2 py-0.5 text-[10px] font-semibold text-violet-600 dark:text-violet-300">
                          <Sparkles size={10} /> Recommended
                        </span>
                      )}
                    </div>

                    <div className="mt-3 flex items-baseline gap-1">
                      <span className="text-2xl font-bold tracking-tight text-foreground">
                        {isTrialCard ? '$0' : money(item.monthly_minor || 0)}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {isTrialCard ? 'today' : '/ mo'}
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      {isTrialCard ? 'Card required · 72-hour trial' : 'Tax-inclusive USD total'}
                    </p>

                    <p className="mt-2.5 text-xs text-muted-foreground leading-relaxed">{item.audience}</p>
                  </div>

                  {isTrialCard ? (
                    <ul className="mt-3.5 pt-3 border-t border-border/60 space-y-1.5 text-xs text-muted-foreground">
                      <li className="flex items-center gap-1.5"><Check size={12} className="text-primary flex-shrink-0" /> 5 live searches</li>
                      <li className="flex items-center gap-1.5"><Check size={12} className="text-primary flex-shrink-0" /> 3 AI operations</li>
                      <li className="flex items-center gap-1.5"><Check size={12} className="text-primary flex-shrink-0" /> 1 manual monitor · 1 user</li>
                      <li className="flex items-center gap-1.5"><Check size={12} className="text-primary flex-shrink-0" /> Cancel anytime before 72h</li>
                    </ul>
                  ) : item.limits ? (
                    <ul className="mt-3.5 pt-3 border-t border-border/60 space-y-1.5 text-xs text-muted-foreground">
                      <li className="flex items-center gap-1.5"><Check size={12} className="text-primary flex-shrink-0" /> {item.limits.searches} searches / month</li>
                      <li className="flex items-center gap-1.5"><Check size={12} className="text-primary flex-shrink-0" /> {item.limits.ai_calls} AI operations</li>
                      <li className="flex items-center gap-1.5"><Check size={12} className="text-primary flex-shrink-0" /> {item.limits.monitors} monitors · {item.limits.team_members} user{item.limits.team_members === 1 ? '' : 's'}</li>
                      <li className="flex items-center gap-1.5"><Check size={12} className="text-primary flex-shrink-0" /> {item.limits.reports} reports / month</li>
                    </ul>
                  ) : null}
                </button>
              );
            })}
          </div>

          {/* Trial Plan Conversion Selector */}
          {trial && (
            <div className="rounded-xl border border-border bg-muted/25 px-4 py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <label className="block text-sm font-medium text-foreground" htmlFor="trial-conversion-plan">
                  Choose the plan after your trial
                </label>
                <p className="text-xs text-muted-foreground mt-0.5">
                  You can switch or cancel before the trial ends. Scheduled checks, reports, API & MCP unlock on paid plans.
                </p>
              </div>
              <select
                id="trial-conversion-plan"
                className="ai-select sm:w-64 flex-shrink-0"
                value={conversion}
                onChange={e => {
                  setConversion(e.target.value);
                  setConsent(false);
                }}
              >
                {paidPlans.map(p => (
                  <option key={p.code} value={p.code}>
                    {p.name} — {money(p.monthly_minor || 0)} / month
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Compact Order Summary, Billing Contact & Explicit Consent */}
          <div className="rounded-2xl border border-border bg-card p-5 space-y-4">
            {/* Compact Billing Contact Row */}
            <div className="grid gap-3.5 sm:grid-cols-2 pb-4 border-b border-border/70">
              <div>
                <label htmlFor="billing-customer-name" className="block text-xs font-semibold text-foreground mb-1.5">
                  Full name for billing
                </label>
                <div className="relative">
                  <User size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
                  <input
                    id="billing-customer-name"
                    type="text"
                    value={customerName}
                    maxLength={120}
                    onChange={e => {
                      setNameTouched(true);
                      setCustomerName(e.target.value);
                    }}
                    placeholder="Enter your full name"
                    className="ai-input pl-9 text-sm"
                  />
                </div>
                <p className="text-[11px] text-muted-foreground mt-1">
                  Prefilled on Creem checkout and receipts. Leave blank to enter directly at checkout.
                </p>
              </div>

              <div>
                <span className="block text-xs font-semibold text-foreground mb-1.5">Account billing email</span>
                <div className="flex items-center justify-between rounded-xl border border-border bg-muted/35 px-3.5 py-2.5 text-sm text-foreground">
                  <span className="truncate">{data.account_email || 'Verified workspace owner email'}</span>
                  <span className="inline-flex items-center gap-1 text-[10px] font-medium text-muted-foreground flex-shrink-0 ml-2">
                    <Lock size={11} /> Account bound
                  </span>
                </div>
                <p className="text-[11px] text-muted-foreground mt-1">
                  Bound to your authenticated workspace owner account for security.
                </p>
              </div>
            </div>

            {/* Compact Order Summary Strip */}
            <dl className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
              <div className="rounded-xl bg-muted/30 px-3.5 py-2.5">
                <dt className="text-[11px] text-muted-foreground">Due today</dt>
                <dd className="font-semibold text-foreground mt-0.5">
                  {trial ? '$0.00 · card required' : `${money(plan?.monthly_minor || 0)} USD`}
                </dd>
              </div>
              <div className="rounded-xl bg-muted/30 px-3.5 py-2.5">
                <dt className="text-[11px] text-muted-foreground">{trial ? 'After 72h trial' : 'Monthly renewal'}</dt>
                <dd className="font-semibold text-foreground mt-0.5">
                  {plan?.name} · {money(plan?.monthly_minor || 0)}/mo
                  <span className="block text-[10px] font-normal text-muted-foreground">Tax-inclusive USD total</span>
                </dd>
              </div>
              <div className="rounded-xl bg-muted/30 px-3.5 py-2.5">
                <dt className="text-[11px] text-muted-foreground">First charge</dt>
                <dd className="font-semibold text-foreground mt-0.5 text-xs leading-snug">
                  {trial ? `72h after activation (est. ${formatDate(reviewTime + 259200)})` : 'At checkout confirmation'}
                </dd>
              </div>
            </dl>

            <p className="text-xs text-muted-foreground leading-relaxed">
              Creem is the merchant of record. USD prices include applicable taxes (such as GST/VAT where applicable); Creem displays the exact tax breakdown and renewal date before authorization. Cancel anytime in Settings → Billing &amp; Subscription.
            </p>

            {/* Deliberate Unchecked Consent */}
            <label className="flex items-start gap-3 rounded-xl border border-border/80 bg-muted/20 p-3.5 text-xs leading-relaxed cursor-pointer">
              <input
                type="checkbox"
                checked={consent}
                onChange={e => setConsent(e.target.checked)}
                disabled={!data.terms_version}
                className="ai-checkbox mt-0.5 flex-shrink-0"
              />
              <span className="text-foreground">
                I choose <strong>{plan?.name}</strong> at <strong>{money(plan?.monthly_minor || 0)} USD/month (tax-inclusive)</strong> and agree to automatic monthly renewal until canceled.{' '}
                {trial ? 'A card is required; the first charge occurs after the 72-hour trial unless canceled. ' : ''}
                I accept the{' '}
                <Link href="/terms" className="text-primary underline">subscription terms</Link>,{' '}
                <Link href="/refund" className="text-primary underline">refund policy</Link>,{' '}
                <Link href="/cancellation" className="text-primary underline">cancellation terms</Link>,{' '}
                <Link href="/delivery-policy" className="text-primary underline">digital delivery policy</Link>, and{' '}
                <Link href="/privacy" className="text-primary underline">privacy policy</Link>.
              </span>
            </label>

            {blockers.length > 0 && (
              <div role="status" className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-xs space-y-1.5">
                <h3 className="font-semibold text-foreground">Checkout unavailable right now</h3>
                <ul className="list-disc pl-4 text-muted-foreground space-y-1">
                  {blockers.map(item => <li key={item}>{item}</li>)}
                </ul>
                <p className="text-muted-foreground">Your onboarding is saved. No trial or charge has been initiated.</p>
              </div>
            )}

            <div className="flex flex-wrap items-center gap-3 pt-1">
              <Button
                size="lg"
                disabled={pending || !consent || blockers.length > 0 || !data.can_manage}
                onClick={() => void checkout()}
                className="ai-btn-primary"
              >
                <CreditCard size={16} className="mr-2" />
                {pending
                  ? 'Opening secure checkout…'
                  : 'Continue to secure checkout'}
              </Button>
              <Button variant="outline" size="default" disabled={pending} onClick={() => void refresh()}>
                <RefreshCw size={14} className="mr-1.5" />
                Check payment status
              </Button>
              <a
                className="ml-auto text-xs font-medium text-muted-foreground hover:text-primary underline"
                href="mailto:contact@planebyte.com?subject=Enterprise%20subscription"
              >
                Need Enterprise? Contact sales
              </a>
            </div>
          </div>
        </>
      )}

      {/* Existing Subscription Management Controls */}
      {data.contract && data.can_manage && (
        <div className="rounded-2xl border border-border bg-card p-5 space-y-3">
          <h3 className="font-semibold text-sm text-foreground">Manage your subscription</h3>
          <p className="text-xs text-muted-foreground">
            <span className="font-medium text-foreground">{formatEntitlementLabel(data.contract)}</span> ·{' '}
            <span className="capitalize">{data.contract.provider} · {data.contract.environment} · {data.contract.status}</span>
          </p>
          <p className="text-xs text-muted-foreground">
            {data.contract.cancel_confirmed_at
              ? 'Cancellation confirmed; no future automatic renewal is scheduled.'
              : 'Cancel future automatic billing before the displayed renewal date. Saved data remains available under the retention policy.'}
          </p>
          <div className="flex flex-wrap gap-2.5">
            <Button variant="outline" size="sm" disabled={pending} onClick={() => void action('portal')}>
              Billing portal, payment method &amp; invoices
            </Button>
            <Button variant="outline" size="sm" disabled={pending || !!data.contract.cancel_confirmed_at} onClick={() => void action('cancel')}>
              Cancel automatic renewal
            </Button>
            <Button variant="outline" size="sm" disabled={pending} onClick={() => void refresh()}>
              Refresh provider status
            </Button>
          </div>
        </div>
      )}

      {!!data.history?.length && (
        <div className="overflow-x-auto rounded-2xl border border-border bg-card">
          <table className="w-full text-left text-xs">
            <caption className="p-4 text-left font-semibold text-sm text-foreground">Payment history</caption>
            <thead className="border-t border-border bg-muted/30 text-muted-foreground">
              <tr>
                {['Date', 'Provider', 'Amount', 'Status', 'Receipt'].map(v => (
                  <th className="p-3 font-medium" key={v}>{v}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.history.map(p => (
                <tr className="border-t border-border" key={p.provider + ':' + p.environment + ':' + p.payment_id}>
                  <td className="p-3">{new Date(p.recorded_at).toLocaleDateString()}</td>
                  <td className="p-3 capitalize">{p.provider} · {p.environment}</td>
                  <td className="p-3 font-medium">{money(p.amount_minor, p.currency)}</td>
                  <td className="p-3 capitalize">{p.status}</td>
                  <td className="p-3 text-muted-foreground">Use billing portal</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {notice && <p role="status" className="text-sm text-primary font-medium">{notice}</p>}
      {error && <p role="alert" className="text-sm text-destructive font-medium">{error}</p>}

      <p className="text-[11px] text-muted-foreground flex items-center gap-1.5">
        <Lock size={12} />
        Card details are handled exclusively by Creem’s secure checkout. PlaneByte never stores card numbers or CVVs.
      </p>
    </section>
  );
}
