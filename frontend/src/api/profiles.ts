import { apiFetch } from "./client";
import type {
  MatchListResponse,
  Profile,
  ProfileCreatePayload,
  ProfileDetail,
  ProfileSkillInput,
  ProfileUpdatePayload,
} from "./types";

export function listProfiles(): Promise<Profile[]> {
  return apiFetch<Profile[]>("/profiles");
}

export function getProfile(profileId: string): Promise<ProfileDetail> {
  return apiFetch<ProfileDetail>(`/profiles/${profileId}`);
}

export function createProfile(payload: ProfileCreatePayload): Promise<Profile> {
  return apiFetch<Profile>("/profiles", { method: "POST", body: payload });
}

export function updateProfile(profileId: string, payload: ProfileUpdatePayload): Promise<Profile> {
  return apiFetch<Profile>(`/profiles/${profileId}`, { method: "PATCH", body: payload });
}

export function deleteProfile(profileId: string): Promise<void> {
  return apiFetch<void>(`/profiles/${profileId}`, { method: "DELETE" });
}

export function setProfileSkills(
  profileId: string,
  skills: ProfileSkillInput[],
): Promise<ProfileDetail> {
  return apiFetch<ProfileDetail>(`/profiles/${profileId}/skills`, {
    method: "PUT",
    body: skills,
  });
}

export function getProfileMatches(profileId: string, limit = 20): Promise<MatchListResponse> {
  return apiFetch<MatchListResponse>(`/profiles/${profileId}/matches`, { query: { limit } });
}

export function sendMatchFeedback(
  profileId: string,
  jobId: string,
  action: "saved" | "rejected",
): Promise<void> {
  return apiFetch<void>(`/profiles/${profileId}/matches/${jobId}/feedback`, {
    method: "POST",
    body: { action },
  });
}
