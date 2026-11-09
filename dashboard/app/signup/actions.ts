"use server";
import {cookies} from "next/headers";
import {redirect} from "next/navigation";
import {randomUUID} from "node:crypto";
import {signIn} from "@/auth";
import {serverEnv} from "@/lib/server/env";
import {currentUser} from "@/lib/server/session";
import {encodeConsent,signupCookie} from "@/lib/server/admission";

export async function signupWithGoogle(form:FormData){
   const env=serverEnv();
   const existing=env.customerAccess?await currentUser():null;
   if(!(env.publicRegistration||env.invitedRegistration||existing)||!env.customerAccess||!env.termsVersion||env.secret.length<32)redirect("/signup?error=registration_unavailable");
   if(form.get("accept_terms")!=="accepted")redirect("/signup?error=terms_required");
   const code=String(form.get("invitation_token")||"").trim();
   if((!env.publicRegistration&&!existing&&!code)||(code&&!/^[A-Za-z0-9_-]{40,100}$/.test(code)))redirect("/signup?error=invitation_required");
   const ticket=encodeConsent({version:env.termsVersion,accepted_at:Math.floor(Date.now()/1000),nonce:randomUUID(),...(code?{invitation_token:code}:{})},env.secret);
  (await cookies()).set(signupCookie,ticket,{httpOnly:true,secure:env.production,sameSite:"lax",path:"/",maxAge:600});
   await signIn("google",{redirectTo:code?"/accept-invitation":"/settings/workspaces"});
}
