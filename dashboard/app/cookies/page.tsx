import { PublishedPolicy } from '@/components/auth/published-policy';

export const metadata = {
  title: 'Cookie Policy & Privacy Preferences · PlaneByte',
  description: 'Audited cookie inventory, browser storage, and consent-gated third-party scripts across PlaneByte.',
  alternates: { canonical: 'https://planebyte.com/cookies' }
};

export default function Page() { return <PublishedPolicy policy="cookies" />; }
