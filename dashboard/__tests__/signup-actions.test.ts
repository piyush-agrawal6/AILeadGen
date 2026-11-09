import {beforeEach,expect,it,vi} from 'vitest';
const mocks=vi.hoisted(()=>({env:{production:false,publicRegistration:false,invitedRegistration:false,customerAccess:true,termsVersion:'synthetic-review-version',secret:'synthetic-server-secret-at-least-32-characters'},set:vi.fn(),signIn:vi.fn(),currentUser:vi.fn()}));
vi.mock('server-only',()=>({}));
vi.mock('next/headers',()=>({cookies:async()=>({set:mocks.set})}));
vi.mock('next/navigation',()=>({redirect:(path:string)=>{throw new Error(path)}}));
vi.mock('@/auth',()=>({signIn:mocks.signIn}));
vi.mock('@/lib/server/env',()=>({serverEnv:()=>mocks.env}));
vi.mock('@/lib/server/session',()=>({currentUser:mocks.currentUser}));
import {signupWithGoogle} from '@/app/signup/actions';
import {decodeConsent} from '@/lib/server/admission';
beforeEach(()=>{mocks.set.mockReset();mocks.signIn.mockReset();mocks.currentUser.mockResolvedValue(null);mocks.env.publicRegistration=false;mocks.env.invitedRegistration=false});
it('leaves registration disabled without setting cookies or contacting Google',async()=>{
  await expect(signupWithGoogle(new FormData())).rejects.toThrow('/signup?error=registration_unavailable');
  expect(mocks.set).not.toHaveBeenCalled();expect(mocks.signIn).not.toHaveBeenCalled();
});
it('requires current consent and a private code for invitation-only admission',async()=>{
  mocks.env.invitedRegistration=true;
  const form=new FormData();
  await expect(signupWithGoogle(form)).rejects.toThrow('terms_required');
  form.set('accept_terms','accepted');
  await expect(signupWithGoogle(form)).rejects.toThrow('invitation_required');
  form.set('invitation_token','invalid');
  await expect(signupWithGoogle(form)).rejects.toThrow('invitation_required');
  expect(mocks.set).not.toHaveBeenCalled();expect(mocks.signIn).not.toHaveBeenCalled();
});
it('stores bounded server-only consent and keeps the invitation out of OAuth redirect URLs',async()=>{
  mocks.env.invitedRegistration=true;
  const form=new FormData(),code='synthetic-private-invitation-'.padEnd(43,'x');
  form.set('accept_terms','accepted');form.set('invitation_token',code);
  await signupWithGoogle(form);
  expect(mocks.set).toHaveBeenCalledWith('planebyte-signup-consent',expect.any(String),{httpOnly:true,secure:false,sameSite:'lax',path:'/',maxAge:600});
  expect(decodeConsent(mocks.set.mock.calls[0][1],mocks.env.secret)).toMatchObject({version:mocks.env.termsVersion,invitation_token:code});
  expect(mocks.signIn).toHaveBeenCalledWith('google',{redirectTo:'/accept-invitation'});
  expect(mocks.env.publicRegistration).toBe(false);
});
it('allows an existing admitted account to renew consent while both registration gates remain closed',async()=>{
  mocks.currentUser.mockResolvedValue({email:'existing@example.test'});
  const form=new FormData();form.set('accept_terms','accepted');
  await signupWithGoogle(form);
  expect(mocks.signIn).toHaveBeenCalledWith('google',{redirectTo:'/settings/workspaces'});
  expect(decodeConsent(mocks.set.mock.calls[0][1],mocks.env.secret)?.invitation_token).toBeUndefined();
});
