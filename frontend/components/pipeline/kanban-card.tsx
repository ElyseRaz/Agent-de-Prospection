"use client";

import { toast } from "sonner";
import { Star01, Stars02 } from "@untitledui/icons";

import { NativeSelect } from "@/components/base/select/select-native";
import { STATUS_OPTIONS } from "@/components/prospects/status-badge";
import { useUpdateProspect } from "@/hooks/use-prospects";
import type { Company, ProspectStatus } from "@/lib/prospects-api";
import { ApiError } from "@/lib/api";
import { cx } from "@/lib/utils/cx";

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
      className={cx(
        "flex cursor-pointer flex-col gap-2 rounded-md bg-primary p-3 text-sm shadow-xs ring-1 ring-secondary transition-opacity hover:ring-brand",
        isDragging ? "opacity-40" : "opacity-100",
      )}
    >
      <p className="font-medium text-primary">{prospect.name}</p>
      {prospect.domain && <p className="text-xs text-tertiary">{prospect.domain}</p>}

      {(prospect.trustpilot_rating !== null || prospect.ai_needs.length > 0) && (
        <div className="flex items-center gap-3 text-xs text-tertiary">
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
        </div>
      )}

      <div onClick={(e) => e.stopPropagation()}>
        <NativeSelect
          size="sm"
          value={prospect.status}
          onChange={(e) => handleStatusChange(e.target.value as ProspectStatus)}
          disabled={updateProspect.isPending}
          options={STATUS_OPTIONS}
        />
      </div>
    </div>
  );
}
