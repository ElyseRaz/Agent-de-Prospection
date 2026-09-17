import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import LinearProgress from "@mui/material/LinearProgress";
import type { ScoreBreakdownItem } from "../../api/types";

interface MatchScoreChipProps {
  score: number;
  breakdown?: ScoreBreakdownItem[];
}

function scoreColor(score: number): "success" | "warning" | "default" {
  if (score >= 70) return "success";
  if (score >= 40) return "warning";
  return "default";
}

export default function MatchScoreChip({ score, breakdown }: MatchScoreChipProps) {
  const chip = <Chip size="small" color={scoreColor(score)} label={`Match ${Math.round(score)}%`} />;

  if (!breakdown || breakdown.length === 0) {
    return chip;
  }

  return (
    <Tooltip
      arrow
      title={
        <Box sx={{ p: 0.5, minWidth: 200 }}>
          {breakdown.map((item) => (
            <Box key={item.criterion} sx={{ mb: 0.75 }}>
              <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                <Typography variant="caption">{item.label}</Typography>
                <Typography variant="caption">{Math.round(item.points)}</Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={Math.min(100, Math.max(0, item.points))}
                sx={{ height: 4, borderRadius: 2 }}
              />
            </Box>
          ))}
        </Box>
      }
    >
      {chip}
    </Tooltip>
  );
}
