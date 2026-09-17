import { useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Link from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Snackbar from "@mui/material/Snackbar";
import Alert from "@mui/material/Alert";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import ThumbUpAltOutlinedIcon from "@mui/icons-material/ThumbUpAltOutlined";
import ThumbDownAltOutlinedIcon from "@mui/icons-material/ThumbDownAltOutlined";
import AddTaskIcon from "@mui/icons-material/AddTask";
import { useNavigate, useParams } from "react-router-dom";
import { useJob } from "../hooks/useJobs";
import { useCreateApplication } from "../hooks/useApplications";
import { useMatchFeedback } from "../hooks/useProfiles";
import { useAuthStore } from "../store/authStore";
import RiskBadge from "../components/jobs/RiskBadge";
import LoadingState from "../components/common/LoadingState";
import ErrorState from "../components/common/ErrorState";

function formatRate(job: { rate_min: string | null; rate_max: string | null; rate_currency: string | null; rate_period: string | null }): string {
  if (!job.rate_min && !job.rate_max) return "TJM non precise";
  const currency = job.rate_currency ?? "";
  if (job.rate_min && job.rate_max && job.rate_min !== job.rate_max) {
    return `${job.rate_min} - ${job.rate_max} ${currency}${job.rate_period ? ` / ${job.rate_period}` : ""}`;
  }
  const value = job.rate_min ?? job.rate_max;
  return `${value} ${currency}${job.rate_period ? ` / ${job.rate_period}` : ""}`;
}

export default function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { data: job, isLoading, isError, error, refetch } = useJob(jobId ?? null);
  const activeProfileId = useAuthStore((s) => s.activeProfileId);
  const createApplication = useCreateApplication(activeProfileId ?? "");
  const matchFeedback = useMatchFeedback(activeProfileId ?? "");
  const [feedback, setFeedback] = useState<{ severity: "success" | "error"; message: string } | null>(
    null,
  );

  if (isLoading) return <LoadingState label="Chargement de l'offre..." />;
  if (isError || !job) {
    return (
      <ErrorState
        message={error instanceof Error ? error.message : "Offre introuvable"}
        onRetry={() => refetch()}
      />
    );
  }

  const requireProfile = (action: () => void) => {
    if (!activeProfileId) {
      setFeedback({ severity: "error", message: "Selectionnez un profil actif dans la barre du haut." });
      return;
    }
    action();
  };

  return (
    <Box>
      <Button startIcon={<ArrowBackIcon />} onClick={() => navigate(-1)} sx={{ mb: 2 }}>
        Retour
      </Button>
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" gap={2}>
          <Box>
            <Typography variant="h5" fontWeight={700}>
              {job.title}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {job.seniority ?? "Seniorite non precisee"} · {job.contract_type ?? "Contrat non precise"} ·{" "}
              {job.remote_type ?? "Remote non precise"}
            </Typography>
          </Box>
          <RiskBadge score={job.risk_score} reasons={job.risk_reasons} />
        </Stack>

        <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mt: 2, rowGap: 1 }}>
          <Chip label={formatRate(job)} />
          {job.timezone_constraint && <Chip variant="outlined" label={job.timezone_constraint} />}
          {job.required_languages.map((lang) => (
            <Chip key={lang} variant="outlined" size="small" label={lang} />
          ))}
        </Stack>

        <Stack direction="row" spacing={1.5} sx={{ mt: 3 }} flexWrap="wrap" useFlexGap>
          <Button
            variant="contained"
            startIcon={<AddTaskIcon />}
            onClick={() =>
              requireProfile(() =>
                createApplication.mutate(job.id, {
                  onSuccess: () => setFeedback({ severity: "success", message: "Ajoutee au pipeline." }),
                  onError: () => setFeedback({ severity: "error", message: "Echec de l'ajout." }),
                }),
              )
            }
          >
            Ajouter au pipeline
          </Button>
          <Button
            variant="outlined"
            color="success"
            startIcon={<ThumbUpAltOutlinedIcon />}
            onClick={() =>
              requireProfile(() =>
                matchFeedback.mutate(
                  { jobId: job.id, action: "saved" },
                  {
                    onSuccess: () => setFeedback({ severity: "success", message: "Marquee comme interessante." }),
                  },
                ),
              )
            }
          >
            Interessant
          </Button>
          <Button
            variant="outlined"
            color="error"
            startIcon={<ThumbDownAltOutlinedIcon />}
            onClick={() =>
              requireProfile(() =>
                matchFeedback.mutate(
                  { jobId: job.id, action: "rejected" },
                  {
                    onSuccess: () => setFeedback({ severity: "success", message: "Marquee comme non pertinente." }),
                  },
                ),
              )
            }
          >
            Pas interesse
          </Button>
          <Button
            variant="text"
            component={Link}
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            endIcon={<OpenInNewIcon />}
          >
            Voir l'annonce originale
          </Button>
        </Stack>

        <Divider sx={{ my: 3 }} />

        <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1 }}>
          Description
        </Typography>
        <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
          {job.description_clean}
        </Typography>

        {job.duplicate_urls.length > 0 && (
          <>
            <Divider sx={{ my: 3 }} />
            <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1 }}>
              Egalement publiee sur
            </Typography>
            <Stack spacing={0.5}>
              {job.duplicate_urls.map((url) => (
                <Link key={url} href={url} target="_blank" rel="noopener noreferrer" variant="body2">
                  {url}
                </Link>
              ))}
            </Stack>
          </>
        )}
      </Paper>

      <Snackbar
        open={Boolean(feedback)}
        autoHideDuration={3000}
        onClose={() => setFeedback(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        {feedback ? (
          <Alert severity={feedback.severity} onClose={() => setFeedback(null)}>
            {feedback.message}
          </Alert>
        ) : undefined}
      </Snackbar>
    </Box>
  );
}
