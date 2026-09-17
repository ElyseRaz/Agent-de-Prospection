import { apiFetch, apiUpload } from "@/lib/api";

export type ProspectStatus = "new" | "contacted" | "replied" | "converted" | "lost";

export interface Contact {
  id: string;
  email: string;
  full_name: string | null;
  source_note: string;
  created_at: string;
}

export interface Company {
  id: string;
  name: string;
  domain: string | null;
  website_url: string | null;
  status: ProspectStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
  trustpilot_rating: number | null;
  trustpilot_review_count: number | null;
  trustpilot_fetched_at: string | null;
  ai_needs: string[];
  ai_summary: string | null;
  ai_analyzed_at: string | null;
}

export interface CompanyDetail extends Company {
  contacts: Contact[];
}

export interface ListProspectsFilters {
  status?: ProspectStatus;
  search?: string;
}

export interface CreateProspectPayload {
  name: string;
  domain?: string | null;
  website_url?: string | null;
  notes?: string | null;
  contact?: {
    email: string;
    full_name?: string | null;
    source_note: string;
  } | null;
}

export interface UpdateProspectPayload {
  name?: string;
  domain?: string | null;
  website_url?: string | null;
  status?: ProspectStatus;
  notes?: string | null;
}

export interface AddContactPayload {
  email: string;
  full_name?: string | null;
  source_note: string;
}

export interface ImportRowResult {
  row: number;
  status: "imported" | "error";
  message?: string;
}

export interface ImportResponse {
  imported: number;
  skipped: number;
  rows: ImportRowResult[];
}

export function listProspects(filters: ListProspectsFilters = {}): Promise<Company[]> {
  return apiFetch<Company[]>("/prospects", {
    query: { status: filters.status, search: filters.search },
  });
}

export function getProspect(id: string): Promise<CompanyDetail> {
  return apiFetch<CompanyDetail>(`/prospects/${id}`);
}

export function createProspect(payload: CreateProspectPayload): Promise<CompanyDetail> {
  return apiFetch<CompanyDetail>("/prospects", { method: "POST", body: payload });
}

export function updateProspect(id: string, payload: UpdateProspectPayload): Promise<Company> {
  return apiFetch<Company>(`/prospects/${id}`, { method: "PATCH", body: payload });
}

export function deleteProspect(id: string): Promise<void> {
  return apiFetch<void>(`/prospects/${id}`, { method: "DELETE" });
}

export function addContact(companyId: string, payload: AddContactPayload): Promise<Contact> {
  return apiFetch<Contact>(`/prospects/${companyId}/contacts`, { method: "POST", body: payload });
}

export function deleteContact(companyId: string, contactId: string): Promise<void> {
  return apiFetch<void>(`/prospects/${companyId}/contacts/${contactId}`, { method: "DELETE" });
}

export function importProspects(file: File): Promise<ImportResponse> {
  return apiUpload<ImportResponse>("/prospects/import", file);
}

export function enrichProspect(id: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/prospects/${id}/enrich`, { method: "POST" });
}

export interface SettingsStatus {
  trustpilot_configured: boolean;
  groq_configured: boolean;
  smtp_configured: boolean;
  daily_send_limit: number;
}

export function getSettingsStatus(): Promise<SettingsStatus> {
  return apiFetch<SettingsStatus>("/settings/status");
}
