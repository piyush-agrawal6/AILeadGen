import { PublishedPolicy } from '@/components/auth/published-policy';

export const metadata = {
  title: 'Privacy Policy · PlaneByte',
  description: 'How PlaneByte collects, uses, stores, discloses, and protects personal information across planebyte.com and app.planebyte.com.',
  alternates: { canonical: 'https://planebyte.com/privacy' }
};

export default function Page() { return <PublishedPolicy policy="privacy" />; }
