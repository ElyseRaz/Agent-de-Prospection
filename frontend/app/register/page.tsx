"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";

import { Button } from "@/components/base/buttons/button";
import { FormInput } from "@/components/forms/form-input";
import { AuthLayout } from "@/components/auth/auth-layout";
import { registerSchema, type RegisterFormValues } from "@/lib/schemas";
import { registerUser, loginUser, fetchCurrentUser } from "@/lib/auth-api";
import { useAuthStore } from "@/store/auth-store";
import { ApiError } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const setTokens = useAuthStore((s) => s.setTokens);
  const setUser = useAuthStore((s) => s.setUser);
  const [submitting, setSubmitting] = useState(false);

  const { control, handleSubmit } = useForm<RegisterFormValues>({ resolver: zodResolver(registerSchema) });

  const onSubmit = async (values: RegisterFormValues) => {
    setSubmitting(true);
    try {
      await registerUser({ email: values.email, password: values.password, fullName: values.fullName });
      const tokens = await loginUser({ email: values.email, password: values.password });
      setTokens(tokens.access_token, tokens.refresh_token);
      const user = await fetchCurrentUser();
      setUser(user);
      router.replace("/dashboard");
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Erreur lors de la creation du compte";
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Créer un compte"
      subtitle="Commence à construire ta base de prospection."
      footer={
        <>
          Déjà inscrit ?{" "}
          <Link href="/login" className="font-medium text-brand-secondary hover:underline">
            Se connecter
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <FormInput control={control} name="fullName" label="Nom complet" autoFocus />
        <FormInput control={control} name="email" label="Email" type="email" />
        <FormInput control={control} name="password" label="Mot de passe" type="password" />
        <FormInput control={control} name="confirmPassword" label="Confirmer le mot de passe" type="password" />
        <Button type="submit" size="lg" isLoading={submitting} className="mt-2 w-full">
          Créer mon compte
        </Button>
      </form>
    </AuthLayout>
  );
}
