import {notFound} from 'next/navigation';
import {canViewLegacyArchive} from '@/lib/server/legacy-access';
export default async function ArchivedExperiment(){
 if(!await canViewLegacyArchive())notFound();
 const {default:Archive}=await import('@/components/legacy/experiment-view');
 return <Archive/>;
}
