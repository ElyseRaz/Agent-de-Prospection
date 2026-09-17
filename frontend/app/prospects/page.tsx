"use client";

import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/layout/app-shell";
import { ComingSoon } from "@/components/layout/coming-soon";

export default function ProspectsPage() {
  return (
    <AuthGuard>
      <AppShell>
        <ComingSoon title="Prospects" phase="Phase 2 (CRM de prospection)" />
      </AppShell>
    </AuthGuard>
  );
}
