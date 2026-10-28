import { act,fireEvent,render,screen,waitFor } from "@testing-library/react";
import { QueryClient,QueryClientProvider } from "@tanstack/react-query";
import { describe,it,expect,vi,beforeEach } from "vitest";
import { LeadFiltersPanel } from "@/components/intelligence/lead-filters";
import { StatusSelect } from "@/components/intelligence/status-select";
import { ReportAction } from "@/components/intelligence/report-action";
import { scoreTone,STATUS_STYLES } from "@/lib/lead-display";
import { request,type LeadPage } from "@/lib/intelligence";
vi.mock("@/lib/intelligence",async original=>({...await original<typeof import("@/lib/intelligence")>(),request:vi.fn()}));
vi.mock("sonner",()=>({toast:{success:vi.fn(),error:vi.fn()}}));
function filters(){const onApply=vi.fn();render(<LeadFiltersPanel value={{}} onApply={onApply} countries={[]} verticals={[]} campaigns={[]}/>);const trigger=screen.getByRole("button",{name:/More filters/});fireEvent.click(trigger);return {trigger,onApply};}
function withQuery(component:React.ReactNode){const client=new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}});render(<QueryClientProvider client={client}>{component}</QueryClientProvider>);return client;}
beforeEach(()=>{vi.mocked(request).mockReset();});
describe("Filter dialog",()=>{
 it("has an obvious close action and restores focus",async()=>{const {trigger}=filters();expect(screen.getByRole("dialog",{name:"Filters"})).toBeVisible();fireEvent.click(screen.getByRole("button",{name:"Close filters"}));await waitFor(()=>expect(screen.queryByRole("dialog")).not.toBeInTheDocument());await waitFor(()=>expect(trigger).toHaveFocus());});
 it("closes on Escape",async()=>{filters();fireEvent.keyDown(document,{key:"Escape"});await waitFor(()=>expect(screen.queryByRole("dialog")).not.toBeInTheDocument());});
 it("keeps internal edits local until Apply",async()=>{const {onApply}=filters();fireEvent.change(screen.getByLabelText("City"),{target:{value:"Denver"}});expect(screen.getByRole("dialog")).toBeVisible();expect(onApply).not.toHaveBeenCalled();fireEvent.click(screen.getByRole("button",{name:"Apply filters"}));expect(onApply).toHaveBeenCalledWith({city:"Denver",page:"1"});});
 it("closes on an outside click",async()=>{filters();await act(()=>new Promise(resolve=>setTimeout(resolve,1)));fireEvent.click(document.querySelector(".filter-overlay")!);await waitFor(()=>expect(screen.queryByRole("dialog")).not.toBeInTheDocument());});
});
describe("Semantic inline workflow",()=>{
 it("includes Lost and labels the editable status",()=>{withQuery(<StatusSelect id={1} value="LOST" name="Example Dental"/>);expect(screen.getByRole("combobox",{name:"Lead status for Example Dental"})).toHaveValue("LOST");expect(screen.getByRole("option",{name:"Do Not Contact"})).toBeInTheDocument();expect(STATUS_STYLES.LOST).toBe("status-lost");});
 it("rolls back only the affected record on failure",async()=>{let reject!:(reason:Error)=>void;vi.mocked(request).mockImplementation(()=>new Promise((_resolve,fail)=>{reject=fail;}));const client=withQuery(<StatusSelect id={1} value="NEW" name="Example"/>);client.setQueryData(["intelligence-leads",""],{items:[{id:1,lead_status:"NEW"},{id:2,lead_status:"WON"}]} as LeadPage);fireEvent.change(screen.getByRole("combobox"),{target:{value:"CONTACTED"}});await waitFor(()=>expect(screen.getByRole("combobox")).toHaveValue("CONTACTED"));await act(async()=>reject(new Error("Temporary failure")));await waitFor(()=>expect(screen.getByRole("combobox")).toHaveValue("NEW"));expect(client.getQueryData<LeadPage>(["intelligence-leads",""])?.items.map(row=>row.lead_status)).toEqual(["NEW","WON"]);});
 it("uses opportunity meaning at all score boundaries",()=>{expect([null,0,39,40,59,60,79,80,100].map(scoreTone)).toEqual(["score-unassessed","score-low","score-low","score-moderate","score-moderate","score-good","score-good","score-strong","score-strong"]);});
});
describe("Client PDF actions",()=>{
 it("switches from generate to protected PDF download",async()=>{vi.mocked(request).mockImplementation(async(path)=>({id:"report-one",status:path.includes("pdf-reports")?"QUEUED":"READY",version:1}));withQuery(<ReportAction id={1} name="Example"/>);fireEvent.click(screen.getByRole("button",{name:"Generate PDF"}));await waitFor(()=>expect(screen.getByRole("link",{name:"Download PDF"})).toHaveAttribute("href","/api/client-reports/report-one/download"));});
 it("shows a retry after generation fails",async()=>{vi.mocked(request).mockRejectedValue(new Error("Internal exception must not appear"));withQuery(<ReportAction id={1} name="Example"/>);fireEvent.click(screen.getByRole("button",{name:"Generate PDF"}));await waitFor(()=>expect(screen.getByRole("button",{name:"Try again"})).toBeEnabled());expect(screen.getByRole("alert")).toHaveTextContent("Report generation failed. Try again.");expect(screen.queryByText("Internal exception must not appear")).not.toBeInTheDocument();});
});
