"use client";
// Selectively adapted from intent-radar-preview/components/ui.tsx. No standalone shell or demo identity.
import {cloneElement,isValidElement,useId,useRef,type ReactElement,type ReactNode} from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import {Radar,X,AlertCircle,type LucideIcon} from 'lucide-react';
export function Badge({children}:{children:ReactNode}){return <span className="ir-badge">{children}</span>}
export function PageHeading({title,description,actions,badge}:{title:string;description:string;actions?:ReactNode;badge?:ReactNode}){return <header className="ir-heading"><div><div className="ir-heading-title"><h1>{title}</h1>{badge}</div><p>{description}</p></div>{actions&&<div className="ir-actions">{actions}</div>}</header>}
export function Field({label,children,hint}:{label:string;children:ReactNode;hint?:string}){const id=useId();const input=isValidElement(children)?cloneElement(children as ReactElement<{'aria-labelledby'?:string;'aria-describedby'?:string}>,{'aria-labelledby':id,'aria-describedby':hint?id+'-hint':undefined}):children;return <label className="ir-field"><span id={id}>{label}</span>{input}{hint&&<small id={id+'-hint'}>{hint}</small>}</label>}
export function EmptyState({title='No signals in this view',description='Try a broader filter or run a public-source search.',action,icon:Icon=Radar}:{title?:string;description?:string;action?:ReactNode;icon?:LucideIcon}){return <section className="ir-empty"><div className="ir-empty-icon"><Icon size={25} aria-hidden="true"/></div><div><h2>{title}</h2><p>{description}</p>{action&&<div className="ir-actions">{action}</div>}</div></section>}
export function LoadingSkeleton() {
  return (
    <div role="status" className="w-full space-y-4 animate-pulse">
      {/* Header Skeleton */}
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div className="space-y-2">
          <div className="h-6 w-48 rounded bg-muted/60" />
          <div className="h-3.5 w-72 rounded bg-muted/40" />
        </div>
        <div className="h-8 w-28 rounded-lg bg-muted/50" />
      </div>

      {/* Metrics Row Skeleton */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="rounded-xl border border-border bg-card p-3.5 space-y-2">
            <div className="h-3 w-24 rounded bg-muted/50" />
            <div className="h-6 w-12 rounded bg-muted/70" />
          </div>
        ))}
      </div>

      {/* Table Skeleton */}
      <div className="overflow-x-auto rounded-xl border border-border bg-card shadow-xs">
        <div className="h-10 border-b border-border bg-muted/30 px-4 flex items-center gap-4">
          <div className="h-3 w-32 rounded bg-muted/60" />
          <div className="h-3 w-20 rounded bg-muted/50" />
          <div className="h-3 w-24 rounded bg-muted/50 ml-auto" />
        </div>
        <div className="divide-y divide-border">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-14 px-4 flex items-center justify-between gap-4">
              <div className="space-y-1.5 flex-1">
                <div className="h-3.5 w-48 rounded bg-muted/60" />
                <div className="h-2.5 w-32 rounded bg-muted/40" />
              </div>
              <div className="h-3 w-20 rounded bg-muted/50" />
              <div className="h-6 w-16 rounded bg-muted/50" />
            </div>
          ))}
        </div>
      </div>
      <span className="sr-only">Loading workspace intelligence…</span>
    </div>
  );
}
export function ErrorState({message,retry}:{message:string;retry?:()=>void}){return <div className="ir-notice ir-error" role="alert"><AlertCircle size={20} aria-hidden="true"/><div><strong>We couldn’t complete that request</strong><p>{message}</p>{retry&&<button onClick={retry}>Try again</button>}</div></div>}
export function Modal({open,onOpenChange,title,description,children,drawer=false}:{drawer?:boolean;open:boolean;onOpenChange:(v:boolean)=>void;title:string;description:string;children:ReactNode}){const focus=useRef<HTMLElement|null>(null);return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal><Dialog.Overlay className="ir-overlay"/><Dialog.Content className={"ir ir-modal"+(drawer?" pb-evidence-drawer":"")} onOpenAutoFocus={()=>{focus.current=document.activeElement as HTMLElement}} onCloseAutoFocus={event=>{event.preventDefault();focus.current?.focus()}}><header><Dialog.Title>{title}</Dialog.Title><Dialog.Close aria-label="Close dialog"><X size={17}/></Dialog.Close></header><Dialog.Description>{description}</Dialog.Description>{children}</Dialog.Content></Dialog.Portal></Dialog.Root>}
