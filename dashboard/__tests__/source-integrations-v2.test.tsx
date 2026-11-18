import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SourceSelection } from '@/components/intent-radar/advanced-controls';
import { SourceManagement } from '@/components/intent-radar/source-management';
import { emptyIntentSearch } from '@/lib/intent-radar';

vi.mock('@/components/intent-radar/provider', () => ({
  useRadarCapabilities: () => ({
    data: {
      stage: 'Beta',
      growth_enabled: true,
      can_write: true,
      can_manage: true,
      sources: [
        { id: 'hacker_news', name: 'Hacker News', state: 'Available', coverage: 'HN v0', documentation: 'https://github.com/HackerNews/API', request_limit_per_check: 30 },
        { id: 'stack_exchange', name: 'Stack Exchange', state: 'Available', coverage: 'SE 2.3', documentation: 'https://api.stackexchange.com/docs', configured_sites: ['stackoverflow', 'devops', 'ai'], request_limit_per_check: 8 },
        { id: 'github', name: 'GitHub', state: 'Available', coverage: 'GitHub REST & GraphQL', documentation: 'https://docs.github.com/en/rest', oauth_configured: true, webhooks_configured: false, request_limit_per_check: 24 },
        { id: 'youtube', name: 'YouTube', state: 'Available', coverage: 'YouTube v3', documentation: 'https://developers.google.com/youtube/v3', ai_analytics_authorized: false, request_limit_per_check: 14 },
        { id: 'bluesky', name: 'Bluesky', state: 'Available', coverage: 'Bluesky API + Jetstream', documentation: 'https://docs.bsky.app', jetstream_enabled: true, request_limit_per_check: 14 },
        { id: 'discourse', name: 'Approved Discourse', state: 'Not configured', coverage: 'Discourse RSS', documentation: 'https://meta.discourse.org', request_limit_per_check: 4 },
        { id: 'atom', name: 'Atom Feeds', state: 'Not configured', coverage: 'Atom 1.0', documentation: 'https://www.rfc-editor.org/rfc/rfc4287', request_limit_per_check: 4 },
      ],
      usage: { searches_today: 0, daily_search_limit: 20, monitor_limit: 50, automatic_schedules_enabled: true, minimum_schedule_hours: 6 },
    },
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useRadarRead: (path: string) => {
    if (path === '/sources/configurations') return { data: { items: [] }, error: null, isPending: false, refetch: vi.fn() };
    if (path === '/icps') return { data: { items: [] }, error: null, isPending: false, refetch: vi.fn() };
    if (path === '/sources/github/status') {
      return {
        data: {
          app_configured: true,
          oauth_configured: true,
          webhooks_configured: false,
          public_search_available: true,
          app_slug: 'planebyte-intent-radar',
          status: 'NOT_CONNECTED',
          installation_id: null,
          account_login: null,
          account_type: null,
          repositories: [],
          last_verified_at: null,
          last_error_code: null,
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
            { preset_id: 'discourse-n8n', name: 'n8n Community', family: 'discourse', endpoint: 'https://community.n8n.io/latest.rss', policy_reference: 'Public RSS', attribution: 'n8n', ai_processing_authorized: false, host_approved: true, configured: false, enabled: false },
            { preset_id: 'atom-nextjs', name: 'Next.js Releases', family: 'atom', endpoint: 'https://github.com/vercel/next.js/releases.atom', policy_reference: 'Atom', attribution: 'Vercel', ai_processing_authorized: true, host_approved: true, configured: false, enabled: false },
          ],
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
            {
              provider: 'bluesky',
              name: 'Bluesky',
              availability: 'Available',
              state: 'COMPLETE',
              last_success: '2026-11-18T05:00:00Z',
              stream_health: { state: 'HEALTHY', sequence: 12345, enabled: true, updated_at: '2026-11-18T05:00:00Z' },
            },
          ],
        },
        error: null,
        isPending: false,
        refetch: vi.fn(),
      };
    }
    return { data: null, error: null, isPending: false, refetch: vi.fn() };
  },
  useRadarMutation: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

describe('Source Integrations v2 UI', () => {
  it('renders all available sources and source-specific filters including YouTube policy gate', () => {
    const qc = new QueryClient();
    const onChange = vi.fn();
    render(
      <QueryClientProvider client={qc}>
        <SourceSelection
          value={{ ...emptyIntentSearch(), sources: ['github', 'youtube', 'bluesky', 'stack_exchange'] }}
          onChange={onChange}
        />
      </QueryClientProvider>
    );
    expect(screen.getByText(/GitHub content types/i)).toBeTruthy();
    expect(screen.getByText(/YouTube discovery mode/i)).toBeTruthy();
    expect(screen.getByText(/derived AI sentiment\/intent scoring remains gated/i)).toBeTruthy();
    expect(screen.getByText(/Bluesky discovery mode/i)).toBeTruthy();
    expect(screen.getByText(/Stack Exchange communities/i)).toBeTruthy();
  });

  it('renders GitHub Connect CTA, Bluesky Jetstream health and categorized preset feed catalog', () => {
    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <SourceManagement />
      </QueryClientProvider>
    );
    expect(screen.getByRole('button', { name: /Connect GitHub/i })).toBeTruthy();
    expect(screen.getByText(/Jetstream v2:/i)).toBeTruthy();
    expect(screen.getByText(/Cursor #12345/i)).toBeTruthy();
    expect(screen.getByRole('heading', { name: /Community Discussions/i })).toBeTruthy();
    expect(screen.getByRole('heading', { name: /Software Releases/i })).toBeTruthy();
    expect(screen.getByText(/n8n Community/i)).toBeTruthy();
    expect(screen.getByText(/Next\.js Releases/i)).toBeTruthy();
  });
});
