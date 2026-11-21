"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { useAuth } from "@/lib/auth";

const navItems = [
  { href: "/dashboard", label: "Overview" },
  { href: "/sales", label: "Sales Analytics" },
  { href: "/products", label: "Menu Analytics" },
  { href: "/outlets", label: "Outlet Performance" },
  { href: "/orders", label: "Order Analytics" },
  { href: "/payments", label: "Payment Analytics" },
  { href: "/data", label: "Data Management" },
  { href: "/datasets", label: "CSV datasets" },
  { href: "/analytics", label: "CSV charts" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="hidden w-56 shrink-0 lg:block">
      <nav className="sticky top-24 space-y-1">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={clsx(
              "block rounded-xl px-4 py-2.5 text-sm font-medium transition",
              pathname === item.href
                ? "bg-emerald-800 text-white"
                : "text-slate-600 hover:bg-white/80 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
            )}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      {user && (
        <div className="mt-8 rounded-xl border border-slate-200 bg-white/70 p-4 dark:border-slate-800 dark:bg-slate-900/70">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
            Signed in
          </p>
          <p className="mt-2 truncate text-sm font-medium text-slate-900 dark:text-white">
            {user.email}
          </p>
          <button
            type="button"
            onClick={logout}
            className="mt-3 text-xs font-semibold text-slate-600 underline-offset-2 hover:text-slate-900 hover:underline dark:text-slate-300"
          >
            Log out
          </button>
        </div>
      )}
    </aside>
  );
}
