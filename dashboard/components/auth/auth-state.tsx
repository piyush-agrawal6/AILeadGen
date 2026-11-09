import Link from 'next/link';
import {ArrowLeft} from 'lucide-react';
import {AuthFrame} from './auth-frame';
export function AuthState({eyebrow,title,description,children}:{eyebrow:string;title:string;description:string;children?:React.ReactNode}){return <AuthFrame><section className="auth-form-content auth-state"><p className="auth-form-eyebrow">{eyebrow}</p><h2>{title}</h2><p className="auth-form-subtitle">{description}</p>{children}<Link className="auth-back" href="/login"><ArrowLeft size={15}/>Back to sign in</Link></section></AuthFrame>;}
