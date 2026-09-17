"use client";

import { useState } from "react";
import { Mail01 } from "@untitledui/icons";

import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/layout/app-shell";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { LoadingIndicator } from "@/components/application/loading-indicator/loading-indicator";
import { CampaignStatusBadge } from "@/components/campaigns/campaign-status-badge";
import { CreateCampaignDialog } from "@/components/campaigns/create-campaign-dialog";
import { CampaignDetailDialog } from "@/components/campaigns/campaign-detail-dialog";
import { useCampaigns } from "@/hooks/use-campaigns";

export default function CampaignsPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { data: campaigns, isLoading } = useCampaigns();

  return (
    <AuthGuard>
      <AppShell>
        <div className="mx-auto flex max-w-6xl flex-col gap-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-xl font-semibold tracking-tight text-primary">Campagnes</h1>
              <p className="text-tertiary">
                Chaque email inclut un lien de desinscription et respecte la limite d&apos;envoi
                quotidienne.
              </p>
            </div>
            <CreateCampaignDialog />
          </div>

          <div className="overflow-hidden rounded-xl bg-primary shadow-xs ring-1 ring-secondary">
            {isLoading ? (
              <div className="flex justify-center p-8">
                <LoadingIndicator size="sm" />
              </div>
            ) : !campaigns || campaigns.length === 0 ? (
              <EmptyState size="sm" className="py-12">
                <EmptyState.Header>
                  <EmptyState.FeaturedIcon color="gray" icon={Mail01} />
                </EmptyState.Header>
                <EmptyState.Content>
                  <EmptyState.Title>Aucune campagne pour l&apos;instant</EmptyState.Title>
                  <EmptyState.Description>Cree la premiere a partir de tes prospects.</EmptyState.Description>
                </EmptyState.Content>
              </EmptyState>
            ) : (
              <table className="w-full">
                <thead className="h-11 bg-secondary">
                  <tr>
                    <th className="px-6 py-2 text-left text-xs font-semibold text-quaternary">Nom</th>
                    <th className="px-6 py-2 text-left text-xs font-semibold text-quaternary">Objet</th>
                    <th className="px-6 py-2 text-left text-xs font-semibold text-quaternary">Statut</th>
                    <th className="px-6 py-2 text-left text-xs font-semibold text-quaternary">Creee le</th>
                    <th className="px-6 py-2 text-left text-xs font-semibold text-quaternary">Envoyee le</th>
                  </tr>
                </thead>
                <tbody>
                  {campaigns.map((campaign) => (
                    <tr
                      key={campaign.id}
                      className="h-16 cursor-pointer border-t border-secondary hover:bg-secondary"
                      onClick={() => setSelectedId(campaign.id)}
                    >
                      <td className="px-6 py-3 text-sm font-medium text-primary">{campaign.name}</td>
                      <td className="px-6 py-3 text-sm text-tertiary">{campaign.subject}</td>
                      <td className="px-6 py-3">
                        <CampaignStatusBadge status={campaign.status} />
                      </td>
                      <td className="px-6 py-3 text-sm text-tertiary">
                        {new Date(campaign.created_at).toLocaleDateString("fr-FR")}
                      </td>
                      <td className="px-6 py-3 text-sm text-tertiary">
                        {campaign.sent_at ? new Date(campaign.sent_at).toLocaleDateString("fr-FR") : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <CampaignDetailDialog id={selectedId} onOpenChange={(open) => !open && setSelectedId(null)} />
      </AppShell>
    </AuthGuard>
  );
}
