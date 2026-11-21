import { it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SubscriptionPayment, type SubscriptionState } from '@/components/workspaces/subscription-payment';
import { request } from '@/lib/intelligence';

vi.mock('@/lib/intelligence', () => ({ request: vi.fn() }));
const mocked = vi.mocked(request);

const data: SubscriptionState = {
  enabled: true,
  required: true,
  active: false,
  provider: null,
  country_verified: false,
  account_email: 'contact@planebyte.com',
  customer_name: null,
  terms_version: 'approved-test-terms',
  trial_eligible: true,
  can_manage: true,
  plans: [
    {
      code: 'starter',
      name: 'Starter',
      monthly_minor: 5900,
      audience: 'Starter audience',
      limits: { searches: 100, ai_calls: 20, ai_tokens: 600000, monitors: 2, team_members: 1, reports: 5 }
    },
    { code: 'growth', name: 'Growth', monthly_minor: 14900, audience: 'Growth audience', limits: null },
    { code: 'scale', name: 'Scale', monthly_minor: 37900, audience: 'Scale audience', limits: null }
  ],
  paid_blockers: ['Merchant acceptance pending'],
  trial_blockers: ['Merchant acceptance pending']
};

function mount(value = data) {
  mocked.mockResolvedValue(value);
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })}>
      <SubscriptionPayment embedded />
    </QueryClientProvider>
  );
}

beforeEach(() => vi.resetAllMocks());

it('shows mandatory card trial, tax-inclusive copy, and explicit conversion without giant review card or skip button', async () => {
  mount();
  expect(await screen.findByRole('heading', { name: 'Choose Your Plan & Payment' })).toBeVisible();
  expect(screen.queryByText('Review before secure checkout')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: /3-Day Free Trial/ })).toHaveAttribute('aria-pressed', 'true');
  expect(screen.getByLabelText('Choose the plan after your trial')).toHaveValue('starter');
  expect(screen.getByLabelText('Full name for billing')).toHaveValue('');
  expect(screen.getByRole('button', { name: 'Continue to secure checkout' })).toBeDisabled();
  expect(screen.queryByRole('link', { name: /dashboard/i })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /skip/i })).not.toBeInTheDocument();
});

it('does not initiate checkout when consent is missing or a path is blocked', async () => {
  mount();
  await screen.findByRole('heading', { name: 'Choose Your Plan & Payment' });
  fireEvent.click(screen.getByRole('checkbox'));
  expect(screen.getByRole('button', { name: 'Continue to secure checkout' })).toBeDisabled();
  expect(mocked.mock.calls.every(([, options]) => !options?.method)).toBe(true);
});

it('selecting a paid plan clears earlier recurring consent and forwards explicit real customer name', async () => {
  mocked.mockImplementation(async (path, options) => {
    if (path === '/billing/subscription') {
      return { ...data, paid_blockers: [], trial_blockers: [], country_verified: true, provider: 'creem' };
    }
    if (path === '/billing/subscription/checkout') {
      const body = JSON.parse(String(options?.body));
      expect(body.customer_name).toBe('Piyush Agrawal');
      expect(body.plan_code).toBe('growth');
      expect(body.variant).toBe('paid');
      return { checkout_url: null, status: 'REVIEW' };
    }
    throw new Error('Unexpected path: ' + path);
  });

  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })}>
      <SubscriptionPayment embedded />
    </QueryClientProvider>
  );

  await screen.findByRole('heading', { name: 'Choose Your Plan & Payment' });
  fireEvent.click(screen.getByRole('checkbox'));
  expect(screen.getByRole('button', { name: 'Continue to secure checkout' })).toBeEnabled();
  fireEvent.click(screen.getByRole('button', { name: /Growth.*149/ }));
  expect(screen.getByRole('checkbox')).not.toBeChecked();
  expect(screen.getByRole('button', { name: 'Continue to secure checkout' })).toBeDisabled();

  fireEvent.change(screen.getByLabelText('Full name for billing'), { target: { value: 'Piyush Agrawal' } });
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(screen.getByRole('button', { name: 'Continue to secure checkout' }));
  expect(await screen.findByText(/requires provider reconciliation/)).toBeVisible();
});

it('keeps provider cancellation and invoice controls visible without product access', async () => {
  mount({
    ...data,
    contract: {
      id: 'local',
      plan_code: 'starter',
      status: 'past_due',
      provider: 'creem',
      environment: 'test',
      period_start: 1,
      period_end: 2,
      trial_start: null,
      trial_end: null,
      next_charge_at: 3,
      cancel_at: null,
      cancel_confirmed_at: null,
      recurring_authorized: 1
    }
  });
  expect(await screen.findByRole('link',{name:'Manage billing'})).toHaveAttribute('href','/settings?category=billing&tab=overview');
  expect(screen.queryByRole('button',{name:'Cancel automatic renewal'})).not.toBeInTheDocument();
  expect(screen.queryByRole('link', { name: /Open dashboard/ })).not.toBeInTheDocument();
});
