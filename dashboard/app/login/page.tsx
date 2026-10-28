import Image from "next/image";
import { signIn } from "@/auth";
export default function Login() {
  return <div className="grid min-h-[80vh] place-items-center"><section className="w-full max-w-sm space-y-8 px-6">
    <div className="space-y-3"><Image className="mb-10 rounded-lg" src="/logo.png" width={44} height={44} alt="PlaneByte"/><p className="text-xs uppercase tracking-[.18em] text-muted-foreground">PlaneByte · Private workspace</p><h1 className="text-3xl font-semibold tracking-tight">PlaneByte</h1><p className="text-sm leading-6 text-muted-foreground">Your next conversation starts with better intelligence.</p></div>
    <form action={async () => { "use server"; await signIn("google", { redirectTo: "/" }); }}><button className="w-full rounded-md border border-primary bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground hover:opacity-90">Sign in with Google <span aria-hidden="true">↗</span></button></form>
    <p className="text-xs leading-5 text-muted-foreground">PlaneByte internal lead intelligence.<br/>Access is limited to approved Google accounts.</p>
  </section></div>;
}
