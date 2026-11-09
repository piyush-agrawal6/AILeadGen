"use client";

import { QueryClient,QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider as NextThemesProvider } from "next-themes";
import * as React from "react";
import { Toaster } from "sonner";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = React.useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 20000,
            gcTime: 300000,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <NextThemesProvider attribute="class" defaultTheme="light" storageKey="heysow-theme" enableSystem>
      <QueryClientProvider client={queryClient}>
        {children}
        <Toaster position="bottom-right" richColors />
      </QueryClientProvider>
    </NextThemesProvider>
  );
}
