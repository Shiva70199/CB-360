"use client";

import type { ReactNode } from "react";
import { AuthLoadingShell } from "@/lib/auth";
import { Navbar } from "./Navbar";
import { Sidebar } from "./Sidebar";

interface LayoutShellProps {
  children: ReactNode;
  withSidebar?: boolean;
}

export function LayoutShell({ children, withSidebar = false }: LayoutShellProps) {
  const content = (
    <div className="flex min-h-screen flex-col bg-slate-50 dark:bg-slate-950">
      <Navbar />
      <div className="mx-auto flex w-full max-w-6xl flex-1 gap-8 px-4 pb-16 pt-10 sm:px-6 lg:px-8">
        {withSidebar && <Sidebar />}
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );

  if (withSidebar) {
    return <AuthLoadingShell>{content}</AuthLoadingShell>;
  }

  return content;
}
