import type { LeadStatus } from "@/lib/intelligence";
export const STATUS_STYLES:Record<LeadStatus,string>={READY_TO_CONTACT:"status-shortlisted",FOLLOW_UP:"status-contacted",MEETING:"status-replied",PROPOSAL:"status-replied",NEW:"status-new",SHORTLISTED:"status-shortlisted",CONTACTED:"status-contacted",REPLIED:"status-replied",NOT_INTERESTED:"status-muted",DO_NOT_CONTACT:"status-danger",WON:"status-won",LOST:"status-lost"};
export function scoreTone(value:number|null|undefined){return value==null?"score-unassessed":value<40?"score-low":value<60?"score-moderate":value<80?"score-good":"score-strong";}
export function safeWebsite(value?:string|null){try{const url=new URL(value||"");return ["https:","http:"].includes(url.protocol)&&!url.username&&!url.password?url.href:null;}catch{return null;}}
export function emailHref(value?:string|null){return value&&/^[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+$/.test(value)?"mailto:"+value:null;}
export function phoneHref(value?:string|null){const clean=value?.replace(/[^+\d]/g,"");return clean&&/\d{7}/.test(clean)?"tel:"+clean:null;}
