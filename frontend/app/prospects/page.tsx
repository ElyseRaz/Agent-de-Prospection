"use client";

import { useState } from "react";
import { Search, Building2 } from "lucide-react";

import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/layout/app-shell";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent } from "@/components/ui/card";
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
              <h1 className="text-2xl font-semibold tracking-tight">Prospects</h1>
              <p className="text-muted-foreground">
                Tes entreprises, ajoutees une a une ou par import — jamais collectees automatiquement.
              </p>
            </div>
            <div className="flex gap-2">
              <ImportDialog />
              <AddProspectDialog />
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[220px]">
              <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Rechercher par nom ou domaine..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-8"
              />
            </div>
            <Select value={status} onValueChange={(value) => setStatus(value as ProspectStatus | "tout")}>
              <SelectTrigger className="w-44">
                <SelectValue placeholder="Statut" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="tout">Tous les statuts</SelectItem>
                {STATUS_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Card>
            <CardContent className="p-0">
              {isLoading ? (
                <div className="p-8 text-center text-sm text-muted-foreground">Chargement...</div>
              ) : !prospects || prospects.length === 0 ? (
                <div className="flex flex-col items-center gap-2 p-12 text-center">
                  <Building2 className="size-8 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">
                    Aucun prospect pour l&apos;instant. Ajoute ta premiere entreprise.
                  </p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nom</TableHead>
                      <TableHead>Domaine</TableHead>
                      <TableHead>Statut</TableHead>
                      <TableHead>Ajoute le</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {prospects.map((prospect) => (
                      <TableRow
                        key={prospect.id}
                        className="cursor-pointer"
                        onClick={() => setSelectedId(prospect.id)}
                      >
                        <TableCell className="font-medium">{prospect.name}</TableCell>
                        <TableCell className="text-muted-foreground">{prospect.domain ?? "—"}</TableCell>
                        <TableCell>
                          <StatusBadge status={prospect.status} />
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {new Date(prospect.created_at).toLocaleDateString("fr-FR")}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>

        <ProspectDetailDialog id={selectedId} onOpenChange={(open) => !open && setSelectedId(null)} />
      </AppShell>
    </AuthGuard>
  );
}
