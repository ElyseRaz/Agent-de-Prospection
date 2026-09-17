import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import type { Application, ApplicationStage } from "../../api/types";
import ApplicationCard from "./ApplicationCard";
import { STAGE_LABELS, STAGE_ORDER } from "./stages";

interface KanbanBoardProps {
  applications: Application[];
  onChangeStage: (applicationId: string, stage: ApplicationStage) => void;
  onOpen: (applicationId: string) => void;
}

export default function KanbanBoard({ applications, onChangeStage, onOpen }: KanbanBoardProps) {
  return (
    <Box sx={{ display: "flex", gap: 2, overflowX: "auto", pb: 2 }}>
      {STAGE_ORDER.map((stage) => {
        const columnApplications = applications.filter((application) => application.stage === stage);
        return (
          <Paper
            key={stage}
            variant="outlined"
            sx={{ minWidth: 260, width: 260, flexShrink: 0, bgcolor: "grey.50", p: 1.5 }}
          >
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1.5 }}>
              <Typography variant="subtitle2">{STAGE_LABELS[stage]}</Typography>
              <Chip size="small" label={columnApplications.length} />
            </Box>
            <Box sx={{ minHeight: 40 }}>
              {columnApplications.map((application) => (
                <ApplicationCard
                  key={application.id}
                  application={application}
                  onChangeStage={(newStage) => onChangeStage(application.id, newStage)}
                  onOpen={() => onOpen(application.id)}
                />
              ))}
              {columnApplications.length === 0 && (
                <Typography variant="caption" color="text.secondary">
                  Aucune candidature
                </Typography>
              )}
            </Box>
          </Paper>
        );
      })}
    </Box>
  );
}
