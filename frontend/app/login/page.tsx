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
import { loginSchema, type LoginFormValues } from "@/lib/schemas";
import { loginUser, fetchCurrentUser } from "@/lib/auth-api";
import { useAuthStore } from "@/store/auth-store";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const setTokens = useAuthStore((s) => s.setTokens);
  const setUser = useAuthStore((s) => s.setUser);
  const [submitting, setSubmitting] = useState(false);

  const { control, handleSubmit } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) });

  const onSubmit = async (values: LoginFormValues) => {
    setSubmitting(true);
    try {
      const tokens = await loginUser(values);
      setTokens(tokens.access_token, tokens.refresh_token);
      const user = await fetchCurrentUser();
      setUser(user);
      toast.success(`Bienvenue, ${user.full_name || user.email}`);
      router.replace("/dashboard");
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Erreur de connexion";
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Connexion"
      subtitle="Accède à ta base de prospection."
      footer={
        <>
          Pas encore de compte ?{" "}
          <Link href="/register" className="font-medium text-brand-secondary hover:underline">
            Créer un compte
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <FormInput control={control} name="email" label="Email" type="email" autoFocus />
        <FormInput control={control} name="password" label="Mot de passe" type="password" />
        <Button type="submit" size="lg" isLoading={submitting} className="mt-2 w-full">
          Se connecter
        </Button>
      </form>
    </AuthLayout>
  );
}
