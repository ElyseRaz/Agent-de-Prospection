import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createProfile,
  deleteProfile,
  getProfile,
  getProfileMatches,
  listProfiles,
  sendMatchFeedback,
  setProfileSkills,
  updateProfile,
} from "../api/profiles";
import type { ProfileCreatePayload, ProfileSkillInput, ProfileUpdatePayload } from "../api/types";

export function useProfiles() {
  return useQuery({ queryKey: ["profiles"], queryFn: listProfiles });
}

export function useProfile(profileId: string | null) {
  return useQuery({
    queryKey: ["profiles", profileId],
    queryFn: () => getProfile(profileId as string),
    enabled: Boolean(profileId),
  });
}

export function useCreateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProfileCreatePayload) => createProfile(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profiles"] }),
  });
}

export function useUpdateProfile(profileId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProfileUpdatePayload) => updateProfile(profileId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profiles"] });
      queryClient.invalidateQueries({ queryKey: ["profiles", profileId] });
    },
  });
}

export function useDeleteProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (profileId: string) => deleteProfile(profileId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profiles"] }),
  });
}

export function useSetProfileSkills(profileId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (skills: ProfileSkillInput[]) => setProfileSkills(profileId, skills),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profiles", profileId] });
      queryClient.invalidateQueries({ queryKey: ["profiles", profileId, "matches"] });
    },
  });
}

export function useProfileMatches(profileId: string | null, limit = 20) {
  return useQuery({
    queryKey: ["profiles", profileId, "matches", limit],
    queryFn: () => getProfileMatches(profileId as string, limit),
    enabled: Boolean(profileId),
  });
}

export function useMatchFeedback(profileId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ jobId, action }: { jobId: string; action: "saved" | "rejected" }) =>
      sendMatchFeedback(profileId, jobId, action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profiles", profileId, "matches"] });
    },
  });
}
