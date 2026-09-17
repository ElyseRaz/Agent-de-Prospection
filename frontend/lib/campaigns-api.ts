import { apiFetch } from "@/lib/api";

export type CampaignStatus = "draft" | "sending" | "sent";
export type RecipientStatus = "pending" | "sent" | "failed" | "unsubscribed";

export interface Template {
  id: string;
  name: string;
  subject: string;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface Campaign {
  id: string;
  name: string;
  subject: string;
  body: string;
  status: CampaignStatus;
  created_at: string;
  updated_at: string;
  sent_at: string | null;
}

export interface Recipient {
  id: string;
  contact_email: string;
  contact_name: string | null;
  company_name: string;
  status: RecipientStatus;
  error_message: string | null;
  sent_at: string | null;
}

export interface CampaignDetail extends Campaign {
  recipients: Recipient[];
  summary: Partial<Record<RecipientStatus, number>>;
}

export interface CreateTemplatePayload {
  name: string;
  subject: string;
  body: string;
}

export interface UpdateTemplatePayload {
  name?: string;
  subject?: string;
  body?: string;
}

export interface CreateCampaignPayload {
  name: string;
  subject: string;
  body: string;
  company_ids: string[];
}

export function listTemplates(): Promise<Template[]> {
  return apiFetch<Template[]>("/templates");
}

export function createTemplate(payload: CreateTemplatePayload): Promise<Template> {
  return apiFetch<Template>("/templates", { method: "POST", body: payload });
}

export function updateTemplate(id: string, payload: UpdateTemplatePayload): Promise<Template> {
  return apiFetch<Template>(`/templates/${id}`, { method: "PATCH", body: payload });
}

export function deleteTemplate(id: string): Promise<void> {
  return apiFetch<void>(`/templates/${id}`, { method: "DELETE" });
}

export function listCampaigns(): Promise<Campaign[]> {
  return apiFetch<Campaign[]>("/campaigns");
}

export function getCampaign(id: string): Promise<CampaignDetail> {
  return apiFetch<CampaignDetail>(`/campaigns/${id}`);
}

export function createCampaign(payload: CreateCampaignPayload): Promise<Campaign> {
  return apiFetch<Campaign>("/campaigns", { method: "POST", body: payload });
}

export function deleteCampaign(id: string): Promise<void> {
  return apiFetch<void>(`/campaigns/${id}`, { method: "DELETE" });
}

export function sendCampaign(id: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/campaigns/${id}/send`, { method: "POST" });
}
