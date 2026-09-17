import { useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Grid from "@mui/material/Grid2";
import Pagination from "@mui/material/Pagination";
import Snackbar from "@mui/material/Snackbar";
import Alert from "@mui/material/Alert";
import ViewListIcon from "@mui/icons-material/ViewList";
import ViewModuleIcon from "@mui/icons-material/ViewModule";
import { useJobSearch } from "../hooks/useJobs";
import { useCreateApplication } from "../hooks/useApplications";
import { useAuthStore } from "../store/authStore";
import JobFilters from "../components/jobs/JobFilters";
import JobTable from "../components/jobs/JobTable";
import JobCard from "../components/jobs/JobCard";
import LoadingState from "../components/common/LoadingState";
import EmptyState from "../components/common/EmptyState";
import ErrorState from "../components/common/ErrorState";
import type { Job, JobSearchFilters } from "../api/types";

const PAGE_SIZE = 25;

export default function JobsSearchPage() {
  const [filters, setFilters] = useState<JobSearchFilters>({
    sort: "relevance",
    limit: PAGE_SIZE,
    offset: 0,
  });
  const [view, setView] = useState<"table" | "card">("table");
  const [feedback, setFeedback] = useState<{ severity: "success" | "error"; message: string } | null>(
    null,
  );

  const activeProfileId = useAuthStore((s) => s.activeProfileId);
  const { data, isLoading, isError, error, refetch, isFetching } = useJobSearch(filters);
  const createApplication = useCreateApplication(activeProfileId ?? "");

  const handleAddToPipeline = (job: Job) => {
    if (!activeProfileId) {
      setFeedback({ severity: "error", message: "Selectionnez un profil actif pour utiliser le pipeline." });
      return;
    }
    createApplication.mutate(job.id, {
      onSuccess: () => setFeedback({ severity: "success", message: "Offre ajoutee au pipeline." }),
      onError: () => setFeedback({ severity: "error", message: "Impossible d'ajouter cette offre." }),
    });
  };

  const page = Math.floor((filters.offset ?? 0) / PAGE_SIZE) + 1;
  const pageCount = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} sx={{ mb: 2 }}>
        Recherche d'offres
      </Typography>
      <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start", flexWrap: "wrap", mb: 2 }}>
        <Box sx={{ flexGrow: 1, minWidth: 280 }}>
          <JobFilters filters={filters} onChange={setFilters} />
        </Box>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={view}
          onChange={(_event, value) => value && setView(value)}
          aria-label="Mode d'affichage"
        >
          <ToggleButton value="table" aria-label="Vue tableau">
            <ViewListIcon fontSize="small" />
          </ToggleButton>
          <ToggleButton value="card" aria-label="Vue cartes">
            <ViewModuleIcon fontSize="small" />
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {isLoading && <LoadingState label="Recherche des offres..." />}
      {isError && (
        <ErrorState
          message={error instanceof Error ? error.message : "Erreur inconnue"}
          onRetry={() => refetch()}
        />
      )}
      {!isLoading && !isError && data && data.results.length === 0 && (
        <EmptyState
          title="Aucune offre ne correspond a ces criteres"
          description="Essayez d'elargir vos filtres (TJM, seniorite, remote)."
        />
      )}
      {!isLoading && !isError && data && data.results.length > 0 && (
        <>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            {data.total} offre(s) trouvee(s) {isFetching && "· actualisation..."}
          </Typography>
          {view === "table" ? (
            <JobTable
              rows={data.results.map((result) => ({ job: result.job }))}
              onAddToPipeline={handleAddToPipeline}
            />
          ) : (
            <Grid container spacing={2}>
              {data.results.map((result) => (
                <Grid key={result.job.id} size={{ xs: 12, sm: 6, lg: 4 }}>
                  <JobCard job={result.job} onAddToPipeline={handleAddToPipeline} />
                </Grid>
              ))}
            </Grid>
          )}
          <Box sx={{ display: "flex", justifyContent: "center", mt: 3 }}>
            <Pagination
              page={page}
              count={pageCount}
              onChange={(_event, value) =>
                setFilters((prev) => ({ ...prev, offset: (value - 1) * PAGE_SIZE }))
              }
              color="primary"
            />
          </Box>
        </>
      )}

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
