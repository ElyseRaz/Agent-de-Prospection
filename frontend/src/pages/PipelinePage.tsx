import { useState } from "react";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import CloseIcon from "@mui/icons-material/Close";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import { useNavigate } from "react-router-dom";
import {
  useApplication,
  useApplications,
  useDeleteApplication,
  useUpdateApplication,
  useUpdateApplicationStage,
} from "../hooks/useApplications";
import { useAuthStore } from "../store/authStore";
import KanbanBoard from "../components/kanban/KanbanBoard";
import LoadingState from "../components/common/LoadingState";
import EmptyState from "../components/common/EmptyState";
import ErrorState from "../components/common/ErrorState";
import { STAGE_LABELS, STAGE_ORDER } from "../components/kanban/stages";
import type { ApplicationStage } from "../api/types";

function ApplicationDetailDialog({
  profileId,
  applicationId,
  onClose,
}: {
  profileId: string;
  applicationId: string;
  onClose: () => void;
}) {
  const { data: application, isLoading } = useApplication(profileId, applicationId);
  const updateApplication = useUpdateApplication(profileId, applicationId);
  const deleteApplication = useDeleteApplication(profileId);
  const navigate = useNavigate();
  const [notes, setNotes] = useState<string | null>(null);
  const [followup, setFollowup] = useState<string | null>(null);

  const currentNotes = notes ?? application?.notes ?? "";
  const currentFollowup = followup ?? (application?.next_followup_at?.slice(0, 10) ?? "");

  return (
    <Dialog open onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        {isLoading ? "Chargement..." : application?.job.title}
        <IconButton onClick={onClose} aria-label="Fermer">
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        {isLoading || !application ? (
          <LoadingState />
        ) : (
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              select
              label="Etape"
              size="small"
              value={application.stage}
              disabled
              helperText="Utilisez le menu de la carte pour changer d'etape"
            >
              {STAGE_ORDER.map((stage) => (
                <MenuItem key={stage} value={stage}>
                  {STAGE_LABELS[stage]}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Notes"
              multiline
              minRows={3}
              value={currentNotes}
              onChange={(event) => setNotes(event.target.value)}
            />
            <TextField
              label="Prochaine relance"
              type="date"
              value={currentFollowup}
              onChange={(event) => setFollowup(event.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <Stack direction="row" spacing={1.5} justifyContent="space-between">
              <Button
                color="error"
                startIcon={<DeleteOutlineIcon />}
                onClick={() => deleteApplication.mutate(application.id, { onSuccess: onClose })}
              >
                Retirer du pipeline
              </Button>
              <Stack direction="row" spacing={1}>
                <Button onClick={() => navigate(`/jobs/${application.job_id}`)}>Voir l'offre</Button>
                <Button
                  variant="contained"
                  onClick={() =>
                    updateApplication.mutate(
                      {
                        notes: currentNotes || null,
                        next_followup_at: currentFollowup ? new Date(currentFollowup).toISOString() : null,
                      },
                      { onSuccess: onClose },
                    )
                  }
                >
                  Enregistrer
                </Button>
              </Stack>
            </Stack>
          </Stack>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function PipelinePage() {
  const activeProfileId = useAuthStore((s) => s.activeProfileId);
  const { data: applications, isLoading, isError, error, refetch } = useApplications(activeProfileId);
  const updateStage = useUpdateApplicationStage(activeProfileId ?? "");
  const [openApplicationId, setOpenApplicationId] = useState<string | null>(null);

  if (!activeProfileId) {
    return (
      <EmptyState
        title="Aucun profil actif"
        description="Selectionnez un profil dans la barre du haut pour suivre votre pipeline de candidatures."
      />
    );
  }

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} sx={{ mb: 2 }}>
        Pipeline de candidatures
      </Typography>
      {isLoading && <LoadingState label="Chargement du pipeline..." />}
      {isError && (
        <ErrorState message={error instanceof Error ? error.message : "Erreur inconnue"} onRetry={() => refetch()} />
      )}
      {!isLoading && !isError && applications && applications.length === 0 && (
        <EmptyState
          title="Pipeline vide"
          description="Ajoutez des offres depuis la recherche ou une fiche offre pour commencer a suivre vos candidatures."
        />
      )}
      {!isLoading && !isError && applications && applications.length > 0 && (
        <KanbanBoard
          applications={applications}
          onChangeStage={(applicationId, stage: ApplicationStage) =>
            updateStage.mutate({ applicationId, stage })
          }
          onOpen={setOpenApplicationId}
        />
      )}
      {openApplicationId && (
        <ApplicationDetailDialog
          profileId={activeProfileId}
          applicationId={openApplicationId}
          onClose={() => setOpenApplicationId(null)}
        />
      )}
    </Box>
  );
}
