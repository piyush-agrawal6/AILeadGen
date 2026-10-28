import { googleAccountAllowed } from "@/lib/auth-policy";
import { serverEnv } from "@/lib/server/env";
import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [Google],
  pages: { signIn: "/login", error: "/login" },
  session: { strategy: "jwt", maxAge: 8 * 60 * 60 },
  trustHost: true,
  useSecureCookies: serverEnv().production,
  callbacks: {
    signIn({ profile }) {
      return googleAccountAllowed(profile, serverEnv().allowed);
    },
    session({ session }) {
      if (session.user?.email) session.user.email = session.user.email.toLowerCase();
      return session;
    },
  },
});
