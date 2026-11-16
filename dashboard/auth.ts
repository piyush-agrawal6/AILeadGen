import { googleAccountAllowed, isWorkEmail } from "@/lib/auth-policy";
import { serverEnv } from "@/lib/server/env";
import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import Credentials from "next-auth/providers/credentials";
import {accountRequest} from "@/lib/server/account-broker";
import {admitGoogle} from "@/lib/server/admission";
export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [Google({authorization:{params:{prompt:'select_account'}}}),...(serverEnv().accounts?[Credentials({credentials:{email:{},password:{},ticket:{}},async authorize(input){
      const email=typeof input.email==='string'?input.email.trim().toLowerCase():'';
      if(!isWorkEmail(email))return null;
      const exchange=typeof input.ticket==='string'&&input.ticket.length===43;
      if(!exchange&&(typeof input.password!=='string'||input.password.length>128))return null;
      const result=await accountRequest(exchange?'exchange':'login',email,exchange?{token:input.ticket}:{email,password:input.password});
      if(!result.ok||!result.data.session_token||result.data.email!==email)return null;
      return {id:email,email,name:result.data.name,planeByteAdmitted:true,planeByteSession:result.data.session_token};
    }})]:[])],
  pages: { signIn: "/login", error: "/login" },
  session: { strategy: "jwt", maxAge: 8 * 60 * 60 },
  trustHost: true,
  useSecureCookies: serverEnv().production,
  events:{async signOut(message){
    if('token' in message&&message.token&&typeof message.token.email==='string'&&typeof message.token.planeByteSession==='string'){
      await accountRequest('logout',message.token.email,{},message.token.planeByteSession);
    }
  }},
  callbacks: {
    async signIn({ profile,user,account }) {
      if(account?.provider==='credentials')return (user as typeof user & {planeByteAdmitted?:boolean}).planeByteAdmitted===true;
      if(typeof profile?.email==='string'&&!isWorkEmail(profile.email))return '/login?error=work_email_required';
      if(!serverEnv().accounts&&googleAccountAllowed(profile,serverEnv().allowed))return true;
      if(account?.provider!=="google"||profile?.email_verified!==true||typeof profile.email!=="string"||typeof profile.sub!=="string"||user.email?.toLowerCase()!==profile.email.toLowerCase())return false;
      const admitted=await admitGoogle({email:profile.email,sub:profile.sub,email_verified:profile.email_verified,name:typeof profile.name==="string"?profile.name:undefined});
      if(admitted){
        const value=user as typeof user & {planeByteAdmitted?:boolean;planeByteSession?:string};
        value.planeByteAdmitted=true;
        if(typeof admitted==='object')value.planeByteSession=admitted.session_token;
      }
      return Boolean(admitted);
    },
    jwt({token,user}){
      if(typeof token.email==='string'&&!isWorkEmail(token.email))return null;
      if(user)token.planeByteSession=(user as typeof user & {planeByteSession?:string}).planeByteSession;
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
