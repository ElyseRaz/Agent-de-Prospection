"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { STATUS_OPTIONS } from "@/components/prospects/status-badge";
import { KanbanCard } from "@/components/pipeline/kanban-card";
import { useProspects } from "@/hooks/use-prospects";
import { updateProspect as updateProspectRequest } from "@/lib/prospects-api";
import type { Company, ProspectStatus } from "@/lib/prospects-api";
import { ApiError } from "@/lib/api";

function KanbanColumnDropZone({
  status,
  label,
  prospects,
  draggedId,
  onOpen,
  onDragStartCard,
  onDragEndCard,
  onDropStatus,
}: {
  status: ProspectStatus;
  label: string;
  prospects: Company[];
  draggedId: string | null;
  onOpen: (id: string) => void;
  onDragStartCard: (id: string) => void;
  onDragEndCard: () => void;
  onDropStatus: (id: string, status: ProspectStatus) => void;
}) {
  const [isOver, setIsOver] = useState(false);

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
        if (!isOver) setIsOver(true);
      }}
      onDragLeave={() => setIsOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsOver(false);
        const id = e.dataTransfer.getData("text/plain");
        if (id) onDropStatus(id, status);
      }}
      className={`flex w-72 shrink-0 flex-col gap-2 rounded-lg border bg-muted/30 p-2.5 transition-colors ${
        isOver ? "border-primary bg-primary/5" : ""
      }`}
    >
      <div className="flex items-center justify-between px-1">
        <p className="text-sm font-semibold">{label}</p>
        <span className="text-xs text-muted-foreground">{prospects.length}</span>
      </div>
      <div className="flex min-h-16 flex-col gap-2">
        {prospects.length === 0 ? (
          <p className="rounded-md border border-dashed p-3 text-center text-xs text-muted-foreground">
            Aucun prospect
          </p>
        ) : (
          prospects.map((prospect) => (
            <KanbanCard
              key={prospect.id}
              prospect={prospect}
              onOpen={onOpen}
              onDragStart={onDragStartCard}
              onDragEnd={onDragEndCard}
              isDragging={draggedId === prospect.id}
            />
          ))
        )}
      </div>
    </div>
  );
}

export function KanbanBoard({ onOpen }: { onOpen: (id: string) => void }) {
  const { data: prospects, isLoading } = useProspects({});
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const handleDropStatus = async (id: string, status: ProspectStatus) => {
    const prospect = prospects?.find((p) => p.id === id);
    if (!prospect || prospect.status === status) return;
    try {
      await updateProspectRequest(id, { status });
      queryClient.invalidateQueries({ queryKey: ["prospects"] });
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Erreur lors du changement de statut");
    }
  };

  if (isLoading) {
    return <div className="p-8 text-center text-sm text-muted-foreground">Chargement...</div>;
  }

  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {STATUS_OPTIONS.map((option) => (
        <KanbanColumnDropZone
          key={option.value}
          status={option.value}
          label={option.label}
          prospects={(prospects ?? []).filter((p) => p.status === option.value)}
          draggedId={draggedId}
          onOpen={onOpen}
          onDragStartCard={setDraggedId}
          onDragEndCard={() => setDraggedId(null)}
          onDropStatus={handleDropStatus}
        />
      ))}
    </div>
  );
}
