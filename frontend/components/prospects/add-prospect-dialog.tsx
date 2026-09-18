"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, X } from "@untitledui/icons";
import { toast } from "sonner";

import { Button } from "@/components/base/buttons/button";
import { ButtonUtility } from "@/components/base/buttons/button-utility";
import { Dialog, DialogTrigger, Modal, ModalOverlay } from "@/components/application/modals/modal";
import { FormInput } from "@/components/forms/form-input";
import { FormTextArea } from "@/components/forms/form-textarea";
import { createProspectSchema, type CreateProspectFormValues } from "@/lib/schemas";
import { useCreateProspect } from "@/hooks/use-prospects";
import { ApiError } from "@/lib/api";

export function AddProspectDialog() {
  const [open, setOpen] = useState(false);
  const createProspect = useCreateProspect();

  const { control, handleSubmit, reset } = useForm<CreateProspectFormValues>({
    resolver: zodResolver(createProspectSchema),
  });

  const onSubmit = async (values: CreateProspectFormValues) => {
    try {
      await createProspect.mutateAsync({
        name: values.name,
        domain: values.domain || null,
        website_url: values.websiteUrl || null,
        address: values.address || null,
        phone: values.phone || null,
        email: values.email || null,
        notes: values.notes || null,
        contact: values.contactEmail
          ? {
              email: values.contactEmail,
              full_name: values.contactFullName || null,
              source_note: values.sourceNote,
            }
          : null,
      });
      toast.success("Prospect ajoute");
      reset();
      setOpen(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Erreur lors de l'ajout du prospect");
    }
  };

  return (
    <DialogTrigger
      isOpen={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) reset();
      }}
    >
      <Button size="md" iconLeading={Plus}>
        Ajouter un prospect
      </Button>
      <ModalOverlay>
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
                <h2 className="text-lg font-semibold text-primary">Ajouter un prospect</h2>
                <p className="mt-1 text-sm text-tertiary">
                  Toi seul apportes les entreprises — aucune collecte automatique.
                </p>

                <form onSubmit={handleSubmit(onSubmit)} className="mt-5 flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-4">
                <FormInput
                  className="col-span-2"
                  control={control}
                  name="name"
                  label="Nom de l'entreprise"
                  autoFocus
                />
                <FormInput control={control} name="domain" label="Domaine" placeholder="acme.com" />
                <FormInput
                  control={control}
                  name="websiteUrl"
                  label="Site web"
                  placeholder="https://acme.com"
                />
                <FormInput control={control} name="phone" label="Telephone" placeholder="+33 1 23 45 67 89" />
                <FormInput
                  control={control}
                  name="email"
                  label="Email de l'entreprise"
                  type="email"
                  placeholder="contact@acme.com"
                />
                <FormInput
                  className="col-span-2"
                  control={control}
                  name="address"
                  label="Adresse"
                  placeholder="12 rue de la Paix, 75002 Paris"
                />
              </div>

              <FormTextArea control={control} name="notes" label="Notes" rows={2} />

              <hr className="border-secondary" />

              <div>
                <p className="text-sm font-medium text-secondary">Premier contact (optionnel)</p>
                <p className="text-xs text-tertiary">Si tu renseignes un email, precise d&apos;ou vient ce contact.</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <FormInput control={control} name="contactEmail" label="Email du contact" type="email" />
                <FormInput control={control} name="contactFullName" label="Nom du contact" />
                <FormTextArea
                  className="col-span-2"
                  control={control}
                  name="sourceNote"
                  label="Origine du contact (source_note)"
                  rows={2}
                  placeholder="Ex : page Contact publique du site, salon pro X, recommandation..."
                />
              </div>

              <div className="mt-2 flex justify-end gap-3">
                <Button type="button" size="md" color="secondary" onClick={close}>
                  Annuler
                </Button>
                <Button type="submit" size="md" isLoading={createProspect.isPending}>
                  Ajouter
                </Button>
              </div>
                </form>
              </>
            )}
          </Dialog>
        </Modal>
      </ModalOverlay>
    </DialogTrigger>
  );
}
