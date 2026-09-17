"use client";

import { useRef, useState } from "react";
import { useController, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Save01, X } from "@untitledui/icons";
import { toast } from "sonner";

import { Button } from "@/components/base/buttons/button";
import { ButtonUtility } from "@/components/base/buttons/button-utility";
import { Input } from "@/components/base/input/input";
import { TextArea } from "@/components/base/textarea/textarea";
import { NativeSelect } from "@/components/base/select/select-native";
import { Checkbox } from "@/components/base/checkbox/checkbox";
import { Dialog, DialogTrigger, Modal, ModalOverlay } from "@/components/application/modals/modal";
import { FormInput } from "@/components/forms/form-input";
import { StatusBadge } from "@/components/prospects/status-badge";
import { createCampaignSchema, type CreateCampaignFormValues } from "@/lib/schemas";
import { useCreateCampaign, useCreateTemplate, useTemplates } from "@/hooks/use-campaigns";
import { useProspects } from "@/hooks/use-prospects";
import { ApiError } from "@/lib/api";

const VARIABLES = [
  { token: "{{entreprise}}", label: "Entreprise" },
  { token: "{{contact}}", label: "Contact" },
  { token: "{{besoin_detecte}}", label: "Besoin detecte" },
];

export function CreateCampaignDialog() {
  const [open, setOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showSaveTemplate, setShowSaveTemplate] = useState(false);
  const [templateName, setTemplateName] = useState("");

  const createCampaign = useCreateCampaign();
  const createTemplate = useCreateTemplate();
  const { data: templates } = useTemplates();
  const { data: prospects, isLoading: loadingProspects } = useProspects({});

  const subjectRef = useRef<HTMLInputElement | null>(null);
  const bodyRef = useRef<HTMLTextAreaElement | null>(null);
  const lastFocused = useRef<"subject" | "body">("body");

  const {
    control,
    handleSubmit,
    reset,
    setValue,
    getValues,
    formState: { errors },
  } = useForm<CreateCampaignFormValues>({
    resolver: zodResolver(createCampaignSchema),
    defaultValues: { name: "", subject: "", body: "", companyIds: [] },
  });

  const subjectField = useController({ control, name: "subject" });
  const bodyField = useController({ control, name: "body" });

  const resetAll = () => {
    reset({ name: "", subject: "", body: "", companyIds: [] });
    setSelectedIds(new Set());
    setShowSaveTemplate(false);
    setTemplateName("");
  };

  const toggleCompany = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      setValue("companyIds", Array.from(next), { shouldValidate: true });
      return next;
    });
  };

  const insertVariable = (token: string) => {
    const target = lastFocused.current === "subject" ? subjectRef.current : bodyRef.current;
    const field = lastFocused.current;
    const current = getValues(field);
    if (target) {
      const start = target.selectionStart ?? current.length;
      const end = target.selectionEnd ?? current.length;
      const next = current.slice(0, start) + token + current.slice(end);
      setValue(field, next, { shouldValidate: true });
      requestAnimationFrame(() => {
        target.focus();
        const pos = start + token.length;
        target.setSelectionRange(pos, pos);
      });
    } else {
      setValue(field, current + token, { shouldValidate: true });
    }
  };

  const applyTemplate = (templateId: string) => {
    const template = templates?.find((t) => t.id === templateId);
    if (!template) return;
    setValue("subject", template.subject, { shouldValidate: true });
    setValue("body", template.body, { shouldValidate: true });
  };

  const handleSaveTemplate = async () => {
    if (!templateName.trim()) return;
    const values = getValues();
    try {
      await createTemplate.mutateAsync({
        name: templateName.trim(),
        subject: values.subject,
        body: values.body,
      });
      toast.success("Modele enregistre");
      setShowSaveTemplate(false);
      setTemplateName("");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Erreur lors de l'enregistrement du modele");
    }
  };

  const onSubmit = async (values: CreateCampaignFormValues) => {
    try {
      await createCampaign.mutateAsync({
        name: values.name,
        subject: values.subject,
        body: values.body,
        company_ids: values.companyIds,
      });
      toast.success("Campagne creee");
      resetAll();
      setOpen(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Erreur lors de la creation de la campagne");
    }
  };

  return (
    <DialogTrigger
      isOpen={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) resetAll();
      }}
    >
      <Button size="md" iconLeading={Plus}>
        Nouvelle campagne
      </Button>
      <ModalOverlay>
        <Modal className="w-full sm:max-w-2xl">
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
                <h2 className="text-lg font-semibold text-primary">Nouvelle campagne</h2>
                <p className="mt-1 text-sm text-tertiary">
                  Chaque email inclut automatiquement un lien de desinscription et respecte la limite
                  d&apos;envoi quotidienne.
                </p>

                <form onSubmit={handleSubmit(onSubmit)} className="mt-5 flex flex-col gap-4">
              <FormInput control={control} name="name" label="Nom de la campagne" autoFocus />

              {templates && templates.length > 0 && (
                <NativeSelect
                  label="Charger un modele"
                  options={[
                    { value: "", label: "Choisir un modele existant (optionnel)", disabled: true },
                    ...templates.map((t) => ({ value: t.id, label: t.name })),
                  ]}
                  defaultValue=""
                  onChange={(e) => e.target.value && applyTemplate(e.target.value)}
                />
              )}

              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-xs text-tertiary">Inserer une variable :</span>
                {VARIABLES.map((variable) => (
                  <Button
                    key={variable.token}
                    type="button"
                    size="sm"
                    color="secondary"
                    className="h-6 px-2 text-xs"
                    onClick={() => insertVariable(variable.token)}
                  >
                    {variable.label}
                  </Button>
                ))}
              </div>

              <Input
                label="Objet"
                isInvalid={!!errors.subject}
                hint={errors.subject?.message}
                value={subjectField.field.value}
                onChange={subjectField.field.onChange}
                onBlur={subjectField.field.onBlur}
                ref={(el) => {
                  subjectField.field.ref(el);
                  subjectRef.current = el;
                }}
                onFocus={() => (lastFocused.current = "subject")}
              />

              <TextArea
                label="Message"
                rows={6}
                isInvalid={!!errors.body}
                hint={errors.body?.message}
                value={bodyField.field.value}
                onChange={bodyField.field.onChange}
                onBlur={bodyField.field.onBlur}
                textAreaRef={(el) => {
                  bodyField.field.ref(el);
                  bodyRef.current = el;
                }}
                onFocus={() => (lastFocused.current = "body")}
              />

              <div className="flex items-center justify-between">
                {showSaveTemplate ? (
                  <div className="flex flex-1 items-center gap-2">
                    <Input
                      placeholder="Nom du modele"
                      value={templateName}
                      onChange={setTemplateName}
                      size="sm"
                      className="flex-1"
                    />
                    <Button
                      type="button"
                      size="sm"
                      color="secondary"
                      isDisabled={!templateName.trim()}
                      isLoading={createTemplate.isPending}
                      onClick={handleSaveTemplate}
                    >
                      Confirmer
                    </Button>
                  </div>
                ) : (
                  <Button
                    type="button"
                    size="sm"
                    color="tertiary"
                    iconLeading={Save01}
                    onClick={() => setShowSaveTemplate(true)}
                  >
                    Enregistrer comme modele
                  </Button>
                )}
              </div>

              <hr className="border-secondary" />

              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-secondary">Destinataires</p>
                  <span className="text-xs text-tertiary">
                    {selectedIds.size} entreprise{selectedIds.size > 1 ? "s" : ""} selectionnee
                    {selectedIds.size > 1 ? "s" : ""}
                  </span>
                </div>
                <p className="text-xs text-tertiary">
                  Tous les contacts des entreprises selectionnees recevront cet email (hors
                  desinscrits).
                </p>
                {errors.companyIds && <p className="text-sm text-error-primary">{errors.companyIds.message}</p>}
                <div className="max-h-56 overflow-y-auto rounded-md ring-1 ring-secondary">
                  {loadingProspects ? (
                    <div className="p-4 text-center text-sm text-tertiary">Chargement...</div>
                  ) : !prospects || prospects.length === 0 ? (
                    <div className="p-4 text-center text-sm text-tertiary">
                      Aucun prospect. Ajoute des entreprises avant de creer une campagne.
                    </div>
                  ) : (
                    <ul className="divide-y divide-secondary">
                      {prospects.map((prospect) => (
                        <li key={prospect.id}>
                          <label className="flex cursor-pointer items-center gap-3 px-3 py-2 text-sm hover:bg-secondary">
                            <Checkbox
                              isSelected={selectedIds.has(prospect.id)}
                              onChange={() => toggleCompany(prospect.id)}
                            />
                            <span className="flex-1 font-medium text-secondary">{prospect.name}</span>
                            <StatusBadge status={prospect.status} />
                          </label>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

              <div className="mt-2 flex justify-end gap-3">
                <Button type="button" color="secondary" onClick={close}>
                  Annuler
                </Button>
                <Button type="submit" isLoading={createCampaign.isPending}>
                  Creer la campagne
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
