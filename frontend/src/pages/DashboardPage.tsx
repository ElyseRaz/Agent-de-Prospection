import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid2";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useNavigate } from "react-router-dom";
import { useApplications } from "../hooks/useApplications";
import { useProfileMatches } from "../hooks/useProfiles";
import { useAuthStore } from "../store/authStore";
import { STAGE_LABELS, STAGE_ORDER } from "../components/kanban/stages";
import MatchScoreChip from "../components/jobs/MatchScoreChip";
import LoadingState from "../components/common/LoadingState";
import EmptyState from "../components/common/EmptyState";

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Paper variant="outlined" sx={{ p: 2.5 }}>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="h4" fontWeight={700} sx={{ mt: 0.5 }}>
        {value}
      </Typography>
    </Paper>
  );
}

export default function DashboardPage() {
  const activeProfileId = useAuthStore((s) => s.activeProfileId);
  const navigate = useNavigate();
  const { data: applications, isLoading: applicationsLoading } = useApplications(activeProfileId);
  const { data: matches, isLoading: matchesLoading } = useProfileMatches(activeProfileId, 5);

  if (!activeProfileId) {
    return (
      <EmptyState
        title="Aucun profil actif"
        description="Selectionnez ou creez un profil pour voir votre tableau de bord personnalise."
      />
    );
  }

  const stageData = STAGE_ORDER.map((stage) => ({
    stage: STAGE_LABELS[stage],
    count: applications?.filter((application) => application.stage === stage).length ?? 0,
  }));

  const wonCount = applications?.filter((application) => application.stage === "won").length ?? 0;
  const activeCount = applications?.filter((a) => a.stage !== "won" && a.stage !== "lost").length ?? 0;
  const avgMatchScore =
    matches && matches.results.length > 0
      ? Math.round(matches.results.reduce((sum, m) => sum + m.score, 0) / matches.results.length)
      : 0;

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} sx={{ mb: 2 }}>
        Tableau de bord
      </Typography>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatCard label="Candidatures en cours" value={activeCount} />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatCard label="Candidatures gagnees" value={wonCount} />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatCard label="Score de match moyen (top 5)" value={`${avgMatchScore}%`} />
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 7 }}>
          <Paper variant="outlined" sx={{ p: 2.5 }}>
            <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1.5 }}>
              Pipeline par etape
            </Typography>
            {applicationsLoading ? (
              <LoadingState label="Chargement..." />
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={stageData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="stage" fontSize={12} interval={0} angle={-20} textAnchor="end" height={60} />
                  <YAxis allowDecimals={false} fontSize={12} />
                  <RechartsTooltip />
                  <Bar dataKey="count" fill="#1a56db" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, md: 5 }}>
          <Paper variant="outlined" sx={{ p: 2.5 }}>
            <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1.5 }}>
              Meilleurs matchs
            </Typography>
            {matchesLoading && <LoadingState label="Chargement..." />}
            {!matchesLoading && (!matches || matches.results.length === 0) && (
              <EmptyState title="Aucun match pour le moment" description="Ajoutez des competences a votre profil." />
            )}
            {!matchesLoading && matches && matches.results.length > 0 && (
              <List dense>
                {matches.results.map((result) => (
                  <ListItemButton
                    key={result.job.id}
                    onClick={() => navigate(`/jobs/${result.job.id}`)}
                    sx={{ borderRadius: 1, display: "flex", justifyContent: "space-between", gap: 1 }}
                  >
                    <ListItemText
                      primary={result.job.title}
                      secondary={result.job.seniority ?? undefined}
                      primaryTypographyProps={{ noWrap: true }}
                    />
                    <MatchScoreChip score={result.score} breakdown={result.breakdown} />
                  </ListItemButton>
                ))}
              </List>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
