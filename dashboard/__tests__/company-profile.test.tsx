import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CompanyProfileSettings } from '@/components/workspaces/company-profile';
import { request } from '@/lib/intelligence';

vi.mock('@/lib/intelligence', () => ({ request: vi.fn() }));
const mocked = vi.mocked(request);
const profile = {
  organization_id: 'owned',
  version: 'one',
  name: 'Controlled Engineering',
  website: 'https://controlled.example.com',
  description: 'Existing engineering description for B2B buyers',
  industry: 'Engineering',
  company_size: '11-50',
  country: 'United Kingdom',
  city: 'Bristol',
  timezone: 'Europe/London',
  contact_email: 'contact@controlled.example.com',
  countries_served: ['United Kingdom'],
  target_customers: [],
  target_industries: [],
  specialties: [],
  positioning: '',
  products_services: [],
  can_edit: true,
  onboarding_status: 'COMPLETED',
  quality_issues: [],
};

function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <CompanyProfileSettings />
    </QueryClientProvider>
  );
}

beforeEach(() => vi.resetAllMocks());

describe('company profile settings', () => {
  it('shows read-first overview, edits fields cleanly, and saves version without posting workspace ownership', async () => {
    mocked.mockImplementation(async (path, options) => {
      if (path === '/organization/workspaces') {
        return { items: [{ organization_id: 'owned', name: 'Controlled Engineering', role: 'OWNER' }], active_organization_id: 'owned' } as never;
      }
      if (path === '/organization/profile' && options?.method === 'PUT') {
        return { ...profile, name: 'Updated Engineering', version: 'two' } as never;
      }
      return profile as never;
    });

    mount();
    expect(await screen.findByText('Controlled Engineering')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: /Edit Profile/i }));
    fireEvent.change(await screen.findByLabelText(/Company name/i), {
      target: { value: 'Updated Engineering' },
    });
    fireEvent.click(screen.getAllByRole('button', { name: /Save Changes/i })[0]);

    expect(await screen.findByRole('status')).toHaveTextContent('Organization profile saved.');
    const call = mocked.mock.calls.find(([path, options]) => path === '/organization/profile' && options?.method === 'PUT');
    const payload = JSON.parse(String(call?.[1]?.body));
    expect(payload.name).toBe('Updated Engineering');
    expect(payload.version).toBe('one');
    expect(payload.organization_id).toBeUndefined();
    expect(payload.can_edit).toBeUndefined();
  });

  it('keeps viewer read-only and does not offer edit or save actions', async () => {
    mocked.mockImplementation(async (path) => {
      if (path === '/organization/workspaces') {
        return { items: [{ organization_id: 'owned', name: 'Controlled Engineering', role: 'VIEWER' }], active_organization_id: 'owned' } as never;
      }
      return { ...profile, can_edit: false } as never;
    });
    mount();
    expect(await screen.findByText('Controlled Engineering')).toBeVisible();
    expect(screen.queryByRole('button', { name: /Edit Profile/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Save Changes/i })).not.toBeInTheDocument();
  });

  it('preserves edits on conflict and provides an explicit reload action', async () => {
    mocked.mockImplementation(async (path, options) => {
      if (path === '/organization/workspaces') {
        return { items: [{ organization_id: 'owned', name: 'Controlled Engineering', role: 'OWNER' }], active_organization_id: 'owned' } as never;
      }
      if (path === '/organization/profile' && options?.method === 'PUT') {
        throw new Error('Company profile changed. Reload it before saving.');
      }
      return profile as never;
    });
    mount();
    fireEvent.click(await screen.findByRole('button', { name: /Edit Profile/i }));
    fireEvent.change(await screen.findByLabelText(/Company name/i), {
      target: { value: 'Unsaved owner edit' },
    });
    fireEvent.click(screen.getAllByRole('button', { name: /Save Changes/i })[0]);
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Company profile changed.'));
    expect(screen.getByLabelText(/Company name/i)).toHaveValue('Unsaved owner edit');
    expect(screen.getByRole('button', { name: /^Reload$/i })).toBeVisible();
  });
});
