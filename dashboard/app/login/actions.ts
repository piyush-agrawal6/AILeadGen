"use server";
import {AuthError} from 'next-auth';
import {signIn} from '@/auth';
export async function googleSignIn():Promise<{error:string|null}>{try{await signIn('google',{redirectTo:'/'});}catch(error){if(error instanceof AuthError)return {error:'We couldn’t connect to Google. Please try again.'};throw error;}return {error:null};}
