"use client";
import {useParams} from 'next/navigation';
import {CampaignWorkspace} from '@/components/operations/campaign-workspace';
export default function CampaignPage(){const {campaignId}=useParams<{campaignId:string}>();return <main className="ops-page"><CampaignWorkspace id={campaignId}/></main>}
