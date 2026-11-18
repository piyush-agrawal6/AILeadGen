import { PublishedPolicy } from '@/components/auth/published-policy';

export const metadata = {
  title: 'Subprocessors & Infrastructure Disclosure · PlaneByte',
  description: 'Verified infrastructure, AI, authentication, email, and payment service providers used by PlaneByte.',
  alternates: { canonical: 'https://planebyte.com/subprocessors' }
};

export default function Page() { return <PublishedPolicy policy="subprocessors" />; }
