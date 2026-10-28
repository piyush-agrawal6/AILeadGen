"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Plus, X } from "lucide-react";
import { toast } from "sonner";
import { request, label, type Country, type Campaign, type CampaignConfig, type Opportunity } from "@/lib/intelligence";
import { PageHeading, Loading, ErrorState } from "@/components/intelligence/common";
import { Button } from "@/components/ui/button";

export default function NewScanPage() {
  const router = useRouter();
  const [mode, setMode] = useState("Recommended Markets");
  const [country, setCountry] = useState("US");
  const [search, setSearch] = useState("");
  const [custom, setCustom] = useState("");
  const [cities, setCities] = useState<string[]>([]);
  const [verticals, setVerticals] = useState(["home_services"]);
  const [opportunities, setOpportunities] = useState<Opportunity[]>(["WEBSITE", "SEO", "SECURITY"]);
  const [social,setSocial]=useState(true); const [activity,setActivity]=useState(true);
  const [scales, setScales] = useState(["LOCAL", "SMALL_GROUP", "MID_MARKET"]);
  const [quality, setQuality] = useState<CampaignConfig["quality"]>("balanced");
  const [results, setResults] = useState<CampaignConfig["results"]>("new");
  const [target, setTarget] = useState(250);
  const [lighthouse, setLighthouse] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const presets = useQuery({ queryKey: ["market-presets"], queryFn: () => request<Country[]>("/markets/presets") });
  const definitions = useQuery({ queryKey: ["verticals"], queryFn: () => request<{key:string;display_name:string}[]>("/verticals") });
  const limits = useQuery({ queryKey: ["limits"], queryFn: () => request<{max_cities_per_scan:number;max_target_leads:number;executor:string}>("/system/limits") });
  const cityList = presets.data?.find(c => c.country_code === country)?.cities || [];
  const toggle = (values: string[], value: string, setter: (next: string[]) => void) => setter(values.includes(value) ? values.filter(v => v !== value) : [...values, value]);
  const count = cities.length * verticals.length;
  const maxCities = limits.data?.max_cities_per_scan ?? 10;
  const maxTarget = limits.data?.max_target_leads ?? 1000;
  const addCities = (next: string[]) => setCities(current => [...new Set([...current, ...next])].slice(0, maxCities));
  const start = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!count || !opportunities.length || !scales.length || target < Math.max(5,count) || target > maxTarget) { setError("Choose locations, verticals and opportunities, then set a target covering every child scan."); return; }
    setBusy(true); setError("");
    try {
      const config: CampaignConfig = { cities, verticals, opportunities, quality, business_scales: scales, results, target, lighthouse_enabled: lighthouse, social_enrichment_enabled:social, social_activity_enabled:social&&activity, request_id: crypto.randomUUID() };
      if (new URLSearchParams(window.location.search).get("fixture") === "true") config.fixture = true;
      const campaign = await request<Campaign>("/campaigns", { method: "POST", body: JSON.stringify(config) });
      toast.success("Campaign started"); router.push("/campaigns/" + campaign.id);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not start this campaign."); setBusy(false); }
  };
  return <div className="mx-auto max-w-6xl">
    <PageHeading eyebrow="Discovery / New campaign" title="Find your next opportunity" description="Choose a focused market. Turn public business evidence into a shortlist."/>
    {presets.isLoading || definitions.isLoading ? <Loading/> : presets.error || definitions.error ? <ErrorState error={presets.error || definitions.error} retry={() => {presets.refetch();definitions.refetch();}}/> :
    <form onSubmit={start} className="grid gap-9 lg:grid-cols-[minmax(0,1fr)_280px]">
      <div className="min-w-0 space-y-8">
        <section className="space-y-4 border-t pt-5"><div className="flex justify-between"><h2 className="text-sm font-semibold">01 <span className="ml-3">Locations</span></h2><span className="text-xs text-muted-foreground">{cities.length} / {maxCities} cities</span></div>
          <div role="tablist" aria-label="Location mode" className="inline-flex flex-wrap gap-1 rounded-md bg-muted p-1">{["Recommended Markets","Custom Location"].map(item => <button type="button" role="tab" aria-selected={mode===item} key={item} onClick={() => setMode(item)} className={"rounded px-3 py-2 text-xs " + (mode===item ? "bg-card text-foreground" : "text-muted-foreground")}>{item}</button>)}</div>
          {mode === "Custom Location" ? <div><label htmlFor="custom-location" className="field-label">City, region and country</label><div className="flex gap-2"><input id="custom-location" className="control flex-1" value={custom} onChange={e=>setCustom(e.target.value)} placeholder="e.g. Kyoto, Japan"/><Button type="button" variant="outline" disabled={custom.trim().length<2 || cities.length>=maxCities} onClick={()=>{addCities([custom.trim()]);setCustom("");}}><Plus className="mr-2 h-3 w-3"/>Add</Button></div><p className="mt-2 text-xs text-muted-foreground">Custom locations resolve globally. Describe one city or bounded area per entry.</p></div> :
          <><div className="grid gap-3 sm:grid-cols-2"><label className="field-label">Country<select className="control mt-2 w-full" value={country} onChange={e=>{setCountry(e.target.value);setSearch("");}}>{presets.data?.map(c=><option key={c.country_code} value={c.country_code}>{c.country}</option>)}</select></label><label className="field-label">Find a city<input className="control mt-2 w-full" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search curated cities"/></label></div>
          <div className="flex flex-wrap gap-4 text-xs"><button type="button" className="text-primary" onClick={()=>addCities(cityList.slice(0,3).map(c=>c.lookup_name))}>Select Recommended</button><button type="button" onClick={()=>addCities(cityList.map(c=>c.lookup_name))}>Select All</button><button type="button" className="text-muted-foreground" onClick={()=>setCities([])}>Clear</button></div>
          <div className="grid max-h-56 grid-cols-2 gap-x-4 gap-y-2 overflow-y-auto sm:grid-cols-3">{cityList.filter(c=>c.display_name.toLowerCase().includes(search.toLowerCase())).map(city=><label key={city.id} data-selected={cities.includes(city.lookup_name)} className="scan-choice flex cursor-pointer items-center gap-2 rounded-md border border-transparent px-2 py-2 text-xs"><input type="checkbox" checked={cities.includes(city.lookup_name)} disabled={!cities.includes(city.lookup_name) && cities.length>=maxCities} onChange={()=>toggle(cities,city.lookup_name,setCities)}/><span className="choice-label">{city.display_name}</span></label>)}</div></>}
          {cities.length>0 && <div className="flex flex-wrap gap-2 border-t pt-3" aria-label="Selected cities">{cities.map(city=><button key={city} type="button" className="inline-flex items-center gap-2 rounded border bg-card px-2 py-1 text-xs" aria-label={"Remove "+city} onClick={()=>setCities(cities.filter(c=>c!==city))}>{city.split(",")[0]}<X className="h-3 w-3"/></button>)}</div>}
        </section>
        <section className="space-y-4 border-t pt-5"><h2 className="text-sm font-semibold">02 <span className="ml-3">Verticals</span></h2><div className="grid gap-2 sm:grid-cols-2">{definitions.data?.filter(v=>v.key!=="restaurant").map(v=><label key={v.key} data-selected={verticals.includes(v.key)} className={"scan-choice flex cursor-pointer items-center gap-3 rounded-md border px-3 py-3 text-sm "+(verticals.includes(v.key)?"border-primary/40 bg-primary/5":"")}><input type="checkbox" checked={verticals.includes(v.key)} onChange={()=>toggle(verticals,v.key,setVerticals)}/>{v.display_name}</label>)}</div><details className="text-xs text-muted-foreground"><summary className="cursor-pointer">Legacy verticals</summary><label className="mt-3 flex items-center gap-2"><input type="checkbox" checked={verticals.includes("restaurant")} onChange={()=>toggle(verticals,"restaurant",setVerticals)}/>Restaurants & Bars</label></details></section>
        <section className="space-y-4 border-t pt-5"><h2 className="text-sm font-semibold">03 <span className="ml-3">Opportunity types</span></h2><div className="grid gap-2 sm:grid-cols-3">{(["WEBSITE","SEO","SECURITY"] as Opportunity[]).map((kind,i)=><label key={kind} data-selected={opportunities.includes(kind)} className={"opportunity-choice opportunity-"+kind.toLowerCase()+" flex cursor-pointer items-center gap-2 rounded-md border px-3 py-3 text-sm"}><input type="checkbox" checked={opportunities.includes(kind)} onChange={()=>setOpportunities(opportunities.includes(kind)?opportunities.filter(k=>k!==kind):[...opportunities,kind])}/>{["Website / Redesign","SEO","Basic Security"][i]}</label>)}</div><p className="text-xs text-muted-foreground">One shared crawl. Passive external evidence. Higher scores mean stronger opportunities.</p></section>
        <section className="grid gap-5 border-t pt-5 sm:grid-cols-2"><div><h2 className="mb-4 text-sm font-semibold">Business size</h2><div className="space-y-2">{["LOCAL","SMALL_GROUP","MID_MARKET","REGIONAL"].map(value=><label className="scan-choice flex items-center gap-2 rounded border border-transparent px-2 py-2 text-sm" data-selected={scales.includes(value)} key={value}><input type="checkbox" checked={scales.includes(value)} onChange={()=>toggle(scales,value,setScales)}/>{label(value)}</label>)}</div></div><div><h2 className="mb-4 text-sm font-semibold">Lead quality</h2><div className="space-y-2">{["maximum_volume","balanced","high_intent"].map(value=><label className="scan-choice flex items-center gap-2 rounded border border-transparent px-2 py-2 text-sm" data-selected={quality===value} key={value}><input type="radio" name="quality" checked={quality===value} onChange={()=>setQuality(value as CampaignConfig["quality"])}/>{label(value)}</label>)}</div></div></section>
        <section className="grid gap-5 border-t pt-5 sm:grid-cols-2"><label className="field-label">Results<select className="control mt-2 w-full" value={results} onChange={e=>setResults(e.target.value as CampaignConfig["results"])}><option value="new">New Leads Only</option><option value="include_previous">New + Previously Seen</option><option value="all">All</option></select></label><label className="field-label">Target qualified leads<input className="control mt-2 w-full" type="number" min={Math.max(5,count)} max={maxTarget} value={target} onChange={e=>setTarget(Number(e.target.value))}/></label></section>
        <details className="border-t pt-4 text-xs text-muted-foreground"><summary className="cursor-pointer">Advanced settings</summary><label className="my-4 flex items-center gap-2"><input type="checkbox" checked={lighthouse} onChange={e=>setLighthouse(e.target.checked)}/>Run bounded Lighthouse performance audits</label><label className="my-4 flex items-center gap-2"><input type="checkbox" checked={social} onChange={e=>setSocial(e.target.checked)}/>Discover public business social profiles</label><label className="my-4 flex items-center gap-2"><input type="checkbox" checked={activity} disabled={!social} onChange={e=>setActivity(e.target.checked)}/>Check verifiable public activity (bounded; unavailable stays Unknown)</label><div className="flex gap-4">{["ENTERPRISE","KNOWN_CHAIN"].map(value=><label key={value} className="flex items-center gap-2"><input type="checkbox" checked={scales.includes(value)} onChange={()=>toggle(scales,value,setScales)}/>Include {label(value)}</label>)}</div></details>
      </div>
      <aside className="self-start lg:sticky lg:top-0"><div className="rounded-md border bg-card p-5"><p className="text-[10px] font-semibold uppercase tracking-[.16em] text-muted-foreground">Campaign preview</p><p className="my-5 text-4xl font-semibold tracking-tight tabular-nums">{count}<span className="ml-2 text-sm font-normal text-muted-foreground">child scans</span></p><dl className="space-y-3 text-sm">{[["Cities",cities.length],["Verticals",verticals.length],["Analyzers",opportunities.length],["Quality",label(quality)],["Business size",scales.map(label).join(" + ")],["Execution",limits.data?.executor==="gcp"?"Cloud worker":"Local worker"]].map(([key,value])=><div className="flex justify-between gap-4" key={key}><dt className="text-muted-foreground">{key}</dt><dd className="max-w-40 text-right">{value}</dd></div>)}</dl><div className="my-5 border-t pt-4"><p className="text-xs text-muted-foreground">Campaign target</p><p className="mt-1 text-xl font-semibold tabular-nums">{target.toLocaleString()} <span className="text-xs font-normal text-muted-foreground">qualified leads</span></p><p className="mt-2 text-xs leading-5 text-muted-foreground">Divided across city × vertical combinations. Qualified results depend on public evidence.</p></div>{error && <p role="alert" className="mb-3 text-xs text-destructive">{error}</p>}<Button type="submit" className="w-full gap-2" disabled={busy || !count || !opportunities.length}><ArrowRight className="h-4 w-4"/>{busy?"Starting campaign…":"Start scan"}</Button></div><p className="mt-3 text-[11px] leading-5 text-muted-foreground">Overture Maps + OpenStreetMap. Workload limits are enforced by the server.</p></aside>
    </form>}
  </div>;
}

