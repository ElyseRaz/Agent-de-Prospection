"use client";

import { Users, Mail, TrendingUp, Target } from "lucide-react";
import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const STATS = [
  { label: "Prospects actifs", value: "0", icon: Users },
  { label: "Emails envoyes ce mois", value: "0", icon: Mail },
  { label: "Taux de reponse", value: "—", icon: TrendingUp },
  { label: "Conversions", value: "0", icon: Target },
];

export default function DashboardPage() {
  return (
    <AuthGuard>
      <AppShell>
        <div className="mx-auto flex max-w-6xl flex-col gap-6">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Tableau de bord</h1>
            <p className="text-muted-foreground">
              Vue d&apos;ensemble de ta prospection commerciale.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {STATS.map((stat) => {
              const Icon = stat.icon;
              return (
                <Card key={stat.label}>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      {stat.label}
                    </CardTitle>
                    <Icon className="size-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{stat.value}</div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Prochaines etapes</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Le socle (authentification, structure de l&apos;application) est en place. Les
              prospects, l&apos;enrichissement IA et les campagnes email arrivent dans les
              phases suivantes.
            </CardContent>
          </Card>
        </div>
      </AppShell>
    </AuthGuard>
  );
}
