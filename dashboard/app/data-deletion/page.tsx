import { PublishedPolicy } from '@/components/auth/published-policy';

export const metadata = {
  title: 'Data Deletion & Account Closure Policy · PlaneByte',
  description: 'How to export data, disconnect GitHub/Google integrations, and request verified account or workspace deletion.',
  alternates: { canonical: 'https://planebyte.com/data-deletion' }
};

export default function Page() { return <PublishedPolicy policy="data-deletion" />; }
