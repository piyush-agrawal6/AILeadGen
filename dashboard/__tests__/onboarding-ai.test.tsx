import { it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AIOnboarding } from '@/components/workspaces/onboarding-ai';
import { request } from '@/lib/intelligence';

vi.mock('@/lib/intelligence', () => ({ request: vi.fn() }));
vi.mock('@/components/workspaces/use-workspace', () => ({
  useWorkspace: () => ({ data: { active_organization_id: 'owned' } })
}));
vi.mock('@/components/workspaces/use-products', () => ({
  useProducts: () => ({ data: { intent_radar: { enabled: false } } })
}));

const mocked = vi.mocked(request);
const profile = {
  organization_id: 'owned',
  version: 'saved',
  can_edit: true,
  onboarding_status: 'IN_PROGRESS',
  name: 'Manual company',
  website: 'https://example.com',
  description: 'Reviewed engineering',
  industry: 'Software',
  company_size: '',
  country: '',
  city: '',
  timezone: '',
  contact_email: '',
  countries_served: [],
  target_customers: [],
  target_industries: [],
  specialties: [],
  positioning: '',
  products_services: [{ name: 'Engineering', category: 'Software', description: 'Core engineering' }]
};
const progress = {
  revision: 1,
  current_step: 'COMPANY',
  objectives: ['RESEARCH_MARKETS'],
  services: profile.products_services,
  default_icp_id: null,
  preferences: {
    setup_mode: 'MANUAL',
    company_review_id: null,
    icp_review_id: null,
    research_keywords: [],
    excluded_keywords: []
  },
  status: 'IN_PROGRESS',
  can_edit: true
};

function mount(state: unknown) {
  mocked.mockImplementation(async path =>
    path.endsWith('/assistant-context')
      ? state
      : path === '/billing/subscription'
        ? {
            enabled: true,
            required: true,
            active: false,
            can_manage: true,
            plans: [{ code: 'starter', name: 'Starter', monthly_minor: 5900, audience: 'Starter', limits: null }],
            trial_blockers: ['Controlled test: no checkout initiated'],
            terms_version: 'approved-test'
          }
        : path.includes('/reviews/')
          ? (state as { reviews: { company: unknown } }).reviews.company
          : { items: [] }
  );
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })}>
      <AIOnboarding />
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  window.sessionStorage.clear();
});

it('keeps invited read-only members out of company editing and assistant actions', async () => {
  mount({
    progress: { ...progress, can_edit: false },
    company: { ...profile, can_edit: false },
    reviews: {},
    capabilities: { company_analysis: false, icp_recommendations: false }
  });
  expect(await screen.findByText('Your workspace owner is preparing this company')).toBeVisible();
  expect(screen.queryByRole('button', { name: 'Save business profile & continue' })).not.toBeInTheDocument();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  expect(mocked.mock.calls.every(([, options]) => !options?.method)).toBe(true);
});

it('removes repetitive Accept this section, View quoted evidence, and Save & Exit clutter', async () => {
  mount({
    progress: { ...progress, preferences: { ...progress.preferences, company_review_id: 'review' } },
    company: profile,
    reviews: {
      company: {
        id: 'review',
        status: 'READY',
        preview: { suggestions: { name: 'Proposed company' }, source_url: 'https://example.com', pages_reviewed: 3 },
        can_retry: false
      }
    },
    capabilities: { company_analysis: true, icp_recommendations: true }
  });
  expect(await screen.findByRole('button', { name: 'Save business profile & continue' })).toBeVisible();
  expect(screen.getByRole('button', { name: 'Skip onboarding' })).toBeVisible();
  expect(screen.queryByRole('button', { name: /Save & Exit/i })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /Accept this section/i })).not.toBeInTheDocument();
  expect(screen.queryByText(/View quoted evidence/i)).not.toBeInTheDocument();
});

it('highlights and focuses invalid Step 1 website inline without exposing raw backend paths', async () => {
  mount({
    progress: { ...progress, current_step: 'OBJECTIVES', preferences: { ...progress.preferences, company_review_id: null } },
    company: { ...profile, website: '' },
    reviews: {},
    capabilities: { company_analysis: true, icp_recommendations: true }
  });
  const input = await screen.findByLabelText('Company website');
  fireEvent.change(input, { target: { value: 'not a valid url' } });
  fireEvent.click(screen.getByRole('button', { name: 'Analyze my website' }));
  expect(await screen.findByText(/Enter a valid public website address/i)).toBeVisible();
  expect(input).toHaveAttribute('aria-invalid', 'true');
  expect(mocked.mock.calls.some(([path]) => path.endsWith('/analyze'))).toBe(false);
});

it('highlights invalid Step 2 fields inline and translates backend validation errors without losing draft', async () => {
  mount({
    progress,
    company: profile,
    reviews: {},
    capabilities: { company_analysis: true, icp_recommendations: true }
  });
  const nameInput = await screen.findByRole('textbox', { name: 'Company name' });
  const siteInput = screen.getByRole('textbox', { name: 'Company website' });
  fireEvent.change(nameInput, { target: { value: 'a' } });
  fireEvent.change(siteInput, { target: { value: 'http://localhost:3000' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save business profile & continue' }));
  expect(await screen.findAllByText('Enter a company name (at least 2 characters).')).toHaveLength(2);
  expect(screen.getAllByText('Enter a valid public website address.')).toHaveLength(2);
  expect(screen.getByText('Please fix the following before continuing')).toBeVisible();
  expect(nameInput).toHaveAttribute('aria-invalid', 'true');
  expect(siteInput).toHaveAttribute('aria-invalid', 'true');
  // Draft values preserved
  expect(nameInput).toHaveValue('a');
  expect(siteInput).toHaveValue('http://localhost:3000');
});

it('adds, edits, and removes products and services cleanly', async () => {
  mount({
    progress,
    company: profile,
    reviews: {},
    capabilities: { company_analysis: true, icp_recommendations: true }
  });
  expect(await screen.findByDisplayValue('Engineering')).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: /Add offering/i }));
  const inputs = screen.getAllByPlaceholderText('e.g. Intent Radar');
  expect(inputs).toHaveLength(2);
  fireEvent.change(inputs[1], { target: { value: 'Intent Radar' } });
  expect(screen.getByDisplayValue('Intent Radar')).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Remove offering Intent Radar' }));
  expect(screen.queryByDisplayValue('Intent Radar')).not.toBeInTheDocument();
});

it('completing setup cannot advertise a product without verified enrollment', async () => {
  mount({
    progress: { ...progress, status: 'COMPLETED' },
    company: profile,
    reviews: {},
    capabilities: { company_analysis: false, icp_recommendations: false }
  });
  expect(await screen.findByRole('heading', { name: 'Your reviewed context is saved' })).toBeVisible();
  await waitFor(() => expect(screen.getByRole('link', { name: 'Open workspace settings →' })).toBeVisible());
  expect(screen.queryByRole('link', { name: /Discover conversations/i })).not.toBeInTheDocument();
  expect(screen.queryByRole('complementary')).not.toBeInTheDocument();
});

it('shows ONE single authoritative error banner on worker failure without a competing Copilot duplicate error card', async () => {
  mount({
    progress: { ...progress, preferences: { ...progress.preferences, company_review_id: 'failed-review' } },
    company: profile,
    reviews: {
      company: {
        id: 'failed-review',
        status: 'FAILED',
        progress_stage: 'FAILED',
        error_code: 'SETUP_STORAGE_UNAVAILABLE',
        preview: null,
        can_retry: true
      }
    },
    capabilities: { company_analysis: true, icp_recommendations: true }
  });
  expect(await screen.findAllByText('Analysis did not complete')).toHaveLength(1);
  expect(screen.getAllByText(/worker could not access required storage/)).toHaveLength(1);
  fireEvent.click(screen.getByRole('button',{name:'Open AI Copilot'}));
  expect(screen.getByText('Needs retry')).toBeVisible();
  fireEvent.click(screen.getByRole('button',{name:'Close AI Copilot'}));
  expect(screen.queryByRole('button', { name: 'Cancel' })).not.toBeInTheDocument();
  expect(screen.getByRole('textbox', { name: 'Company name' })).toHaveValue('Manual company');
});

it('shows three setup milestones and an on-demand keyboard-accessible Copilot', async () => {
  mount({ progress, company: profile, reviews: {}, capabilities: { company_analysis: true, icp_recommendations: true } });
  const rail = await screen.findByRole('navigation', { name: 'Onboarding Progress' });
  for (const name of ['Your business', 'Your ideal customers', 'First discovery']) {
    expect(rail).toHaveTextContent(name);
  }
  expect(rail).not.toHaveTextContent('Plan & Payment');
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Open AI Copilot' }));
  expect(await screen.findByRole('dialog', { name: 'PlaneByte AI Copilot' })).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Close AI Copilot' }));
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
});

it('keeps completed research saved and links to billing without granting access', async () => {
  const state = {
    payment: { required: true, active: false },
    progress: { ...progress, status: 'COMPLETED' },
    company: profile,
    reviews: {},
    capabilities: { company_analysis: true, icp_recommendations: true }
  };
  mount(state);
  expect(await screen.findByRole('heading', { name: 'Your reviewed context is saved' })).toBeVisible();
  expect(screen.queryByRole('heading', { name: 'Your workspace is ready' })).not.toBeInTheDocument();
  expect(screen.getByRole('link',{name:'Manage Subscription'})).toHaveAttribute('href','/settings?category=billing&tab=overview');
  expect(mocked.mock.calls.every(([, options]) => !options?.method)).toBe(true);
});

it('terminates failed Copilot guidance and retries the same owned job without discarding the draft', async () => {
  const state = { progress, company: profile, reviews: {}, capabilities: { company_analysis: true, icp_recommendations: true } };
  let retried = false;
  const failed = { id: 'advice-owned', status: 'FAILED', progress_stage: 'FAILED', error_code: 'AI_OUTPUT_TRUNCATED', can_retry: true, preview: null };
  mocked.mockImplementation(async (path, options) => {
    if (path.endsWith('/assistant-context')) return state;
    if (path.endsWith('/assistant')) return { mode: 'AI guidance', job: failed };
    if (path.endsWith('/control')) {
      expect(JSON.parse(String(options?.body))).toEqual({ action: 'RETRY' });
      retried = true;
      return { status: 'QUEUED' };
    }
    if (path.endsWith('/reviews/advice-owned')) {
      return retried ? { ...failed, status: 'READY', can_retry: false, preview: { answer: 'Reviewed guidance based on the saved engineering offering.' } } : failed;
    }
    return { items: [] };
  });
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })}>
      <AIOnboarding />
    </QueryClientProvider>
  );
  fireEvent.change(await screen.findByRole('textbox', { name: 'Company name' }), { target: { value: 'Unsaved manual edit' } });
  fireEvent.click(screen.getByRole('button',{name:'Open AI Copilot'}));
  fireEvent.change(screen.getByRole('textbox', { name: 'Ask Copilot about your business' }), { target: { value: 'Explain our offering' } });
  fireEvent.click(screen.getByRole('button', { name: 'Send question to Copilot' }));
  expect(await screen.findByText(/stopped early before finishing/i)).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Retry guidance' }));
  expect(await screen.findByText('Reviewed guidance based on the saved engineering offering.')).toBeVisible();
  fireEvent.click(screen.getByRole('button',{name:'Close AI Copilot'}));
  expect(screen.getByRole('textbox', { name: 'Company name' })).toHaveValue('Unsaved manual edit');
  expect(mocked.mock.calls.filter(([path]) => path.endsWith('/assistant'))).toHaveLength(1);
});

it('applies actionable Copilot proposed_updates and allows discarding without silently overwriting manual edits', async () => {
  const state = { progress, company: profile, reviews: {}, capabilities: { company_analysis: true, icp_recommendations: true } };
  const advice = {
    id: 'advice-apply',
    status: 'READY',
    progress_stage: 'READY',
    can_retry: false,
    preview: {
      answer: 'Here is a sharper positioning statement.',
      proposed_updates: [
        { target: 'positioning', label: 'Apply positioning statement', value: 'Buyer-intent intelligence that uncovers live B2B demand.', mode: 'replace' },
        { target: 'industry', label: 'Apply industry', value: 'B2B SaaS', mode: 'replace' }
      ]
    }
  };
  mocked.mockImplementation(async path => {
    if (path.endsWith('/assistant-context')) return state;
    if (path.endsWith('/assistant')) return { mode: 'AI guidance', job: advice };
    if (path.endsWith('/reviews/advice-apply')) return advice;
    return { items: [] };
  });
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })}>
      <AIOnboarding />
    </QueryClientProvider>
  );
  fireEvent.change(await screen.findByRole('textbox', { name: 'Company name' }), { target: { value: 'Custom Unsaved Name' } });
  fireEvent.click(screen.getByRole('button',{name:'Open AI Copilot'}));
  fireEvent.change(screen.getByRole('textbox', { name: 'Ask Copilot about your business' }), { target: { value: 'Make my positioning more specific' } });
  fireEvent.click(screen.getByRole('button', { name: 'Send question to Copilot' }));
  const applyBtn = await screen.findByRole('button', { name: 'Apply positioning statement' });
  expect(screen.getByRole('textbox', { name: 'Business positioning',hidden:true })).toHaveValue('');
  fireEvent.click(applyBtn);
  fireEvent.click(screen.getByRole('button',{name:'Discard suggestion: Apply industry'}));
  expect(screen.queryByRole('button',{name:'Apply industry'})).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Close AI Copilot'}));
  expect(screen.getByRole('textbox', { name: 'Business positioning' })).toHaveValue('Buyer-intent intelligence that uncovers live B2B demand.');
  expect(screen.getByRole('textbox', { name: 'Company name' })).toHaveValue('Custom Unsaved Name');

});

it('renders Workspace Ready completion screen with 3 next actions and no Copilot panel when billing is verified active', async () => {
  mount({
    payment: { required: true, active: true, contract: { plan_code: 'starter', status: 'trialing', provider: 'creem', trial_end: 1795000000 } },
    progress: { ...progress, status: 'COMPLETED' },
    company: profile,
    reviews: {},
    capabilities: { company_analysis: false, icp_recommendations: false }
  });
  expect(await screen.findByRole('heading', { name: 'Your workspace is ready' })).toBeVisible();
  expect(screen.getByRole('link', { name: /Discover conversations/i })).toHaveAttribute('href', '/intent-radar/discover');
  expect(screen.getByRole('link', { name: /Create your first monitor/i })).toHaveAttribute('href', '/intent-radar/monitors/new');
  expect(screen.getByRole('link', { name: /Explore your Intelligence Graph/i })).toHaveAttribute('href', '/intent-radar');
  expect(screen.getByText('Starter Trial')).toBeVisible();
  expect(screen.queryByRole('complementary')).not.toBeInTheDocument();
});
