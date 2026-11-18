import { PublishedPolicy } from '@/components/auth/published-policy';

export const metadata = {
  title: 'Terms of Service · PlaneByte',
  description: 'Terms governing access to PlaneByte, Intent Radar, and Growth Intelligence.',
  alternates: { canonical: 'https://planebyte.com/terms' }
};

export default function Page() { return <PublishedPolicy policy="terms" />; }
