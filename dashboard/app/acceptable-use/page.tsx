import { PublishedPolicy } from '@/components/auth/published-policy';

export const metadata = {
  title: 'Acceptable Use Policy · PlaneByte',
  description: 'Responsible research, third-party integration, AI Copilot, export, and API usage rules for PlaneByte.',
  alternates: { canonical: 'https://planebyte.com/acceptable-use' }
};

export default function Page() { return <PublishedPolicy policy="acceptable-use" />; }
