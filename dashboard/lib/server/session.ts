import { auth } from "@/auth";
import "server-only";
import {privateSession} from "./private-session";
import {accountRequest} from "./account-broker";
import {cache} from "react";
import { serverEnv } from "./env";
import {isWorkEmail} from '@/lib/auth-policy';
export const currentUser=cache(async function currentUser() {
  const env = serverEnv();
  if (!env.production && process.env.AUTH_DISABLED_LOCAL === "true") return { email: env.allowed[0] || "local@localhost", name: "Local development" };
  const session = await auth();
  if(session?.user?.email&&!isWorkEmail(session.user.email))return null;
  const admitted=(session?.user as {planeByteAdmitted?:boolean}|undefined)?.planeByteAdmitted===true;
  if(env.accounts){
    if(!env.customerAccess||!admitted||!session?.user?.email)return null;
    const capability=await privateSession();if(!capability)return null;
    const result=await accountRequest('session',session.user.email.toLowerCase(),{},capability);
    if(!result.ok)return null;
    if(result.data.requires_terms)return {...session.user,requiresTerms:true};
  }
  return session?.user?.email && (env.accounts?env.customerAccess&&admitted:env.allowed.includes(session.user.email.toLowerCase())||env.customerAccess&&admitted) ? session.user : null;
});
