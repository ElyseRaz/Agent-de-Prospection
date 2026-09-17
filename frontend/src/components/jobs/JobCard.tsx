import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import AddTaskIcon from "@mui/icons-material/AddTask";
import { useNavigate } from "react-router-dom";
import type { Job, ScoreBreakdownItem } from "../../api/types";
import RiskBadge from "./RiskBadge";
import MatchScoreChip from "./MatchScoreChip";

interface JobCardProps {
  job: Job;
  score?: number;
  breakdown?: ScoreBreakdownItem[];
  onAddToPipeline?: (job: Job) => void;
}

function formatRate(job: Job): string {
  if (!job.rate_min && !job.rate_max) return "TJM non precise";
  const currency = job.rate_currency ?? "";
  if (job.rate_min && job.rate_max && job.rate_min !== job.rate_max) {
    return `${job.rate_min}-${job.rate_max} ${currency}${job.rate_period ? `/${job.rate_period}` : ""}`;
  }
  const value = job.rate_min ?? job.rate_max;
  return `${value} ${currency}${job.rate_period ? `/${job.rate_period}` : ""}`;
}

export default function JobCard({ job, score, breakdown, onAddToPipeline }: JobCardProps) {
  const navigate = useNavigate();

  return (
    <Card variant="outlined">
      <CardActionArea onClick={() => navigate(`/jobs/${job.id}`)}>
        <CardContent>
          <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={1}>
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="subtitle1" fontWeight={700} noWrap>
                {job.title}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {job.seniority ?? "Seniorite non precisee"} · {job.contract_type ?? "Contrat non precise"}
              </Typography>
            </Box>
            {score !== undefined && <MatchScoreChip score={score} breakdown={breakdown} />}
          </Stack>
          <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mt: 1.5, rowGap: 1 }}>
            {job.remote_type && <Chip size="small" variant="outlined" label={job.remote_type} />}
            <Chip size="small" variant="outlined" label={formatRate(job)} />
            <RiskBadge score={job.risk_score} reasons={job.risk_reasons} />
          </Stack>
        </CardContent>
      </CardActionArea>
      {onAddToPipeline && (
        <Box sx={{ display: "flex", justifyContent: "flex-end", px: 1, pb: 1 }}>
          <Tooltip title="Ajouter au pipeline">
            <IconButton
              size="small"
              onClick={(event) => {
                event.stopPropagation();
                onAddToPipeline(job);
              }}
              aria-label="Ajouter au pipeline"
            >
              <AddTaskIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      )}
    </Card>
  );
}
