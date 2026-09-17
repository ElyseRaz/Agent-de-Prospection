"use client";

import { useState } from "react";
import { Mail } from "lucide-react";

import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
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
              <h1 className="text-2xl font-semibold tracking-tight">Campagnes</h1>
              <p className="text-muted-foreground">
                Chaque email inclut un lien de desinscription et respecte la limite d&apos;envoi
                quotidienne.
              </p>
            </div>
            <CreateCampaignDialog />
          </div>

          <Card>
            <CardContent className="p-0">
              {isLoading ? (
                <div className="p-8 text-center text-sm text-muted-foreground">Chargement...</div>
              ) : !campaigns || campaigns.length === 0 ? (
                <div className="flex flex-col items-center gap-2 p-12 text-center">
                  <Mail className="size-8 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">
                    Aucune campagne pour l&apos;instant. Cree la premiere a partir de tes prospects.
                  </p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nom</TableHead>
                      <TableHead>Objet</TableHead>
                      <TableHead>Statut</TableHead>
                      <TableHead>Creee le</TableHead>
                      <TableHead>Envoyee le</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {campaigns.map((campaign) => (
                      <TableRow
                        key={campaign.id}
                        className="cursor-pointer"
                        onClick={() => setSelectedId(campaign.id)}
                      >
                        <TableCell className="font-medium">{campaign.name}</TableCell>
                        <TableCell className="text-muted-foreground">{campaign.subject}</TableCell>
                        <TableCell>
                          <CampaignStatusBadge status={campaign.status} />
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {new Date(campaign.created_at).toLocaleDateString("fr-FR")}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {campaign.sent_at
                            ? new Date(campaign.sent_at).toLocaleDateString("fr-FR")
                            : "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>

        <CampaignDetailDialog id={selectedId} onOpenChange={(open) => !open && setSelectedId(null)} />
      </AppShell>
    </AuthGuard>
  );
}
