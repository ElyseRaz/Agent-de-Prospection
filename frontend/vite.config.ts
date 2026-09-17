import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En dev (conteneur `frontend` du docker-compose), on proxie /api et /health
// vers le service `api` du reseau Docker interne, pour que le serveur Vite
// fonctionne de la meme facon qu'en passant par Nginx (meme chemins relatifs
// cote client, aucune configuration de CORS a gerer).
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: "http://api:8000",
        changeOrigin: true,
      },
      "/health": {
        target: "http://api:8000",
        changeOrigin: true,
      },
    },
  },
});
