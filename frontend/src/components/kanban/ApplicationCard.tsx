import { useState } from "react";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import EventIcon from "@mui/icons-material/Event";
import { useNavigate } from "react-router-dom";
import { useJob } from "../../hooks/useJobs";
import type { Application, ApplicationStage } from "../../api/types";
import { STAGE_LABELS, STAGE_ORDER } from "./stages";

interface ApplicationCardProps {
  application: Application;
  onChangeStage: (stage: ApplicationStage) => void;
  onOpen: () => void;
}

export default function ApplicationCard({ application, onChangeStage, onOpen }: ApplicationCardProps) {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const { data: job, isLoading } = useJob(application.job_id);
  const navigate = useNavigate();

  const isOverdue =
    application.next_followup_at !== null && new Date(application.next_followup_at) < new Date();

  return (
    <Card variant="outlined" sx={{ mb: 1.5 }}>
      <CardContent sx={{ p: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
          <Box sx={{ minWidth: 0, cursor: "pointer" }} onClick={onOpen}>
            {isLoading ? (
              <Skeleton width={140} />
            ) : (
              <Typography variant="body2" fontWeight={600} noWrap sx={{ maxWidth: 170 }}>
                {job?.title ?? "Offre supprimee"}
              </Typography>
            )}
          </Box>
          <IconButton
            size="small"
            onClick={(event) => setAnchorEl(event.currentTarget)}
            aria-label="Changer d'etape"
          >
            <MoreVertIcon fontSize="small" />
          </IconButton>
          <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}>
            {STAGE_ORDER.filter((stage) => stage !== application.stage).map((stage) => (
              <MenuItem
                key={stage}
                onClick={() => {
                  setAnchorEl(null);
                  onChangeStage(stage);
                }}
              >
                Deplacer vers {STAGE_LABELS[stage]}
              </MenuItem>
            ))}
            <MenuItem
              onClick={() => {
                setAnchorEl(null);
                navigate(`/jobs/${application.job_id}`);
              }}
            >
              Voir l'offre
            </MenuItem>
          </Menu>
        </Stack>
        <Stack direction="row" spacing={0.75} flexWrap="wrap" sx={{ mt: 1, rowGap: 0.75 }}>
          {application.expected_value && (
            <Chip size="small" variant="outlined" label={`${application.expected_value} EUR`} />
          )}
          {application.next_followup_at && (
            <Tooltip title="Prochaine relance">
              <Chip
                size="small"
                color={isOverdue ? "error" : "default"}
                variant={isOverdue ? "filled" : "outlined"}
                icon={<EventIcon fontSize="small" />}
                label={new Date(application.next_followup_at).toLocaleDateString("fr-FR")}
              />
            </Tooltip>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
