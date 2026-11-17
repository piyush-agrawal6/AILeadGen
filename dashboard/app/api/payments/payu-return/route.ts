import {NextResponse} from 'next/server';
export async function POST(){return NextResponse.json({error:'This payment provider is retired. Open Billing & Subscription to use Creem.'},{status:410});}
