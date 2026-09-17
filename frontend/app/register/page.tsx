"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Rocket01 } from "@untitledui/icons";
import { toast } from "sonner";

import { Button } from "@/components/base/buttons/button";
import { FormInput } from "@/components/forms/form-input";
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
      await registerUser({ email: values.email, password: values.password });
      const tokens = await loginUser({ email: values.email, password: values.password });
      setTokens(tokens.access_token, tokens.refresh_token);
      const user = await fetchCurrentUser();
      setUser(user);
      router.replace("/");
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Erreur lors de la creation du compte";
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-secondary p-4">
      <div className="w-full max-w-sm rounded-2xl bg-primary p-6 shadow-lg ring-1 ring-secondary">
        <div className="mb-6 flex items-center gap-2">
          <Rocket01 className="size-6 text-fg-brand-primary" />
          <span className="text-lg font-semibold text-primary">LeadPilot</span>
        </div>
        <h1 className="text-xl font-semibold text-primary">Creer un compte</h1>
        <p className="mt-1 text-sm text-tertiary">Commence a construire ta base de prospection.</p>

        <form onSubmit={handleSubmit(onSubmit)} className="mt-6 flex flex-col gap-4">
          <FormInput control={control} name="email" label="Email" type="email" autoFocus />
          <FormInput control={control} name="password" label="Mot de passe" type="password" />
          <FormInput
            control={control}
            name="confirmPassword"
            label="Confirmer le mot de passe"
            type="password"
          />
          <Button type="submit" size="lg" isLoading={submitting} className="mt-2 w-full">
            Creer mon compte
          </Button>
        </form>

        <p className="mt-4 text-center text-sm text-tertiary">
          Deja inscrit ?{" "}
          <Link href="/login" className="font-medium text-brand-secondary hover:underline">
            Se connecter
          </Link>
        </p>
      </div>
    </div>
  );
}
