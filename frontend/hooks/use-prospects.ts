import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addContact,
  createProspect,
  deleteContact,
  deleteProspect,
  getProspect,
  importProspects,
  listProspects,
  updateProspect,
  type AddContactPayload,
  type CreateProspectPayload,
  type ListProspectsFilters,
  type UpdateProspectPayload,
} from "@/lib/prospects-api";

const prospectsKey = (filters: ListProspectsFilters) => ["prospects", filters] as const;
const prospectKey = (id: string) => ["prospects", "detail", id] as const;

export function useProspects(filters: ListProspectsFilters) {
  return useQuery({
    queryKey: prospectsKey(filters),
    queryFn: () => listProspects(filters),
  });
}

export function useProspect(id: string | null) {
  return useQuery({
    queryKey: prospectKey(id ?? ""),
    queryFn: () => getProspect(id as string),
    enabled: Boolean(id),
  });
}

export function useCreateProspect() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateProspectPayload) => createProspect(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["prospects"] }),
  });
}

export function useUpdateProspect(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: UpdateProspectPayload) => updateProspect(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prospects"] });
      queryClient.invalidateQueries({ queryKey: prospectKey(id) });
    },
  });
}

export function useDeleteProspect() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteProspect(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["prospects"] }),
  });
}

export function useAddContact(companyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AddContactPayload) => addContact(companyId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: prospectKey(companyId) }),
  });
}

export function useDeleteContact(companyId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (contactId: string) => deleteContact(companyId, contactId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: prospectKey(companyId) }),
  });
}

export function useImportProspects() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => importProspects(file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["prospects"] }),
  });
}
