"use client";

import { Sparkles, Star } from "lucide-react";

import { STATUS_OPTIONS } from "@/components/prospects/status-badge";
import { useUpdateProspect } from "@/hooks/use-prospects";
import type { Company, ProspectStatus } from "@/lib/prospects-api";
import { ApiError } from "@/lib/api";
import { toast } from "sonner";

interface KanbanCardProps {
  prospect: Company;
  onOpen: (id: string) => void;
  onDragStart: (id: string) => void;
  onDragEnd: () => void;
  isDragging: boolean;
}

export function KanbanCard({ prospect, onOpen, onDragStart, onDragEnd, isDragging }: KanbanCardProps) {
  const updateProspect = useUpdateProspect(prospect.id);

  const handleStatusChange = async (status: ProspectStatus) => {
    try {
      await updateProspect.mutateAsync({ status });
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Erreur lors du changement de statut");
    }
  };

  return (
    <div
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData("text/plain", prospect.id);
        e.dataTransfer.effectAllowed = "move";
        onDragStart(prospect.id);
      }}
      onDragEnd={onDragEnd}
      onClick={() => onOpen(prospect.id)}
      className={`flex cursor-pointer flex-col gap-2 rounded-md border bg-card p-3 text-sm shadow-sm transition-opacity hover:border-primary/50 ${
        isDragging ? "opacity-40" : "opacity-100"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="font-medium">{prospect.name}</p>
      </div>
      {prospect.domain && <p className="text-xs text-muted-foreground">{prospect.domain}</p>}

      {(prospect.trustpilot_rating !== null || prospect.ai_needs.length > 0) && (
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {prospect.trustpilot_rating !== null && (
            <span className="flex items-center gap-1">
              <Star className="size-3.5 text-amber-500" />
              {prospect.trustpilot_rating.toFixed(1)}
            </span>
          )}
          {prospect.ai_needs.length > 0 && (
            <span className="flex items-center gap-1">
              <Sparkles className="size-3.5 text-primary" />
              {prospect.ai_needs.length}
            </span>
          )}
        </div>
      )}

      <select
        value={prospect.status}
        onClick={(e) => e.stopPropagation()}
        onChange={(e) => handleStatusChange(e.target.value as ProspectStatus)}
        disabled={updateProspect.isPending}
        className="h-7 rounded-md border border-input bg-transparent px-1.5 text-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        {STATUS_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
