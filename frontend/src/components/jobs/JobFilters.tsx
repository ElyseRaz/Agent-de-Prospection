import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import InputAdornment from "@mui/material/InputAdornment";
import SearchIcon from "@mui/icons-material/Search";
import Button from "@mui/material/Button";
import ClearIcon from "@mui/icons-material/Clear";
import type { ContractType, JobSearchFilters, RemoteType, SeniorityLevel } from "../../api/types";

interface JobFiltersProps {
  filters: JobSearchFilters;
  onChange: (filters: JobSearchFilters) => void;
}

const SENIORITY_OPTIONS: { value: SeniorityLevel; label: string }[] = [
  { value: "junior", label: "Junior" },
  { value: "intermediate", label: "Intermediaire" },
  { value: "senior", label: "Senior" },
  { value: "lead", label: "Lead" },
  { value: "expert", label: "Expert" },
];

const REMOTE_OPTIONS: { value: RemoteType; label: string }[] = [
  { value: "full_remote", label: "Full remote" },
  { value: "remote_zone_restricted", label: "Remote (zone restreinte)" },
  { value: "hybrid", label: "Hybride" },
  { value: "onsite", label: "Sur site" },
];

const CONTRACT_OPTIONS: { value: ContractType; label: string }[] = [
  { value: "freelance", label: "Freelance" },
  { value: "cdi", label: "CDI" },
  { value: "mission", label: "Mission" },
];

const SORT_OPTIONS: { value: NonNullable<JobSearchFilters["sort"]>; label: string }[] = [
  { value: "relevance", label: "Pertinence" },
  { value: "freshness", label: "Plus recent" },
  { value: "rate", label: "TJM" },
];

export default function JobFilters({ filters, onChange }: JobFiltersProps) {
  const set = <K extends keyof JobSearchFilters>(key: K, value: JobSearchFilters[K]) => {
    onChange({ ...filters, [key]: value, offset: 0 });
  };

  const hasActiveFilters =
    Boolean(filters.q) ||
    Boolean(filters.rate_min_eur) ||
    Boolean(filters.rate_max_eur) ||
    Boolean(filters.seniority) ||
    Boolean(filters.remote_type) ||
    Boolean(filters.contract_type);

  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5, alignItems: "center" }}>
      <TextField
        size="small"
        placeholder="Rechercher un poste, une techno..."
        value={filters.q ?? ""}
        onChange={(event) => set("q", event.target.value || undefined)}
        sx={{ minWidth: 260, flexGrow: 1 }}
        slotProps={{
          input: {
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          },
        }}
      />
      <TextField
        size="small"
        label="TJM min (EUR)"
        type="number"
        value={filters.rate_min_eur ?? ""}
        onChange={(event) => set("rate_min_eur", event.target.value || undefined)}
        sx={{ width: 140 }}
      />
      <TextField
        size="small"
        label="TJM max (EUR)"
        type="number"
        value={filters.rate_max_eur ?? ""}
        onChange={(event) => set("rate_max_eur", event.target.value || undefined)}
        sx={{ width: 140 }}
      />
      <TextField
        size="small"
        select
        label="Seniorite"
        value={filters.seniority ?? ""}
        onChange={(event) => set("seniority", (event.target.value || undefined) as SeniorityLevel | undefined)}
        sx={{ width: 160 }}
      >
        <MenuItem value="">Toutes</MenuItem>
        {SENIORITY_OPTIONS.map((option) => (
          <MenuItem key={option.value} value={option.value}>
            {option.label}
          </MenuItem>
        ))}
      </TextField>
      <TextField
        size="small"
        select
        label="Remote"
        value={filters.remote_type ?? ""}
        onChange={(event) => set("remote_type", (event.target.value || undefined) as RemoteType | undefined)}
        sx={{ width: 190 }}
      >
        <MenuItem value="">Tous</MenuItem>
        {REMOTE_OPTIONS.map((option) => (
          <MenuItem key={option.value} value={option.value}>
            {option.label}
          </MenuItem>
        ))}
      </TextField>
      <TextField
        size="small"
        select
        label="Contrat"
        value={filters.contract_type ?? ""}
        onChange={(event) => set("contract_type", (event.target.value || undefined) as ContractType | undefined)}
        sx={{ width: 150 }}
      >
        <MenuItem value="">Tous</MenuItem>
        {CONTRACT_OPTIONS.map((option) => (
          <MenuItem key={option.value} value={option.value}>
            {option.label}
          </MenuItem>
        ))}
      </TextField>
      <TextField
        size="small"
        select
        label="Tri"
        value={filters.sort ?? "relevance"}
        onChange={(event) => set("sort", event.target.value as JobSearchFilters["sort"])}
        sx={{ width: 150 }}
      >
        {SORT_OPTIONS.map((option) => (
          <MenuItem key={option.value} value={option.value}>
            {option.label}
          </MenuItem>
        ))}
      </TextField>
      {hasActiveFilters && (
        <Button
          size="small"
          startIcon={<ClearIcon />}
          onClick={() =>
            onChange({
              sort: filters.sort,
              limit: filters.limit,
              offset: 0,
            })
          }
        >
          Reinitialiser
        </Button>
      )}
    </Box>
  );
}
