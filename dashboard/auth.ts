import { googleAccountAllowed } from "@/lib/auth-policy";
import { serverEnv } from "@/lib/server/env";
import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import {admitGoogle} from "@/lib/server/admission";
export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [Google({authorization:{params:{prompt:'select_account'}}})],
  pages: { signIn: "/login", error: "/login" },
  session: { strategy: "jwt", maxAge: 8 * 60 * 60 },
  trustHost: true,
  useSecureCookies: serverEnv().production,
  callbacks: {
    async signIn({ profile,user,account }) {
      if(googleAccountAllowed(profile,serverEnv().allowed))return true;
      if(account?.provider!=="google"||profile?.email_verified!==true||typeof profile.email!=="string"||typeof profile.sub!=="string"||user.email?.toLowerCase()!==profile.email.toLowerCase())return false;
      const admitted=await admitGoogle({email:profile.email,sub:profile.sub,email_verified:profile.email_verified,name:typeof profile.name==="string"?profile.name:undefined});
      if(admitted)(user as typeof user & {planeByteAdmitted?:boolean}).planeByteAdmitted=true;
      return admitted;
    },
    jwt({token,user}){
      if(user)token.planeByteAdmitted=(user as typeof user & {planeByteAdmitted?:boolean}).planeByteAdmitted===true;
      return token;
    },
    session({ session,token }) {
      if (session.user?.email) session.user.email = session.user.email.toLowerCase();
      if(session.user)(session.user as typeof session.user & {planeByteAdmitted?:boolean}).planeByteAdmitted=token.planeByteAdmitted===true;
      return session;
    },
  },
});
