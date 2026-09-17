"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Plus } from "lucide-react";
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
import { createProspectSchema, type CreateProspectFormValues } from "@/lib/schemas";
import { useCreateProspect } from "@/hooks/use-prospects";
import { ApiError } from "@/lib/api";

export function AddProspectDialog() {
  const [open, setOpen] = useState(false);
  const createProspect = useCreateProspect();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateProspectFormValues>({ resolver: zodResolver(createProspectSchema) });

  const onSubmit = async (values: CreateProspectFormValues) => {
    try {
      await createProspect.mutateAsync({
        name: values.name,
        domain: values.domain || null,
        website_url: values.websiteUrl || null,
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
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) reset();
      }}
    >
      <DialogTrigger render={<Button><Plus className="size-4" />Ajouter un prospect</Button>} />
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Ajouter un prospect</DialogTitle>
          <DialogDescription>
            Toi seul apportes les entreprises — aucune collecte automatique.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2 flex flex-col gap-1.5">
              <Label htmlFor="name">Nom de l&apos;entreprise</Label>
              <Input id="name" autoFocus {...register("name")} />
              {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="domain">Domaine</Label>
              <Input id="domain" placeholder="acme.com" {...register("domain")} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="websiteUrl">Site web</Label>
              <Input id="websiteUrl" placeholder="https://acme.com" {...register("websiteUrl")} />
              {errors.websiteUrl && (
                <p className="text-sm text-destructive">{errors.websiteUrl.message}</p>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="notes">Notes</Label>
            <Textarea id="notes" rows={2} {...register("notes")} />
          </div>

          <Separator />

          <div className="flex flex-col gap-1">
            <p className="text-sm font-medium">Premier contact (optionnel)</p>
            <p className="text-xs text-muted-foreground">
              Si tu renseignes un email, precise d&apos;ou vient ce contact.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="contactEmail">Email</Label>
              <Input id="contactEmail" type="email" {...register("contactEmail")} />
              {errors.contactEmail && (
                <p className="text-sm text-destructive">{errors.contactEmail.message}</p>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="contactFullName">Nom du contact</Label>
              <Input id="contactFullName" {...register("contactFullName")} />
            </div>
            <div className="col-span-2 flex flex-col gap-1.5">
              <Label htmlFor="sourceNote">Origine du contact (source_note)</Label>
              <Textarea
                id="sourceNote"
                rows={2}
                placeholder="Ex : page Contact publique du site, salon pro X, recommandation..."
                {...register("sourceNote")}
              />
              {errors.sourceNote && (
                <p className="text-sm text-destructive">{errors.sourceNote.message}</p>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button type="submit" disabled={createProspect.isPending}>
              {createProspect.isPending ? <Loader2 className="size-4 animate-spin" /> : "Ajouter"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
