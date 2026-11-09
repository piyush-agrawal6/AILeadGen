import type {Metadata} from 'next';
import {AuthState} from '@/components/auth/auth-state';
export const metadata:Metadata={title:'Reset password · PlaneByte'};
export default function Reset(){return <AuthState eyebrow="ACCOUNT SECURITY" title="Your password is managed by Google" description="This workspace doesn’t use a separate PlaneByte password. Reset your Google password through Google’s secure recovery flow."><a className="auth-primary-button" href="https://accounts.google.com/signin/recovery" target="_blank" rel="noopener noreferrer">Continue to Google recovery <span aria-hidden="true">↗</span></a><p className="auth-fineprint">PlaneByte cannot validate password-reset links in this deployment. Never enter a password into an unverified link.</p></AuthState>;}
