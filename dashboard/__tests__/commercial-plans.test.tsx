import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { CommercialPlans, type CommercialCatalog } from '@/components/workspaces/commercial-plans';

const catalog = JSON.parse(readFileSync('../app/billing/commercial_catalog.json', 'utf8')) as CommercialCatalog;

it('shows approved USD prices, hides dense Before purchasing block, and expands Compare All Features on demand', () => {
  render(
    <CommercialPlans
      selectedPlan="growth"
      data={{
        catalog,
        provider: 'creem',
        checkout_enabled: false,
        blockers: ['Recurring capability unverified'],
        historical_payments: [],
      }}
    />
  );
  expect(screen.getByText('$59', { selector: '.commercial-price' })).toBeVisible();
  expect(screen.getByText(/Your selection is saved/)).toBeVisible();
  expect(screen.getByRole('button', { name: /Choose Growth/ })).toBeVisible();
  expect(screen.queryByRole('link', { name: /Choose Growth/ })).not.toBeInTheDocument();
  expect(screen.queryByRole('heading', { name: 'Before purchasing' })).not.toBeInTheDocument();
  expect(screen.queryByText('Pending approval')).not.toBeInTheDocument();
  expect(screen.queryByText(/internal test|₹100|₹200|₹300/i)).not.toBeInTheDocument();

  // Comparison table starts collapsed by default and opens when clicked
  const toggle = screen.getByRole('button', { name: /Compare All Features/i });
  expect(toggle).toHaveAttribute('aria-expanded', 'false');
  fireEvent.click(toggle);
  expect(toggle).toHaveAttribute('aria-expanded', 'true');
  expect(screen.getByText('600,000')).toBeVisible();
  expect(screen.getByText('Monthly monitoring checks')).toBeVisible();
});
