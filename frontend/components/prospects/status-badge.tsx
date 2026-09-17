import { Badge } from "@/components/ui/badge";
import type { ProspectStatus } from "@/lib/prospects-api";

const STATUS_CONFIG: Record<ProspectStatus, { label: string; className: string }> = {
  new: { label: "Nouveau", className: "bg-muted text-muted-foreground" },
  contacted: { label: "Contacte", className: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300" },
  replied: {
    label: "Repondu",
    className: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  },
  converted: {
    label: "Converti",
    className: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  },
  lost: { label: "Perdu", className: "bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300" },
};

export const STATUS_OPTIONS = Object.entries(STATUS_CONFIG).map(([value, config]) => ({
  value: value as ProspectStatus,
  label: config.label,
}));

export function StatusBadge({ status }: { status: ProspectStatus }) {
  const config = STATUS_CONFIG[status];
  return <Badge className={config.className}>{config.label}</Badge>;
}
