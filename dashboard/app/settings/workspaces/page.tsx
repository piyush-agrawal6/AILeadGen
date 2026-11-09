import {notFound} from 'next/navigation';
import {CreateWorkspace} from '@/components/workspaces/create-workspace';
export default function NewWorkspace(){if(process.env.HEYSOW_WORKSPACE_MANAGEMENT_ENABLED!=='true')notFound();return <CreateWorkspace/>}
