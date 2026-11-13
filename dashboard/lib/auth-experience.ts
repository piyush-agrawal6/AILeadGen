export const authPages=["/login","/signup","/forgot-password","/reset-password","/verify-email","/accept-invitation"] as const;
export function isAuthPage(path:string){return (authPages as readonly string[]).includes(path);}
export function isPublicPage(path:string){return isAuthPage(path)||["/terms","/privacy","/start"].includes(path);}
/** Only fixed messages are displayed; never echo provider text or query tokens. */
export function authenticationError(code:string|undefined):string|null{
 if(!code)return null;
 if(code==='AccessDenied')return 'This account couldn’t access your workspace. Try the Google account connected to your workspace, or ask your workspace administrator for help.';
 if(code==='OAuthAccountNotLinked')return 'Use the same sign-in method you originally used for this account.';
 if(code==='Configuration')return 'Sign-in is temporarily unavailable. Please try again later.';
 return 'We couldn’t complete sign-in. Please try again. Your workspace hasn’t been changed.';
}
