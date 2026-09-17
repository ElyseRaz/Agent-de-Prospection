"use client";

import { useState } from "react";

import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/layout/app-shell";
import { KanbanBoard } from "@/components/pipeline/kanban-board";
import { ProspectDetailDialog } from "@/components/prospects/prospect-detail-dialog";

export default function PipelinePage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  return (
    <AuthGuard>
      <AppShell>
        <div className="flex flex-col gap-6">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Suivi</h1>
            <p className="text-muted-foreground">
              Glisse une fiche vers une autre colonne pour changer son statut, ou utilise le menu
              deroulant de la fiche.
            </p>
          </div>

          <KanbanBoard onOpen={setSelectedId} />
        </div>

        <ProspectDetailDialog id={selectedId} onOpenChange={(open) => !open && setSelectedId(null)} />
      </AppShell>
    </AuthGuard>
  );
}
