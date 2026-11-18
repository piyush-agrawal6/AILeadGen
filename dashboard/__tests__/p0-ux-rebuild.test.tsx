import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { readFileSync } from 'node:fs';
import { BillingSection } from '@/components/settings/sections/billing-section';
import { ResearchSourcesPanel } from '@/components/intent-radar/integrations/ResearchSourcesPanel';
import { CustomFeedsPanel } from '@/components/intent-radar/integrations/CustomFeedsPanel';
import { DiscoverExperience } from '@/components/intent-radar/discovery';
import { SignalCard } from '@/components/intent-radar/signals';
import { request } from '@/lib/intelligence';
import type { UsageData } from '@/components/workspaces/usage';
import type { IntentSignal } from '@/lib/intent-radar';

const catalog = JSON.parse(readFileSync('../app/billing/commercial_catalog.json', 'utf8'));

const mocks = vi.hoisted(() => ({
  usageData: undefined as UsageData | undefined,
  mutateAsync: vi.fn(),
  mutate: vi.fn(),
  radarRead: vi.fn(),
}));

vi.mock('@/lib/intelligence', () => ({ request: vi.fn() }));
const mockedRequest = vi.mocked(request);

vi.mock('@/components/workspaces/usage', async () => {
  const actual = await vi.importActual<typeof import('@/components/workspaces/usage')>('@/components/workspaces/usage');
  return {
    ...actual,
    useUsage: () => ({
      data: mocks.usageData,
      isPending: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    }),
  };
});

vi.mock('@/components/intent-radar/provider', () => ({
  useRadarCapabilities: () => ({
    data: {
      stage: 'Beta',
      growth_enabled: true,
      can_write: true,
      can_manage: true,
      sources: [
        { id: 'github', name: 'GitHub', state: 'Connected', coverage: 'GitHub public + connected repos', documentation: 'https://docs.github.com/en/rest', request_limit_per_check: 24 },
        { id: 'youtube', name: 'YouTube', state: 'Available', coverage: 'YouTube Data API v3', documentation: 'https://developers.google.com/youtube/v3', ai_analytics_authorized: false, request_limit_per_check: 14 },
        { id: 'bluesky', name: 'Bluesky', state: 'Available', coverage: 'Bluesky API + Jetstream', documentation: 'https://docs.bsky.app', jetstream_enabled: true, request_limit_per_check: 14 },
        { id: 'stack_exchange', name: 'Stack Exchange', state: 'Available', coverage: 'SE API 2.3', documentation: 'https://api.stackexchange.com/docs', configured_sites: ['stackoverflow', 'devops'], request_limit_per_check: 8 },
        { id: 'hacker_news', name: 'Hacker News', state: 'Available', coverage: 'HN Firebase v0', documentation: 'https://github.com/HackerNews/API', request_limit_per_check: 30 },
        { id: 'discourse', name: 'Approved Discourse', state: 'Available', coverage: 'Discourse RSS', documentation: 'https://meta.discourse.org', request_limit_per_check: 4 },
        { id: 'atom', name: 'Atom Feeds', state: 'Available', coverage: 'Atom 1.0', documentation: 'https://www.rfc-editor.org/rfc/rfc4287', request_limit_per_check: 4 },
      ],
      usage: { searches_today: 5, daily_search_limit: 20, monitor_limit: 50, automatic_schedules_enabled: true, minimum_schedule_hours: 6 },
    },
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useRadarRead: (path: string) => mocks.radarRead(path),
  useRadarMutation: () => ({ mutateAsync: mocks.mutateAsync, mutate: mocks.mutate, isPending: false }),
  useRadarRefresh: () => vi.fn(),
}));

function makeTrialUsage(overrides: Partial<UsageData> = {}): UsageData {
  return {
    access: {
      kind: 'Starter Trial',
      is_trial: true,
      intent_radar: true,
      growth_intelligence: true,
      commercial_subscription: false,
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
      cancel_confirmed_at: '2026-11-18T04:39:13+00:00',
    },
    search_usage: { manual_searches: 5, scheduled_checks: 0, total_searches: 5, reset_at: '2026-11-21T04:09:57+00:00' },
    commercial: { catalog, provider: 'creem', checkout_enabled: true, blockers: [], historical_payments: [] },
    usage: [
      { dimension: 'searches', label: 'Requested searches today', used: 5, limit: 20, remaining: 15, basis: 'daily', resets_at: null, near_limit: false },
      { dimension: 'plan_searches', label: 'Monthly searches', used: 5, reserved: 0, limit: 5, remaining: 0, basis: '3-day card trial', resets_at: '2026-11-21T04:09:57+00:00', near_limit: true },
      { dimension: 'plan_ai_calls', label: 'Shared AI operations', used: 3, reserved: 0, limit: 3, remaining: 0, basis: '3-day card trial', resets_at: '2026-11-21T04:09:57+00:00', near_limit: true },
      { dimension: 'plan_ai_tokens', label: 'Shared reserved AI token capacity', used: 4331, reserved: 0, limit: 150000, remaining: 145669, basis: '3-day card trial', resets_at: '2026-11-21T04:09:57+00:00', near_limit: false },
      { dimension: 'plan_monitors', label: 'Active monitors', used: 0, reserved: 0, limit: 1, remaining: 1, basis: 'capacity', resets_at: null, near_limit: false },
      { dimension: 'plan_monitor_executions', label: 'Monthly monitoring checks', used: 0, reserved: 0, limit: 0, remaining: 0, basis: '3-day card trial', resets_at: null, near_limit: false },
      { dimension: 'plan_reports', label: 'Monthly reports', used: 0, reserved: 0, limit: 0, remaining: 0, basis: '3-day card trial', resets_at: null, near_limit: false },
      { dimension: 'plan_api_requests', label: 'Developer API requests', used: 0, reserved: 0, limit: 0, remaining: 0, basis: '3-day card trial', resets_at: null, near_limit: false },
      { dimension: 'plan_team_members', label: 'Team seats', used: 1, reserved: 0, limit: 1, remaining: 0, basis: 'capacity', resets_at: null, near_limit: true },
    ],
    provider_usage: { requests: 12, input_tokens_reported: 28031, output_tokens_reported: 9361, estimated_cost_usd: null, unreported_requests: 0 },
    source_requests: [],
    team_seats: 1,
    sandbox_tools_available: false,
    support_url: 'mailto:contact@planebyte.com',
    unmetered: [],
    ...overrides,
  };
}

function wrap(node: React.ReactNode) {
  return (
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })}>
      {node}
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.usageData = makeTrialUsage();
  mocks.radarRead.mockImplementation((path: string) => {
    if (path === '/settings') {
      return { data: { discovery_keywords: [], discovery_excluded: [], topics: [], min_relevance: 0, default_view: 'cards', alerts_enabled: false, alert_threshold: 70, revision: 1, default_icp_id: null }, error: null, isPending: false, refetch: vi.fn() };
    }
    if (path === '/icps') return { data: { items: [] }, error: null, isPending: false, refetch: vi.fn() };
    if (path === '/sources/github/status') {
      return {
        data: {
          app_configured: true,
          oauth_configured: true,
          webhooks_configured: false,
          public_search_available: true,
          app_slug: 'planebyte-intent-radar',
          status: 'CONNECTED',
          installation_id: '182639090',
          account_login: 'planebytelabs',
          account_type: 'Organization',
          repositories: [{ id: 1, full_name: 'planebytelabs/radar', private: true, selected: true }],
          last_verified_at: '2026-11-18T06:00:00Z',
          last_error_code: null,
        },
        error: null,
        isPending: false,
        refetch: vi.fn(),
      };
    }
    if (path === '/sources/health') {
      return {
        data: {
          items: [
            { provider: 'bluesky', name: 'Bluesky', availability: 'Available', state: 'COMPLETE', last_success: '2026-11-18T06:00:00Z', stream_health: { state: 'HEALTHY', sequence: 999, enabled: true, updated_at: '2026-11-18T06:00:00Z' } },
          ],
        },
        error: null,
        isPending: false,
        refetch: vi.fn(),
      };
    }
    if (path === '/sources/configurations') {
      return {
        data: {
          items: [
            { id: 'cfg-1', name: 'Next.js Releases', family: 'atom', endpoint: 'https://github.com/vercel/next.js/releases.atom', policy_reference: 'Public Atom', attribution: 'Vercel', retention_days: 7, polling_minutes: 60, enabled: true, ai_processing_authorized: true, content_kind: 'release_announcement' },
            { id: 'cfg-2', name: 'Postman Community', family: 'discourse', endpoint: 'https://community.postman.com/latest.rss', policy_reference: 'Public RSS', attribution: 'Postman', retention_days: 7, polling_minutes: 60, enabled: true, ai_processing_authorized: false },
          ],
        },
        error: null,
        isPending: false,
        refetch: vi.fn(),
      };
    }
    if (path === '/sources/presets') {
      return {
        data: {
          items: [
            { preset_id: 'discourse-postman', name: 'Postman Community', family: 'discourse', endpoint: 'https://community.postman.com/latest.rss', policy_reference: 'Public RSS', attribution: 'Postman', ai_processing_authorized: false, host_approved: true, configured: true, enabled: true },
            { preset_id: 'atom-nextjs', name: 'Next.js Releases', family: 'atom', endpoint: 'https://github.com/vercel/next.js/releases.atom', policy_reference: 'Atom', attribution: 'Vercel', content_kind: 'release_announcement', ai_processing_authorized: true, host_approved: true, configured: true, enabled: true },
            { preset_id: 'atom-arxiv-ai', name: 'arXiv AI', family: 'atom', endpoint: 'https://rss.arxiv.org/atom/cs.AI', policy_reference: 'arXiv', attribution: 'arXiv', content_kind: 'research_paper', ai_processing_authorized: true, host_approved: true, configured: false, enabled: false },
          ],
        },
        error: null,
        isPending: false,
        refetch: vi.fn(),
      };
    }
    return { data: null, error: null, isPending: false, refetch: vi.fn() };
  });
});

afterEach(cleanup);

describe('P0 Billing & Usage Redesign', () => {
  it('shows Canceled Starter Trial cleanly without Choose Your Plan & Payment, distinguishes daily vs monthly exhaustion, and hides 0/0 progress bars', async () => {
    mockedRequest.mockResolvedValue({
      enabled: true,
      required: true,
      active: true,
      provider: 'creem',
      can_manage: true,
      plans: catalog.plans,
      history: [],
      contract: {
        id: 'c-trial',
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
        cancel_confirmed_at: '2026-11-18T04:39:13+00:00',
        recurring_authorized: 1,
        is_trial: true,
        entitlement_label: 'Starter Trial',
      },
    });

    render(wrap(<BillingSection activeTab="overview" />));
    expect(await screen.findByText('Starter Trial')).toBeVisible();
    expect(screen.getByText('Canceled — Access Remaining')).toBeVisible();
    expect(screen.getByText(/Your trial has been canceled\. You can continue using your current access until/)).toBeVisible();
    expect(screen.queryByText('Choose Your Plan & Payment')).not.toBeInTheDocument();
    expect(screen.getByText('Search allowance exhausted')).toBeVisible();
    expect(screen.getByText(/even though your daily safety limit has remaining capacity/)).toBeVisible();
    expect(screen.getByText('Not included in your current plan')).toBeVisible();
    expect(screen.getByRole('button', { name: /Detailed Usage/i })).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByRole('button', { name: /AI Usage Details/i })).toHaveAttribute('aria-expanded', 'false');
  });
});

describe('P0 Integrations & Custom Feeds Redesign', () => {
  it('renders Research Sources with connected GitHub account planebytelabs, YouTube policy restriction, and Bluesky Jetstream', () => {
    render(wrap(<ResearchSourcesPanel />));
    expect(screen.getByText('planebytelabs')).toBeVisible();
    expect(screen.getByText(/Derived AI analysis restricted by YouTube API policy/)).toBeVisible();
    expect(screen.getByText(/Jetstream v2:/)).toBeVisible();
    expect(screen.queryByText(/Reddit Discussions/i)).not.toBeInTheDocument();
  });

  it('renders Active Feeds first, categorized Preset Feed Catalog with search/filters, and intentional Add custom feed drawer', async () => {
    mocks.mutateAsync.mockResolvedValue({ ok: true });
    render(wrap(<CustomFeedsPanel />));

    expect(screen.getByText('Active Feeds (2)')).toBeVisible();
    expect(screen.getAllByText('Next.js Releases').length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText('Postman Community').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByRole('heading', { name: /Research & Technology/i })).toBeVisible();

    // Filter presets by search
    fireEvent.change(screen.getByLabelText('Search preset feeds'), { target: { value: 'arXiv' } });
    expect(screen.getByText('arXiv AI')).toBeVisible();

    // Open Add custom feed drawer (form is NOT permanently expanded on page!)
    expect(screen.queryByLabelText('HTTPS feed URL')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Add custom feed/i }));
    expect(await screen.findByLabelText('HTTPS feed URL')).toBeVisible();
    expect(screen.getByText(/cannot be self-declared here/i)).toBeVisible();
  });
});

describe('P0 Discover Advanced Search, AI Fallback & Signal Cards', () => {
  it('shows guided 3-step Advanced Search with collapsible Advanced Filters and upfront AI exhaustion banner', async () => {
    mocks.mutateAsync.mockResolvedValue({
      draft: { configuration: { keywords: ['kubernetes'], excluded: [], topics: [], phrases: [], offerings: '', source: 'Hacker News', sources: ['github'], categories: [], language: 'Any / unverified', geography: 'Any / unknown', from_date: null, to_date: null, min_relevance: 0, result_limit: 20 } },
      mode: 'Manual fallback',
      fallback_reason: 'The AI draft allowance is exhausted; manual editing remains available.',
      quota_exhausted: true,
    });

    render(wrap(<DiscoverExperience />));
    expect(screen.getByRole('heading', { name: 'Discover Conversations' })).toBeVisible();
    expect(screen.getByRole('button', { name: /Advanced Filters/i })).toHaveAttribute('aria-expanded', 'false');

    // Switch to Describe with AI and verify upfront exhausted allowance notice
    fireEvent.click(screen.getByRole('button', { name: /Describe with AI/i }));
    expect(screen.getByText(/Shared AI operations allowance exhausted/i)).toBeVisible();
    expect(screen.getByRole('link', { name: /View Billing & Usage/i })).toBeVisible();

    // Generate criteria returns labeled manual fallback
    fireEvent.change(screen.getByLabelText('What are you looking for?'), {
      target: { value: 'Find GitHub discussions about Kubernetes observability' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Generate Criteria/i }));
    expect(await screen.findByText(/Manual Fallback Criteria \(AI did not generate this draft\)/i)).toBeVisible();
  });

  it('distinguishes Usage Limit Reached from empty results when /discover returns 429', async () => {
    mocks.mutateAsync.mockRejectedValue(new Error('Monthly searches allowance exhausted.'));
    render(wrap(<DiscoverExperience />));

    fireEvent.change(screen.getByLabelText('Add Keywords'), { target: { value: 'observability' } });
    fireEvent.keyDown(screen.getByLabelText('Add Keywords'), { key: 'Enter' });
    fireEvent.click(screen.getByRole('button', { name: /Review Search/i }));
    fireEvent.click(screen.getByRole('button', { name: /Run Search/i }));

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Usage Limit Reached' })).toBeVisible();
    });
    expect(screen.queryByText('No matching discussions found')).not.toBeInTheDocument();
  });

  it('SignalCard clearly distinguishes Buyer-Intent Discussion vs Market / Tech Intelligence', () => {
    const releaseSignal: IntentSignal = {
      id: 'sig-1',
      title: 'Next.js 16.5 release notes',
      source: 'Atom Feeds',
      source_url: 'https://github.com/vercel/next.js/releases/tag/v16.5.0',
      excerpt: 'Release changelog for Next.js 16.5.',
      observed_at: '2026-11-18T05:00:00Z',
      retrieved_at: '2026-11-18T05:05:00Z',
      category: 'Market / technology intelligence',
      score: 42,
      status: 'New',
      notes: '',
      revision: 1,
      available: 1,
      saved: false,
      evidence: {
        matched_keywords: ['next.js'],
        matched_topics: [],
        intent_phrase: null,
        confidence: 'medium',
        explanation: 'Release announcement',
        observed_text: 'Release',
        unknown: [],
        purchasing_event_verified: false,
        provenance: { content_kind: 'release_announcement' },
      },
      monitors: [],
    };
    render(wrap(<SignalCard signal={releaseSignal} />));
    expect(screen.getByText('Market / Tech Intelligence')).toBeVisible();
  });
});
