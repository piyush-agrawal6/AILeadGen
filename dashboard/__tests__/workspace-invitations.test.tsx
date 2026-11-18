import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { InvitationSettings, InvitationResponse } from '@/components/workspaces/invitations';
import { request } from '@/lib/intelligence';

vi.mock('@/lib/intelligence', () => ({ request: vi.fn() }));
const mocked = vi.mocked(request);
const empty = { items: [], total: 0, page: 1, page_size: 25, can_invite_admin: true };

beforeEach(() => vi.resetAllMocks());

function mount() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <InvitationSettings />
    </QueryClientProvider>
  );
}

describe('workspace invitations', () => {
  it('creates a real request through the Invite Member dialog and shows the one-time link', async () => {
    mocked.mockImplementation(async (path, options) => {
      if (path === '/organization/workspaces') {
        return { items: [{ organization_id: 'org-1', name: 'PlaneByte', role: 'OWNER' }], active_organization_id: 'org-1' } as never;
      }
      if (options?.method === 'POST') {
        return {
          id: 'invite-one',
          email: 'teammate@example.test',
          role: 'MEMBER',
          status: 'PENDING',
          expires_at: '2026-12-01',
          token: 'a'.repeat(43),
          delivery: 'EMAIL_QUEUED',
        } as never;
      }
      return empty as never;
    });

    mount();
    fireEvent.click(await screen.findByRole('button', { name: /Invite Member/i }));
    fireEvent.change(await screen.findByLabelText('Work email'), {
      target: { value: 'teammate@example.test' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Send Invitation/i }));

    expect(await screen.findByDisplayValue(window.location.origin + '/accept-invitation#' + 'a'.repeat(43))).toBeVisible();
    const call = mocked.mock.calls.find(([p, options]) => p === '/organization/invitations' && options?.method === 'POST');
    expect(JSON.parse(String(call?.[1]?.body))).toEqual({ email: 'teammate@example.test', role: 'MEMBER' });
    expect(screen.getByRole('status')).toHaveTextContent(/Invitation email sent/i);
  });

  it('keeps the invitation code on error and never posts a caller-selected identity', async () => {
    mocked.mockRejectedValueOnce(new Error('Invitation is unavailable for this account.'));
    render(<InvitationResponse email="teammate@example.test" />);
    fireEvent.change(screen.getByLabelText('Invitation code'), { target: { value: 'b'.repeat(43) } });
    fireEvent.click(screen.getByRole('button', { name: /Accept Invitation/i }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Invitation is unavailable'));
    expect(screen.getByLabelText('Invitation code')).toHaveValue('b'.repeat(43));
    expect(JSON.parse(String(mocked.mock.calls[0][1]?.body))).toEqual({ token: 'b'.repeat(43), action: 'ACCEPT' });
  });

  it('shows successful acceptance and removes the reusable action', async () => {
    mocked.mockResolvedValueOnce({ status: 'ACCEPTED', organization_id: 'org-1' });
    render(<InvitationResponse email="teammate@example.test" />);
    fireEvent.change(screen.getByLabelText('Invitation code'), { target: { value: 'c'.repeat(43) } });
    fireEvent.click(screen.getByRole('button', { name: /Accept Invitation/i }));
    expect(await screen.findByRole('status')).toHaveTextContent('Invitation accepted.');
    expect(screen.queryByRole('button', { name: /Accept Invitation/i })).not.toBeInTheDocument();
  });
});
