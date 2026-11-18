import { PublishedPolicy } from '@/components/auth/published-policy';

export const metadata = {
  title: 'Digital Delivery Policy · PlaneByte',
  description: 'Electronic SaaS provisioning and provider-verified activation for PlaneByte Intent Radar.',
  alternates: { canonical: 'https://planebyte.com/delivery-policy' }
};

export default function Page() { return <PublishedPolicy policy="delivery-policy" />; }
