"use client";

import { CheckCircle, XCircle } from "@untitledui/icons";

import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/layout/app-shell";
import { useSettingsStatus } from "@/hooks/use-prospects";

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
