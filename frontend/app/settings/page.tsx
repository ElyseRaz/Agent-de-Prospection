"use client";

import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/layout/app-shell";
import { ComingSoon } from "@/components/layout/coming-soon";

export default function SettingsPage() {
  return (
    <AuthGuard>
      <AppShell>
        <ComingSoon title="Parametres" phase="Phase 3 (cles API Trustpilot/Groq, SMTP)" />
      </AppShell>
    </AuthGuard>
  );
}
