import type {Metadata} from 'next';
import {AuthState} from '@/components/auth/auth-state';
import {GoogleForm} from '@/components/auth/google-form';
import {googleSignIn} from '../login/actions';
export const metadata:Metadata={title:'Verify your email · PlaneByte'};
export default function Verify(){return <AuthState eyebrow="A SECURE START" title="Verify with your Google account" description="PlaneByte checks your verified Google email when you sign in. There’s no separate email verification code to enter here."><GoogleForm action={googleSignIn}/><p className="auth-fineprint">Continue with the account associated with your workspace. A link or query parameter alone never verifies your identity.</p></AuthState>;}
