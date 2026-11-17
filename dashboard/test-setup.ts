import "@testing-library/jest-dom/vitest";
import {vi} from 'vitest';
// jsdom omits this standard browser API used by the approved motion styling.
if(typeof window.matchMedia!=='function')Object.defineProperty(window,'matchMedia',{writable:true,value:(query:string)=>({matches:false,media:query,onchange:null,addListener:vi.fn(),removeListener:vi.fn(),addEventListener:vi.fn(),removeEventListener:vi.fn(),dispatchEvent:()=>true})});
