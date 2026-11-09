import type {Metadata} from 'next';
import {AuthState} from '@/components/auth/auth-state';
import {brand} from '@/lib/brand';
export const metadata:Metadata={title:'Sign-in help · PlaneByte'};
export default function Recovery(){return <AuthState eyebrow="LET’S GET YOU BACK IN" title="Need help signing in?" description="PlaneByte uses your Google account for secure sign-in. If you can’t access your Google account, use Google’s account recovery process."><a className="auth-primary-button" href="https://accounts.google.com/signin/recovery" target="_blank" rel="noopener noreferrer">Recover your Google account <span aria-hidden="true">↗</span></a><div className="auth-information"><strong>Google works, but your workspace is unavailable?</strong><p>Contact your workspace administrator or <a className="text-primary underline" href={'mailto:'+brand.supportEmail}>PlaneByte support</a> to check your access. Your company permissions are separate from your Google sign-in.</p></div></AuthState>}
