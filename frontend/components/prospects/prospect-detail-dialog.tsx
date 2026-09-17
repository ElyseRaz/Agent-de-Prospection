"use client";

import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Trash2, Plus, Sparkles, Star } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
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

  // Le job d'enrichissement est asynchrone (Asynq) : on reinterroge la
  // fiche jusqu'a ce que `updated_at` change par rapport a l'instant du
  // declenchement, avec un plafond de securite si le worker ne repond pas.
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
    handleSubmit,
    reset,
    formState: { errors },
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
    register: registerContact,
    handleSubmit: handleSubmitContact,
    reset: resetContact,
    formState: { errors: contactErrors },
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
    <Dialog open={Boolean(id)} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{prospect?.name ?? "Prospect"}</DialogTitle>
        </DialogHeader>

        {isLoading || !prospect ? (
          <div className="flex justify-center py-8">
            <Loader2 className="size-5 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2 flex flex-col gap-1.5">
                  <Label htmlFor="edit-name">Nom</Label>
                  <Input id="edit-name" {...register("name")} />
                  {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="edit-domain">Domaine</Label>
                  <Input id="edit-domain" {...register("domain")} />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="edit-website">Site web</Label>
                  <Input id="edit-website" {...register("websiteUrl")} />
                  {errors.websiteUrl && (
                    <p className="text-sm text-destructive">{errors.websiteUrl.message}</p>
                  )}
                </div>
                <div className="col-span-2 flex flex-col gap-1.5">
                  <Label htmlFor="edit-status">Statut</Label>
                  <select
                    id="edit-status"
                    {...register("status")}
                    className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                  >
                    {STATUS_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-span-2 flex flex-col gap-1.5">
                  <Label htmlFor="edit-notes">Notes</Label>
                  <Textarea id="edit-notes" rows={3} {...register("notes")} />
                </div>
              </div>
              <DialogFooter className="justify-between sm:justify-between">
                <Button
                  type="button"
                  variant="destructive"
                  onClick={handleDelete}
                  disabled={deleteProspect.isPending}
                >
                  <Trash2 className="size-4" />
                  Supprimer
                </Button>
                <Button type="submit" disabled={updateProspect.isPending}>
                  {updateProspect.isPending ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    "Enregistrer"
                  )}
                </Button>
              </DialogFooter>
            </form>

            <Separator />

            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">Enrichissement</p>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleEnrich}
                  disabled={enrichProspect.isPending || isPolling}
                >
                  {enrichProspect.isPending || isPolling ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Sparkles className="size-4" />
                  )}
                  {isPolling ? "Enrichissement en cours..." : "Enrichir"}
                </Button>
              </div>

              {(prospect.trustpilot_fetched_at || prospect.ai_analyzed_at) && (
                <div className="flex flex-col gap-2 rounded-md border p-2.5 text-sm">
                  {prospect.trustpilot_fetched_at && (
                    <div className="flex items-center gap-2">
                      <Star className="size-4 text-amber-500" />
                      {prospect.trustpilot_rating !== null ? (
                        <span>
                          Trustpilot : <strong>{prospect.trustpilot_rating.toFixed(1)}/5</strong>
                          {prospect.trustpilot_review_count !== null &&
                            ` (${prospect.trustpilot_review_count} avis)`}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">
                          Trustpilot : entreprise non trouvee
                        </span>
                      )}
                    </div>
                  )}
                  {prospect.ai_analyzed_at && (
                    <div className="flex flex-col gap-1.5">
                      {prospect.ai_needs.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {prospect.ai_needs.map((need) => (
                            <Badge key={need} variant="secondary">
                              {need}
                            </Badge>
                          ))}
                        </div>
                      ) : (
                        <span className="text-muted-foreground">
                          Aucun besoin specifique detecte par l&apos;IA
                        </span>
                      )}
                      {prospect.ai_summary && (
                        <p className="text-xs text-muted-foreground">{prospect.ai_summary}</p>
                      )}
                    </div>
                  )}
                </div>
              )}
              {!prospect.trustpilot_fetched_at && !prospect.ai_analyzed_at && !isPolling && (
                <p className="text-xs text-muted-foreground">
                  Pas encore enrichi. Necessite un domaine (Trustpilot) et/ou un site web (analyse
                  IA) renseignes ci-dessus.
                </p>
              )}
            </div>

            <Separator />

            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">Contacts</p>
                <Button size="sm" variant="ghost" onClick={() => setShowAddContact((v) => !v)}>
                  <Plus className="size-4" />
                  Ajouter
                </Button>
              </div>

              {prospect.contacts.length === 0 && (
                <p className="text-sm text-muted-foreground">Aucun contact pour l&apos;instant.</p>
              )}

              <ul className="flex flex-col gap-2">
                {prospect.contacts.map((contact) => (
                  <li
                    key={contact.id}
                    className="flex items-start justify-between rounded-md border p-2.5 text-sm"
                  >
                    <div>
                      <p className="font-medium">{contact.email}</p>
                      {contact.full_name && (
                        <p className="text-xs text-muted-foreground">{contact.full_name}</p>
                      )}
                      <p className="mt-1 text-xs text-muted-foreground">{contact.source_note}</p>
                    </div>
                    <Button
                      size="icon-sm"
                      variant="ghost"
                      onClick={async () => {
                        try {
                          await deleteContact.mutateAsync(contact.id);
                        } catch (error) {
                          toast.error(
                            error instanceof ApiError ? error.message : "Erreur lors de la suppression",
                          );
                        }
                      }}
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  </li>
                ))}
              </ul>

              {showAddContact && (
                <form
                  onSubmit={handleSubmitContact(onAddContact)}
                  className="flex flex-col gap-2 rounded-md border p-3"
                >
                  <div className="grid grid-cols-2 gap-2">
                    <div className="flex flex-col gap-1">
                      <Label htmlFor="contact-email" className="text-xs">
                        Email
                      </Label>
                      <Input id="contact-email" type="email" {...registerContact("email")} />
                      {contactErrors.email && (
                        <p className="text-xs text-destructive">{contactErrors.email.message}</p>
                      )}
                    </div>
                    <div className="flex flex-col gap-1">
                      <Label htmlFor="contact-fullname" className="text-xs">
                        Nom
                      </Label>
                      <Input id="contact-fullname" {...registerContact("fullName")} />
                    </div>
                  </div>
                  <div className="flex flex-col gap-1">
                    <Label htmlFor="contact-source" className="text-xs">
                      Origine du contact
                    </Label>
                    <Textarea id="contact-source" rows={2} {...registerContact("sourceNote")} />
                    {contactErrors.sourceNote && (
                      <p className="text-xs text-destructive">{contactErrors.sourceNote.message}</p>
                    )}
                  </div>
                  <Button type="submit" size="sm" disabled={addContact.isPending} className="self-end">
                    {addContact.isPending ? <Loader2 className="size-4 animate-spin" /> : "Ajouter le contact"}
                  </Button>
                </form>
              )}
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
