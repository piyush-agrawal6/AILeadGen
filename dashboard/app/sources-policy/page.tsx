import { PublishedPolicy } from '@/components/auth/published-policy';

export const metadata = {
  title: 'Third-Party Sources & Data Usage Policy · PlaneByte',
  description: 'Disclosures for YouTube Data API v3, GitHub, Bluesky, Stack Exchange, Hacker News, Discourse, and RSS/Atom sources.',
  alternates: { canonical: 'https://planebyte.com/sources-policy' }
};

export default function Page() { return <PublishedPolicy policy="sources-policy" />; }
