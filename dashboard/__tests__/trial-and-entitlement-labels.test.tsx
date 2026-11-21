import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { readFileSync } from 'node:fs';
import { SubscriptionPayment, type SubscriptionState } from '@/components/workspaces/subscription-payment';
import { UsageOverview, type UsageData } from '@/components/workspaces/usage';
import { OnboardingCompletion } from '@/components/workspaces/onboarding/OnboardingCompletion';
import { request } from '@/lib/intelligence';

vi.mock('@/lib/intelligence', () => ({ request: vi.fn() }));
const mockedRequest = vi.mocked(request);

const usageState = vi.hoisted(() => ({ data: undefined as UsageData | undefined }));
vi.mock('@/components/workspaces/use-workspace', () => ({
  useWorkspace: () => ({ data: { active_organization_id: 'ws-test' } })
}));
vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual<typeof import('@tanstack/react-query')>('@tanstack/react-query');
  return {
    ...actual,
    useQuery: (opts: { queryKey?: unknown[]; queryFn?: unknown }) => {
      if (Array.isArray(opts.queryKey) && opts.queryKey[0] === 'workspace-usage') {
        return { data: usageState.data, isPending: false, error: null, refetch: vi.fn() };
      }
      return actual.useQuery(opts as Parameters<typeof actual.useQuery>[0]);
    }
  };
});

const catalog = JSON.parse(readFileSync('../app/billing/commercial_catalog.json', 'utf8'));

function makeUsage(overrides: Partial<UsageData> = {}): UsageData {
  return {
    access: {
      kind: 'Starter Trial',
      is_trial: true,
      intent_radar: true,
      growth_intelligence: true,
      commercial_subscription: false
    },
    subscription: {
      status: 'ACTIVE',
      provider_status: 'canceled',
      mode: 'live',
      plan_code: 'starter',
      is_trial: true,
      entitlement_label: 'Starter Trial',
      period_start: 1794974997,
      period_end: 1795234197,
      trial_start: 1794974997,
      trial_end: 1795234197,
      cancel_confirmed_at: '2026-11-18T04:39:13.128290+00:00'
    },
    commercial: { catalog, provider: 'creem', checkout_enabled: true, blockers: [], historical_payments: [] },
    usage: [
      {
        dimension: 'plan_searches',
        label: 'Monthly searches',
        used: 5,
        reserved: 0,
        limit: 5,
        remaining: 0,
        basis: '3-day card trial; includes reserved capacity',
        resets_at: '2026-11-21T04:09:57+00:00',
        near_limit: true
      }
    ],
    provider_usage: {
      requests: 3,
      input_tokens_reported: 3000,
      output_tokens_reported: 1331,
      estimated_cost_usd: null,
      unreported_requests: 0
    },
    source_requests: [],
    team_seats: 1,
    sandbox_tools_available: false,
    support_url: 'mailto:contact@planebyte.com',
    unmetered: [],
    ...overrides
  };
}

function mountSubscription(value: SubscriptionState) {
  mockedRequest.mockResolvedValue(value);
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })}>
      <SubscriptionPayment />
    </QueryClientProvider>
  );
}

beforeEach(() => vi.resetAllMocks());
afterEach(cleanup);

it('SubscriptionPayment clearly labels canceled Starter Trial separately from Paid Starter', async () => {
  mountSubscription({
    enabled: true,
    required: true,
    active: true,
    provider: 'creem',
    can_manage: true,
    plans: catalog.plans,
    contract: {
      id: 'c-1',
      plan_code: 'starter',
      status: 'canceled',
      provider: 'creem',
      environment: 'production',
      period_start: 1794974997,
      period_end: 1795234197,
      trial_start: 1794974997,
      trial_end: 1795234197,
      next_charge_at: null,
      cancel_at: 1795234197,
      cancel_confirmed_at: '2026-11-18T04:39:13.128290+00:00',
      recurring_authorized: 1,
      is_trial: true,
      entitlement_label: 'Starter Trial'
    }
  });

  expect((await screen.findAllByText('Starter Trial')).length).toBeGreaterThanOrEqual(1);
  expect(screen.getByText(/3-Day Trial/)).toBeVisible();
  expect(screen.getByText('Renewal canceled')).toBeVisible();
  expect(screen.getByText(/Access through/)).toBeVisible();
  expect(screen.queryByText('Paid Plan')).not.toBeInTheDocument();
});

it('SubscriptionPayment clearly labels Paid Starter as a Paid Plan', async () => {
  mountSubscription({
    enabled: true,
    required: true,
    active: true,
    provider: 'creem',
    can_manage: true,
    plans: catalog.plans,
    contract: {
      id: 'c-2',
      plan_code: 'starter',
      status: 'active',
      provider: 'creem',
      environment: 'production',
      period_start: 1794974997,
      period_end: 1797653397,
      trial_start: null,
      trial_end: null,
      next_charge_at: 1797653397,
      cancel_at: null,
      cancel_confirmed_at: null,
      recurring_authorized: 1,
      is_trial: false,
      entitlement_label: 'Paid Starter'
    }
  });

  expect((await screen.findAllByText('Paid Starter')).length).toBeGreaterThanOrEqual(1);
  expect(screen.getByText(/Paid Plan/)).toBeVisible();
  expect(screen.queryByText('3-Day Trial')).not.toBeInTheDocument();
});

it('UsageOverview shows Starter Trial allowances without internal testing banner for regular trial customers', () => {
  usageState.data = makeUsage();
  render(<UsageOverview />);
  expect(screen.getByText('Starter Trial')).toBeVisible();
  expect(screen.getByText('Starter Trial (3-day card trial)')).toBeVisible();
  expect(screen.getByRole('heading', { name: 'Starter Trial allowances' })).toBeVisible();
  expect(screen.getByText(/Automatic renewal is canceled/)).toBeVisible();
  expect(screen.queryByText(/Temporary internal testing allowance/i)).not.toBeInTheDocument();
});

it('UsageOverview shows temporary internal testing banner ONLY when explicitly active', () => {
  usageState.data = makeUsage({
    internal_testing: {
      active: true,
      expires_at: 1795161600,
      base_entitlement: 'Starter Trial',
      base_usage: { searches: 5, ai_calls: 3 }
    }
  });
  render(<UsageOverview />);
  expect(screen.getByRole('heading', { name: 'Temporary internal testing allowance active' })).toBeVisible();
  expect(screen.getByRole('heading', { name: 'Temporary internal testing allowances' })).toBeVisible();
});

it('OnboardingCompletion clearly distinguishes Starter Trial vs Paid Starter', () => {
  const { rerender } = render(
    <OnboardingCompletion
      hasVerifiedAccess
      companyName="PlaneByte"
      primaryICPName="SaaS Founders"
      researchTermCount={6}
      paymentActive
      contract={{
        plan_code: 'starter',
        status: 'canceled',
        provider: 'creem',
        period_start: 1794974997,
        period_end: 1795234197,
        trial_start: 1794974997,
        trial_end: 1795234197,
        cancel_confirmed_at: '2026-11-18T04:39:13Z',
        is_trial: true,
        entitlement_label: 'Starter Trial'
      }}
    />
  );
  expect(screen.getByText('Starter Trial')).toBeVisible();
  expect(screen.getByText(/Renewal canceled · ends/)).toBeVisible();

  rerender(
    <OnboardingCompletion
      hasVerifiedAccess
      companyName="Acme"
      primaryICPName="Enterprise Ops"
      researchTermCount={6}
      paymentActive
      contract={{
        plan_code: 'starter',
        status: 'active',
        provider: 'creem',
        period_start: 1794974997,
        period_end: 1797653397,
        next_charge_at: 1797653397,
        is_trial: false,
        entitlement_label: 'Paid Starter'
      }}
    />
  );
  expect(screen.getByText('Paid Starter')).toBeVisible();
  expect(screen.getByText(/Renews/)).toBeVisible();
});
