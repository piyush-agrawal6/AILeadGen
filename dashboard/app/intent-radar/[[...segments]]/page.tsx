import {notFound, redirect} from 'next/navigation';
import {IntentRadarExperience} from '@/components/intent-radar/experience';
const routes = [
  '',
  'graph',
  'assistant',
  'ideal-customers',
  'ideal-customers/new',
  'ideal-customers/compare',
  'discover',
  'discover/new',
  'discover/history',
  'discover/saved',
  'monitors',
  'monitors/new',
  'signals',
  'opportunities',
  'actions',
  'saved',
  'alerts',
  'integrations',
  'integrations/sheets',
  'integrations/webhooks',
  'integrations/github/callback',
  'settings',
  'growth',
  'growth/themes',
  'growth/competitors',
  'growth/research',
  'growth/trends',
  'growth/saved',
  'growth/watchlists',
  'growth/reports',
];

export default async function Page({ params }: { params: Promise<{ segments?: string[] }> }) {
  const { segments = [] } = await params;
  const route = segments.join('/');

  if (route === 'graph') redirect('/intent-radar');
  if (route === 'growth/trends') redirect('/intent-radar/growth/themes');
  if (route === 'growth/watchlists') redirect('/intent-radar/monitors');
  if (route === 'growth/saved') redirect('/intent-radar/saved');
  if (route === 'growth/reports') redirect('/intent-radar/growth/research');

  const isDynamicRoute = /^\/(?:monitors|signals|opportunities|discover\/runs|ideal-customers|growth\/themes|growth\/competitors|growth\/research)\/[a-zA-Z0-9_-]+(?:\/edit)?$/.test(
    '/' + route
  );

  if (!routes.includes(route) && !isDynamicRoute) {
    notFound();
  }

  return <IntentRadarExperience route={route} />;
}
