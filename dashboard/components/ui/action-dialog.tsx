"use client";
import * as Dialog from '@radix-ui/react-dialog';
import {X} from 'lucide-react';
import {Button} from './button';
export function ActionDialog({trigger,title,description,children,open,onOpenChange,busy=false}:{trigger:string;title:string;description:string;children:React.ReactNode;open:boolean;onOpenChange:(open:boolean)=>void;busy?:boolean}){
 return <Dialog.Root open={open} onOpenChange={value=>{if(!busy)onOpenChange(value)}}><Dialog.Trigger asChild><Button>{trigger}</Button></Dialog.Trigger><Dialog.Portal><Dialog.Overlay className="fixed inset-0 z-50 bg-slate-950/30 backdrop-blur-[2px]"/><Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[90dvh] w-[calc(100%-2rem)] max-w-2xl -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl border bg-background p-5 shadow-2xl sm:p-7"><Dialog.Title className="pr-10 text-xl font-semibold">{title}</Dialog.Title><Dialog.Description className="mt-2 pr-6 text-sm leading-relaxed text-muted-foreground">{description}</Dialog.Description><Dialog.Close asChild><button className="absolute right-4 top-4 rounded-lg p-2 text-muted-foreground hover:bg-muted" aria-label={'Close '+title.toLowerCase()} disabled={busy}><X size={19}/></button></Dialog.Close><div className="mt-6">{children}</div></Dialog.Content></Dialog.Portal></Dialog.Root>;
}
