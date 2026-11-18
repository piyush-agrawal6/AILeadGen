import { PublishedPolicy } from '@/components/auth/published-policy';

export const metadata = {
  title: 'Cancellation & Subscription Policy · PlaneByte',
  description: 'Self-service subscription cancellation, 3-day free trial conversion, and refund rules for PlaneByte.',
  alternates: { canonical: 'https://planebyte.com/cancellation-refund-policy' }
};

export default function Page() { return <PublishedPolicy policy="cancellation" />; }
