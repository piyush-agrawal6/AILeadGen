import {describe,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {authenticationError,isPublicPage} from '@/lib/auth-experience';
import {GoogleForm} from '@/components/auth/google-form';
import {AuthFrame} from '@/components/auth/auth-frame';
import {googleAccountAllowed} from '@/lib/auth-policy';
describe('PlaneByte authentication experience',()=>{
 it('opens only the exact supported public pages',()=>{
  for(const route of ['/login','/signup','/forgot-password','/reset-password','/verify-email','/accept-invitation','/terms','/privacy'])expect(isPublicPage(route)).toBe(true);
  for(const route of ['/signup/private','/api/users','/api/authentication','/settings','/leads','/accept-invitation/admin'])expect(isPublicPage(route)).toBe(false);
 });
 it('shows safe errors and never echoes arbitrary provider text',()=>{
  expect(authenticationError(undefined)).toBeNull();expect(authenticationError('AccessDenied')).toMatch(/workspace/);
  expect(authenticationError('<script>secret-token</script>')).not.toContain('secret-token');
  expect(googleAccountAllowed({email:'outside@example.com',email_verified:true},['owner@example.com'])).toBe(false);
 });
 it('uses PlaneByte branding and real product capabilities without legacy wording',()=>{
  render(<AuthFrame><h2>Welcome back</h2></AuthFrame>);
  expect(screen.getByRole('heading',{name:'Welcome back'})).toBeTruthy();expect(screen.getAllByText(/Discover relevant/).length).toBeGreaterThan(0);
  expect(screen.getByRole('link',{name:'Privacy Policy'}).getAttribute('href')).toBe('/privacy');expect(screen.getAllByText('PlaneByte')).toHaveLength(2);expect(screen.queryByText(/HeySow/)).toBeNull();
 });
 it('prevents duplicate submissions while connecting and shows server errors',async()=>{
  let finish!:(value:{error:string|null})=>void;
  const action=vi.fn(()=>new Promise<{error:string|null}>(resolve=>{finish=resolve}));render(<GoogleForm action={action}/>);
  fireEvent.click(screen.getByRole('button',{name:/Continue with Google/}));
  await waitFor(()=>expect(screen.getByRole('button',{name:/Connecting to Google/}).hasAttribute('disabled')).toBe(true));
  finish({error:'We couldn’t connect to Google. Please try again.'});
  expect(await screen.findByRole('alert')).toHaveTextContent('Please try again');expect(action).toHaveBeenCalledTimes(1);
 });
});
