"use client";

import { useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Plus, Save } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
    register,
    handleSubmit,
    reset,
    setValue,
    getValues,
    formState: { errors },
  } = useForm<CreateCampaignFormValues>({
    resolver: zodResolver(createCampaignSchema),
    defaultValues: { name: "", subject: "", body: "", companyIds: [] },
  });

  const { ref: subjectFormRef, ...subjectField } = register("subject");
  const { ref: bodyFormRef, ...bodyField } = register("body");

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

  const applyTemplate = (templateId: string | null) => {
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
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) resetAll();
      }}
    >
      <DialogTrigger render={<Button><Plus className="size-4" />Nouvelle campagne</Button>} />
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Nouvelle campagne</DialogTitle>
          <DialogDescription>
            Chaque email inclut automatiquement un lien de desinscription et respecte la limite
            d&apos;envoi quotidienne.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="campaign-name">Nom de la campagne</Label>
            <Input id="campaign-name" autoFocus {...register("name")} />
            {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
          </div>

          {templates && templates.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <Label>Charger un modele</Label>
              <Select onValueChange={applyTemplate}>
                <SelectTrigger>
                  <SelectValue placeholder="Choisir un modele existant (optionnel)" />
                </SelectTrigger>
                <SelectContent>
                  {templates.map((template) => (
                    <SelectItem key={template.id} value={template.id}>
                      {template.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs text-muted-foreground">Inserer une variable :</span>
            {VARIABLES.map((variable) => (
              <Button
                key={variable.token}
                type="button"
                size="sm"
                variant="outline"
                className="h-6 px-2 text-xs"
                onClick={() => insertVariable(variable.token)}
              >
                {variable.label}
              </Button>
            ))}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="campaign-subject">Objet</Label>
            <Input
              id="campaign-subject"
              {...subjectField}
              ref={(el) => {
                subjectFormRef(el);
                subjectRef.current = el;
              }}
              onFocus={() => (lastFocused.current = "subject")}
            />
            {errors.subject && <p className="text-sm text-destructive">{errors.subject.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="campaign-body">Message</Label>
            <Textarea
              id="campaign-body"
              rows={6}
              {...bodyField}
              ref={(el) => {
                bodyFormRef(el);
                bodyRef.current = el;
              }}
              onFocus={() => (lastFocused.current = "body")}
            />
            {errors.body && <p className="text-sm text-destructive">{errors.body.message}</p>}
          </div>

          <div className="flex items-center justify-between">
            {showSaveTemplate ? (
              <div className="flex flex-1 items-center gap-2">
                <Input
                  placeholder="Nom du modele"
                  value={templateName}
                  onChange={(e) => setTemplateName(e.target.value)}
                  className="h-8"
                />
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  disabled={createTemplate.isPending || !templateName.trim()}
                  onClick={handleSaveTemplate}
                >
                  {createTemplate.isPending ? <Loader2 className="size-4 animate-spin" /> : "Confirmer"}
                </Button>
              </div>
            ) : (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => setShowSaveTemplate(true)}
              >
                <Save className="size-4" />
                Enregistrer comme modele
              </Button>
            )}
          </div>

          <Separator />

          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">Destinataires</p>
              <span className="text-xs text-muted-foreground">
                {selectedIds.size} entreprise{selectedIds.size > 1 ? "s" : ""} selectionnee
                {selectedIds.size > 1 ? "s" : ""}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              Tous les contacts des entreprises selectionnees recevront cet email (hors
              desinscrits).
            </p>
            {errors.companyIds && (
              <p className="text-sm text-destructive">{errors.companyIds.message}</p>
            )}
            <div className="max-h-56 overflow-y-auto rounded-md border">
              {loadingProspects ? (
                <div className="p-4 text-center text-sm text-muted-foreground">Chargement...</div>
              ) : !prospects || prospects.length === 0 ? (
                <div className="p-4 text-center text-sm text-muted-foreground">
                  Aucun prospect. Ajoute des entreprises avant de creer une campagne.
                </div>
              ) : (
                <ul className="divide-y">
                  {prospects.map((prospect) => (
                    <li key={prospect.id}>
                      <label className="flex cursor-pointer items-center gap-3 px-3 py-2 text-sm hover:bg-muted/50">
                        <input
                          type="checkbox"
                          className="size-4 accent-primary"
                          checked={selectedIds.has(prospect.id)}
                          onChange={() => toggleCompany(prospect.id)}
                        />
                        <span className="flex-1 font-medium">{prospect.name}</span>
                        <StatusBadge status={prospect.status} />
                      </label>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button type="submit" disabled={createCampaign.isPending}>
              {createCampaign.isPending ? <Loader2 className="size-4 animate-spin" /> : "Creer la campagne"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
