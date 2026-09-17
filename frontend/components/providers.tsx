"use client";

import { useRouter } from "next/navigation";
import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-aria-components";
import { queryClient } from "@/lib/query-client";

declare module "react-aria-components" {
  interface RouterConfig {
    routerOptions: NonNullable<Parameters<ReturnType<typeof useRouter>["push"]>[1]>;
  }
}

export function Providers({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  return (
    <RouterProvider navigate={router.push}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </RouterProvider>
  );
}
