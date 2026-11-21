"use client";

import { AuthProvider } from "@/lib/auth";
import { FilterProvider } from "@/lib/filters";
import { ThemeProvider } from "@/lib/theme";
import { ToastProvider } from "@/components/Toast";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <AuthProvider>
        <FilterProvider>
          <ToastProvider>{children}</ToastProvider>
        </FilterProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
