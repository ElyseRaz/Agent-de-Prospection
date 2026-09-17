import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Snackbar from "@mui/material/Snackbar";
import Alert from "@mui/material/Alert";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Grid from "@mui/material/Grid2";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import {
  useCreateProfile,
  useDeleteProfile,
  useProfile,
  useProfiles,
  useSetProfileSkills,
  useUpdateProfile,
} from "../hooks/useProfiles";
import { useAuthStore } from "../store/authStore";
import LoadingState from "../components/common/LoadingState";
import EmptyState from "../components/common/EmptyState";
import type { ProfileSkillInput, SkillLevel } from "../api/types";

const SKILL_LEVELS: SkillLevel[] = ["beginner", "intermediate", "advanced", "expert"];

export default function ProfilePage() {
  const { data: profiles, isLoading } = useProfiles();
  const activeProfileId = useAuthStore((s) => s.activeProfileId);
  const setActiveProfileId = useAuthStore((s) => s.setActiveProfileId);
  const [selectedId, setSelectedId] = useState<string | null>(activeProfileId);
  const createProfile = useCreateProfile();
  const deleteProfile = useDeleteProfile();
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedId && profiles && profiles.length > 0) {
      setSelectedId(profiles[0].id);
    }
  }, [profiles, selectedId]);

  const handleCreate = () => {
    createProfile.mutate(
      { name: "Nouveau profil" },
      {
        onSuccess: (profile) => {
          setSelectedId(profile.id);
          setFeedback("Profil cree.");
        },
      },
    );
  };

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} sx={{ mb: 2 }}>
        Profils de recherche
      </Typography>
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Paper variant="outlined" sx={{ p: 1.5 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
              <Typography variant="subtitle2">Mes profils</Typography>
              <IconButton size="small" onClick={handleCreate} aria-label="Creer un profil">
                <AddIcon fontSize="small" />
              </IconButton>
            </Stack>
            {isLoading && <LoadingState label="Chargement..." />}
            {!isLoading && (!profiles || profiles.length === 0) && (
              <EmptyState title="Aucun profil" actionLabel="Creer un profil" onAction={handleCreate} />
            )}
            <List dense>
              {profiles?.map((profile) => (
                <ListItemButton
                  key={profile.id}
                  selected={profile.id === selectedId}
                  onClick={() => setSelectedId(profile.id)}
                  sx={{ borderRadius: 1 }}
                >
                  <ListItemText
                    primary={profile.name}
                    secondary={profile.id === activeProfileId ? "Profil actif" : undefined}
                  />
                </ListItemButton>
              ))}
            </List>
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, md: 8 }}>
          {selectedId ? (
            <ProfileEditor
              profileId={selectedId}
              isActive={selectedId === activeProfileId}
              onActivate={() => setActiveProfileId(selectedId)}
              onDelete={() => {
                deleteProfile.mutate(selectedId, {
                  onSuccess: () => {
                    setSelectedId(null);
                    setFeedback("Profil supprime.");
                  },
                });
              }}
              onSaved={() => setFeedback("Profil enregistre.")}
            />
          ) : (
            <EmptyState title="Selectionnez ou creez un profil" />
          )}
        </Grid>
      </Grid>
      <Snackbar
        open={Boolean(feedback)}
        autoHideDuration={2500}
        onClose={() => setFeedback(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        {feedback ? <Alert severity="success">{feedback}</Alert> : undefined}
      </Snackbar>
    </Box>
  );
}

function ProfileEditor({
  profileId,
  isActive,
  onActivate,
  onDelete,
  onSaved,
}: {
  profileId: string;
  isActive: boolean;
  onActivate: () => void;
  onDelete: () => void;
  onSaved: () => void;
}) {
  const { data: profile, isLoading } = useProfile(profileId);
  const updateProfile = useUpdateProfile(profileId);
  const setSkills = useSetProfileSkills(profileId);

  const [name, setName] = useState("");
  const [targetRate, setTargetRate] = useState("");
  const [floorRate, setFloorRate] = useState("");
  const [timezone, setTimezone] = useState("");
  const [skills, setSkillsState] = useState<ProfileSkillInput[]>([]);

  useEffect(() => {
    if (profile) {
      setName(profile.name);
      setTargetRate(profile.target_rate ?? "");
      setFloorRate(profile.floor_rate ?? "");
      setTimezone(profile.timezone ?? "");
      setSkillsState(
        profile.skills.map((skill) => ({
          skill_slug: skill.skill_slug,
          level: skill.level,
          years: skill.years,
          is_required: skill.is_required,
        })),
      );
    }
  }, [profile]);

  if (isLoading || !profile) return <LoadingState label="Chargement du profil..." />;

  const handleSaveDetails = () => {
    updateProfile.mutate(
      {
        name,
        target_rate: targetRate || null,
        floor_rate: floorRate || null,
        timezone: timezone || null,
      },
      { onSuccess: onSaved },
    );
  };

  const handleAddSkill = () => {
    setSkillsState((prev) => [...prev, { skill_slug: "", level: "intermediate", is_required: false }]);
  };

  const handleSkillChange = (index: number, patch: Partial<ProfileSkillInput>) => {
    setSkillsState((prev) => prev.map((skill, i) => (i === index ? { ...skill, ...patch } : skill)));
  };

  const handleRemoveSkill = (index: number) => {
    setSkillsState((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSaveSkills = () => {
    setSkills.mutate(skills.filter((skill) => skill.skill_slug.trim().length > 0), { onSuccess: onSaved });
  };

  return (
    <Paper variant="outlined" sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="subtitle1" fontWeight={600}>
          Details du profil
        </Typography>
        <Stack direction="row" spacing={1}>
          {!isActive && (
            <Button size="small" onClick={onActivate}>
              Activer ce profil
            </Button>
          )}
          {isActive && <Chip size="small" color="primary" label="Actif" />}
          <IconButton size="small" color="error" onClick={onDelete} aria-label="Supprimer le profil">
            <DeleteOutlineIcon fontSize="small" />
          </IconButton>
        </Stack>
      </Stack>
      <Stack spacing={2}>
        <TextField label="Nom du profil" size="small" value={name} onChange={(e) => setName(e.target.value)} />
        <Stack direction="row" spacing={2}>
          <TextField
            label="TJM cible"
            size="small"
            value={targetRate}
            onChange={(e) => setTargetRate(e.target.value)}
            fullWidth
          />
          <TextField
            label="TJM plancher"
            size="small"
            value={floorRate}
            onChange={(e) => setFloorRate(e.target.value)}
            fullWidth
          />
        </Stack>
        <TextField
          label="Fuseau horaire"
          size="small"
          value={timezone}
          onChange={(e) => setTimezone(e.target.value)}
          placeholder="Europe/Paris"
        />
        <Box>
          <Button variant="contained" onClick={handleSaveDetails} disabled={updateProfile.isPending}>
            Enregistrer les details
          </Button>
        </Box>
      </Stack>

      <Divider sx={{ my: 3 }} />

      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
        <Typography variant="subtitle1" fontWeight={600}>
          Competences
        </Typography>
        <IconButton size="small" onClick={handleAddSkill} aria-label="Ajouter une competence">
          <AddIcon fontSize="small" />
        </IconButton>
      </Stack>
      <Stack spacing={1.5}>
        {skills.map((skill, index) => (
          <Stack key={index} direction="row" spacing={1.5} alignItems="center">
            <TextField
              size="small"
              label="Competence"
              value={skill.skill_slug}
              onChange={(e) => handleSkillChange(index, { skill_slug: e.target.value })}
              sx={{ flexGrow: 1 }}
            />
            <TextField
              size="small"
              select
              label="Niveau"
              value={skill.level}
              onChange={(e) => handleSkillChange(index, { level: e.target.value as SkillLevel })}
              sx={{ width: 150 }}
            >
              {SKILL_LEVELS.map((level) => (
                <MenuItem key={level} value={level}>
                  {level}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              size="small"
              label="Requis"
              select
              value={skill.is_required ? "yes" : "no"}
              onChange={(e) => handleSkillChange(index, { is_required: e.target.value === "yes" })}
              sx={{ width: 110 }}
            >
              <MenuItem value="no">Optionnel</MenuItem>
              <MenuItem value="yes">Requis</MenuItem>
            </TextField>
            <IconButton size="small" onClick={() => handleRemoveSkill(index)} aria-label="Retirer">
              <DeleteOutlineIcon fontSize="small" />
            </IconButton>
          </Stack>
        ))}
        {skills.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            Aucune competence renseignee.
          </Typography>
        )}
      </Stack>
      <Box sx={{ mt: 2 }}>
        <Button variant="outlined" onClick={handleSaveSkills} disabled={setSkills.isPending}>
          Enregistrer les competences
        </Button>
      </Box>
    </Paper>
  );
}
