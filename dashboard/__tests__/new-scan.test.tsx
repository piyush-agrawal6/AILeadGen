import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import NewScan from "@/app/scans/new/page";
import { request } from "@/lib/intelligence";
import { Score, ErrorState, Empty } from "@/components/intelligence/common";

const push=vi.hoisted(()=>vi.fn());
vi.mock("next/navigation",()=>({useRouter:()=>({push})}));
vi.mock("@/lib/intelligence",async original=>({...await original<typeof import("@/lib/intelligence")>(),request:vi.fn()}));
vi.mock("sonner",()=>({toast:{success:vi.fn()}}));
const mocked=vi.mocked(request);
const presets=[{country:"United States",country_code:"US",cities:[{id:"miami",display_name:"Miami",lookup_name:"Miami, United States",priority:1},{id:"dallas",display_name:"Dallas",lookup_name:"Dallas, United States",priority:2}]}];

beforeEach(()=>{push.mockClear();mocked.mockReset();mocked.mockImplementation(async path=>{
  if(path==="/markets/presets")return presets;
  if(path==="/verticals")return [{key:"home_services",display_name:"Home Services"},{key:"dentists",display_name:"Dentists"}];
  if(path==="/system/limits")return {max_cities_per_scan:10,max_target_leads:1000,executor:"local"};
  if(path==="/campaigns")return {id:"campaign-test"};
  return {};
});});
function setup(){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><NewScan/></QueryClientProvider>);}

describe("Campaign configuration",()=>{
  it("starts disabled until a city is selected",async()=>{setup();await screen.findByLabelText("Miami");expect(screen.getByRole("button",{name:"Start scan"})).toBeDisabled();});
  it("selects several cities and removes a selected chip",async()=>{setup();fireEvent.click(await screen.findByLabelText("Miami"));fireEvent.click(screen.getByLabelText("Dallas"));expect(screen.getByRole("button",{name:"Remove Miami, United States"})).toBeInTheDocument();fireEvent.click(screen.getByRole("button",{name:"Remove Miami, United States"}));expect(screen.getByLabelText("Miami")).not.toBeChecked();expect(screen.getByLabelText("Dallas")).toBeChecked();});
  it("submits multiple cities, verticals, opportunities and quality",async()=>{setup();fireEvent.click(await screen.findByLabelText("Miami"));fireEvent.click(screen.getByLabelText("Dallas"));fireEvent.click(screen.getByLabelText("Dentists"));fireEvent.click(screen.getByLabelText("High Intent"));fireEvent.change(screen.getByLabelText("Target qualified leads"),{target:{value:"8"}});fireEvent.click(screen.getByRole("button",{name:"Start scan"}));await waitFor(()=>expect(push).toHaveBeenCalledWith("/campaigns/campaign-test"));const call=mocked.mock.calls.find(([path])=>path==="/campaigns");const body=JSON.parse(String(call?.[1]?.body));expect(body.cities).toHaveLength(2);expect(body.verticals).toEqual(["home_services","dentists"]);expect(body.opportunities).toEqual(["WEBSITE","SEO","SECURITY"]);expect(body.quality).toBe("high_intent");expect(body.target).toBe(8);});
  it("supports global custom locations",async()=>{setup();await screen.findByLabelText("Miami");fireEvent.click(screen.getByRole("tab",{name:"Custom Location"}));fireEvent.change(screen.getByLabelText("City, region and country"),{target:{value:"Kyoto, Japan"}});fireEvent.click(screen.getByRole("button",{name:"Add"}));expect(screen.getByRole("button",{name:"Remove Kyoto, Japan"})).toBeInTheDocument();});
  it("shows a server error and permits retry",async()=>{setup();fireEvent.click(await screen.findByLabelText("Miami"));mocked.mockImplementation(async path=>{if(path==="/campaigns")throw new Error("Active campaign limit reached.");return {};});fireEvent.click(screen.getByRole("button",{name:"Start scan"}));expect(await screen.findByRole("alert")).toHaveTextContent("Active campaign limit reached.");expect(screen.getByRole("button",{name:"Start scan"})).not.toBeDisabled();});
  it("renders unassessed scores explicitly",()=>{render(<Score value={null}/>);expect(screen.getByTitle("Not assessed with available evidence")).toHaveTextContent("—");});
  it("renders actionable errors and useful empty states",()=>{const retry=vi.fn();render(<><ErrorState error={new Error("Engine unavailable")} retry={retry}/><Empty title="No matching leads" detail="Clear a filter to widen this search."/></>);fireEvent.click(screen.getByRole("button",{name:"Try again"}));expect(retry).toHaveBeenCalled();expect(screen.getByText("Clear a filter to widen this search.")).toBeInTheDocument();});
});
