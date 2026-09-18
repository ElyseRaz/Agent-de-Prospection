"use client";

import { useState } from "react";
import { SearchLg, Star01, Stars02 } from "@untitledui/icons";

import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/layout/app-shell";
import { Input } from "@/components/base/input/input";
import { NativeSelect } from "@/components/base/select/select-native";
import { EmptyState } from "@/components/application/empty-state/empty-state";
import { LoadingIndicator } from "@/components/application/loading-indicator/loading-indicator";
import { StatusBadge, STATUS_OPTIONS } from "@/components/prospects/status-badge";
import { AddProspectDialog } from "@/components/prospects/add-prospect-dialog";
import { ImportDialog } from "@/components/prospects/import-dialog";
import { ProspectDetailDialog } from "@/components/prospects/prospect-detail-dialog";
import { useProspects } from "@/hooks/use-prospects";
import type { ProspectStatus } from "@/lib/prospects-api";

export default function ProspectsPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<ProspectStatus | "tout">("tout");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: prospects, isLoading } = useProspects({
    search: search || undefined,
    status: status === "tout" ? undefined : status,
  });

  return (
    <AuthGuard>
      <AppShell>
        <div className="mx-auto flex max-w-6xl flex-col gap-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-xl font-semibold tracking-tight text-primary">Prospects</h1>
              <p className="text-tertiary">
                Tes entreprises, ajoutees une a une ou par import — jamais collectees automatiquement.
              </p>
            </div>
            <div className="flex gap-2">
              <ImportDialog />
              <AddProspectDialog />
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Input
              placeholder="Rechercher par nom ou domaine..."
              value={search}
              onChange={setSearch}
              icon={SearchLg}
              className="max-w-xs"
            />
            <NativeSelect
              className="w-44"
              options={[{ value: "tout", label: "Tous les statuts" }, ...STATUS_OPTIONS]}
              value={status}
              onChange={(e) => setStatus(e.target.value as ProspectStatus | "tout")}
            />
          </div>

          <div className="overflow-hidden rounded-xl bg-primary shadow-xs ring-1 ring-secondary">
            {isLoading ? (
              <div className="flex justify-center p-8">
                <LoadingIndicator size="sm" />
              </div>
            ) : !prospects || prospects.length === 0 ? (
              <EmptyState size="sm" className="py-12">
                <EmptyState.Header>
                  <EmptyState.FeaturedIcon color="gray" icon={SearchLg} />
                </EmptyState.Header>
                <EmptyState.Content>
                  <EmptyState.Title>Aucun prospect pour l&apos;instant</EmptyState.Title>
                  <EmptyState.Description>Ajoute ta premiere entreprise.</EmptyState.Description>
                </EmptyState.Content>
              </EmptyState>
            ) : (
              <table className="w-full">
                <thead className="h-11 bg-secondary">
                  <tr>
                    <th className="px-6 py-2 text-left text-xs font-semibold text-quaternary">Nom</th>
                    <th className="px-6 py-2 text-left text-xs font-semibold text-quaternary">Domaine</th>
                    <th className="px-6 py-2 text-left text-xs font-semibold text-quaternary">Statut</th>
                    <th className="px-6 py-2 text-left text-xs font-semibold text-quaternary">Enrichissement</th>
                    <th className="px-6 py-2 text-left text-xs font-semibold text-quaternary">Ajoute le</th>
                  </tr>
                </thead>
                <tbody>
                  {prospects.map((prospect) => (
                    <tr
                      key={prospect.id}
                      className="h-16 cursor-pointer border-t border-secondary hover:bg-secondary"
                      onClick={() => setSelectedId(prospect.id)}
                    >
                      <td className="px-6 py-3 text-sm font-medium text-primary">
                        {prospect.name}
                        {(prospect.phone || prospect.email) && (
                          <p className="mt-0.5 text-xs font-normal text-tertiary">
                            {[prospect.phone, prospect.email].filter(Boolean).join(" · ")}
                          </p>
                        )}
                      </td>
                      <td className="px-6 py-3 text-sm text-tertiary">{prospect.domain ?? "—"}</td>
                      <td className="px-6 py-3">
                        <StatusBadge status={prospect.status} />
                      </td>
                      <td className="px-6 py-3 text-sm text-tertiary">
                        <div className="flex items-center gap-3">
                          {prospect.trustpilot_rating !== null && (
                            <span className="flex items-center gap-1">
                              <Star01 className="size-3.5 text-warning-primary" />
                              {prospect.trustpilot_rating.toFixed(1)}
                            </span>
                          )}
                          {prospect.ai_needs.length > 0 && (
                            <span className="flex items-center gap-1">
                              <Stars02 className="size-3.5 text-utility-blue-500" />
                              {prospect.ai_needs.length}
                            </span>
                          )}
                          {prospect.trustpilot_rating === null && prospect.ai_needs.length === 0 && "—"}
                        </div>
                      </td>
                      <td className="px-6 py-3 text-sm text-tertiary">
                        {new Date(prospect.created_at).toLocaleDateString("fr-FR")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <ProspectDetailDialog id={selectedId} onOpenChange={(open) => !open && setSelectedId(null)} />
      </AppShell>
    </AuthGuard>
  );
}
