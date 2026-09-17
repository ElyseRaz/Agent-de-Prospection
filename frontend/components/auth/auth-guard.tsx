"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { LoadingIndicator } from "@/components/application/loading-indicator/loading-indicator";
import { useAuthStore } from "@/store/auth-store";

/** Protection cote client : attend l'hydratation du store persiste avant de
 * decider, pour ne jamais rediriger un utilisateur deja connecte pendant le
 * court instant ou le localStorage n'est pas encore lu (SSR -> hydration). */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const hasHydrated = useAuthStore((s) => s.hasHydrated);
  const accessToken = useAuthStore((s) => s.accessToken);
  const router = useRouter();

  useEffect(() => {
    if (hasHydrated && !accessToken) {
      router.replace("/login");
    }
  }, [hasHydrated, accessToken, router]);

  if (!hasHydrated || !accessToken) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingIndicator type="line-spinner" size="md" />
      </div>
    );
  }

  return <>{children}</>;
}
