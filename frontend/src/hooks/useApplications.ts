import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createApplication,
  deleteApplication,
  getApplication,
  listApplications,
  updateApplication,
  updateApplicationStage,
} from "../api/applications";
import type { ApplicationStage, ApplicationUpdatePayload } from "../api/types";

export function useApplications(profileId: string | null) {
  return useQuery({
    queryKey: ["applications", profileId],
    queryFn: () => listApplications(profileId as string),
    enabled: Boolean(profileId),
  });
}

export function useApplication(profileId: string | null, applicationId: string | null) {
  return useQuery({
    queryKey: ["applications", profileId, applicationId],
    queryFn: () => getApplication(profileId as string, applicationId as string),
    enabled: Boolean(profileId) && Boolean(applicationId),
  });
}

export function useCreateApplication(profileId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => createApplication(profileId, jobId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["applications", profileId] }),
  });
}

export function useUpdateApplicationStage(profileId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ applicationId, stage }: { applicationId: string; stage: ApplicationStage }) =>
      updateApplicationStage(profileId, applicationId, stage),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["applications", profileId] });
      queryClient.invalidateQueries({
        queryKey: ["applications", profileId, variables.applicationId],
      });
    },
  });
}

export function useUpdateApplication(profileId: string, applicationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ApplicationUpdatePayload) =>
      updateApplication(profileId, applicationId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications", profileId] });
      queryClient.invalidateQueries({ queryKey: ["applications", profileId, applicationId] });
    },
  });
}

export function useDeleteApplication(profileId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (applicationId: string) => deleteApplication(profileId, applicationId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["applications", profileId] }),
  });
}
