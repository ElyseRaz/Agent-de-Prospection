import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import Box from "@mui/material/Box";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import type { RiskReason } from "../../api/types";

interface RiskBadgeProps {
  score: number;
  reasons: RiskReason[];
}

function riskLevel(score: number): { label: string; color: "success" | "warning" | "error" } {
  if (score >= 66) return { label: "Risque eleve", color: "error" };
  if (score >= 33) return { label: "Risque modere", color: "warning" };
  return { label: "Risque faible", color: "success" };
}

export default function RiskBadge({ score, reasons }: RiskBadgeProps) {
  const level = riskLevel(score);

  const tooltipContent = (
    <Box sx={{ p: 0.5 }}>
      {reasons.length === 0 ? (
        <span>Aucun signal de risque detecte.</span>
      ) : (
        <Box component="ul" sx={{ m: 0, pl: 2 }}>
          {reasons.map((reason) => (
            <li key={reason.code}>{reason.label}</li>
          ))}
        </Box>
      )}
    </Box>
  );

  return (
    <Tooltip title={tooltipContent} arrow>
      <Chip
        size="small"
        color={level.color}
        variant={reasons.length > 0 ? "filled" : "outlined"}
        icon={reasons.length > 0 ? <WarningAmberIcon /> : <CheckCircleOutlineIcon />}
        label={`${level.label} (${score})`}
      />
    </Tooltip>
  );
}
