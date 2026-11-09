import {notFound} from 'next/navigation';
import {canViewLegacyArchive} from '@/lib/server/legacy-access';
export default async function ArchivedResults(){
 if(!await canViewLegacyArchive())notFound();
 const {default:Archive}=await import('@/components/legacy/intro-results');
 return <Archive/>;
}
