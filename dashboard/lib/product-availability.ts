/** Availability never grants a workspace entitlement. All legacy pages remain. */
export const leadEngineEnabled=(value:unknown):boolean=>value==='true';
const leadPages=['/lead-engine','/find-leads','/leads','/master-leads','/contacts','/enrichment','/lists','/tasks','/campaigns','/outreach','/schedules','/scans','/discovery','/runs','/automation','/assistant','/recommendations','/reports','/experiments','/system','/acquisition',
 '/settings/acquisition','/settings/scanning','/settings/preferences','/settings/limits','/settings/email','/settings/templates','/settings/markets','/settings/foundation','/settings/system','/settings/integrations'];
export const isLeadEnginePage=(path:string):boolean=>{let normalized=path;try{normalized=decodeURIComponent(path)}catch{/* Next rejects malformed paths. */}return leadPages.some(prefix=>normalized===prefix||normalized.startsWith(prefix+'/'))};
