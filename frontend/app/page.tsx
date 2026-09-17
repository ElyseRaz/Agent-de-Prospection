"use client";

import { Users01, Mail01, TrendUp01, Target01 } from "@untitledui/icons";
import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/layout/app-shell";
import { useProspects } from "@/hooks/use-prospects";
import { useCampaigns } from "@/hooks/use-campaigns";

export default function DashboardPage() {
  const { data: prospects, isLoading: loadingProspects } = useProspects({});
  const { data: campaigns, isLoading: loadingCampaigns } = useCampaigns();

  const activeCount = prospects?.filter((p) => p.status !== "lost").length ?? 0;
  const convertedCount = prospects?.filter((p) => p.status === "converted").length ?? 0;
  const repliedCount = prospects?.filter((p) => p.status === "replied" || p.status === "converted").length ?? 0;
  const contactedCount = prospects?.filter((p) => p.status !== "new").length ?? 0;
  const replyRate = contactedCount > 0 ? Math.round((repliedCount / contactedCount) * 100) : null;
  const sentCampaigns = campaigns?.filter((c) => c.status === "sent").length ?? 0;

  const stats = [
    {
      label: "Prospects actifs",
      value: loadingProspects ? "…" : String(activeCount),
      icon: Users01,
      color: "text-fg-brand-primary",
    },
    {
      label: "Campagnes envoyees",
      value: loadingCampaigns ? "…" : String(sentCampaigns),
      icon: Mail01,
      color: "text-utility-blue-500",
    },
    {
      label: "Taux de reponse",
      value: loadingProspects ? "…" : replyRate !== null ? `${replyRate}%` : "—",
      icon: TrendUp01,
      color: "text-fg-brand-primary",
    },
    {
      label: "Conversions",
      value: loadingProspects ? "…" : String(convertedCount),
      icon: Target01,
      color: "text-utility-blue-500",
    },
  ];

  return (
    <AuthGuard>
      <AppShell>
        <div className="mx-auto flex max-w-6xl flex-col gap-6">
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-primary">Tableau de bord</h1>
            <p className="text-tertiary">Vue d&apos;ensemble de ta prospection commerciale.</p>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {stats.map((stat) => {
              const Icon = stat.icon;
              return (
                <div
                  key={stat.label}
                  className="flex flex-col gap-3 rounded-xl bg-primary p-5 shadow-xs ring-1 ring-secondary"
                >
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-tertiary">{stat.label}</p>
                    <Icon className={`size-5 ${stat.color}`} />
                  </div>
                  <p className="text-display-xs font-semibold text-primary">{stat.value}</p>
                </div>
              );
            })}
          </div>

          <div className="rounded-xl bg-primary p-5 shadow-xs ring-1 ring-secondary">
            <h2 className="text-md font-semibold text-primary">A propos de LeadPilot</h2>
            <p className="mt-1 text-sm text-tertiary">
              CRM de prospection, enrichissement IA (Trustpilot, analyse de site) et campagnes email
              sont en place. Chaque contact est ajoute manuellement avec sa source, et chaque email
              inclut un lien de desinscription et respecte une limite d&apos;envoi quotidienne.
            </p>
          </div>
        </div>
      </AppShell>
    </AuthGuard>
  );
}
