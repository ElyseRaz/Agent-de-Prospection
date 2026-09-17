"use client";

import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/layout/app-shell";
import { ComingSoon } from "@/components/layout/coming-soon";

export default function CampaignsPage() {
  return (
    <AuthGuard>
      <AppShell>
        <ComingSoon title="Campagnes" phase="Phase 4 (campagnes email)" />
      </AppShell>
    </AuthGuard>
  );
}
