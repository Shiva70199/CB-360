"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { useAuth } from "@/lib/auth";
import { BrandMark } from "./BrandMark";

const publicPaths = ["/login", "/register", "/"];

export function Navbar() {
  const pathname = usePathname();
  const { logout, token } = useAuth();
  const isPublic = publicPaths.includes(pathname);

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/90">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
        <Link
          href={token ? "/dashboard" : "/"}
          className="flex items-center gap-3 transition hover:opacity-90"
        >
          <BrandMark height={36} />
          <span className="text-sm font-semibold tracking-tight text-slate-900 sm:text-base dark:text-white">
            CB <span className="text-emerald-800 dark:text-emerald-300">360</span>
          </span>
        </Link>

        <div className="flex items-center gap-3">
          {token && !isPublic && (
            <nav className="flex items-center gap-1 lg:hidden">
              {[
                { href: "/dashboard", label: "Home" },
                { href: "/data", label: "Data" },
                { href: "/sales", label: "Sales" },
              ].map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={clsx(
                    "rounded-full px-3 py-1.5 text-xs font-semibold transition",
                    pathname === item.href
                      ? "bg-slate-900 text-white"
                      : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                  )}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          )}

          {token ? (
            <button
              type="button"
              onClick={logout}
              className="hidden rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 sm:inline-flex dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
            >
              Log out
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                href="/login"
                className="rounded-full px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:text-slate-900 dark:text-slate-300"
              >
                Log in
              </Link>
              <Link
                href="/register"
                className="rounded-full border border-emerald-800 bg-emerald-800 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-emerald-700 hover:border-emerald-700"
              >
                Sign up
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
