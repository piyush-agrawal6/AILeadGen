import type {
AppSettingsSchema,
DashboardResponse,
LeadDetailResponse,
LeadPaginationResponse,
MarketItem,
PipelineEventSchema,
PipelineRunDetail,
ReportArtifactItem,
ScanCreateRequest,
ScanCreateResponse,
SystemDoctorResponse,
VerticalItem,
} from "@/types/api";

const getBaseUrl = (): string => {
  if (typeof window !== "undefined") {
    return "";
  }
  return "";
};

async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const base = getBaseUrl();
  const url = endpoint.startsWith("http") ? endpoint : `${base}${endpoint}`;

  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    let errorMsg = `API error ${res.status}: ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        errorMsg = errJson.detail;
      }
    } catch {}
    throw new Error(errorMsg);
  }

  return res.json() as Promise<T>;
}

// Dashboard
export async function getDashboard(): Promise<DashboardResponse> {
  return apiFetch<DashboardResponse>("/api/dashboard");
}

// Markets & Verticals
export async function getMarkets(): Promise<MarketItem[]> {
  return apiFetch<MarketItem[]>("/api/markets");
}

export async function getVerticals(): Promise<VerticalItem[]> {
  return apiFetch<VerticalItem[]>("/api/verticals");
}

// Scans
export async function getScans(params?: {
  status?: string;
  vertical?: string;
  page?: number;
  page_size?: number;
}): Promise<PipelineRunDetail[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.vertical) searchParams.set("vertical", params.vertical);
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));

  const qs = searchParams.toString();
  return apiFetch<PipelineRunDetail[]>(`/api/scans${qs ? `?${qs}` : ""}`);
}

export async function createScan(data: ScanCreateRequest): Promise<ScanCreateResponse> {
  return apiFetch<ScanCreateResponse>("/api/scans", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getScan(id: number): Promise<PipelineRunDetail> {
  return apiFetch<PipelineRunDetail>(`/api/scans/${id}`);
}

export async function cancelScan(id: number): Promise<{ success: boolean; message: string }> {
  return apiFetch<{ success: boolean; message: string }>(`/api/scans/${id}/cancel`, {
    method: "POST",
  });
}

export async function resumeScan(id: number): Promise<{ success: boolean; message: string }> {
  return apiFetch<{ success: boolean; message: string }>(`/api/scans/${id}/resume`, {
    method: "POST",
  });
}

export async function getScanEvents(id: number, afterId?: number): Promise<PipelineEventSchema[]> {
  const qs = afterId ? `?after_id=${afterId}` : "";
  return apiFetch<PipelineEventSchema[]>(`/api/scans/${id}/events${qs}`);
}

// Leads
export interface LeadSearchParams {
  search?: string;
  tier?: string;
  min_score?: number;
  vertical?: string;
  country?: string;
  state?: string;
  city?: string;
  website_status?: string;
  has_email?: boolean;
  has_phone?: boolean;
  has_form?: boolean;
  recommended_service?: string;
  min_perf?: number;
  max_perf?: number;
  min_seo?: number;
  max_seo?: number;
  source?: string;
  quality_status?: string;
  run_id?: number;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_dir?: string;
}

export async function getLeads(params: LeadSearchParams = {}): Promise<LeadPaginationResponse> {
  const searchParams = new URLSearchParams();
  for (const [key, val] of Object.entries(params)) {
    if (val !== undefined && val !== null && val !== "") {
      searchParams.set(key, String(val));
    }
  }
  const qs = searchParams.toString();
  return apiFetch<LeadPaginationResponse>(`/api/leads${qs ? `?${qs}` : ""}`);
}

export async function getLead(id: number): Promise<LeadDetailResponse> {
  return apiFetch<LeadDetailResponse>(`/api/leads/${id}`);
}

export async function generateLeadReport(id: number): Promise<{
  success: boolean;
  message: string;
  report_file: string;
  download_url: string;
}> {
  return apiFetch<{
    success: boolean;
    message: string;
    report_file: string;
    download_url: string;
  }>(`/api/leads/${id}/report`, {
    method: "POST",
  });
}

// Reports
export async function getReports(): Promise<ReportArtifactItem[]> {
  return apiFetch<ReportArtifactItem[]>("/api/reports");
}

// Settings
export async function getSettings(): Promise<AppSettingsSchema> {
  return apiFetch<AppSettingsSchema>("/api/settings");
}

export async function updateSettings(data: AppSettingsSchema): Promise<AppSettingsSchema> {
  return apiFetch<AppSettingsSchema>("/api/settings", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// System
export async function getDoctor(): Promise<SystemDoctorResponse> {
  return apiFetch<SystemDoctorResponse>("/api/system/doctor");
}

export async function rerunDoctor(): Promise<SystemDoctorResponse> {
  return apiFetch<SystemDoctorResponse>("/api/system/doctor", {
    method: "POST",
  });
}
