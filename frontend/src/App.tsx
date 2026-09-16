import { useEffect, useState } from "react";

type HealthStatus = {
  status: string;
  db: string;
};

type FetchState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "success"; data: HealthStatus };

export default function App() {
  const [state, setState] = useState<FetchState>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    fetch("/health", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Statut HTTP ${response.status}`);
        }
        return response.json() as Promise<HealthStatus>;
      })
      .then((data) => setState({ kind: "success", data }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setState({
          kind: "error",
          message: error instanceof Error ? error.message : "Erreur inconnue",
        });
      });

    return () => controller.abort();
  }, []);

  return (
    <main style={{ fontFamily: "sans-serif", padding: "2rem" }}>
      <h1>RemoteRadar</h1>
      <p>Phase 1 — socle backend/infra.</p>
      {state.kind === "loading" && <p>Verification de la connexion API...</p>}
      {state.kind === "error" && (
        <p style={{ color: "crimson" }}>Echec de connexion a l&apos;API : {state.message}</p>
      )}
      {state.kind === "success" && (
        <p style={{ color: "green" }}>
          API en ligne — statut: {state.data.status}, base de donnees: {state.data.db}
        </p>
      )}
    </main>
  );
}
