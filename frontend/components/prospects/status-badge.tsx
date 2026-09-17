import { Badge } from "@/components/base/badges/badges";
import type { BadgeColor } from "@/components/base/badges/badges";
import type { ProspectStatus } from "@/lib/prospects-api";

const STATUS_CONFIG: Record<ProspectStatus, { label: string; color: BadgeColor<"pill-color"> }> = {
  new: { label: "Nouveau", color: "gray" },
  contacted: { label: "Contacte", color: "blue" },
  replied: { label: "Repondu", color: "warning" },
  converted: { label: "Converti", color: "success" },
  lost: { label: "Perdu", color: "error" },
};

export const STATUS_OPTIONS = Object.entries(STATUS_CONFIG).map(([value, config]) => ({
  value: value as ProspectStatus,
  label: config.label,
}));

export function StatusBadge({ status }: { status: ProspectStatus }) {
  const config = STATUS_CONFIG[status];
  return <Badge color={config.color}>{config.label}</Badge>;
}
