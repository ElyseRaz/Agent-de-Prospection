"use client";

import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Stars02, Star01, Trash01, X } from "@untitledui/icons";
import { toast } from "sonner";

import { Button } from "@/components/base/buttons/button";
import { ButtonUtility } from "@/components/base/buttons/button-utility";
import { Badge } from "@/components/base/badges/badges";
import { Dialog, Modal, ModalOverlay } from "@/components/application/modals/modal";
import { NativeSelect } from "@/components/base/select/select-native";
import { FormInput } from "@/components/forms/form-input";
import { FormTextArea } from "@/components/forms/form-textarea";
import { LoadingIndicator } from "@/components/application/loading-indicator/loading-indicator";
import { STATUS_OPTIONS } from "@/components/prospects/status-badge";
import {
  editProspectSchema,
  addContactSchema,
  type EditProspectFormValues,
  type AddContactFormValues,
} from "@/lib/schemas";
import {
  useProspect,
  useUpdateProspect,
  useDeleteProspect,
  useAddContact,
  useDeleteContact,
  useEnrichProspect,
} from "@/hooks/use-prospects";
import { ApiError } from "@/lib/api";

const MAX_POLL_DURATION_MS = 30_000;

interface ProspectDetailDialogProps {
  id: string | null;
  onOpenChange: (open: boolean) => void;
}

export function ProspectDetailDialog({ id, onOpenChange }: ProspectDetailDialogProps) {
  const [isPolling, setIsPolling] = useState(false);
  const { data: prospect, isLoading } = useProspect(id, { poll: isPolling });
  const updateProspect = useUpdateProspect(id ?? "");
  const deleteProspect = useDeleteProspect();
  const addContact = useAddContact(id ?? "");
  const deleteContact = useDeleteContact(id ?? "");
  const enrichProspect = useEnrichProspect(id ?? "");
  const [showAddContact, setShowAddContact] = useState(false);
  const enrichSnapshotRef = useRef<string | null>(null);

  useEffect(() => {
    if (!isPolling || !prospect) return;
    if (enrichSnapshotRef.current && prospect.updated_at !== enrichSnapshotRef.current) {
      setIsPolling(false);
      toast.success("Enrichissement termine");
    }
  }, [isPolling, prospect]);

  const handleEnrich = async () => {
    if (!prospect) return;
    enrichSnapshotRef.current = prospect.updated_at;
    try {
      await enrichProspect.mutateAsync();
      setIsPolling(true);
      toast.info("Enrichissement lance (Trustpilot + analyse IA du site)");
      setTimeout(() => setIsPolling(false), MAX_POLL_DURATION_MS);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Erreur lors du lancement de l'enrichissement");
    }
  };

  const {
    register,
    control,
    handleSubmit,
    reset,
  } = useForm<EditProspectFormValues>({ resolver: zodResolver(editProspectSchema) });

  useEffect(() => {
    if (prospect) {
      reset({
        name: prospect.name,
        domain: prospect.domain ?? "",
        websiteUrl: prospect.website_url ?? "",
        status: prospect.status,
        notes: prospect.notes ?? "",
      });
    }
  }, [prospect, reset]);

  const {
    control: contactControl,
    handleSubmit: handleSubmitContact,
    reset: resetContact,
  } = useForm<AddContactFormValues>({ resolver: zodResolver(addContactSchema) });

  const onSubmit = async (values: EditProspectFormValues) => {
    try {
      await updateProspect.mutateAsync({
        name: values.name,
        domain: values.domain || null,
        website_url: values.websiteUrl || null,
        status: values.status,
        notes: values.notes || null,
      });
      toast.success("Prospect mis a jour");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Erreur lors de la mise a jour");
    }
  };

  const onAddContact = async (values: AddContactFormValues) => {
    try {
      await addContact.mutateAsync({
        email: values.email,
        full_name: values.fullName || null,
        source_note: values.sourceNote,
      });
      toast.success("Contact ajoute");
      resetContact();
      setShowAddContact(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Erreur lors de l'ajout du contact");
    }
  };

  const handleDelete = async () => {
    if (!id) return;
    if (!window.confirm("Supprimer definitivement ce prospect et ses contacts ?")) return;
    try {
      await deleteProspect.mutateAsync(id);
      toast.success("Prospect supprime");
      onOpenChange(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Erreur lors de la suppression");
    }
  };

  return (
    <ModalOverlay isOpen={Boolean(id)} onOpenChange={onOpenChange}>
      <Modal className="w-full sm:max-w-lg">
        <Dialog className="relative max-h-[inherit] w-full overflow-y-auto p-6 outline-hidden">
          {({ close }) => (
            <>
              <ButtonUtility
                size="sm"
                color="tertiary"
                icon={X}
                tooltip="Fermer"
                onClick={close}
                className="absolute top-4 right-4"
              />
              <h2 className="text-lg font-semibold text-primary">{prospect?.name ?? "Prospect"}</h2>

              {isLoading || !prospect ? (
            <div className="flex justify-center py-8">
              <LoadingIndicator size="sm" />
            </div>
          ) : (
            <>
              <form onSubmit={handleSubmit(onSubmit)} className="mt-5 flex flex-col gap-4">
                <div className="grid grid-cols-2 gap-4">
                  <FormInput className="col-span-2" control={control} name="name" label="Nom" />
                  <FormInput control={control} name="domain" label="Domaine" />
                  <FormInput control={control} name="websiteUrl" label="Site web" />
                  <div className="col-span-2">
                    <NativeSelect label="Statut" options={STATUS_OPTIONS} {...register("status")} />
                  </div>
                  <FormTextArea className="col-span-2" control={control} name="notes" label="Notes" rows={3} />
                </div>
                <div className="flex justify-between">
                  <Button
                    type="button"
                    color="secondary-destructive"
                    iconLeading={Trash01}
                    isLoading={deleteProspect.isPending}
                    onClick={handleDelete}
                  >
                    Supprimer
                  </Button>
                  <Button type="submit" isLoading={updateProspect.isPending}>
                    Enregistrer
                  </Button>
                </div>
              </form>

              <hr className="my-5 border-secondary" />

              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-secondary">Enrichissement</p>
                  <Button
                    size="sm"
                    color="secondary"
                    iconLeading={Stars02}
                    isLoading={enrichProspect.isPending || isPolling}
                    onClick={handleEnrich}
                  >
                    {isPolling ? "Enrichissement en cours..." : "Enrichir"}
                  </Button>
                </div>

                {(prospect.trustpilot_fetched_at || prospect.ai_analyzed_at) && (
                  <div className="flex flex-col gap-2 rounded-md bg-secondary p-2.5 text-sm">
                    {prospect.trustpilot_fetched_at && (
                      <div className="flex items-center gap-2">
                        <Star01 className="size-4 text-warning-primary" />
                        {prospect.trustpilot_rating !== null ? (
                          <span className="text-secondary">
                            Trustpilot : <strong>{prospect.trustpilot_rating.toFixed(1)}/5</strong>
                            {prospect.trustpilot_review_count !== null &&
                              ` (${prospect.trustpilot_review_count} avis)`}
                          </span>
                        ) : (
                          <span className="text-tertiary">Trustpilot : entreprise non trouvee</span>
                        )}
                      </div>
                    )}
                    {prospect.ai_analyzed_at && (
                      <div className="flex flex-col gap-1.5">
                        {prospect.ai_needs.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {prospect.ai_needs.map((need) => (
                              <Badge key={need} color="blue">
                                {need}
                              </Badge>
                            ))}
                          </div>
                        ) : (
                          <span className="text-tertiary">Aucun besoin specifique detecte par l&apos;IA</span>
                        )}
                        {prospect.ai_summary && <p className="text-xs text-tertiary">{prospect.ai_summary}</p>}
                      </div>
                    )}
                  </div>
                )}
                {!prospect.trustpilot_fetched_at && !prospect.ai_analyzed_at && !isPolling && (
                  <p className="text-xs text-tertiary">
                    Pas encore enrichi. Necessite un domaine (Trustpilot) et/ou un site web (analyse
                    IA) renseignes ci-dessus.
                  </p>
                )}
              </div>

              <hr className="my-5 border-secondary" />

              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-secondary">Contacts</p>
                  <Button size="sm" color="tertiary" iconLeading={Plus} onClick={() => setShowAddContact((v) => !v)}>
                    Ajouter
                  </Button>
                </div>

                {prospect.contacts.length === 0 && (
                  <p className="text-sm text-tertiary">Aucun contact pour l&apos;instant.</p>
                )}

                <ul className="flex flex-col gap-2">
                  {prospect.contacts.map((contact) => (
                    <li
                      key={contact.id}
                      className="flex items-start justify-between rounded-md bg-secondary p-2.5 text-sm"
                    >
                      <div>
                        <p className="font-medium text-secondary">{contact.email}</p>
                        {contact.full_name && <p className="text-xs text-tertiary">{contact.full_name}</p>}
                        <p className="mt-1 text-xs text-tertiary">{contact.source_note}</p>
                      </div>
                      <ButtonUtility
                        size="xs"
                        color="tertiary"
                        icon={Trash01}
                        tooltip="Supprimer"
                        onClick={async () => {
                          try {
                            await deleteContact.mutateAsync(contact.id);
                          } catch (error) {
                            toast.error(error instanceof ApiError ? error.message : "Erreur lors de la suppression");
                          }
                        }}
                      />
                    </li>
                  ))}
                </ul>

                {showAddContact && (
                  <form
                    onSubmit={handleSubmitContact(onAddContact)}
                    className="flex flex-col gap-3 rounded-md bg-secondary p-3"
                  >
                    <div className="grid grid-cols-2 gap-3">
                      <FormInput control={contactControl} name="email" label="Email" type="email" />
                      <FormInput control={contactControl} name="fullName" label="Nom" />
                      <FormTextArea
                        className="col-span-2"
                        control={contactControl}
                        name="sourceNote"
                        label="Origine du contact"
                        rows={2}
                      />
                    </div>
                    <Button type="submit" size="sm" isLoading={addContact.isPending} className="self-end">
                      Ajouter le contact
                    </Button>
                  </form>
                )}
              </div>
                </>
              )}
            </>
          )}
        </Dialog>
      </Modal>
    </ModalOverlay>
  );
}
