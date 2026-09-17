import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createCampaign,
  createTemplate,
  deleteCampaign,
  deleteTemplate,
  getCampaign,
  listCampaigns,
  listTemplates,
  sendCampaign,
  updateTemplate,
  type CreateCampaignPayload,
  type CreateTemplatePayload,
  type UpdateTemplatePayload,
} from "@/lib/campaigns-api";

const campaignKey = (id: string) => ["campaigns", "detail", id] as const;

export function useCampaigns() {
  return useQuery({
    queryKey: ["campaigns"],
    queryFn: listCampaigns,
  });
}

export function useCampaign(id: string | null, options: { poll?: boolean } = {}) {
  return useQuery({
    queryKey: campaignKey(id ?? ""),
    queryFn: () => getCampaign(id as string),
    enabled: Boolean(id),
    // Une campagne "sending" avance via le worker Asynq en tache de fond -
    // on reinterroge le detail toutes les 2s le temps que ca se termine.
    refetchInterval: options.poll ? 2000 : false,
  });
}

export function useCreateCampaign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateCampaignPayload) => createCampaign(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["campaigns"] }),
  });
}

export function useDeleteCampaign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteCampaign(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["campaigns"] }),
  });
}

export function useSendCampaign(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => sendCampaign(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      queryClient.invalidateQueries({ queryKey: campaignKey(id) });
    },
  });
}

export function useTemplates() {
  return useQuery({
    queryKey: ["templates"],
    queryFn: listTemplates,
  });
}

export function useCreateTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateTemplatePayload) => createTemplate(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["templates"] }),
  });
}

export function useUpdateTemplate(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: UpdateTemplatePayload) => updateTemplate(id, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["templates"] }),
  });
}

export function useDeleteTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteTemplate(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["templates"] }),
  });
}
