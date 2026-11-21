"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { AuthLoadingShell, useAuth, useRequireAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";
import { FilterBar } from "./FilterBar";
import { BrandMark } from "@/components/BrandMark";

const NAV = [
  { href: "/dashboard", label: "Overview", icon: "▣" },
  { href: "/sales", label: "Sales Analytics", icon: "↗" },
  { href: "/products", label: "Menu Analytics", icon: "▤" },
  { href: "/outlets", label: "Outlet Performance", icon: "⌂" },
  { href: "/orders", label: "Order Analytics", icon: "☰" },
  { href: "/payments", label: "Payment Analytics", icon: "₹" },
  { href: "/data", label: "Data Management", icon: "⇪" },
];

export function DashboardFrame({
  title,
  subtitle,
  children,
  showFilters = true,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  showFilters?: boolean;
}) {
  useRequireAuth();
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  return (
    <AuthLoadingShell>
      <div className="flex min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
        <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col bg-[#10261c] text-slate-100 lg:flex">
          <div className="border-b border-white/10 px-5 py-5">
            <div className="flex items-center gap-3">
              <span className="rounded-md bg-white/95 p-1">
                <BrandMark height={40} />
              </span>
              <div>
                <p className="text-sm font-semibold tracking-tight">CB 360</p>
                <p className="text-[11px] text-emerald-200/80">Business Intelligence</p>
              </div>
            </div>
            <div className="mt-4 rounded-xl bg-white/5 px-3 py-3">
              <p className="text-xs font-semibold text-emerald-50">California Burrito Analytics</p>
              <p className="mt-1 text-[11px] leading-snug text-emerald-100/70">
                Restaurant Operations & Business Intelligence
              </p>
            </div>
          </div>
          <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition",
                  pathname === item.href
                    ? "bg-emerald-700 text-white shadow-lg shadow-emerald-950/40"
                    : "text-slate-300 hover:bg-white/5 hover:text-white"
                )}
              >
                <span className="w-4 text-center text-xs opacity-80">{item.icon}</span>
                {item.label}
              </Link>
            ))}
          </nav>
          <div className="border-t border-white/10 p-4">
            <p className="truncate text-xs text-slate-400">{user?.email}</p>
            <button
              type="button"
              onClick={logout}
              className="mt-2 text-xs font-semibold text-emerald-300 hover:text-emerald-200"
            >
              Log out
            </button>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/90 backdrop-blur dark:border-slate-800 dark:bg-slate-900/90">
            <div className="flex items-center justify-between gap-4 px-4 py-4 sm:px-6">
              <div>
                <h1 className="text-lg font-bold tracking-tight text-slate-900 dark:text-white sm:text-xl">
                  {title}
                </h1>
                {subtitle && (
                  <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={toggleTheme}
                  className="bi-btn-secondary"
                  aria-label="Toggle theme"
                >
                  {theme === "dark" ? "Light" : "Dark"}
                </button>
                <button type="button" onClick={logout} className="bi-btn-secondary lg:hidden">
                  Log out
                </button>
              </div>
            </div>
            <nav className="flex gap-1 overflow-x-auto px-4 pb-3 lg:hidden">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={clsx(
                    "whitespace-nowrap rounded-full px-3 py-1.5 text-xs font-semibold",
                    pathname === item.href
                      ? "bg-emerald-800 text-white"
                      : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                  )}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </header>

          <main className="mx-auto w-full max-w-7xl flex-1 space-y-5 px-4 py-6 sm:px-6">
            {showFilters && <FilterBar />}
            {children}
          </main>
        </div>
      </div>
    </AuthLoadingShell>
  );
}
