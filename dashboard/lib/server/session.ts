import { auth } from "@/auth";
import "server-only";
import {privateSession} from "./private-session";
import {accountRequest} from "./account-broker";
import {cache} from "react";
import { serverEnv } from "./env";
export const currentUser=cache(async function currentUser() {
  const env = serverEnv();
  if (!env.production && process.env.AUTH_DISABLED_LOCAL === "true") return { email: env.allowed[0] || "local@localhost", name: "Local development" };
  const session = await auth();
  const admitted=(session?.user as {planeByteAdmitted?:boolean}|undefined)?.planeByteAdmitted===true;
  if(env.accounts&&env.customerAccess&&admitted&&session?.user?.email&&!env.allowed.includes(session.user.email.toLowerCase())){
    const capability=await privateSession();if(!capability)return null;
    const result=await accountRequest('session',session.user.email.toLowerCase(),{},capability);
    if(!result.ok)return null;
    if(result.data.requires_terms)return {...session.user,requiresTerms:true};
  }
  return session?.user?.email && (env.allowed.includes(session.user.email.toLowerCase())||env.customerAccess&&admitted) ? session.user : null;
});
