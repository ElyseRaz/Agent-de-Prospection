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
