"use client";

import Link from "next/link";
import { Users01, Mail01, TrendUp01, Target01, ArrowRight, UserPlus01, BarChartSquare02 } from "@untitledui/icons";
import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/layout/app-shell";
import { FeaturedIcon } from "@/components/foundations/featured-icon/featured-icon";
import { useAuthStore } from "@/store/auth-store";
import { useProspects } from "@/hooks/use-prospects";
import { useCampaigns } from "@/hooks/use-campaigns";
import { getDisplayName } from "@/lib/utils/user-display";

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
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
      color: "brand" as const,
    },
    {
      label: "Campagnes envoyées",
      value: loadingCampaigns ? "…" : String(sentCampaigns),
      icon: Mail01,
      color: "success" as const,
    },
    {
      label: "Taux de réponse",
      value: loadingProspects ? "…" : replyRate !== null ? `${replyRate}%` : "—",
      icon: TrendUp01,
      color: "warning" as const,
    },
    {
      label: "Conversions",
      value: loadingProspects ? "…" : String(convertedCount),
      icon: Target01,
      color: "brand" as const,
    },
  ];

  const quickActions = [
    {
      href: "/prospects",
      label: "Ajouter des prospects",
      description: "Saisie manuelle ou import CSV, avec source obligatoire.",
      icon: UserPlus01,
    },
    {
      href: "/campaigns",
      label: "Lancer une campagne",
      description: "Rédige un email et respecte la limite d'envoi quotidienne.",
      icon: Mail01,
    },
    {
      href: "/pipeline",
      label: "Suivre le pipeline",
      description: "Visualise l'avancement contacté / répondu / converti.",
      icon: BarChartSquare02,
    },
  ];

  return (
    <AuthGuard>
      <AppShell>
        <div className="mx-auto flex max-w-6xl flex-col gap-8">
          <div className="flex flex-col gap-1">
            <h1 className="text-display-xs font-semibold tracking-tight text-primary">
              {user ? `Bonjour, ${getDisplayName(user.full_name, user.email)}` : "Tableau de bord"}
            </h1>
            <p className="text-tertiary">Vue d&apos;ensemble de ta prospection commerciale.</p>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {stats.map((stat) => {
              const Icon = stat.icon;
              return (
                <div
                  key={stat.label}
                  className="flex flex-col gap-4 rounded-2xl bg-primary p-5 shadow-xs ring-1 ring-secondary transition duration-150 hover:shadow-md"
                >
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-tertiary">{stat.label}</p>
                    <FeaturedIcon icon={Icon} color={stat.color} theme="light" size="sm" />
                  </div>
                  <p className="text-display-sm font-semibold text-primary">{stat.value}</p>
                </div>
              );
            })}
          </div>

          <div className="flex flex-col gap-4">
            <h2 className="text-md font-semibold text-primary">Actions rapides</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {quickActions.map((action) => {
                const Icon = action.icon;
                return (
                  <Link
                    key={action.href}
                    href={action.href}
                    className="group flex flex-col gap-3 rounded-2xl bg-primary p-5 shadow-xs ring-1 ring-secondary transition duration-150 hover:-translate-y-0.5 hover:shadow-md"
                  >
                    <FeaturedIcon icon={Icon} color="brand" theme="modern" size="md" />
                    <div>
                      <p className="flex items-center gap-1 text-sm font-semibold text-primary">
                        {action.label}
                        <ArrowRight className="size-3.5 text-fg-brand-primary opacity-0 transition group-hover:translate-x-0.5 group-hover:opacity-100" />
                      </p>
                      <p className="mt-1 text-sm text-tertiary">{action.description}</p>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>

          <div className="rounded-2xl bg-brand-section p-6 ring-1 ring-secondary">
            <h2 className="text-md font-semibold text-primary_on-brand">À propos de LeadPilot</h2>
            <p className="mt-2 max-w-2xl text-sm text-secondary_on-brand">
              CRM de prospection, enrichissement IA (Trustpilot, analyse de site) et campagnes email
              sont en place. Chaque contact est ajouté manuellement avec sa source, et chaque email
              inclut un lien de désinscription et respecte une limite d&apos;envoi quotidienne.
            </p>
          </div>
        </div>
      </AppShell>
    </AuthGuard>
  );
}
