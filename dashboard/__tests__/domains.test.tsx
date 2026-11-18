import { it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DomainSettings } from '@/components/workspaces/domains';
import { request } from '@/lib/intelligence';

vi.mock('@/lib/intelligence', () => ({ request: vi.fn() }));
const call = vi.mocked(request);

function mount() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <DomainSettings />
    </QueryClientProvider>
  );
}

beforeEach(() => vi.resetAllMocks());

it('shows the one-time DNS proof and retains it when verification fails', async () => {
  call.mockImplementation(async (path, options) => {
    if (path === '/organization/workspaces') {
      return { items: [{ organization_id: 'org-1', name: 'PlaneByte', role: 'OWNER' }], active_organization_id: 'org-1' } as never;
    }
    if (path.endsWith('/verify')) throw new Error('DNS is temporarily unavailable. Retry later.');
    if (options?.method === 'POST') {
      return {
        id: 'owned-record',
        domain: 'example.com',
        record_type: 'TXT',
        record_name: '_heysow-verify.example.com',
        record_value: 'heysow-verification=controlled-one-time-proof',
        expires_at: '2026-12-01T00:00:00Z',
      } as never;
    }
    return { items: [], can_edit: true } as never;
  });

  mount();
  fireEvent.click(await screen.findByRole('button', { name: /Add Domain/i }));
  fireEvent.change(await screen.findByLabelText('Domain name'), { target: { value: 'example.com' } });
  fireEvent.click(screen.getByRole('button', { name: /Generate DNS Record/i }));

  expect(await screen.findByText('heysow-verification=controlled-one-time-proof')).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: /Verify Now/i }));
  expect(await screen.findByRole('alert')).toHaveTextContent('DNS is temporarily unavailable.');
  expect(screen.getByText('heysow-verification=controlled-one-time-proof')).toBeVisible();
});

it('displays verified history to a viewer without mutation controls', async () => {
  call.mockImplementation(async (path) => {
    if (path === '/organization/workspaces') {
      return { items: [{ organization_id: 'org-1', name: 'PlaneByte', role: 'VIEWER' }], active_organization_id: 'org-1' } as never;
    }
    return {
      items: [{ id: 'owned-record', domain: 'example.com', status: 'VERIFIED', verified_at: '2026-11-06T00:00:00Z' }],
      can_edit: false,
    } as never;
  });
  mount();
  expect(await screen.findByText('example.com')).toBeVisible();
  expect(screen.queryByRole('button', { name: /Add Domain/i })).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /Revoke/i })).not.toBeInTheDocument();
});

it('distinguishes a missing TXT record from proven domain ownership', async () => {
  call.mockImplementation(async (path) => {
    if (path === '/organization/workspaces') {
      return { items: [{ organization_id: 'org-1', name: 'PlaneByte', role: 'OWNER' }], active_organization_id: 'org-1' } as never;
    }
    if (path.endsWith('/verify')) return { status: 'PENDING' } as never;
    return {
      items: [{ id: 'owned-record', domain: 'example.com', status: 'PENDING', verified_at: null }],
      can_edit: true,
    } as never;
  });
  mount();
  fireEvent.click(await screen.findByRole('button', { name: /^Verify$/i }));
  expect(await screen.findByRole('alert')).toHaveTextContent(/Matching TXT record not found yet/i);
});
