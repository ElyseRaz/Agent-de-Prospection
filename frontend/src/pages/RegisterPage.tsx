import { useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Alert from "@mui/material/Alert";
import Paper from "@mui/material/Paper";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import RadarIcon from "@mui/icons-material/Radar";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import { useLogin, useRegister } from "../hooks/useAuth";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const register = useRegister();
  const login = useLogin();
  const navigate = useNavigate();

  const passwordsMismatch = confirmPassword.length > 0 && password !== confirmPassword;

  const handleSubmit = () => {
    register.mutate(
      { email, password },
      {
        onSuccess: () => {
          login.mutate({ email, password }, { onSuccess: () => navigate("/", { replace: true }) });
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
          Creez votre compte pour commencer a suivre les offres remote.
        </Typography>
        {register.isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Impossible de creer le compte (email deja utilise ?).
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
            helperText="8 caracteres minimum"
            fullWidth
          />
          <TextField
            label="Confirmer le mot de passe"
            type="password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            error={passwordsMismatch}
            helperText={passwordsMismatch ? "Les mots de passe ne correspondent pas" : " "}
            fullWidth
            onKeyDown={(event) => {
              if (event.key === "Enter" && !passwordsMismatch) handleSubmit();
            }}
          />
          <Button
            variant="contained"
            size="large"
            onClick={handleSubmit}
            disabled={
              !email || password.length < 8 || passwordsMismatch || register.isPending || login.isPending
            }
          >
            {register.isPending || login.isPending ? (
              <CircularProgress size={22} color="inherit" />
            ) : (
              "Creer mon compte"
            )}
          </Button>
        </Box>
        <Typography variant="body2" sx={{ mt: 3, textAlign: "center" }}>
          Deja inscrit ? <RouterLink to="/login">Se connecter</RouterLink>
        </Typography>
      </Paper>
    </Box>
  );
}
