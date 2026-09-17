import { createTheme } from "@mui/material/styles";
import { frFR } from "@mui/material/locale";

export const theme = createTheme(
  {
    palette: {
      mode: "light",
      primary: { main: "#1a56db" },
      secondary: { main: "#7c3aed" },
      success: { main: "#0d9488" },
      warning: { main: "#d97706" },
      error: { main: "#dc2626" },
      background: { default: "#f5f6f8", paper: "#ffffff" },
    },
    shape: { borderRadius: 8 },
    typography: {
      fontFamily: [
        "Inter",
        "-apple-system",
        "BlinkMacSystemFont",
        "Segoe UI",
        "Roboto",
        "Helvetica",
        "Arial",
        "sans-serif",
      ].join(","),
    },
    components: {
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: { root: { textTransform: "none" } },
      },
      MuiAppBar: {
        defaultProps: { color: "inherit", elevation: 0 },
        styleOverrides: { root: { borderBottom: "1px solid #e5e7eb" } },
      },
    },
  },
  frFR,
);
