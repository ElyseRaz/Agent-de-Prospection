import { apiFetch } from "./client";
import type {
  Application,
  ApplicationDetail,
  ApplicationStage,
  ApplicationUpdatePayload,
} from "./types";

export function listApplications(profileId: string): Promise<Application[]> {
  return apiFetch<Application[]>(`/profiles/${profileId}/applications`);
}

export function getApplication(profileId: string, applicationId: string): Promise<ApplicationDetail> {
  return apiFetch<ApplicationDetail>(`/profiles/${profileId}/applications/${applicationId}`);
}

export function createApplication(profileId: string, jobId: string): Promise<Application> {
  return apiFetch<Application>(`/profiles/${profileId}/applications`, {
    method: "POST",
    body: { job_id: jobId },
  });
}

export function updateApplicationStage(
  profileId: string,
  applicationId: string,
  stage: ApplicationStage,
): Promise<Application> {
  return apiFetch<Application>(`/profiles/${profileId}/applications/${applicationId}/stage`, {
    method: "PATCH",
    body: { stage },
  });
}

export function updateApplication(
  profileId: string,
  applicationId: string,
  payload: ApplicationUpdatePayload,
): Promise<Application> {
  return apiFetch<Application>(`/profiles/${profileId}/applications/${applicationId}`, {
    method: "PATCH",
    body: payload,
  });
}

export function deleteApplication(profileId: string, applicationId: string): Promise<void> {
  return apiFetch<void>(`/profiles/${profileId}/applications/${applicationId}`, {
    method: "DELETE",
  });
}
