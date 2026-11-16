import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {describe,it,expect,vi} from 'vitest';
import {AccountForm} from '@/components/auth/account-form';
describe('account forms',()=>{
 it('keeps password labels and help text separately accessible',()=>{
  render(<AccountForm action={async()=>({error:null})} kind="signup" requestId="fixture-request"/>);
  const password=screen.getByLabelText('Password',{exact:true});
  expect(password).toHaveAttribute('type','password');expect(password).toHaveAccessibleDescription('Use a unique passphrase of 15–128 characters.');
  expect(screen.getByLabelText('Company email')).toHaveAttribute('type','email');
 });
 it('disables duplicate OTP submission and displays a safe error',async()=>{
  let finish!:(value:{error:string|null})=>void;
  const submit=vi.fn(()=>new Promise<{error:string|null}>(resolve=>{finish=resolve}));
  render(<AccountForm action={submit} kind="verify"/>);fireEvent.change(screen.getByLabelText('Verification code'),{target:{value:'123456'}});fireEvent.click(screen.getByRole('button'));
  await waitFor(()=>expect(screen.getByRole('button')).toBeDisabled());finish({error:'The code is incorrect or expired.'});expect(await screen.findByRole('alert')).toHaveTextContent('incorrect or expired');expect(submit).toHaveBeenCalledTimes(1);
 });
});
