import { describe,it,expect } from "vitest";
import { sameOrigin } from "@/lib/origin-policy";
describe("BFF origin authorization",()=>{
  it("accepts the actual browser host even when Next uses an internal origin",()=>expect(sameOrigin("http://127.0.0.1:13000","127.0.0.1:13000",false)).toBe(true));
  it("rejects cross-origin writes",()=>expect(sameOrigin("https://attacker.example","leadengine.example",true)).toBe(false));
  it("requires HTTPS for hosted writes",()=>expect(sameOrigin("http://leadengine.example","leadengine.example",true)).toBe(false));
  it("rejects missing and malformed origins",()=>{expect(sameOrigin(null,"leadengine.example",true)).toBe(false);expect(sameOrigin("null","leadengine.example",true)).toBe(false);});
});
