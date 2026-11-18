import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CompanyProfileSettings } from '@/components/workspaces/company-profile';
import { CapabilityFeatures } from '@/components/workspaces/features';
import { request } from '@/lib/intelligence';

vi.mock('@/lib/intelligence', () => ({ request: vi.fn() }));
const mocked = vi.mocked(request);

const profile = {
  organization_id: 'owned',
  version: 'v1',
  name: 'Existing company',
  website: 'https://example.com',
  description: 'Owner description for B2B workflow software',
  industry: 'Software',
  company_size: '',
  country: '',
  city: '',
  timezone: 'UTC',
  contact_email: '',
  countries_served: [],
  target_customers: [],
  target_industries: [],
  specialties: [],
  positioning: '',
  products_services: [],
  can_edit: true,
  onboarding_status: 'IN_PROGRESS',
  quality_issues: [],
};

const preview = {
  id: 'review-owned',
  website: 'https://example.com',
  status: 'READY',
  progress_stage: 'READY',
  can_retry: false,
  preview: {
    suggestions: {
      name: 'Evidence company',
      description: 'Published company information',
      products_services: [{ name: 'Engineering', category: '', description: '' }],
    },
    sources: { name: { url: 'https://example.com/about', kind: 'AI_SUPPORTED_BY_PUBLIC_TEXT' } },
    evidence: { name: [{ url: 'https://example.com/about', quote: 'Evidence company provides engineering.' }] },
    source_url: 'https://example.com',
    retrieved_at: '2026-11-06T01:00:00Z',
    missing_fields: ['timezone', 'company_size'],
    ownership_verified: false,
    pages_reviewed: 2,
  },
};

function mount() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <CapabilityFeatures.Provider value={{ companyDiscovery: true }}>
        <CompanyProfileSettings />
      </CapabilityFeatures.Provider>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  mocked.mockImplementation(async (path, options) => {
    if (path === '/organization/workspaces') {
      return { items: [{ organization_id: 'owned', name: 'Existing company', role: 'OWNER' }], active_organization_id: 'owned' } as never;
    }
    if (path === '/organization/profile') {
      return (options?.method === 'PUT' ? { ...profile, ...JSON.parse(String(options.body)), version: 'v2' } : profile) as never;
    }
    if (path.endsWith('/capabilities')) {
      return { can_analyze: true, ai_enabled: true, configured: true, max_pages: 5, estimated_ai_operations: 1, ai_calls_remaining: 15 } as never;
    }
    return preview as never;
  });
});

describe('reviewed company AI auto-fill', () => {
  it('only applies selected fields to the draft and requires a separate save with owned evidence', async () => {
    mount();
    // Open AI research panel from overview, then run analysis
    fireEvent.click(await screen.findByRole('button', { name: /Analyze Website with AI/i }));
    const runBtns = await screen.findAllByRole('button', { name: /Analyze Website with AI/i });
    fireEvent.click(runBtns[runBtns.length - 1]);

    await screen.findByText('Review AI-Extracted Profile Draft');
    // Uncheck description so only name & products_services are applied
    fireEvent.click(screen.getByRole('checkbox', { name: /Company description/i }));
    fireEvent.click(screen.getByRole('button', { name: /Apply Selected \(2\)/i }));

    expect(screen.getByLabelText('Company name *')).toHaveValue('Evidence company');
    expect(screen.getByLabelText('Company description')).toHaveValue('Owner description for B2B workflow software');
    expect(mocked.mock.calls.some(([, options]) => options?.method === 'PUT')).toBe(false);

    fireEvent.click(screen.getAllByRole('button', { name: /Save Changes/i })[0]);
    await screen.findByText('Organization profile saved.');
    const mutation = mocked.mock.calls.find(([path, options]) => path === '/organization/profile' && options?.method === 'PUT');
    const body = JSON.parse(String(mutation![1]!.body));
    expect(body.review_id).toBe('review-owned');
    expect(body.reviewed_fields).toEqual(['name', 'products_services']);
    expect(body.organization_id).toBeUndefined();
  });

  it('structures a no-website description without starting website discovery', async () => {
    mount();
    fireEvent.click(await screen.findByRole('button', { name: /Analyze Website with AI/i }));
    fireEvent.click(await screen.findByRole('button', { name: /Describe Business/i }));
    fireEvent.change(screen.getByPlaceholderText(/Describe what your company builds/i), {
      target: { value: 'We provide engineering services for international businesses.' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Generate Profile Draft/i }));
    await screen.findByText('Review AI-Extracted Profile Draft');
    const mutation = mocked.mock.calls.find(([path, options]) => path === '/organization/website-reviews' && options?.method === 'POST');
    const body = JSON.parse(String(mutation![1]!.body));
    expect(body.source_kind).toBe('DESCRIPTION');
    expect(body.website).toBe('');
    expect(body.use_ai).toBe(true);
  });

  it('shows provider failure safely without modifying saved profile', async () => {
    mocked.mockImplementation(async (path, options) => {
      if (path === '/organization/workspaces') {
        return { items: [{ organization_id: 'owned', name: 'Existing company', role: 'OWNER' }], active_organization_id: 'owned' } as never;
      }
      if (path === '/organization/profile') return profile as never;
      if (path.endsWith('/capabilities')) return { can_analyze: true, max_pages: 5 } as never;
      if (options?.method === 'POST') throw new Error('AI unavailable. Please retry.');
      return preview as never;
    });
    mount();
    fireEvent.click(await screen.findByRole('button', { name: /Analyze Website with AI/i }));
    const runBtns = await screen.findAllByRole('button', { name: /Analyze Website with AI/i });
    fireEvent.click(runBtns[runBtns.length - 1]);
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('AI unavailable'));
  });

  it('does not request AI capabilities or expose extraction actions to a viewer', async () => {
    mocked.mockImplementation(async (path) => {
      if (path === '/organization/workspaces') {
        return { items: [{ organization_id: 'owned', name: 'Existing company', role: 'VIEWER' }], active_organization_id: 'owned' } as never;
      }
      return { ...profile, can_edit: false } as never;
    });
    mount();
    expect(await screen.findByText('Existing company')).toBeVisible();
    expect(screen.queryByRole('button', { name: /Analyze Website with AI/i })).not.toBeInTheDocument();
    expect(mocked.mock.calls.some(([path]) => path.includes('website-reviews'))).toBe(false);
  });
});
