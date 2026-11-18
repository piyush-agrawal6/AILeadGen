import { PublishedPolicy } from '@/components/auth/published-policy';

export const metadata = {
  title: 'Data Processing Addendum (Draft) · PlaneByte',
  description: 'Standard B2B Data Processing Addendum draft pending qualified legal review and bilateral execution.',
  alternates: { canonical: 'https://planebyte.com/dpa' }
};

export default function Page() { return <PublishedPolicy policy="dpa" />; }
