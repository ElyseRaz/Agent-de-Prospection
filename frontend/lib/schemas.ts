import { z } from "zod";

export const registerSchema = z
  .object({
    email: z.string().min(1, "Email requis").email("Email invalide"),
    password: z.string().min(8, "8 caracteres minimum"),
    confirmPassword: z.string().min(1, "Confirmation requise"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Les mots de passe ne correspondent pas",
    path: ["confirmPassword"],
  });

export type RegisterFormValues = z.infer<typeof registerSchema>;

export const loginSchema = z.object({
  email: z.string().min(1, "Email requis").email("Email invalide"),
  password: z.string().min(1, "Mot de passe requis"),
});

export type LoginFormValues = z.infer<typeof loginSchema>;

const optionalUrl = z
  .string()
  .optional()
  .or(z.literal(""))
  .refine((v) => !v || /^https?:\/\//.test(v), "URL invalide (doit commencer par http:// ou https://)");

export const createProspectSchema = z
  .object({
    name: z.string().min(1, "Nom requis"),
    domain: z.string().optional().or(z.literal("")),
    websiteUrl: optionalUrl,
    notes: z.string().optional().or(z.literal("")),
    contactEmail: z.string(),
    contactFullName: z.string().optional().or(z.literal("")),
    sourceNote: z.string(),
  })
  .refine((data) => !data.contactEmail || z.string().email().safeParse(data.contactEmail).success, {
    message: "Email de contact invalide",
    path: ["contactEmail"],
  })
  .refine((data) => !data.contactEmail || data.sourceNote.trim().length > 0, {
    message: "Obligatoire des qu'un email de contact est fourni (origine du contact)",
    path: ["sourceNote"],
  });

export type CreateProspectFormValues = z.infer<typeof createProspectSchema>;

export const editProspectSchema = z.object({
  name: z.string().min(1, "Nom requis"),
  domain: z.string().optional().or(z.literal("")),
  websiteUrl: optionalUrl,
  status: z.enum(["new", "contacted", "replied", "converted", "lost"]),
  notes: z.string().optional().or(z.literal("")),
});

export type EditProspectFormValues = z.infer<typeof editProspectSchema>;

export const addContactSchema = z.object({
  email: z.string().min(1, "Email requis").email("Email invalide"),
  fullName: z.string().optional().or(z.literal("")),
  sourceNote: z.string().min(1, "Obligatoire : d'ou vient ce contact ?"),
});

export type AddContactFormValues = z.infer<typeof addContactSchema>;

export const createCampaignSchema = z.object({
  name: z.string().min(1, "Nom requis"),
  subject: z.string().min(1, "Objet requis"),
  body: z.string().min(1, "Corps du message requis"),
  companyIds: z.array(z.string()).min(1, "Selectionne au moins un prospect"),
});

export type CreateCampaignFormValues = z.infer<typeof createCampaignSchema>;

export const saveTemplateSchema = z.object({
  name: z.string().min(1, "Nom du modele requis"),
});

export type SaveTemplateFormValues = z.infer<typeof saveTemplateSchema>;
