import { useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Alert from "@mui/material/Alert";
import Paper from "@mui/material/Paper";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import RadarIcon from "@mui/icons-material/Radar";
import { Link as RouterLink, useLocation, useNavigate } from "react-router-dom";
import { useLogin } from "../hooks/useAuth";
import { ApiError } from "../api/client";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [needsTotp, setNeedsTotp] = useState(false);
  const login = useLogin();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as { from?: string } | null)?.from ?? "/";

  const handleSubmit = () => {
    login.mutate(
      { email, password, totp_code: totpCode || undefined },
      {
        onSuccess: () => navigate(from, { replace: true }),
        onError: (error) => {
          if (error instanceof ApiError && error.status === 401 && !needsTotp) {
            setNeedsTotp(true);
          }
        },
      },
    );
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "background.default",
        p: 2,
      }}
    >
      <Paper variant="outlined" sx={{ p: 4, width: 380 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 3 }}>
          <RadarIcon color="primary" fontSize="large" />
          <Typography variant="h5" fontWeight={700}>
            RemoteRadar
          </Typography>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Connectez-vous pour retrouver vos offres et votre pipeline.
        </Typography>
        {login.isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {needsTotp ? "Code d'authentification requis ou invalide." : "Identifiants invalides."}
          </Alert>
        )}
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <TextField
            label="Email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoFocus
            fullWidth
          />
          <TextField
            label="Mot de passe"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            fullWidth
            onKeyDown={(event) => {
              if (event.key === "Enter" && !needsTotp) handleSubmit();
            }}
          />
          {needsTotp && (
            <TextField
              label="Code 2FA"
              value={totpCode}
              onChange={(event) => setTotpCode(event.target.value)}
              fullWidth
            />
          )}
          <Button
            variant="contained"
            size="large"
            onClick={handleSubmit}
            disabled={!email || !password || login.isPending}
          >
            {login.isPending ? <CircularProgress size={22} color="inherit" /> : "Se connecter"}
          </Button>
        </Box>
        <Typography variant="body2" sx={{ mt: 3, textAlign: "center" }}>
          Pas encore de compte ? <RouterLink to="/register">Creer un compte</RouterLink>
        </Typography>
      </Paper>
    </Box>
  );
}
