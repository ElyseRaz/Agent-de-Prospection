"use client";

import { CheckCircle2, XCircle } from "lucide-react";

import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
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
    <div className="flex items-start justify-between gap-4 rounded-md border p-3">
      <div>
        <p className="text-sm font-medium">{name}</p>
        <p className="text-xs text-muted-foreground">{description}</p>
        {!configured && (
          <p className="mt-1 text-xs text-muted-foreground">
            A configurer via <code>{envVar}</code> dans <code>.env</code>
          </p>
        )}
      </div>
      {configured ? (
        <span className="flex items-center gap-1 text-xs font-medium text-emerald-600">
          <CheckCircle2 className="size-4" />
          Configure
        </span>
      ) : (
        <span className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
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
            <h1 className="text-2xl font-semibold tracking-tight">Parametres</h1>
            <p className="text-muted-foreground">
              Les cles d&apos;API restent exclusivement dans le fichier <code>.env</code> du
              serveur — jamais stockees en base ni affichees ici.
            </p>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Fournisseurs d&apos;enrichissement</CardTitle>
              <CardDescription>
                Chaque fournisseur est independant : absent, l&apos;enrichissement continue
                simplement sans lui.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {isLoading ? (
                <p className="text-sm text-muted-foreground">Chargement...</p>
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
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Campagnes email</CardTitle>
              <CardDescription>
                Sans SMTP configure, les campagnes restent en brouillon au lieu d&apos;envoyer.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {isLoading ? (
                <p className="text-sm text-muted-foreground">Chargement...</p>
              ) : (
                <>
                  <ProviderRow
                    name="SMTP"
                    description="Serveur d'envoi utilise pour les campagnes."
                    configured={status?.smtp_configured ?? false}
                    envVar="SMTP_HOST"
                  />
                  <div className="flex items-center justify-between rounded-md border p-3">
                    <div>
                      <p className="text-sm font-medium">Limite d&apos;envoi quotidienne</p>
                      <p className="text-xs text-muted-foreground">
                        Appliquee cote serveur par campagne, par utilisateur.
                      </p>
                    </div>
                    <span className="text-sm font-medium">{status?.daily_send_limit ?? "—"}</span>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </AppShell>
    </AuthGuard>
  );
}
