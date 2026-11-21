'use client';
import React from 'react';
import Link from 'next/link';
import { Check, CheckCircle2, Network, Radio, Search, ShieldCheck } from 'lucide-react';
import { formatUnixDate, type PaymentContract } from './types';

export function OnboardingCompletion({
  hasVerifiedAccess,
  companyName,
  primaryICPName,
  researchTermCount,
  paymentActive,
  contract
}: {
  hasVerifiedAccess: boolean;
  companyName: string;
  primaryICPName: string;
  researchTermCount: number;
  paymentActive: boolean;
  contract?: PaymentContract | null;
}) {
  return (
    <section className="pb-ready-canvas max-w-3xl mx-auto my-8" aria-label="Workspace Ready">
      <div className="pb-ready-hero">
        <div className="pb-ready-emblem" aria-hidden="true">
          <CheckCircle2 size={30} />
        </div>
        <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-foreground">
          {hasVerifiedAccess ? 'Your workspace is ready' : 'Your reviewed context is saved'}
        </h1>
        <p className="text-sm text-muted-foreground max-w-xl mx-auto mt-2 leading-relaxed">
          {hasVerifiedAccess
            ? 'Your business profile and research preferences are saved. Start discovering relevant conversations.'
            : 'Your business profile, ideal customer segments, and research preferences are safely stored. Product features unlock once your subscription is confirmed.'}
        </p>
      </div>

      <div className="p-6 sm:p-8 space-y-6">
        <nav className="flex flex-wrap justify-center gap-3 text-sm" aria-label="Completed setup actions">{hasVerifiedAccess&&<Link className="control" href="/intent-radar/discover/new?from=onboarding">Review first discovery</Link>}<Link className="control" href="/intent-radar">Go to Dashboard</Link><Link className="control" href="/settings?category=billing&tab=overview">Manage Subscription</Link><Link className="control" href="/settings/company">Edit Business Profile</Link></nav>
        <dl className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5">
            <dt className="text-muted-foreground flex items-center gap-1.5">
              <Check size={13} className="text-primary" aria-hidden="true" /> Company
            </dt>
            <dd className="text-sm font-semibold text-foreground mt-1 truncate">{companyName || 'Saved'}</dd>
          </div>

          <Link
            href="/intent-radar/ideal-customers"
            className="block rounded-xl border border-border/80 bg-muted/20 p-3.5 transition-colors hover:border-primary/40"
          >
            <dt className="text-muted-foreground flex items-center gap-1.5">
              <Check size={13} className="text-primary" aria-hidden="true" /> Primary ICP
            </dt>
            <dd className="text-sm font-semibold text-foreground mt-1 truncate">{primaryICPName || 'Configured'}</dd>
          </Link>

          <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5">
            <dt className="text-muted-foreground flex items-center gap-1.5">
              <Check size={13} className="text-primary" aria-hidden="true" /> Research terms
            </dt>
            <dd className="text-sm font-semibold text-foreground mt-1">
              {researchTermCount} term{researchTermCount === 1 ? '' : 's'} saved
            </dd>
          </div>

          <div className="rounded-xl border border-border/80 bg-muted/20 p-3.5">
            <dt className="text-muted-foreground flex items-center gap-1.5">
              <ShieldCheck size={13} className="text-primary" aria-hidden="true" /> Plan status
            </dt>
            {(() => {
              const isTrial = Boolean(
                contract &&
                  (contract.is_trial ??
                    (contract.status === 'trialing' ||
                      (contract.trial_start != null && contract.period_start === contract.trial_start)))
              );
              const tier = contract?.plan_code
                ? contract.plan_code.charAt(0).toUpperCase() + contract.plan_code.slice(1)
                : '';
              const label =
                contract?.entitlement_label ||
                (contract ? (isTrial ? `${tier} Trial` : `Paid ${tier}`) : null);
              return (
                <>
                  <dd className="text-sm font-semibold text-foreground mt-1">
                    {paymentActive && label
                      ? label
                      : hasVerifiedAccess
                        ? 'Active'
                        : 'Saved context'}
                  </dd>
                  {contract && isTrial && (contract.trial_end ?? contract.period_end) && (
                    <span className="block text-[11px] text-muted-foreground mt-0.5">
                      {contract.cancel_confirmed_at ? 'Renewal canceled · ends ' : 'Trial ends '}
                      {formatUnixDate(contract.trial_end ?? contract.period_end)}
                    </span>
                  )}
                  {contract && !isTrial && contract.next_charge_at && !contract.cancel_confirmed_at && (
                    <span className="block text-[11px] text-muted-foreground mt-0.5">
                      Renews {formatUnixDate(contract.next_charge_at)}
                    </span>
                  )}
                  {contract && !isTrial && contract.cancel_confirmed_at && contract.period_end && (
                    <span className="block text-[11px] text-muted-foreground mt-0.5">
                      Renewal canceled · ends {formatUnixDate(contract.period_end)}
                    </span>
                  )}
                </>
              );
            })()}
          </div>
        </dl>

        {hasVerifiedAccess ? (
          <div className="flex flex-wrap items-center justify-center gap-3 pt-1">
            <Link
              href="/intent-radar/discover"
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm hover:opacity-95 transition-opacity"
            >
              <Search size={15} aria-hidden="true" /> Discover conversations
            </Link>
            <Link
              href="/intent-radar/monitors/new"
              className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2.5 text-sm font-medium text-foreground hover:border-primary/50 transition-colors"
            >
              <Radio size={15} className="text-primary" aria-hidden="true" /> Create your first monitor
            </Link>
            <Link
              href="/intent-radar"
              className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2.5 text-sm font-medium text-foreground hover:border-primary/50 transition-colors"
            >
              <Network size={15} className="text-primary" aria-hidden="true" /> Explore your Intelligence Graph
            </Link>
          </div>
        ) : (
          <div className="text-center pt-1">
            <Link href="/settings" className="text-primary underline text-sm font-semibold">
              Open workspace settings →
            </Link>
          </div>
        )}
      </div>
    </section>
  );
}
