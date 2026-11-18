import { PublishedPolicy } from '@/components/auth/published-policy';

export const metadata = {
  title: 'Refund Policy · PlaneByte',
  description: 'Refund review eligibility, billing error reconciliation, and Creem Merchant of Record settlement rules.',
  alternates: { canonical: 'https://planebyte.com/cancellation-refund-policy' }
};

export default function Page() { return <PublishedPolicy policy="refund" />; }
