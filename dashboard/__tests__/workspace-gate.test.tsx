import { it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { WorkspaceGate } from '@/components/workspaces/gate';
import { request } from '@/lib/intelligence';

vi.mock('@/lib/intelligence', () => ({ request: vi.fn() }));
const { replace, push } = vi.hoisted(() => ({ replace: vi.fn(), push: vi.fn() }));
vi.mock('next/navigation', () => ({ usePathname: () => '/', useRouter: () => ({ replace, push }) }));
const mocked = vi.mocked(request);

function mount() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <WorkspaceGate>
        <p>Private product</p>
      </WorkspaceGate>
    </QueryClientProvider>
  );
}

beforeEach(() => vi.resetAllMocks());

it('offers a new signed-in user their own workspace without mounting private data views', async () => {
  mocked.mockResolvedValue({ items: [], active_organization_id: null, active_onboarding_status: null });
  mount();
  expect(await screen.findByRole('link', { name: 'Create your workspace' })).toHaveAttribute('href', '/settings/workspaces');
  expect(screen.queryByText('Private product')).not.toBeInTheDocument();
});

it('keeps incomplete company setup outside product views when not deferred', async () => {
  mocked.mockResolvedValue({
    items: [{ organization_id: 'owned', name: 'Company', role: 'OWNER' }],
    active_organization_id: 'owned',
    active_onboarding_status: 'IN_PROGRESS',
    active_onboarding_deferred: false
  });
  mount();
  await waitFor(() => expect(replace).toHaveBeenCalledWith('/onboarding'));
  expect(screen.queryByText('Private product')).not.toBeInTheDocument();
});

it('renders product content without repeated onboarding banner when onboarding is deferred', async () => {
  mocked.mockResolvedValue({
    items: [{ organization_id: 'owned', name: 'Company', role: 'OWNER' }],
    active_organization_id: 'owned',
    active_onboarding_status: 'IN_PROGRESS',
    active_onboarding_deferred: true
  });
  mount();
  expect(await screen.findByText('Private product')).toBeVisible();
  expect(screen.queryByText('Finish setting up your workspace')).not.toBeInTheDocument();
  expect(replace).not.toHaveBeenCalled();
});

it('renders products only after verified completed workspace metadata', async () => {
  mocked.mockResolvedValue({
    items: [{ organization_id: 'owned', name: 'Company', role: 'OWNER' }],
    active_organization_id: 'owned',
    active_onboarding_status: 'COMPLETED'
  });
  mount();
  await waitFor(() => expect(screen.getByText('Private product')).toBeVisible());
  expect(screen.queryByText('Finish setting up your workspace')).not.toBeInTheDocument();
});

it('lets invited members review setup without auto redirecting or creating a company', async () => {
  mocked.mockResolvedValue({
    items: [{ organization_id: 'owned', name: 'Company', role: 'MEMBER' }],
    active_organization_id: 'owned',
    active_onboarding_status: 'IN_PROGRESS'
  });
  mount();
  expect(await screen.findByRole('link', { name: 'Continue onboarding' })).toBeVisible();
  expect(replace).not.toHaveBeenCalled();
  expect(screen.queryByText('Private product')).not.toBeInTheDocument();
});
