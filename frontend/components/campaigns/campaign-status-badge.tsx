import { Badge } from "@/components/base/badges/badges";
import type { BadgeColor } from "@/components/base/badges/badges";
import type { CampaignStatus } from "@/lib/campaigns-api";

const STATUS_CONFIG: Record<CampaignStatus, { label: string; color: BadgeColor<"pill-color"> }> = {
  draft: { label: "Brouillon", color: "gray" },
  sending: { label: "Envoi en cours", color: "blue" },
  sent: { label: "Envoyee", color: "success" },
};

export function CampaignStatusBadge({ status }: { status: CampaignStatus }) {
  const config = STATUS_CONFIG[status];
  return <Badge color={config.color}>{config.label}</Badge>;
}
