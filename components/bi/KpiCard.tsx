"use client";

import clsx from "clsx";

interface KpiCardProps {
  label: string;
  value: string;
  hint?: string;
  growthPct?: number | null;
  accent?: "blue" | "orange" | "slate";
  loading?: boolean;
}

export function KpiCard({
  label,
  value,
  hint,
  growthPct,
  accent = "blue",
  loading,
}: KpiCardProps) {
  if (loading) {
    return <div className="bi-card h-28 animate-pulse bg-slate-200/70 dark:bg-slate-800" />;
  }

  const accentBar =
    accent === "orange" ? "bg-emerald-400" : accent === "slate" ? "bg-slate-400" : "bg-emerald-800";

  return (
    <div className="bi-card relative overflow-hidden p-5">
      <span className={clsx("absolute inset-y-0 left-0 w-1", accentBar)} />
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">
        {label}
      </p>
      <p className="mt-3 text-2xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-3xl">
        {value}
      </p>
      <div className="mt-2 flex items-center gap-2 text-xs">
        {growthPct !== null && growthPct !== undefined ? (
          <span
            className={clsx(
              "font-semibold",
              growthPct >= 0 ? "text-emerald-600" : "text-rose-600"
            )}
          >
            {growthPct >= 0 ? "+" : ""}
            {growthPct.toFixed(1)}% vs prior
          </span>
        ) : hint ? (
          <span className="text-slate-500 dark:text-slate-400">{hint}</span>
        ) : null}
      </div>
    </div>
  );
}
