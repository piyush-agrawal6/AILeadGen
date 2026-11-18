import { it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { PublishedPolicy } from '@/components/auth/published-policy';
import { PrivacyControls } from '@/components/auth/privacy-controls';
import { isPublicPage } from '@/lib/auth-experience';
import { listPrivacyRequests } from '@/app/account-security-actions';

vi.mock('next-themes', () => ({ useTheme: () => ({ theme: 'light', setTheme: vi.fn() }) }));
vi.mock('@/app/account-security-actions', () => ({
  exportAccountDetails: vi.fn(),
  submitPrivacyRequest: vi.fn(),
  listPrivacyRequests: vi.fn()
}));

beforeEach(() => vi.resetAllMocks());

it('marks all 11 legal policy routes as public without login barriers', () => {
  for (const path of [
    '/privacy',
    '/terms',
    '/cookies',
    '/refund',
    '/cancellation',
    '/delivery-policy',
    '/acceptable-use',
    '/sources-policy',
    '/data-deletion',
    '/subprocessors',
    '/dpa'
  ]) {
    expect(isPublicPage(path)).toBe(true);
  }
});

it('renders Privacy Policy with mandatory YouTube API Services links, TOC, and honest individual operator identity', () => {
  render(<PublishedPolicy policy="privacy" />);
  expect(screen.getByRole('heading', { name: 'PlaneByte Privacy Policy' })).toBeVisible();
  expect(screen.getByRole('navigation', { name: 'On this page' })).toBeVisible();
  expect(screen.getByRole('link', { name: 'YouTube Terms of Service' })).toHaveAttribute(
    'href',
    'https://www.youtube.com/t/terms'
  );
  expect(screen.getByRole('link', { name: 'Google Privacy Policy' })).toHaveAttribute(
    'href',
    'https://policies.google.com/privacy'
  );
  expect(screen.getByRole('link', { name: 'Google Security Settings' })).toHaveAttribute(
    'href',
    'https://security.google.com/settings/security/permissions'
  );
  expect(screen.queryByText(/Planebyte Studios/i)).not.toBeInTheDocument();
});

it('renders DPA clearly marked as Draft Pending Signature without claiming pre-executed SCCs', () => {
  render(<PublishedPolicy policy="dpa" />);
  expect(screen.getByRole('heading', { name: /Data Processing Addendum \(Draft Pending Signature\)/ })).toBeVisible();
  expect(screen.getByText(/Draft Pending Legal Review & Bilateral Signature/)).toBeVisible();
});

it('renders PrivacyControls with recorded privacy request history and connected-sources revocation link', async () => {
  vi.mocked(listPrivacyRequests).mockResolvedValue([
    { id: 'req-12345678-abcd', kind: 'EXPORT', status: 'REQUESTED', created_at: '2026-11-18T00:00:00Z' }
  ]);
  render(<PrivacyControls />);
  expect(screen.getByRole('link', { name: /Manage & revoke connected sources/i })).toHaveAttribute(
    'href',
    '/settings?category=integrations'
  );
  await waitFor(() => expect(screen.getByText('Recorded privacy requests')).toBeVisible());
  expect(screen.getByText('REQUESTED')).toBeVisible();
});
