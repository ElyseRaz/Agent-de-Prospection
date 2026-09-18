"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle, XCircle, AlertTriangle } from "@untitledui/icons";
import { toast } from "sonner";

import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/layout/app-shell";
import { Avatar } from "@/components/base/avatar/avatar";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { FormInput } from "@/components/forms/form-input";
import { useSettingsStatus } from "@/hooks/use-prospects";
import { profileSchema, type ProfileFormValues } from "@/lib/schemas";
import { updateCurrentUser } from "@/lib/auth-api";
import { useAuthStore } from "@/store/auth-store";
import { getDisplayName, getInitials } from "@/lib/utils/user-display";
import { ApiError } from "@/lib/api";

function ProviderRow({
  name,
  description,
  configured,
  envVar,
}: {
  name: string;
  description: string;
  configured: boolean;
  envVar: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4 rounded-md bg-secondary p-3">
      <div>
        <p className="text-sm font-medium text-secondary">{name}</p>
        <p className="text-xs text-tertiary">{description}</p>
        {!configured && (
          <p className="mt-1 text-xs text-tertiary">
            A configurer via <code>{envVar}</code> dans <code>.env</code>
          </p>
        )}
      </div>
      {configured ? (
        <span className="flex items-center gap-1 text-xs font-medium text-success-primary">
          <CheckCircle className="size-4" />
          Configure
        </span>
      ) : (
        <span className="flex items-center gap-1 text-xs font-medium text-tertiary">
          <XCircle className="size-4" />
          Non configure
        </span>
      )}
    </div>
  );
}

export default function SettingsPage() {
  const { data: status, isLoading } = useSettingsStatus();
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);

  const {
    control,
    handleSubmit,
    formState: { isSubmitting, isDirty },
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    values: { fullName: user?.full_name ?? "" },
  });

  const onSubmitProfile = async (values: ProfileFormValues) => {
    try {
      const updated = await updateCurrentUser({ fullName: values.fullName });
      setUser(updated);
      toast.success("Profil mis a jour");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Erreur lors de la mise a jour du profil");
    }
  };

  return (
    <AuthGuard>
      <AppShell>
        <div className="mx-auto flex max-w-2xl flex-col gap-6">
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-primary">Parametres</h1>
            <p className="text-tertiary">
              Les cles d&apos;API restent exclusivement dans le fichier <code>.env</code> du
              serveur — jamais stockees en base ni affichees ici.
            </p>
          </div>

          <div className="rounded-xl bg-primary shadow-xs ring-1 ring-secondary">
            <div className="border-b border-secondary p-5">
              <h2 className="text-md font-semibold text-primary">Mon compte</h2>
              <p className="text-sm text-tertiary">Ton nom et ton avatar, visibles dans toute l&apos;application.</p>
            </div>
            <form onSubmit={handleSubmit(onSubmitProfile)} className="flex flex-col gap-4 p-5">
              <div className="flex items-center gap-4">
                <Avatar size="lg" initials={getInitials(user?.full_name, user?.email)} alt={getDisplayName(user?.full_name, user?.email)} />
                <div>
                  <p className="text-sm font-medium text-primary">{getDisplayName(user?.full_name, user?.email)}</p>
                  <p className="text-sm text-tertiary">{user?.email}</p>
                </div>
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormInput control={control} name="fullName" label="Nom complet" />
                <Input label="Email" value={user?.email ?? ""} isDisabled onChange={() => {}} />
              </div>
              <Button type="submit" size="sm" className="self-end" isLoading={isSubmitting} isDisabled={!isDirty}>
                Enregistrer
              </Button>
            </form>
          </div>

          <div className="rounded-xl bg-primary shadow-xs ring-1 ring-secondary">
            <div className="border-b border-secondary p-5">
              <h2 className="text-md font-semibold text-primary">Fournisseurs d&apos;enrichissement</h2>
              <p className="text-sm text-tertiary">
                Chaque fournisseur est independant : absent, l&apos;enrichissement continue simplement
                sans lui.
              </p>
            </div>
            <div className="flex flex-col gap-3 p-5">
              {isLoading ? (
                <p className="text-sm text-tertiary">Chargement...</p>
              ) : (
                <>
                  <ProviderRow
                    name="Trustpilot"
                    description="Note et nombre d'avis, recherche par domaine d'entreprise."
                    configured={status?.trustpilot_configured ?? false}
                    envVar="TRUSTPILOT_API_KEY"
                  />
                  <ProviderRow
                    name="Groq"
                    description="Analyse IA de la page d'accueil publique pour detecter des besoins."
                    configured={status?.groq_configured ?? false}
                    envVar="GROQ_API_KEY"
                  />
                </>
              )}
            </div>
          </div>

          <div className="rounded-xl bg-primary shadow-xs ring-1 ring-secondary">
            <div className="border-b border-secondary p-5">
              <h2 className="text-md font-semibold text-primary">Campagnes email</h2>
              <p className="text-sm text-tertiary">
                Sans SMTP configure, les campagnes restent en brouillon au lieu d&apos;envoyer.
              </p>
            </div>
            <div className="flex flex-col gap-3 p-5">
              {isLoading ? (
                <p className="text-sm text-tertiary">Chargement...</p>
              ) : (
                <>
                  <ProviderRow
                    name="SMTP"
                    description="Serveur d'envoi utilise pour les campagnes."
                    configured={status?.smtp_configured ?? false}
                    envVar="SMTP_HOST"
                  />
                  {status?.smtp_configured && status.smtp_from_risky && (
                    <div className="flex items-start gap-3 rounded-md bg-utility-yellow-50 p-3 ring-1 ring-utility-yellow-200">
                      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-utility-yellow-500" />
                      <div>
                        <p className="text-sm font-medium text-utility-yellow-700">
                          Adresse d&apos;expedition a risque : <code>{status.smtp_from}</code>
                        </p>
                        <p className="mt-1 text-xs text-utility-yellow-700">
                          C&apos;est un domaine de messagerie grand public (Gmail, Outlook, Yahoo...).
                          Envoyer en son nom via un relais SMTP tiers echoue generalement
                          l&apos;alignement DMARC du fournisseur reel — les emails finissent en spam
                          ou sont rejetes silencieusement. Utilise plutot une adresse sur un domaine
                          que tu controles, verifie cote SMTP (SPF/DKIM), via <code>SMTP_FROM</code>{" "}
                          dans <code>.env</code>.
                        </p>
                      </div>
                    </div>
                  )}
                  <div className="flex items-center justify-between rounded-md bg-secondary p-3">
                    <div>
                      <p className="text-sm font-medium text-secondary">Limite d&apos;envoi quotidienne</p>
                      <p className="text-xs text-tertiary">Appliquee cote serveur par campagne, par utilisateur.</p>
                    </div>
                    <span className="text-sm font-medium text-secondary">{status?.daily_send_limit ?? "—"}</span>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </AppShell>
    </AuthGuard>
  );
}
