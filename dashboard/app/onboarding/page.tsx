import {notFound} from 'next/navigation';
import {OnboardingSettings} from '@/components/workspaces/onboarding';
export default function Onboarding(){if(process.env.HEYSOW_WORKSPACE_MANAGEMENT_ENABLED!=='true')notFound();return <OnboardingSettings/>}
